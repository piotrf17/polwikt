"""Renders a WikiNode parse tree as indented text, for `polwikt inspect` (R8.5)."""

from __future__ import annotations

from wikitextprocessor import WikiNode

_MAX_TEXT = 70


def format_tree(node: WikiNode | str, depth: int = 0) -> str:
    """One line per node: kind, its arguments, then children indented below it."""
    lines: list[str] = []
    _walk(node, depth, lines)
    return "\n".join(lines)


def _walk(node: WikiNode | str, depth: int, lines: list[str]) -> None:
    pad = "  " * depth
    if isinstance(node, str):
        if node.strip():
            lines.append(f"{pad}{_clip(node)!r}")
        return
    head = f"{pad}{node.kind.name}"
    if node.sarg:
        head += f" {node.sarg!r}"
    elif node.largs:
        head += " " + " | ".join(_clip(_flatten(arg)) for arg in node.largs)
    if node.attrs:
        head += f" {node.attrs}"
    lines.append(head)
    for child in node.children:
        _walk(child, depth + 1, lines)


def _flatten(arg: object) -> str:
    """Template and link arguments are lists of strings and nodes; show them flat."""
    if isinstance(arg, str):
        return arg
    if isinstance(arg, list):
        return "".join(_flatten(a) for a in arg)
    if isinstance(arg, WikiNode):
        return f"<{arg.kind.name}>"
    return str(arg)


def _clip(text: str) -> str:
    text = text.replace("\n", "⏎")
    return text if len(text) <= _MAX_TEXT else text[: _MAX_TEXT - 1] + "…"
