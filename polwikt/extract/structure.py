"""Walks a page's Polish section into etymology groups, entries and senses (R5.1-R5.5).

Headings attach by what they are, never by depth (R5.2). A *container* is the
language section, an etymology group or a `Pronunciation N` split; the pronunciation
and alternative-forms sections among its children are shared by every entry inside it
(R5.5). A POS heading makes an entry in the current etymology group: the group of the
nearest `Etymology` heading before it, numbered (`Etymology 2` around it) or not
(`Etymology` as a preceding sibling). Entry subsections (`Declension`, `Usage notes`)
belong to the entry they follow, as children or as siblings.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from wikitextprocessor import NodeKind, WikiNode

from polwikt.expand.policy import Action, Policy, canonical_name
from polwikt.expand.run import expand_text
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.pronunciation import pronunciations
from polwikt.parse.headings import Heading, HeadingMap, Kind
from polwikt.parse.text import one_line, plain_text
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


@dataclass
class Walk:
    """Everything one page's walk produces; turned into Word + PageRecord by page.py."""

    wtp: PolwiktWtp
    policy: Policy
    headings: HeadingMap
    drop_labels: frozenset[str]
    groups: list[Group] = field(default_factory=list)
    entries: list[EntryDraft] = field(default_factory=list)
    unknown: list[p3.UnknownSection] = field(default_factory=list)
    stats: Counter[str] = field(default_factory=Counter)
    _default_group: int | None = None
    _pron_cache: dict[int, list[pb.Pronunciation]] = field(default_factory=dict)

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
                case Kind.POS_NOT_EMITTED:
                    self.stats[f"pos.not_emitted.{head.name}"] += 1
                    last = None
                case Kind.ENTRY:
                    self._entry_section(last, child, head)
                case Kind.TRIVIA | Kind.IGNORED:
                    pass  # Trivia's frequency is M6 (R6.13)
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
    ) -> EntryDraft:
        draft = EntryDraft(pb.Entry(pos=f"POS_{head.pos}"), 0)
        draft.group = self._group_for(group)
        draft.entry.etymology = draft.group
        own_shared: list[WikiNode] = []
        for child in node.children:
            if not isinstance(child, WikiNode):
                continue
            if child.kind == NodeKind.TEMPLATE:
                name = canonical(self.wtp, child)
                if self.policy.action(name) is Action.BOTH:
                    draft.calls.headword.append(template_call(self.wtp, child, name))
            elif child.kind == NodeKind.LIST and child.sarg == "#":
                for item in list_items(child):
                    if (sense := self._sense(item)) is not None:
                        draft.entry.senses.append(sense)
            elif child.kind in LEVELS:
                sub = self.headings.classify(heading_text(child))
                if sub.kind in (Kind.PRONUNCIATION, Kind.ALTERNATIVE_FORMS):
                    own_shared.append(child)
                elif sub.kind == Kind.ENTRY:
                    self._entry_section(draft, child, sub)
                elif sub.kind == Kind.UNKNOWN:
                    self._unknown(child, sub)
        for section in shared + own_shared:
            if self.headings.classify(heading_text(section)).kind is Kind.PRONUNCIATION:
                draft.entry.pronunciations.extend(self._pronunciations(section))
        self.stats[f"pos.{head.pos}"] += 1
        self.entries.append(draft)
        return draft

    def _entry_section(
        self, draft: EntryDraft | None, node: WikiNode, head: Heading
    ) -> None:
        if draft is None:
            self.stats[f"section.orphan.{head.name}"] += 1
            return
        if head.name in _TABLE_SECTIONS:
            for child in node.children:
                if isinstance(child, WikiNode) and child.kind == NodeKind.TEMPLATE:
                    name = canonical(self.wtp, child)
                    if self.policy.action(name) is Action.EXPAND:
                        draft.calls.inflection.append(
                            template_call(self.wtp, child, name)
                        )

    def _pronunciations(self, section: WikiNode) -> list[pb.Pronunciation]:
        key = id(section)  # a page-level section is shared: expand it once
        if key not in self._pron_cache:
            self._pron_cache[key] = pronunciations(
                self.wtp, section, self.drop_labels, self.stats
            )
        return self._pron_cache[key]  # RepeatedField.extend copies each message

    # -- senses -------------------------------------------------------------------

    def _sense(self, item: WikiNode) -> pb.Sense | None:
        parts: list[str] = []
        sub_items: list[WikiNode] = []
        for child in item.children:
            if isinstance(child, WikiNode) and child.kind == NodeKind.LIST:
                if re.fullmatch(r"#+", child.sarg) and len(child.sarg) > len(item.sarg):
                    sub_items.extend(list_items(child))
                continue  # #: examples and #* quotations are M6 (R6.9)
            if (
                isinstance(child, WikiNode)
                and child.kind == NodeKind.TEMPLATE
                and not self.policy.in_gloss(canonical(self.wtp, child))
            ):
                continue
            parts.append(
                child if isinstance(child, str) else self.wtp.node_to_wikitext(child)
            )
        expanded = expand_text(self.wtp, "".join(parts)).text
        sense = pb.Sense(gloss=one_line(plain_text(expanded)))
        for sub in sub_items:
            if (child_sense := self._sense(sub)) is not None:
                sense.subsenses.append(child_sense)
        if not sense.gloss and not sense.subsenses:
            self.stats["sense.empty"] += 1
            return None
        self.stats["senses" if len(item.sarg) == 1 else "subsenses"] += 1
        return sense


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
