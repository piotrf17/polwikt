"""{{lb}} / {{tlb}} labels to canonical names, split into labels/regions/topics (R6.7).

Lookup follows Module:labels' own order over the dump's data modules: the Polish
module first, then the general, qualifier, regional and topical ones. A string entry
is an alias. The module a label comes from, or its regional/topical categories,
decides its kind. Unrecognised labels are kept as free text (`labels`) and counted;
capitalised ones are localities and go to `regions` (data/labels.toml).
"""

from __future__ import annotations

import re
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
    # A topical label's categories, as Module:labels names them (R6.10):
    # `topical_categories = true` is the label itself, capitalised ("Music").
    topics: tuple[str, ...] = ()


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
                kind = _kind(module, entry)
                topics = _topics(label, entry) if kind is Kind.TOPIC else ()
                return Label(label, kind, True, topics)
        return Label(label, Kind.LABEL, False)

    def parse_args(self, values: list[str], stats: Counter[str]) -> list[Label]:
        """The labels of one {{lb|pl|…}} call (its arguments after the language)."""
        out: list[Label] = []
        for value in values:
            for part in split_on_comma(value):
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


def split_on_comma(value: str) -> list[str]:
    """Module:labels' rule: "regional,dated" is two labels, but a comma followed by
    whitespace is prose ("of news, rumors, etc." is one), and nothing inside <...> or
    [...] is split."""
    parts: list[str] = []
    depth, start = 0, 0
    for i, char in enumerate(value):
        if char in "<[":
            depth += 1
        elif char in ">]" and depth:
            depth -= 1
        elif char == "," and depth == 0 and not value[i + 1 : i + 2].isspace():
            parts.append(value[start:i])
            start = i + 1
    return [*parts, value[start:]]


@cache
def _config() -> dict[str, Any]:
    path = resources.files("polwikt.data").joinpath("labels.toml")
    return tomllib.loads(path.read_text("utf-8"))


def _capitalized_kind() -> Kind:
    return Kind(_config()["unrecognized_capitalized"])


@cache
def _topic_category() -> re.Pattern[str]:
    prefix = re.escape(_config()["topic_category_prefix"])
    return re.compile(rf"\[\[\s*Category\s*:\s*{prefix}([^|\]]+)")


def topic_categories(expanded: str) -> list[str]:
    """The topical categories ("Countries in Africa") expanded wikitext emits."""
    return list(dict.fromkeys(m.strip() for m in _topic_category().findall(expanded)))


def _kind(module: str, entry: dict[Any, Any]) -> Kind:
    if module == _QUALIFIERS:
        return Kind.QUALIFIER
    if entry.get("regional_categories") or module.endswith("/regional"):
        return Kind.REGION
    if entry.get("topical_categories") or module.endswith("/topical"):
        return Kind.TOPIC
    return Kind.LABEL


def _topics(label: str, entry: dict[Any, Any]) -> tuple[str, ...]:
    cats = entry.get("topical_categories")
    if cats is None or cats is True:
        return (label[:1].upper() + label[1:],)
    if isinstance(cats, dict):  # a Lua list decoded with string keys
        values = [
            cats[k]
            for k in sorted(cats, key=lambda k: int(k) if str(k).isdigit() else 0)
        ]
    else:
        values = cats if isinstance(cats, list) else [cats]
    return tuple(label[:1].upper() + label[1:] if c is True else str(c) for c in values)
