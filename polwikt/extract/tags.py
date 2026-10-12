"""Form-of tags ("gen|p", "nom//acc//voc|p") to GrammaticalTags (R6.6).

Shortcuts resolve through the dump's Module:form of/data/1 and /2; `;` separates tag
sets and `//` joins alternatives, so one call can yield several GrammaticalTags.
Canonical names map to enums via data/tags.toml; the rest are raw tags.
"""

from __future__ import annotations

import itertools
import tomllib
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
from typing import Any

from polwikt.expand.lua_data import load_modules
from polwikt.expand.wtp import PolwiktWtp
from polwikt.proto import polwikt_pb2 as pb

_MODULES = ["Module:form of/data/1", "Module:form of/data/2"]
_SET_SEPARATOR = ";"
_ALTERNATIVE = "//"


@dataclass(frozen=True)
class TagMap:
    fields: dict[str, tuple[str, str]]
    combinations: list[tuple[frozenset[str], tuple[str, str]]]


@cache
def tag_map() -> TagMap:
    text = resources.files("polwikt.data").joinpath("tags.toml").read_text("utf-8")
    data = tomllib.loads(text)

    def split(value: str) -> tuple[str, str]:
        name, enum_value = value.split(".", 1)
        return name, enum_value

    fields = {tag: split(value) for tag, value in data["fields"].items()}
    combos = [(frozenset(c["tags"]), split(c["value"])) for c in data["combination"]]
    combos.sort(key=lambda c: -len(c[0]))
    return TagMap(fields, combos)


@dataclass
class TagSets:
    sets: list[pb.GrammaticalTags] = field(default_factory=list)
    raw: list[str] = field(default_factory=list)  # unmapped tags, source order


class TagIndex:
    def __init__(self, wtp: PolwiktWtp) -> None:
        loaded = load_modules(wtp, _MODULES)
        self._tags: set[str] = set()
        self._shortcuts: dict[str, Any] = {}
        for name in _MODULES:
            self._tags.update(loaded[name].get("tags", {}))
            for key, value in loaded[name].get("shortcuts", {}).items():
                self._shortcuts.setdefault(key, value)

    def canonical(self, tag: str, depth: int = 0) -> list[str]:
        """One written tag as canonical names: a shortcut may stand for several."""
        tag = tag.strip()
        if tag in self._tags or depth > 4:
            return [tag]
        short = self._shortcuts.get(tag)
        if isinstance(short, str):
            return self.canonical(short, depth + 1)
        if isinstance(short, dict):
            parts = [short[k] for k in sorted(short, key=int)]
            return [t for p in parts for t in self.canonical(p, depth + 1)]
        return [tag]

    def _alternatives(self, arg: str) -> list[list[str]]:
        """`nom//acc` as two choices; a shortcut may itself be one ("mn" -> "m//n")."""
        out: list[list[str]] = []
        for alt in arg.split(_ALTERNATIVE):
            names = self.canonical(alt)
            if len(names) == 1 and _ALTERNATIVE in names[0]:
                out.extend(self._alternatives(names[0]))
            else:
                out.append(names)
        return out

    def parse(self, args: list[str]) -> TagSets:
        """The tag arguments of {{inflection of}} (after the lemma) as tag sets."""
        out = TagSets()
        groups: list[list[str]] = [[]]
        for arg in args:
            if arg.strip() == _SET_SEPARATOR:
                groups.append([])
            elif arg.strip():
                groups[-1].append(arg)
        for group in groups:
            choices = [self._alternatives(arg) for arg in group]
            for combo in itertools.product(*choices) if choices else []:
                tags = [t for alternative in combo for t in alternative]
                grammatical, raw = to_grammatical(tags)
                out.sets.append(grammatical)
                out.raw.extend(t for t in raw if t not in out.raw)
        return out


def to_grammatical(tags: list[str]) -> tuple[pb.GrammaticalTags, list[str]]:
    """Canonical tags onto the enum fields; returns the ones no field covers."""
    mapping = tag_map()
    result = pb.GrammaticalTags()
    remaining = list(tags)
    for combo, (name, value) in mapping.combinations:
        if combo <= set(remaining):
            setattr(result, name, value)
            remaining = [t for t in remaining if t not in combo]
    raw: list[str] = []
    for tag in remaining:
        target = mapping.fields.get(tag)
        if target is None:
            raw.append(tag)
        else:
            setattr(result, target[0], target[1])
    return result, raw
