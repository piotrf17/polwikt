"""Pieces of rendered Wiktionary HTML: qualifier labels and language-tagged terms.

Module output marks every qualifier or label as an `ib-content` span ("colloquial",
"Kuyavia") and every linked term as a span with its `lang` attribute; reading these is
how a list built inside a module (pronunciation lines, derived-verb tables) is taken
apart. Language-agnostic: the caller names the language.
"""

from __future__ import annotations

import re
from functools import cache

from polwikt.parse.text import plain_text

_LABEL = re.compile(r'<span class="ib-content[^"]*">(.*?)</span>')


def labels(html: str) -> list[str]:
    """The text of each qualifier or label span, in order."""
    return [t for m in _LABEL.findall(html) if (t := plain_text(m))]


def strip_labels(html: str) -> str:
    return _LABEL.sub("", html)


@cache
def term_pattern(lang: str) -> re.Pattern[str]:
    """A term span: `<span class="Latn" lang="pl">[[:kod#Polish|kod]]</span>`."""
    return re.compile(rf'<span class="[^"]*" lang="{re.escape(lang)}">(.*?)</span>')


def terms(html: str, lang: str) -> list[str]:
    return [t for m in term_pattern(lang).findall(html) if (t := plain_text(m))]


@cache
def term_separator(lang: str) -> re.Pattern[str]:
    """The ", " between two terms of a list, where one term's qualifiers end; a
    bracketed second term (`dochodzić impf, [dojść pf]`) too."""
    return re.compile(rf',\s*\[?(?=<span class="[^"]*" lang="{re.escape(lang)}">)')
