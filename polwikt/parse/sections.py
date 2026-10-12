"""Slices one language's L2 section out of a page's raw wikitext (R3.2, R5.2)."""

from __future__ import annotations

import re

from polwikt.dump.scan import language_heading_re

_ANY_L2 = re.compile(r"^==[^=].*?[^=]==[ \t]*$", re.MULTILINE)


def language_section(text: str, language: str) -> str | None:
    """The `==language==` section, heading included, up to the next L2, or None."""
    start = language_heading_re((language,)).search(text)
    if start is None:
        return None
    end = _ANY_L2.search(text, start.end())
    return text[start.start() : end.start() if end else len(text)].rstrip("\n") + "\n"
