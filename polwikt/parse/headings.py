"""Classifies section headings by what they are, from data/sections.toml (R5.2)."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from importlib import resources

_NUMBER = re.compile(r"\s+\d+$")


class Kind(StrEnum):
    POS = "pos"
    POS_NOT_EMITTED = "pos_not_emitted"
    ETYMOLOGY = "etymology"
    PRONUNCIATION = "pronunciation"
    ALTERNATIVE_FORMS = "alternative_forms"
    ENTRY = "entry"
    TRIVIA = "trivia"
    IGNORED = "ignored"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Heading:
    kind: Kind
    name: str  # the heading without its number: "Etymology", "Noun"
    pos: str = ""  # polwikt.Pos value name without the POS_ prefix, for Kind.POS


class HeadingMapError(Exception):
    """sections.toml lists a heading twice or names an unknown kind."""


@dataclass(frozen=True)
class HeadingMap:
    pos: dict[str, str]
    kinds: dict[str, Kind]

    def classify(self, heading: str) -> Heading:
        name = _NUMBER.sub("", " ".join(heading.split()))
        if name in self.pos:
            return Heading(Kind.POS, name, self.pos[name])
        return Heading(self.kinds.get(name, Kind.UNKNOWN), name)


def parse_heading_map(text: str) -> HeadingMap:
    data = tomllib.loads(text)
    pos = dict(data.get("pos", {}))
    kinds: dict[str, Kind] = {}
    for key, names in data.get("sections", {}).items():
        try:
            kind = Kind(key)
        except ValueError as e:
            raise HeadingMapError(f"unknown section kind {key!r}") from e
        for name in names:
            if name in kinds or name in pos:
                raise HeadingMapError(f"{name!r} is listed twice")
            kinds[name] = kind
    return HeadingMap(pos, kinds)


@cache
def heading_map() -> HeadingMap:
    """The packaged map (data/sections.toml)."""
    path = resources.files("polwikt.data").joinpath("sections.toml")
    return parse_heading_map(path.read_text(encoding="utf-8"))
