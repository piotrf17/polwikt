"""Walks a page's Polish section into etymology groups, entries and senses (R5.1-R5.5).

Headings attach by what they are, never by depth (R5.2). A *container* is the
language section, an etymology group or a `Pronunciation N` split; the pronunciation
and alternative-forms sections among its children are shared by every entry inside it
(R5.5). A POS heading makes an entry in the current etymology group: the group of the
nearest `Etymology` heading before it, numbered (`Etymology 2` around it) or not
(`Etymology` as a preceding sibling). Entry subsections (`Declension`, `Usage notes`)
belong to the entry they follow, as children or as siblings.

Middle Polish cascade (R6.6a): a sense with a `drop_labels` label is dropped by the
sense parser; an entry goes with a `{{tlb}}` drop label or when all its senses went;
page.py drops the page when no entry is left. Every step is counted (R6.6c).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from wikitextprocessor import NodeKind, WikiNode

from polwikt.expand.policy import Action, Policy, canonical_name
from polwikt.expand.run import expand_text
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.headword import (
    NOUN_TEMPLATES,
    comparison,
    comparison_templates,
    noun_info,
)
from polwikt.extract.inflection import TableParser, drop_label, table_kind
from polwikt.extract.labels import Kind as LabelKind
from polwikt.extract.pronunciation import pronunciations
from polwikt.extract.sense import Indexes, SenseParser, positional, template_args
from polwikt.parse.headings import Heading, HeadingMap, Kind
from polwikt.parse.text import plain_text
from polwikt.proto import p3_pb2 as p3
from polwikt.proto import polwikt_pb2 as pb

LEVELS = frozenset(
    {
        NodeKind.LEVEL2,
        NodeKind.LEVEL3,
        NodeKind.LEVEL4,
        NodeKind.LEVEL5,
        NodeKind.LEVEL6,
    }
)
_NAMED_ARG = re.compile(r"^\s*([^=\n{}\[\]|]+?)\s*=(.*)$", re.DOTALL)
# Inflection subsections whose expand-policy templates are the entry's tables (R4.2.1).
_TABLE_SECTIONS = frozenset(
    {"Declension", "Declination", "Inflection", "Conjugation", "Conjugation/Declension"}
)
_USAGE_SECTIONS = frozenset({"Usage notes", "Usage", "Note", "Usage terms"})
_TOPIC_TEMPLATES = frozenset({"topics"})  # {{C|pl|Cats}}, {{topics|pl|…}} (R6.10)
# A footnote defined in Usage notes: "<sup>1</sup>The feminine accusative … tą is …"
_FOOTNOTE_LINE = re.compile(r"(?im)^\s*<sup\b[^>]*>\s*([0-9]+|[*†]+)\s*</sup>(.*)$")
_SUP_MARKER = re.compile(r"(?i)<sup\b[^>]*>\s*(?:[0-9]+|[*†]+)\s*</sup>")


@dataclass
class Group:
    """One etymology group: its section text and raw etymology calls."""

    text: str = ""
    calls: list[p3.TemplateCall] = field(default_factory=list)


@dataclass
class EntryDraft:
    entry: pb.Entry
    group: int  # index into Walk.groups
    calls: p3.EntryCalls = field(default_factory=p3.EntryCalls)
    # Table footnotes the expansion left unexplained, (index into entry.forms,
    # marker), and the notes the entry's Usage notes define: `ten`'s "1" lives there.
    markers: list[tuple[int, str]] = field(default_factory=list)
    footnotes: dict[str, str] = field(default_factory=dict)


@dataclass
class Walk:
    """Everything one page's walk produces; turned into Word + PageRecord by page.py."""

    wtp: PolwiktWtp
    policy: Policy
    headings: HeadingMap
    drop_labels: frozenset[str]
    index: Indexes
    title: str = ""
    groups: list[Group] = field(default_factory=list)
    entries: list[EntryDraft] = field(default_factory=list)
    unknown: list[p3.UnknownSection] = field(default_factory=list)
    stats: Counter[str] = field(default_factory=Counter)
    page_topics: list[str] = field(default_factory=list)  # {{C}} outside any entry
    colabelled: list[str] = field(default_factory=list)  # R6.6c report
    dropped_any: list[str] = field(default_factory=list)  # drop labels that fired
    _default_group: int | None = None
    _pron_cache: dict[int, list[pb.Pronunciation]] = field(default_factory=dict)
    _parser: SenseParser | None = None
    _tables: TableParser | None = None

    @property
    def parser(self) -> SenseParser:
        if self._parser is None:
            self._parser = SenseParser(
                self.wtp, self.policy, self.index, self.stats, canonical
            )
        return self._parser

    @property
    def table_parser(self) -> TableParser:
        if self._tables is None:
            self._tables = TableParser(
                self.wtp, self.index.labels, self.index.drop, self.stats
            )
        return self._tables

    # -- containers ---------------------------------------------------------------

    def container(
        self, node: WikiNode, shared: list[WikiNode], group: int | None
    ) -> None:
        children = [
            c for c in node.children if isinstance(c, WikiNode) and c.kind in LEVELS
        ]
        heads = [self.headings.classify(heading_text(c)) for c in children]
        local = [
            c
            for c, h in zip(children, heads, strict=True)
            if h.kind in (Kind.PRONUNCIATION, Kind.ALTERNATIVE_FORMS)
            and not self._holds_entries(c)
        ]
        scope = shared + local
        last: EntryDraft | None = None
        last_dropped = False
        for child, head in zip(children, heads, strict=True):
            match head.kind:
                case Kind.ETYMOLOGY:
                    group = self._new_group(child)
                    self.container(child, scope, group)
                    last = None
                case Kind.PRONUNCIATION | Kind.ALTERNATIVE_FORMS:
                    if self._holds_entries(child):  # "Pronunciation 1" with POS inside
                        self.container(child, scope, group)
                        last = None
                case Kind.POS:
                    last = self._entry(child, head, scope, group)
                    last_dropped = last is None
                case Kind.POS_NOT_EMITTED:
                    self.stats[f"pos.not_emitted.{head.name}"] += 1
                    last = None
                case Kind.ENTRY:
                    if last is None and last_dropped:  # its Declension, Usage notes…
                        self.stats[f"dropped.section.{head.name}"] += 1
                    else:
                        self._entry_section(last, child, head)
                case Kind.TRIVIA | Kind.IGNORED:
                    # Trivia's frequency is M9 (R6.13). A {{C|pl|…}} here sits at the
                    # foot of the page, after every entry: it is the page's.
                    _extend_unique(self.page_topics, self._topics(child))
                case Kind.UNKNOWN:
                    self._unknown(child, head)

    def _holds_entries(self, node: WikiNode) -> bool:
        for child in node.children:
            if isinstance(child, WikiNode) and child.kind in LEVELS:
                head = self.headings.classify(heading_text(child))
                if head.kind in (Kind.POS, Kind.POS_NOT_EMITTED) or self._holds_entries(
                    child
                ):
                    return True
        return False

    def _new_group(self, node: WikiNode) -> int:
        group = Group()
        parts: list[str] = []
        for child in node.children:
            if isinstance(child, WikiNode) and child.kind in LEVELS:
                continue
            if isinstance(child, WikiNode) and child.kind == NodeKind.TEMPLATE:
                name = canonical(self.wtp, child)
                if not self.policy.in_text(name):
                    continue
                if self.policy.action(name) is Action.CAPTURE:
                    group.calls.append(template_call(self.wtp, child, name))
            parts.append(self.wtp.node_to_wikitext(child))
        group.text = plain_text(expand_text(self.wtp, "".join(parts)).text)
        self.groups.append(group)
        return len(self.groups) - 1

    def _group_for(self, group: int | None) -> int:
        if group is not None:
            return group
        if self._default_group is None:  # no Etymology heading before this entry
            self.groups.append(Group())
            self._default_group = len(self.groups) - 1
        return self._default_group

    def _unknown(self, node: WikiNode, head: Heading) -> None:
        self.stats[f"heading.unknown.{head.name}"] += 1
        self.unknown.append(
            p3.UnknownSection(
                heading=heading_text(node), wikitext=self.wtp.node_to_wikitext(node)
            )
        )

    # -- entries ------------------------------------------------------------------

    def _entry(
        self, node: WikiNode, head: Heading, shared: list[WikiNode], group: int | None
    ) -> EntryDraft | None:
        draft = EntryDraft(pb.Entry(pos=f"POS_{head.pos}"), 0)
        own_shared: list[WikiNode] = []
        term_drop: list[str] = []
        dropped_before = len(self.parser.dropped)
        for child in node.children:
            if not isinstance(child, WikiNode):
                continue
            if child.kind == NodeKind.TEMPLATE:
                name = canonical(self.wtp, child)
                action = self.policy.action(name)
                if action is Action.BOTH:
                    draft.calls.headword.append(template_call(self.wtp, child, name))
                    self._headword(draft, child, name)
                elif action is Action.EXPAND:  # a table straight under the POS
                    self._table(draft, child, name)
                elif name == "term-label":
                    term_drop += self._term_labels(draft.entry, child)
                elif name in _TOPIC_TEMPLATES:
                    _extend_unique(draft.entry.topics, self._topic_args(child))
            elif child.kind == NodeKind.LIST and child.sarg == "#":
                for item in list_items(child):
                    if (sense := self.parser.parse(item)) is not None:
                        draft.entry.senses.append(sense)
            elif child.kind in LEVELS:
                sub = self.headings.classify(heading_text(child))
                if sub.kind in (Kind.PRONUNCIATION, Kind.ALTERNATIVE_FORMS):
                    own_shared.append(child)
                elif sub.kind == Kind.ENTRY:
                    self._entry_section(draft, child, sub)
                elif sub.kind == Kind.UNKNOWN:
                    self._unknown(child, sub)
        dropped = self.parser.dropped[dropped_before:]
        self._count_dropped_senses(dropped)
        if term_drop or (dropped and not draft.entry.senses):
            labels = term_drop or sorted({lab for d in dropped for lab in d.labels})
            for label in labels:
                self.stats[f"dropped.entry.{label}"] += 1
            self.dropped_any.extend(labels)
            return None  # R6.6a: a Middle Polish entry, or one with nothing left
        for section in shared + own_shared:
            if self.headings.classify(heading_text(section)).kind is Kind.PRONUNCIATION:
                draft.entry.pronunciations.extend(self._pronunciations(section))
        draft.group = self._group_for(group)
        draft.entry.etymology = draft.group
        self.stats[f"pos.{head.pos}"] += 1
        self.entries.append(draft)
        return draft

    def _count_dropped_senses(self, dropped: list[Any]) -> None:
        for d in dropped:
            for label in d.labels:
                self.stats[f"dropped.sense.{label}"] += d.senses
                self.dropped_any.append(label)
            if d.colabelled:
                self.stats["dropped.sense.colabelled"] += 1
                self.colabelled.append(self.title)

    def _term_labels(self, entry: pb.Entry, node: WikiNode) -> list[str]:
        """{{tlb|pl|…}} on the headword line: entry labels, or an entry drop (R6.6a)."""
        values = positional(template_args(self.wtp, node))[1:]
        labels = self.index.labels.parse_args(values, self.stats)
        hits = sorted({lab.name for lab in labels} & self.index.drop)
        for label in labels:
            target = entry.topics if label.kind is LabelKind.TOPIC else entry.labels
            _extend_unique(target, [label.name])
        return hits

    def _topics(self, node: WikiNode) -> list[str]:
        found: list[str] = []
        for child in node.children:
            if isinstance(child, WikiNode) and child.kind == NodeKind.TEMPLATE:
                if canonical(self.wtp, child) in _TOPIC_TEMPLATES:
                    _extend_unique(found, self._topic_args(child))
            elif isinstance(child, WikiNode) and child.kind in LEVELS:
                _extend_unique(found, self._topics(child))
        return found

    def _topic_args(self, node: WikiNode) -> list[str]:
        return [
            plain_text(v) for v in positional(template_args(self.wtp, node))[1:] if v
        ]

    def _entry_section(
        self, draft: EntryDraft | None, node: WikiNode, head: Heading
    ) -> None:
        if draft is None:
            self.stats[f"section.orphan.{head.name}"] += 1
            return
        _extend_unique(draft.entry.topics, self._topics(node))
        if head.name in _USAGE_SECTIONS:
            body = "".join(
                self.wtp.node_to_wikitext(c)
                for c in node.children
                if not (isinstance(c, WikiNode) and c.kind in LEVELS)
            )
            for marker, note in _FOOTNOTE_LINE.findall(body):
                draft.footnotes[marker] = plain_text(expand_text(self.wtp, note).text)
            body = _SUP_MARKER.sub("", body)  # the marker's meaning moves to the form
            text = plain_text(expand_text(self.wtp, body).text)
            self._resolve_footnotes(draft)
            if text:
                notes = draft.entry.usage_notes
                draft.entry.usage_notes = f"{notes}\n{text}" if notes else text
        if head.name in _TABLE_SECTIONS:
            for child in node.children:
                if isinstance(child, WikiNode) and child.kind == NodeKind.TEMPLATE:
                    name = canonical(self.wtp, child)
                    if self.policy.action(name) is Action.EXPAND:
                        self._table(draft, child, name)

    # -- grammar --------------------------------------------------------------------

    def _headword(self, draft: EntryDraft, node: WikiNode, name: str) -> None:
        """Genders and comparison from the headword call's arguments (R6.1, R6.3)."""
        entry = draft.entry
        if name in NOUN_TEMPLATES and not entry.HasField("noun"):
            entry.noun.CopyFrom(noun_info(template_args(self.wtp, node), self.stats))
        elif name in comparison_templates() and not entry.HasField("adjective"):
            found = comparison(
                self.title,
                template_args(self.wtp, node),
                self.index.labels,
                self.index.drop,
                self.stats,
            )
            entry.adjective.CopyFrom(found.info)
            if found.forms:
                self._add_table(entry, found.table(), found.forms)

    def _table(self, draft: EntryDraft, node: WikiNode, name: str) -> None:
        """One table template: its raw call (R4.2.1), then its parsed paradigm."""
        draft.calls.inflection.append(template_call(self.wtp, node, name))
        if label := drop_label(name):
            self.stats[f"dropped.table.{label}"] += 1  # R6.6a, never expanded
            return
        if table_kind(name) == "conjugation":
            self.stats["table.deferred.conjugation"] += 1  # M8
            return
        paradigm = self.table_parser.parse(name, node)
        entry = draft.entry
        for parsed in paradigm.tables:
            base = len(entry.forms)
            self._add_table(entry, parsed.table, parsed.forms)
            draft.markers += [(base + i, marker) for i, marker in parsed.markers]
        self._resolve_footnotes(draft)
        if entry.pos in (pb.Pos.POS_NOUN, pb.Pos.POS_PROPER_NOUN):
            if paradigm.plurale_tantum:
                entry.noun.plurale_tantum = True
            if paradigm.singulare_tantum:
                entry.noun.singulare_tantum = True

    def _resolve_footnotes(self, draft: EntryDraft) -> None:
        """Label the forms whose marker the entry's Usage notes explain; the rest wait
        (page.py counts what is left as table.footnote.unresolved)."""
        waiting: list[tuple[int, str]] = []
        for index, marker in draft.markers:
            if marker in draft.footnotes:
                self.table_parser.add_note(
                    draft.entry.forms[index], draft.footnotes[marker]
                )
            else:
                waiting.append((index, marker))
        draft.markers = waiting

    @staticmethod
    def _add_table(
        entry: pb.Entry, table: pb.InflectionTable, forms: list[pb.Form]
    ) -> None:
        for form in forms:
            form.table = len(entry.tables)
        entry.tables.append(table)
        entry.forms.extend(forms)

    def _pronunciations(self, section: WikiNode) -> list[pb.Pronunciation]:
        key = id(section)  # a page-level section is shared: expand it once
        if key not in self._pron_cache:
            self._pron_cache[key] = pronunciations(
                self.wtp, section, self.drop_labels, self.stats
            )
        return self._pron_cache[key]  # RepeatedField.extend copies each message


def _extend_unique(target: Any, values: list[str]) -> None:
    for value in values:
        if value and value not in target:
            target.append(value)


def list_items(node: WikiNode) -> list[WikiNode]:
    items = (c for c in node.children if isinstance(c, WikiNode))
    return [c for c in items if c.kind == NodeKind.LIST_ITEM]


def heading_text(node: WikiNode) -> str:
    return (
        "".join(p for p in node.largs[0] if isinstance(p, str)).strip()
        if node.largs
        else ""
    )


def canonical(wtp: PolwiktWtp, node: WikiNode) -> str:
    name = "".join(p for p in node.largs[0] if isinstance(p, str)).strip()
    return canonical_name(wtp, name)


def template_call(wtp: PolwiktWtp, node: WikiNode, name: str) -> p3.TemplateCall:
    """The raw `{name, args}` of a call (R4.2.1): positional keys are "1", "2", …"""
    written = "".join(p for p in node.largs[0] if isinstance(p, str)).strip()
    call = p3.TemplateCall(name=name, written_name="" if written == name else written)
    position = 0
    for arg in node.largs[1:]:
        raw = "".join(p if isinstance(p, str) else wtp.node_to_wikitext(p) for p in arg)
        named = _NAMED_ARG.match(raw)
        if named:
            call.args.append(p3.TemplateArg(key=named.group(1), value=named.group(2)))
        else:
            position += 1
            call.args.append(p3.TemplateArg(key=str(position), value=raw))
    return call
