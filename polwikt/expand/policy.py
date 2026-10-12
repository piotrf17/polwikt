"""Expansion policy (R4.2): canonical template name to action, from data/templates.toml.

Aliases are resolved through the page store before lookup, so `{{lb}}` and `{{label}}`
share one policy entry. Names the policy doesn't know are recorded with a count and
the first page they were seen on: the R4.6 backlog.
"""

from __future__ import annotations

import tomllib
from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum
from functools import cache
from importlib import resources
from typing import Any

_MAX_REDIRECTS = 5


class Action(StrEnum):
    EXPAND = "expand"
    CAPTURE = "capture"
    BOTH = "both"
    RENDER = "render"
    IGNORE = "ignore"


class PolicyError(Exception):
    """templates.toml is malformed or lists a name under two actions."""


@dataclass(frozen=True)
class Policy:
    names: dict[str, Action]
    prefixes: tuple[tuple[str, Action], ...]  # longest first
    gloss_omit: frozenset[str] = frozenset()

    def in_text(self, canonical: str) -> bool:
        """Whether the template's rendering belongs in plain text at all."""
        return self.action(canonical) is not Action.IGNORE

    def in_gloss(self, canonical: str) -> bool:
        """Whether it belongs in a gloss; labels, government etc. have own fields."""
        return self.in_text(canonical) and canonical not in self.gloss_omit

    def action(self, canonical: str) -> Action | None:
        if (exact := self.names.get(canonical)) is not None:
            return exact
        for prefix, action in self.prefixes:
            if canonical.startswith(prefix):
                return action
        return None


@cache
def default_policy() -> Policy:
    return load_policy()


def load_policy(text: str | None = None) -> Policy:
    """Parses templates.toml (the packaged one unless `text` is given)."""
    if text is None:
        text = (
            resources.files("polwikt.data")
            .joinpath("templates.toml")
            .read_text(encoding="utf-8")
        )
    data = tomllib.loads(text)
    names: dict[str, Action] = {}
    prefixes: dict[str, Action] = {}
    gloss_omit = frozenset(data.pop("gloss", {}).get("omit", []))
    for key, table in data.items():
        try:
            action = Action(key)
        except ValueError as e:
            raise PolicyError(f"unknown action [{key}]") from e
        for target, entries in (
            (names, table.get("names", [])),
            (prefixes, table.get("prefixes", [])),
        ):
            for entry in entries:
                if entry in target and target[entry] is not action:
                    raise PolicyError(f"{entry!r} is both {target[entry]} and {action}")
                target[entry] = action
    ordered = tuple(sorted(prefixes.items(), key=lambda kv: (-len(kv[0]), kv[0])))
    return Policy(names, ordered, gloss_omit)


def canonical_name(wtp: Any, name: str) -> str:
    """The template's own page name, after following redirects (`lb` -> `label`)."""
    name = " ".join(name.replace("_", " ").split())
    ns = wtp.NAMESPACE_DATA["Template"]["id"]
    prefix = wtp.NAMESPACE_DATA["Template"]["name"] + ":"
    for _ in range(_MAX_REDIRECTS):
        page = wtp.get_page(name, ns)
        if page is None or page.redirect_to is None:
            break
        name = page.redirect_to
    return name.removeprefix(prefix)


@dataclass
class Unhandled:
    """Templates no policy entry covers: count and first example page (R4.6)."""

    counts: Counter[str] = field(default_factory=Counter)
    examples: dict[str, str] = field(default_factory=dict)

    def add(self, name: str, page: str) -> None:
        self.counts[name] += 1
        self.examples.setdefault(name, page)

    def rows(self) -> list[dict[str, Any]]:
        return [
            {"template": name, "count": count, "example": self.examples[name]}
            for name, count in sorted(
                self.counts.items(), key=lambda kv: (-kv[1], kv[0])
            )
        ]
