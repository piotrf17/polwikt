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
from dataclasses import dataclass, field
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
# Footnote markers: <sup>1</sup> from the modules, or a bare digit a hand-written table
# puts after a form (`tą1`). Held as \x03…\x04 through plain_text.
_SUP = re.compile(r"(?i)<sup\b[^>]*>\s*([0-9]+|[*†]+)\s*</sup>")
_MARKER = re.compile("\x03([^\x04]*)\x04")
_FOOTNOTE = re.compile(r"(?<=[^\W\d_])(\d+)$")
# A note the module prints after its table: `<sup>1</sup>Archaic.`
_NOTE = re.compile(r"(?i)<sup\b[^>]*>\s*([0-9]+|[*†]+)\s*</sup>[ \t]*([^\n<][^\n]*)")
_TABLE = re.compile(r"(?s)\{\|.*?\n\|\}")
_TRAILING_PAREN = re.compile(r"^(.*?)\s*\(([^()]*)\)$")
_ABSENT = frozenset({"", "-", "\u2013", "\u2014", "?"})  # hyphen, en and em dash
_SPACE = re.compile(r"\s+")


# A cell's tags at one of its positions: (tags, unmapped header texts, (row, col)).
TagSet = tuple[tuple[str, ...], tuple[str, ...], tuple[int, int]]


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
class ParsedTable:
    table: pb.InflectionTable
    forms: list[pb.Form]
    # Footnote markers the expansion itself doesn't explain: (index into forms,
    # marker), for the entry's Usage notes to resolve (`ten`).
    markers: list[tuple[int, str]] = field(default_factory=list)


@dataclass
class Paradigm:
    """One table template's output: its tables, each with its forms."""

    tables: list[ParsedTable]
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
        protected = _SUP.sub(lambda m: f"\x03{m.group(1)}\x04", protected)
        outside = _TABLE.sub("", text)  # notes the module prints under its table
        notes = {m.group(1): plain_text(m.group(2)) for m in _NOTE.finditer(outside)}
        found = tables(self.wtp, self.wtp.parse(protected))
        if not found:
            self.stats["table.none"] += 1
        for table in found:
            forms, markers = self._forms(table)
            unresolved = []
            for index, marker in markers:
                if marker in notes:
                    self.add_note(forms[index], notes[marker])
                else:
                    unresolved.append((index, marker))
            if not forms:
                self.stats["table.no_forms"] += 1
                continue
            title = _SPACE.sub(" ", table.title).strip() or _DEFAULT_TITLES[kind]
            message = pb.InflectionTable(
                kind=_KINDS[kind], title=title, irregular=irregular
            )
            out.tables.append(ParsedTable(message, forms, unresolved))
            self.stats[f"table.{kind}"] += 1
            self.stats["table.forms"] += len(forms)
        return out

    # -- cells ----------------------------------------------------------------------

    def add_note(self, form: pb.Form, note: str) -> None:
        """A footnote on a form is a label: canonical when it names one ("Archaic.")."""
        text = note.strip().rstrip(".").strip()
        if not text:
            return
        label = self.labels.classify(text.lower())
        name = label.name if label.recognized else text
        if name not in form.labels:
            form.labels.append(name)
        self.stats["table.footnote.resolved"] += 1

    def _forms(self, table: Table) -> tuple[list[pb.Form], list[tuple[int, str]]]:
        """Forms in reading order — row by row, a spanning cell at each position it
        covers — plus the footnote markers on them (index into the forms)."""
        placed: list[tuple[tuple[int, int], int, pb.Form, str | None]] = []
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
            for tags, raw_headers, position in tag_sets:
                grammatical, raw = to_grammatical(list(tags))
                for text, labels, marker in alternatives:
                    form = pb.Form(form=text, tags=grammatical, labels=labels)
                    form.raw_tags.extend(dict.fromkeys([*raw, *raw_headers]))
                    placed.append((position, len(placed), form, marker))
        placed.sort(key=lambda p: (p[0], p[1]))
        forms = [form for _, _, form, _ in placed]
        markers = [(i, m) for i, (_, _, _, m) in enumerate(placed) if m is not None]
        return forms, markers

    def _tag_sets(self, table: Table, cell: Cell) -> list[TagSet] | None:
        """The distinct (tags, unmapped header texts, first position) of a cell."""
        found: list[TagSet] = []
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
                if all((tags, tuple(unknown)) != (t, u) for t, u, _ in found):
                    found.append((tags, tuple(unknown), (row, col)))
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

    def _alternatives(self, wikitext: str) -> list[tuple[str, list[str], str | None]]:
        """A cell's forms in source order, each with its labels and footnote marker."""
        text = plain_text(_BREAK.sub(" / ", wikitext))
        out: list[tuple[str, list[str], str | None]] = []
        for part in _split_alternatives(text):
            marker = next((m.group(1) for m in _MARKER.finditer(part)), None)
            part = _MARKER.sub("", part)
            labels = [
                label for m in _PROTECTED.finditer(part) for label in self._modifier(m)
            ]
            form = _PROTECTED.sub("", part).strip()
            if paren := _TRAILING_PAREN.match(form):
                form, note = paren.group(1).strip(), paren.group(2).strip()
                labels.append(note)
                self.stats["table.form.parenthetical"] += 1
            if bare := _FOOTNOTE.search(form):
                form, marker = form[: bare.start()], marker or bare.group(1)
            if marker is not None:
                self.stats["table.form.footnote"] += 1
            if form in _ABSENT:
                continue
            dropped = sorted(self.drop.intersection(labels))
            if dropped:
                for label in dropped:
                    self.stats[f"dropped.form.{label}"] += 1
                continue
            unique = list(dict.fromkeys(label for label in labels if label))
            out.append((form, unique, marker))
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


def _merge_animacy(found: list[TagSet]) -> list[TagSet]:
    """Positions of one cell that differ only in animacy are one Form without it,
    placed at the first of them."""
    groups: dict[tuple[tuple[str, ...], tuple[str, ...]], list[TagSet]] = {}
    for tags, unknown, position in found:
        key = (tuple(t for t in tags if t not in _ANIMACY), unknown)
        groups.setdefault(key, []).append((tags, unknown, position))
    out: list[TagSet] = []
    for (bare, unknown), members in groups.items():
        if len(members) == 1:
            out.append(members[0])
        else:
            out.append((bare, unknown, min(m[2] for m in members)))
    return out
