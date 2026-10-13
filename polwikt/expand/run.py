"""Expands wikitext or one template node and reports the errors it raised (R4.3)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from wikitextprocessor import WikiNode

from polwikt.expand.wtp import PolwiktWtp


@dataclass(frozen=True)
class Expansion:
    text: str
    errors: tuple[str, ...]  # upstream error messages raised by this expansion

    @property
    def ok(self) -> bool:
        return not self.errors


# Upstream's template hook: (name, args) -> the expansion, or None to expand normally.
TemplateFn = Callable[[str, dict[Any, str]], str | None]


def expand_text(
    wtp: PolwiktWtp, text: str, template_fn: TemplateFn | None = None
) -> Expansion:
    """Expands `text` on the current page; Lua failures become counted errors (R4.3)."""
    before = len(wtp.errors)
    out = wtp.expand(text, template_fn=template_fn)
    errors = tuple(e["msg"] for e in wtp.errors[before:])
    for msg in errors:
        kind = (
            "lua.timeout"
            if "Lua timeout error" in msg
            else ("lua.error" if msg.startswith("LUA error") else "expand.error")
        )
        wtp.stats[kind] += 1
    return Expansion(out, errors)


def expand_node(
    wtp: PolwiktWtp, node: WikiNode, template_fn: TemplateFn | None = None
) -> Expansion:
    """Expands one parsed template call, e.g. a `{{pl-decl-noun-m-anml}}` table."""
    return expand_text(wtp, wtp.node_to_wikitext(node), template_fn)
