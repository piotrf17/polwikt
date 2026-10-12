"""Expanded declension tables to `InflectionTable`s and flat tagged `Form`s (R6.1,
R6.3, R6.4, R7.8).

A data cell's tags are its row headers plus its column headers, mapped through
data/inflection.toml. A cell spanning several header positions gives one Form per
distinct tag set, except that positions differing only in animacy merge into one
Form without it (`dobry` spans masculine animate and inanimate: just masculine).
Alternatives in a cell (`oczu/ócz/oczów`) are adjacent Forms, primary first. Cell
qualifiers (`familij<q:obsolete>`, `downy (deprecative)`) become Form labels, and a
form carrying a drop label is dropped and counted (R6.6a).
"""

from __future__ import annotations

import itertools
import re
import tomllib
from collections import Counter
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any

from wikitextprocessor import WikiNode

from polwikt.expand.run import expand_node
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.labels import LabelIndex
from polwikt.extract.tags import to_grammatical
from polwikt.parse.tables import Cell, Table, cell_wikitext, tables
from polwikt.parse.text import plain_text
from polwikt.proto import polwikt_pb2 as pb

_KINDS = {
    "declension": pb.InflectionTable.Kind.KIND_DECLENSION,
    "conjugation": pb.InflectionTable.Kind.KIND_CONJUGATION,
    "comparison": pb.InflectionTable.Kind.KIND_COMPARISON,
    "combined_forms": pb.InflectionTable.Kind.KIND_COMBINED_FORMS,
}
_DEFAULT_TITLES = {
    "declension": "Declension",
    "conjugation": "Conjugation",
    "combined_forms": "Combined forms",
}
_ANIMACY = frozenset({"personal", "animate", "inanimate"})
# Inline modifiers in a cell, `familij<q:obsolete>`, held as \x01q:obsolete\x02 while
# the expansion is parsed and reduced to plain text.
_MODIFIER = re.compile(r"<(q|qq|l|ll):([^<>]*)>")
_PROTECTED = re.compile("\x01(q|qq|l|ll):([^\x02]*)\x02")
_BREAK = re.compile(r"(?i)<br\s*/?>")
_FOOTNOTE = re.compile(r"(?<=[^\W\d_])\d+$")
_TRAILING_PAREN = re.compile(r"^(.*?)\s*\(([^()]*)\)$")
_ABSENT = frozenset({"", "-", "\u2013", "\u2014", "?"})  # hyphen, en and em dash
_SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Config:
    headers: dict[str, tuple[str, ...]]
    kind_names: dict[str, str]
    kind_prefixes: dict[str, str]
    irregular_templates: frozenset[str]
    irregular_category: str
    drop: dict[str, str]  # template prefix -> label
    plurale_category: str
    singulare_category: str
    headword: dict[str, Any]


@cache
def config() -> Config:
    path = resources.files("polwikt.data").joinpath("inflection.toml")
    data = tomllib.loads(path.read_text("utf-8"))
    return Config(
        headers={k: tuple(v) for k, v in data["headers"].items()},
        kind_names=dict(data["kinds"]["names"]),
        kind_prefixes=dict(data["kinds"]["prefixes"]),
        irregular_templates=frozenset(data["irregular"]["templates"]),
        irregular_category=data["irregular"]["category"],
        drop=dict(data["drop"]),
        plurale_category=data["tantum"]["plurale"],
        singulare_category=data["tantum"]["singulare"],
        headword=data["headword"],
    )


def table_kind(name: str) -> str:
    cfg = config()
    if name in cfg.kind_names:
        return cfg.kind_names[name]
    prefixes = [p for p in cfg.kind_prefixes if name.startswith(p)]
    return cfg.kind_prefixes[max(prefixes, key=len)] if prefixes else "declension"


def drop_label(name: str) -> str | None:
    """The label a table template is dropped under, if it is (R6.6a)."""
    hits = [p for p in config().drop if name.startswith(p)]
    return config().drop[max(hits, key=len)] if hits else None


@dataclass
class Paradigm:
    """One table template's output: its tables, each with its forms."""

    tables: list[tuple[pb.InflectionTable, list[pb.Form]]]
    plurale_tantum: bool = False
    singulare_tantum: bool = False


class TableParser:
    """Reads one entry's table templates; per page, like SenseParser."""

    def __init__(
        self,
        wtp: PolwiktWtp,
        labels: LabelIndex,
        drop: frozenset[str],
        stats: Counter[str],
    ) -> None:
        self.wtp = wtp
        self.labels = labels
        self.drop = drop
        self.stats = stats

    def parse(self, name: str, node: WikiNode) -> Paradigm:
        cfg = config()
        expansion = expand_node(self.wtp, node)
        text = expansion.text
        kind = table_kind(name)
        irregular = name in cfg.irregular_templates or (
            f"[[Category:{cfg.irregular_category}" in text
        )
        out = Paradigm([])
        out.plurale_tantum = f"[[Category:{cfg.plurale_category}" in text
        out.singulare_tantum = f"[[Category:{cfg.singulare_category}" in text
        # Before parsing: the parser would read `<q:obsolete>` as an HTML <q> tag.
        protected = _MODIFIER.sub(lambda m: f"\x01{m.group(1)}:{m.group(2)}\x02", text)
        found = tables(self.wtp, self.wtp.parse(protected))
        if not found:
            self.stats["table.none"] += 1
        for table in found:
            forms = self._forms(table)
            if not forms:
                self.stats["table.no_forms"] += 1
                continue
            title = _SPACE.sub(" ", table.title).strip() or _DEFAULT_TITLES[kind]
            message = pb.InflectionTable(
                kind=_KINDS[kind], title=title, irregular=irregular
            )
            out.tables.append((message, forms))
            self.stats[f"table.{kind}"] += 1
            self.stats["table.forms"] += len(forms)
        return out

    # -- cells ----------------------------------------------------------------------

    def _forms(self, table: Table) -> list[pb.Form]:
        forms: list[pb.Form] = []
        self._headers: dict[int, list[tuple[str, ...]] | None] = {}  # per header cell
        for cell in table.cells:
            if cell.header:
                continue
            alternatives = self._alternatives(cell_wikitext(self.wtp, cell))
            if not alternatives:
                continue
            tag_sets = self._tag_sets(table, cell)
            if tag_sets is None:
                self.stats["table.cell.no_headers"] += 1
                continue
            for tags, raw_headers in tag_sets:
                grammatical, raw = to_grammatical(list(tags))
                for text, labels in alternatives:
                    form = pb.Form(form=text, tags=grammatical, labels=labels)
                    form.raw_tags.extend(dict.fromkeys([*raw, *raw_headers]))
                    forms.append(form)
        return forms

    def _tag_sets(
        self, table: Table, cell: Cell
    ) -> list[tuple[tuple[str, ...], tuple[str, ...]]] | None:
        """The distinct (tags, unmapped header texts) a cell's positions carry."""
        found: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
        any_header = False
        for row, col in cell.positions():
            headers = table.row_headers(row, col) + table.col_headers(row, col)
            choices: list[list[tuple[str, ...]]] = []
            unknown: list[str] = []
            for header in headers:
                any_header = True
                if id(header) not in self._headers:
                    self._headers[id(header)] = self._header(header)
                alternatives = self._headers[id(header)]
                if alternatives is None:
                    unknown.append(_header_text(self.wtp, header))
                else:
                    choices.append(alternatives)
            for combo in itertools.product(*choices):
                tags = tuple(dict.fromkeys(t for part in combo for t in part))
                if (tags, tuple(unknown)) not in found:
                    found.append((tags, tuple(unknown)))
        if not any_header:
            return None
        return _merge_animacy(found)

    def _header(self, header: Cell) -> list[tuple[str, ...]] | None:
        text = _header_text(self.wtp, header).lower()
        headers = config().headers
        if text in headers:
            return [headers[text]]
        parts = [p.strip() for p in text.split("/")]
        if len(parts) > 1 and all(p in headers for p in parts):
            return [headers[p] for p in parts]
        self.stats[f"table.header.unknown.{text}"] += 1
        return None

    def _alternatives(self, wikitext: str) -> list[tuple[str, list[str]]]:
        """A cell's forms in source order, each with its labels."""
        text = plain_text(_BREAK.sub(" / ", wikitext))
        out: list[tuple[str, list[str]]] = []
        for part in _split_alternatives(text):
            labels = [
                label for m in _PROTECTED.finditer(part) for label in self._modifier(m)
            ]
            form = _PROTECTED.sub("", part).strip()
            if paren := _TRAILING_PAREN.match(form):
                form, note = paren.group(1).strip(), paren.group(2).strip()
                labels.append(note)
                self.stats["table.form.parenthetical"] += 1
            if _FOOTNOTE.search(form):
                form = _FOOTNOTE.sub("", form)
                self.stats["table.form.footnote"] += 1
            if form in _ABSENT:
                continue
            dropped = sorted(self.drop.intersection(labels))
            if dropped:
                for label in dropped:
                    self.stats[f"dropped.form.{label}"] += 1
                continue
            out.append((form, list(dict.fromkeys(label for label in labels if label))))
        return out

    def _modifier(self, match: re.Match[str]) -> list[str]:
        """<q:…> is free text; <l:…> holds labels, canonicalised (R6.7)."""
        key, value = match.group(1), match.group(2)
        if key in ("l", "ll"):
            return [lab.name for lab in self.labels.parse_args([value], self.stats)]
        return [plain_text(value)]


def _header_text(wtp: PolwiktWtp, header: Cell) -> str:
    return _SPACE.sub(" ", plain_text(cell_wikitext(wtp, header))).strip()


def _split_alternatives(text: str) -> list[str]:
    """`a / b (x, y), c` -> ['a', 'b (x, y)', 'c']: never inside parentheses."""
    parts: list[str] = []
    depth, start = 0, 0
    for i, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        elif char in "/," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def _merge_animacy(
    found: list[tuple[tuple[str, ...], tuple[str, ...]]],
) -> list[tuple[tuple[str, ...], tuple[str, ...]]]:
    """Positions of one cell that differ only in animacy are one Form without it."""
    groups: dict[tuple[tuple[str, ...], tuple[str, ...]], list[tuple[str, ...]]] = {}
    for tags, unknown in found:
        key = (tuple(t for t in tags if t not in _ANIMACY), unknown)
        groups.setdefault(key, []).append(tags)
    out: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
    for (bare, unknown), members in groups.items():
        out.append((bare if len(members) > 1 else members[0], unknown))
    return out
