"""The pipeline's Wtp: upstream's, made hermetic and title-aware (R3.2a, R4.5).

On top of `wikitextprocessor.Wtp` this adds:

- **Existence from `all_titles`.** P1 keeps only Polish ns-0 pages, so upstream's
  `get_page` would call every other page a red link. A miss in `pages` falls back to
  the title-only table and returns a body-less page, so `{{#ifexist:}}`, Lua `.exists`
  and redirect info are right.
- **`getContent()` on a title-only page** returns upstream's `nil` ("no such page"),
  which modules handle (`Module:etymon` renders the link and stops the chain), and is
  counted with the title listed in `title_only_reads`, never silent (R3.2a).
  Transcluding one renders empty, counted.
- **A lookup recorder**: every page lookup, and which rows answered it, so the golden
  snapshot can hold exactly what expansion touched (R3.8a, R8.1a).
- **Virtual modules**: Lua source registered in Python (`virtual_modules`) and served
  to `{{#invoke:}}` without touching the store, for reading Wiktionary's data modules
  inside a real frame (expand/lua_data.py).
- **Strict snapshot mode**: opened on a snapshot store, a lookup the snapshot did not
  record is listed in `stale_lookups` — the snapshot needs regenerating.
"""

from __future__ import annotations

import re
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wikitextprocessor import Page, Wtp

from polwikt.expand import hermetic

# `model` of the body-less Page returned for a title known only from all_titles.
TITLE_ONLY = "polwikt:title-only"

# en.wiktionary's link trail: [[kot]]y renders as one link "koty" only for [a-z].
_LINKTRAIL = re.compile(r"(?s)([a-z]+)(.*)")

LookupKey = tuple[str, int | None, bool]


class PolwiktWtp(Wtp):
    """Upstream's Wtp over a P1 store or golden snapshot; one per worker (R3.10)."""

    def __init__(self, db_path: Path, *, record: bool = False) -> None:
        hermetic.install()
        super().__init__(db_path=db_path, lang_code="en", quiet=True)
        self.linktrailing_re = _LINKTRAIL
        self.stats: Counter[str] = hermetic.stats_of(self)
        hermetic.use_epoch(self, _dump_epoch(self.db_conn))
        # Upstream's process_dump would fetch this from the live API (R4.5): empty.
        self.db_conn.execute(
            "CREATE TEMP TABLE IF NOT EXISTS interwiki_maps "
            "(prefix TEXT PRIMARY KEY, url TEXT, protorel INTEGER, local INTEGER)"
        )
        self.record = record
        self.lookups: set[LookupKey] = set()
        self.found_pages: set[tuple[str, int]] = set()
        self.found_titles: set[tuple[str, int]] = set()
        self.stale_lookups: set[LookupKey] = set()
        self.title_only_reads: set[str] = set()
        self.virtual_modules: dict[str, str] = {}
        # Per-worker caches of what extraction derives from Wiktionary data (labels).
        self.extract_cache: dict[str, Any] = {}
        self._snapshot_lookups = _snapshot_lookups(self.db_conn)
        self._title_cache: dict[LookupKey, Page | None] = {}

    @property
    def is_snapshot(self) -> bool:
        return self._snapshot_lookups is not None

    def get_page(  # type: ignore[override]  # upstream's is an lru_cache wrapper
        self,
        title: str,
        namespace_id: int | None = None,
        no_redirect: bool = False,
    ) -> Page | None:
        key = (title, namespace_id, no_redirect)
        if self.record:
            self.lookups.add(key)
        if self._snapshot_lookups is not None and key not in self._snapshot_lookups:
            self.stale_lookups.add(key)
        page: Page | None = super().get_page(title, namespace_id, no_redirect)
        if page is not None:
            if self.record:
                self.found_pages.add((page.title, page.namespace_id))
            return page
        page = self._title_only(key)
        if page is not None and self.record:
            self.found_titles.add((page.title, page.namespace_id))
        return page

    def get_page_body(self, title: str, namespace_id: int | None) -> str | None:
        if (virtual := self.virtual_modules.get(title)) is not None:
            return virtual
        page = self.get_page_resolve_redirect(title, namespace_id)
        if page is not None and page.model == TITLE_ONLY:
            # Raising instead (the first design) turned a missing link in an etymology
            # chain into a lost etymology: Module:etymon handles nil, not an error.
            self.stats["getContent.title_only"] += 1
            self.title_only_reads.add(page.title)
            return None
        body: str | None = None if page is None else page.body
        return body

    def _template_to_body(self, title: str, text: str | None) -> str:
        # Transcluding a title-only page (`{{Wiktionary:Picture dictionary/…}}`): the
        # wiki would show its text, which P1 didn't keep. Empty, and counted (R3.2a).
        if text is None:
            self.stats["transclude.title_only"] += 1
            return ""
        body: str = super()._template_to_body(title, text)
        return body

    def _title_only(self, key: LookupKey) -> Page | None:
        if key in self._title_cache:
            return self._title_cache[key]
        title, namespace_id, no_redirect = key
        candidates = self._candidates(title, namespace_id)
        query = (
            "SELECT title, ns, redirect_to FROM all_titles "
            f"WHERE title IN ({','.join('?' * len(candidates))})"
        )
        args: list[Any] = list(candidates)
        if namespace_id is not None:
            query += " AND ns = ?"
            args.append(namespace_id)
        if no_redirect:
            query += " AND redirect_to IS NULL"
        page = None
        for row_title, ns, redirect_to in self.db_conn.execute(
            query + " LIMIT 1", args
        ):
            page = Page(
                title=row_title,
                namespace_id=ns,
                redirect_to=redirect_to,
                need_pre_expand=False,
                body=None,
                model=TITLE_ONLY,
            )
        self._title_cache[key] = page
        return page

    def _candidates(self, title: str, namespace_id: int | None) -> list[str]:
        """The spellings upstream's get_page would try, as all_titles stores them."""
        title = title.replace("_", " ").removeprefix("Main:")
        if not namespace_id:
            return [title]
        prefix = self.LOCAL_NS_NAME_BY_ID[namespace_id] + ":"
        if not title.startswith(prefix):
            title = prefix + title
        rest = title[len(prefix) :]
        upper = prefix + rest[:1].upper() + rest[1:]
        return [title] if upper == title else [title, upper]


def _dump_epoch(conn: sqlite3.Connection) -> datetime:
    """Midnight UTC on the store's dump date: the frozen 'now' (R4.5)."""
    try:
        row = conn.execute(
            "SELECT value FROM scan_meta WHERE key = 'dump_file'"
        ).fetchone()
    except sqlite3.OperationalError:
        row = None
    match = re.search(r"-(\d{8})-", row[0]) if row else None
    if match is None:
        return datetime(2000, 1, 1, tzinfo=UTC)
    return datetime.strptime(match.group(1), "%Y%m%d").replace(tzinfo=UTC)


def _snapshot_lookups(conn: sqlite3.Connection) -> set[LookupKey] | None:
    try:
        rows = conn.execute("SELECT title, ns, no_redirect FROM snapshot_lookups")
    except sqlite3.OperationalError:
        return None
    return {(title, ns, bool(no_redirect)) for title, ns, no_redirect in rows}
