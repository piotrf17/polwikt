"""Finds language headings and slices one language's L2 section out of a page (R3.2)."""

from __future__ import annotations

import re


def language_heading_re(languages: tuple[str, ...]) -> re.Pattern[str]:
    """An L2 heading line for any of `languages`, tolerating inner spaces (R3.2)."""
    names = "|".join(re.escape(lang) for lang in languages)
    return re.compile(rf"^==[ \t]*(?:{names})[ \t]*==[ \t]*$", re.MULTILINE)


def any_heading_re(languages: tuple[str, ...]) -> re.Pattern[str]:
    """A heading line of any level naming one of `languages`: near-miss detection."""
    names = "|".join(re.escape(lang) for lang in languages)
    return re.compile(rf"^=+[ \t]*(?:{names})[ \t]*=+.*$", re.MULTILINE)


_ANY_L2 = re.compile(r"^==[^=].*?[^=]==[ \t]*$", re.MULTILINE)


def language_section(text: str, language: str) -> str | None:
    """The `==language==` section, heading included, up to the next L2, or None."""
    start = language_heading_re((language,)).search(text)
    if start is None:
        return None
    end = _ANY_L2.search(text, start.end())
    return text[start.start() : end.start() if end else len(text)].rstrip("\n") + "\n"
