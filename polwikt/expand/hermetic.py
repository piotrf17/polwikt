"""Makes upstream expansion hermetic: no network, clock or randomness (R4.5, G5).

wikitextprocessor reaches outside the process in three ways at the pinned SHA, and each
is closed here by replacing the upstream entry point:

- **Wikidata.** `mw.wikibase.*`, the label/description lookups and `{{#statements}}`
  run live HTTP queries (and write their results into the page store's cache tables).
  Each entry point is replaced by a stub that counts the call on the Wtp and returns
  upstream's own "no data" answer. A session that raises on use is the backstop, so a
  path we missed fails loudly instead of reaching the network.
- **Interwiki map.** Upstream fetches it from the siteinfo API; the stub returns none
  (an empty map: `{{fullurl:}}` treats every prefix as local).
- **State across pages.** Upstream keeps some Wiktionary modules loaded across Lua
  resets; `Module:headword/page` caches the page title in one, so output depended on
  the previous page. Every reset now drops all `Module:` instances, as Scribunto does.
- **Clock.** Magic words (`{{CURRENTYEAR}}`) and `mw.language:formatDate` read
  `datetime.now()`, and Lua modules see `os.date`/`os.time`/`os.clock`. All of them read
  a fixed instant instead: midnight UTC on the dump date. Lua's own per-call timeout
  keeps the real clock; a timeout is an error, counted, never output.

The patches are process-wide and idempotent; `install()` runs before any Wtp is built.
"""

from __future__ import annotations

import os
import time
from collections import Counter
from datetime import UTC, datetime, tzinfo
from typing import Any

from wikitextprocessor import interwiki, luaexec, parserfns, wikidata

_installed = False


class NetworkAttemptError(RuntimeError):
    """Something tried to reach the network during expansion (R4.5)."""


def stats_of(wtp: Any) -> Counter[str]:
    """The per-Wtp counter the stubs write to; created on first use."""
    stats: Counter[str] | None = getattr(wtp, "hermetic_stats", None)
    if stats is None:
        stats = Counter()
        wtp.hermetic_stats = stats
    return stats


def epoch_of(wtp: Any) -> datetime:
    """The frozen 'now' for this Wtp, set from the dump date (default 2000-01-01)."""
    epoch: datetime | None = getattr(wtp, "epoch", None)
    return epoch or datetime(2000, 1, 1, tzinfo=UTC)


class _RaisingSession:
    """Stands in for upstream's requests.Session: any use is a bug in our stubs."""

    def close(self) -> None:
        """Upstream closes the session on close_db_conn(); that is not network use."""

    def __getattr__(self, name: str) -> Any:
        raise NetworkAttemptError(f"wikitextprocessor reached for the network ({name})")


def _counted(name: str, answer: Any) -> Any:
    def stub(wtp: Any, *args: Any, **kwargs: Any) -> Any:
        stats_of(wtp)[f"wikidata.{name}"] += 1
        return answer

    return stub


# Upstream's "no data" answers: an empty label/description, no entity id, no entity.
_WIKIDATA_STUBS = {
    "mw_wikibase_getlabel": (luaexec, ""),
    "mw_wikibase_getdescription": (luaexec, ""),
    "mw_wikibase_getEntityIdForCurrentPage": (luaexec, None),
    "mw_wikibase_getEntityIdForTitle": (luaexec, None),
    "mw_wikibase_getEntity": (wikidata, None),
    "mw_wikibase_getSitelink": (wikidata, None),
    "statement_query": (wikidata, ""),
}


class _FrozenDatetime(datetime):
    """`datetime` whose now() is the dump epoch; patched in where upstream calls it."""

    current: datetime = datetime(2000, 1, 1, tzinfo=UTC)

    @classmethod
    def now(cls, tz: tzinfo | None = None) -> _FrozenDatetime:
        moment = cls.current.astimezone(tz) if tz else cls.current.replace(tzinfo=None)
        return cls.combine(moment.date(), moment.timetz())


_FREEZE_LUA = """
function(env, epoch)
  local real_date, real_time = os.date, os.time
  env.os = {
    clock = function() return 0 end,
    difftime = os.difftime,
    time = function(t) if t ~= nil then return real_time(t) end return epoch end,
    date = function(fmt, t)
      fmt = fmt or "%c"
      if fmt:sub(1, 1) ~= "!" then fmt = "!" .. fmt end
      return real_date(fmt, t or epoch)
    end,
  }
  if env.math ~= nil and env.math.randomseed ~= nil then env.math.randomseed(0) end
  -- Upstream keeps some Wiktionary modules loaded across resets for speed; one of
  -- them caches the page title (Module:headword/page), so a page's output depended on
  -- the page before it. Scribunto gives every #invoke fresh modules: so do we.
  for name, _ in pairs(package.loaded) do
    if type(name) == "string" and name:sub(1, 7) == "Module:" then
      package.loaded[name] = nil
    end
  end
end
"""


def _freeze_lua_env(wtp: Any) -> None:
    """After each env reset: frozen `os`, seeded `math.random`, no retained modules."""
    lua = wtp.lua
    env = lua.eval("getfenv")(wtp.lua_invoke)
    lua.eval(_FREEZE_LUA)(env, int(epoch_of(wtp).timestamp()))


def install() -> None:
    """Applies every patch once per process."""
    global _installed
    if _installed:
        return
    # Local-time formatting (astimezone(), os.date without "!") must not depend on the
    # machine running the pipeline.
    os.environ["TZ"] = "UTC"
    time.tzset()

    for name, (module, answer) in _WIKIDATA_STUBS.items():
        if not hasattr(module, name):
            raise RuntimeError(f"upstream moved {module.__name__}.{name}; recheck R4.5")
        setattr(module, name, _counted(name, answer))

    def no_session(wtp: Any) -> None:
        wtp.wikidata_session = _RaisingSession()

    wikidata.init_wikidata_session = no_session
    interwiki.get_interwiki_data = lambda wtp: []

    for module in (parserfns, luaexec):
        if getattr(module, "datetime", None) is not datetime:
            raise RuntimeError(f"{module.__name__} no longer imports datetime; recheck")
        module.datetime = _FrozenDatetime  # type: ignore[attr-defined]

    original_set_functions = luaexec.call_set_functions

    def set_functions_then_freeze(ctx: Any, set_functions: Any) -> None:
        original_set_functions(ctx, set_functions)
        _freeze_lua_env(ctx)

    luaexec.call_set_functions = set_functions_then_freeze
    _installed = True


def use_epoch(wtp: Any, epoch: datetime) -> None:
    """Points the frozen clock at `epoch` for this Wtp (one Wtp per process, R3.10)."""
    wtp.epoch = epoch
    _FrozenDatetime.current = epoch
    wtp.wikidata_session = _RaisingSession()


__all__ = [
    "NetworkAttemptError",
    "epoch_of",
    "install",
    "stats_of",
    "use_epoch",
]
