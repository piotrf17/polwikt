"""Turns expanded wikitext into the plain text the output carries (R7.6a)."""

from __future__ import annotations

import html
import re

_REF = re.compile(r"(?is)<ref\b[^>]*?(?:/>|>.*?</ref\s*>)")
_COMMENT = re.compile(r"(?s)<!--.*?-->")
_CATEGORY = re.compile(r"(?i)\[\[\s*:?\s*Category\s*:[^\]]*\]\]")
_FILE = re.compile(
    r"(?i)\[\[\s*(?:File|Image)\s*:[^\[\]]*(?:\[\[[^\]]*\]\][^\[\]]*)*\]\]"
)
_LINK = re.compile(r"\[\[([^\[\]|]*)(?:\|([^\[\]]*))?\]\]")
_EXTERNAL = re.compile(r"\[(?:https?:)?//[^\s\]]+(?:\s+([^\]]*))?\]")
_TAG = re.compile(r"(?s)<[^<>]+>")
_BOLD_ITALIC = re.compile(r"'{2,}")
_SPACE = re.compile(r"[ \t\u00a0]+")
_DIV = re.compile(r"(?i)<(/?)div\b[^>]*>")
# Collapsible boxes are navigation, never prose: {{etymon|tree=1}}'s "Etymology tree".
_BOX = re.compile(r'(?i)<div\b[^>]*class="[^"]*\b(?:NavFrame|etytree)\b[^"]*"[^>]*>')
_LIST_MARK = re.compile(r"^[#*:;]+\s*")
# Bidi marks and zero-width characters, e.g. the LRM {{surf}} puts after "+".
_INVISIBLE = re.compile(r"[\u200b-\u200f\u2060\ufeff]")


def plain_text(wikitext: str) -> str:
    """Display text of expanded wikitext: links become labels, markup and tags go."""
    text = _drop_boxes(_REF.sub("", wikitext))
    text = _COMMENT.sub("", text)
    text = _CATEGORY.sub("", text)
    text = _FILE.sub("", text)
    text = _LINK.sub(_link_label, text)
    text = _EXTERNAL.sub(lambda m: m.group(1) or "", text)
    text = _TAG.sub("", text)
    text = _BOLD_ITALIC.sub("", text)
    text = html.unescape(text)
    text = _INVISIBLE.sub("", text)
    text = _SPACE.sub(" ", text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def one_line(text: str) -> str:
    """A gloss on one line: a rendered sub-list joins its lead-in ("…of mama: a; b")."""
    lines = [_LIST_MARK.sub("", line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    if len(lines) <= 1:
        return lines[0] if lines else ""
    head, rest = lines[0], lines[1:]
    return f"{head} {'; '.join(rest)}" if head.endswith(":") else " ".join(lines)


def _link_label(m: re.Match[str]) -> str:
    target, label = m.group(1), m.group(2)
    if label is not None:
        return label
    # [[:kot#Polish]] or [[w:Poland]] show as "kot" / "Poland" with no label given.
    target = target.lstrip(":").split("#", 1)[0]
    return target.split(":", 1)[1] if re.match(r"^[a-z]{1,3}:", target) else target


def _drop_boxes(text: str) -> str:
    """Removes each collapsible box with everything nested inside it."""
    while (start := _BOX.search(text)) is not None:
        depth, end = 0, len(text)
        for tag in _DIV.finditer(text, start.start()):
            depth += -1 if tag.group(1) else 1
            if depth == 0:
                end = tag.end()
                break
        text = text[: start.start()] + text[end:]
    return text
