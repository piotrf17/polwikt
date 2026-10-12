"""{{lb}} / {{tlb}} labels to canonical names, split into labels/regions/topics (R6.7).

Lookup follows Module:labels' own order over the dump's data modules: the Polish
module first, then the general, qualifier, regional and topical ones. A string entry
is an alias. The module a label comes from, or its regional/topical categories,
decides its kind. Unrecognised labels are kept as free text (`labels`) and counted;
capitalised ones are localities and go to `regions` (data/labels.toml).
"""

from __future__ import annotations

import tomllib
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from importlib import resources
from typing import Any

from polwikt.expand.lua_data import load_modules
from polwikt.expand.wtp import PolwiktWtp

_MODULES = (
    "Module:labels/data/lang/pl",
    "Module:labels/data",
    "Module:labels/data/qualifiers",
    "Module:labels/data/regional",
    "Module:labels/data/topical",
)
_QUALIFIERS = "Module:labels/data/qualifiers"
# Module:labels' connectors between labels: not labels themselves.
_CONNECTORS = frozenset({"_", "and", "or", ",", ";", "&"})


class Kind(StrEnum):
    LABEL = "label"
    REGION = "region"
    TOPIC = "topic"
    QUALIFIER = "qualifier"  # "chiefly", "usually": modifies the next label


@dataclass(frozen=True)
class Label:
    name: str
    kind: Kind
    recognized: bool


class LabelIndex:
    def __init__(self, wtp: PolwiktWtp, language: str = "pl") -> None:
        modules = [m.replace("/pl", f"/{language}") for m in _MODULES]
        loaded = load_modules(wtp, modules)
        self._language = language
        self._data: list[tuple[str, dict[str, Any]]] = [(m, loaded[m]) for m in modules]

    def classify(self, raw: str) -> Label:
        label = raw.strip().removeprefix("!")
        label = label.split("!", 1)[0] if "!" in label else label  # label!display
        for module, data in self._data:
            entry = data.get(label)
            if isinstance(entry, str):  # an alias
                label, entry = entry, data.get(entry)
            if isinstance(entry, dict):
                langs = entry.get("langs")
                if isinstance(langs, dict) and self._language not in langs.values():
                    continue
                return Label(label, _kind(module, entry), True)
        return Label(label, Kind.LABEL, False)

    def parse_args(self, values: list[str], stats: Counter[str]) -> list[Label]:
        """The labels of one {{lb|pl|…}} call (its arguments after the language)."""
        out: list[Label] = []
        for value in values:
            for part in value.split(", ") if ", " in value else [value]:
                if not part.strip() or part.strip() in _CONNECTORS:
                    continue
                label = self.classify(part)
                if not label.recognized:
                    stats["label.unrecognized"] += 1
                    if label.name[:1].isupper() and _capitalized_kind() is Kind.REGION:
                        label = Label(label.name, Kind.REGION, False)
                        stats["label.region_by_capital"] += 1
                if label.kind is Kind.QUALIFIER:
                    stats["label.qualifier"] += 1
                    continue
                out.append(label)
        return out


@cache
def _capitalized_kind() -> Kind:
    path = resources.files("polwikt.data").joinpath("labels.toml")
    return Kind(tomllib.loads(path.read_text("utf-8"))["unrecognized_capitalized"])


def _kind(module: str, entry: dict[Any, Any]) -> Kind:
    if module == _QUALIFIERS:
        return Kind.QUALIFIER
    if entry.get("regional_categories") or module.endswith("/regional"):
        return Kind.REGION
    if entry.get("topical_categories") or module.endswith("/topical"):
        return Kind.TOPIC
    return Kind.LABEL
