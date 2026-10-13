"""Entry relations from term-list sections, Alternative forms and the headword line.

Sections (R5.5, R6.4): every term a `Derived terms`, `Synonyms`, `Alternative forms`…
section lists becomes a Relation of the section's type (`data/relations.toml`). Terms
come from {{col}} items, link templates and raw links on a list line, {{alter}}, and
the rendering of module-built lists ({{pl-derived verbs}} pastes prefixes onto
suffixes). A line's {{q}} labels and {{sense}} gloss apply to every term on it; a
term's own `<q:…>`/`<l:…>`/`<t:…>` modifiers to that term. Collocations ({{coi}})
become entry examples (R6.12). Templates that list no terms of the entry (category
lists, navboxes) are counted, and so is any template not known at all.

Headword line (R3.14): `dim=`, `adj=`, `f=`, `dem=`… of {{pl-noun}} and friends.

A term labelled with a `drop_labels` label (R6.6a) is dropped and counted by kind.
"""

from __future__ import annotations

import re
import tomllib
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
from typing import Any

from wikitextprocessor import NodeKind, WikiNode

from polwikt.expand.run import expand_text
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.labels import LabelIndex, split_on_comma
from polwikt.extract.sense import positional, split_modifiers, template_args
from polwikt.parse import rendered
from polwikt.parse.text import plain_text
from polwikt.proto import polwikt_pb2 as pb

LANG = "pl"
_RAW_LINK = re.compile(r"\[\[([^\[\]|]+)(?:\|[^\[\]]*)?\]\]")
_PARENTHETICAL = re.compile(r"\(([^()]+)\)")
_LI = re.compile(r"(?s)<li>(.*?)</li>")
_NOT_A_TERM = frozenset({"", "-", ".", "_", ",", ";"})
_ALTERNATIVE = "TYPE_ALTERNATIVE_FORM"

Canonical = Callable[[PolwiktWtp, WikiNode], str]
ExampleFn = Callable[["pb.Example.Kind", dict[str, str]], "pb.Example | None"]


@dataclass(frozen=True)
class Config:
    sections: dict[str, str]
    collocation_sections: frozenset[str]
    columns: frozenset[str]
    links: frozenset[str]
    alternatives: frozenset[str]
    rendered: frozenset[str]
    qualifiers: frozenset[str]
    senses: frozenset[str]
    collocations: frozenset[str]
    not_terms: frozenset[str]
    not_term_prefixes: tuple[str, ...]
    headword: dict[str, dict[str, str]]

    def handles(self, heading: str) -> bool:
        return heading in self.sections or heading in self.collocation_sections


@cache
def config() -> Config:
    path = resources.files("polwikt.data").joinpath("relations.toml")
    data: dict[str, Any] = tomllib.loads(path.read_text("utf-8"))
    sections = dict(data["sections"])
    collocations = frozenset(sections.pop("collocations"))
    t = data["templates"]
    return Config(
        sections=sections,
        collocation_sections=collocations,
        columns=frozenset(t["columns"]),
        links=frozenset(t["links"]),
        alternatives=frozenset(t["alternatives"]),
        rendered=frozenset(t["rendered"]),
        qualifiers=frozenset(t["qualifiers"]),
        senses=frozenset(t["senses"]),
        collocations=frozenset(t["collocations"]),
        not_terms=frozenset(t["not_terms"]),
        not_term_prefixes=tuple(t["not_term_prefixes"]),
        headword={k: dict(v) for k, v in data["headword"].items()},
    )


@dataclass
class Term:
    term: str
    labels: list[str] = field(default_factory=list)
    gloss: str = ""


@dataclass
class Found:
    relations: list[pb.Relation] = field(default_factory=list)
    examples: list[pb.Example] = field(default_factory=list)


def terms(value: str, labels: LabelIndex, stats: Counter[str]) -> list[Term]:
    """A list parameter: comma-separated terms with inline <q:…>/<l:…>/<t:…>."""
    out: list[Term] = []
    for raw in split_on_comma(value):
        if raw.strip():
            out.append(_modified(raw, labels, stats))
    return out


def _modified(raw: str, labels: LabelIndex, stats: Counter[str]) -> Term:
    term, modifiers = split_modifiers(raw)
    found: list[str] = []
    for key in ("q", "qq"):
        if modifiers.get(key):
            found.append(plain_text(modifiers[key]))
    for key in ("l", "ll"):
        if given := modifiers.get(key):
            found += [lab.name for lab in labels.parse_args([given], stats)]
    gloss = modifiers.get("t") or modifiers.get("gloss") or ""
    return Term(plain_text(term), found, plain_text(gloss))


def headword_relations(
    template: str,
    args: dict[str, str],
    labels: LabelIndex,
    drop: frozenset[str],
    stats: Counter[str],
) -> list[pb.Relation]:
    """{{pl-noun|f|dim=uliczka|abbr=ul.}} -> diminutive and abbreviation Relations."""
    out: list[pb.Relation] = []
    for param, type_name in config().headword.get(template, {}).items():
        for key in numbered(args, param):
            for t in terms(args[key], labels, stats):
                if t.term in _NOT_A_TERM:  # adv=-: no adverb
                    continue
                if relation := _relation(type_name, t, drop, stats):
                    out.append(relation)
    return out


def numbered(args: dict[str, str], param: str) -> list[str]:
    """`pf`, `pf2`, `pf3`, … in order: a list parameter's keys present in `args`."""
    keys = [param] if param in args else []
    n = 2
    while f"{param}{n}" in args:
        keys.append(f"{param}{n}")
        n += 1
    return keys


def _relation(
    type_name: str, t: Term, drop: frozenset[str], stats: Counter[str]
) -> pb.Relation | None:
    if hit := sorted(drop.intersection(t.labels)):
        kind = "alternative_form" if type_name == _ALTERNATIVE else "relation"
        for label in hit:
            stats[f"dropped.{kind}.{label}"] += 1
        return None
    return pb.Relation(
        type=type_name,
        term=t.term,
        gloss=t.gloss,
        labels=list(dict.fromkeys(t.labels)),
    )


@dataclass
class RelationParser:
    """Reads one relation section of a page into Relations and examples."""

    wtp: PolwiktWtp
    canonical: Canonical
    labels: LabelIndex
    drop: frozenset[str]
    stats: Counter[str]
    example: ExampleFn

    def section(self, heading: str, node: WikiNode) -> Found:
        cfg = config()
        type_name = cfg.sections.get(heading, "")
        found = Found()
        loose: list[WikiNode | str] = []
        for child in node.children:
            if isinstance(child, WikiNode) and child.kind == NodeKind.LIST:
                self._line(type_name, loose, found)
                loose = []
                self._list(type_name, child, found)
            elif isinstance(child, WikiNode) and str(child.kind.name).startswith(
                "LEVEL"
            ):
                continue
            else:
                loose.append(child)
        self._line(type_name, loose, found)
        return found

    def _list(self, type_name: str, node: WikiNode, found: Found) -> None:
        for item in node.children:
            if not (isinstance(item, WikiNode) and item.kind == NodeKind.LIST_ITEM):
                continue
            own = [c for c in item.children if not _is_list(c)]
            self._line(type_name, own, found)
            for sub in item.children:
                if _is_list(sub):
                    assert isinstance(sub, WikiNode)
                    self._list(type_name, sub, found)

    def _line(
        self, type_name: str, nodes: Sequence[WikiNode | str], found: Found
    ) -> None:
        cfg = config()
        line_labels: list[str] = []
        gloss = ""
        listed: list[Term] = []
        text: list[str] = []
        for node in nodes:
            if isinstance(node, str):
                text.append(node)
                continue
            if node.kind == NodeKind.LINK:
                listed += self._raw_links(self.wtp.node_to_wikitext(node))
                continue
            if node.kind != NodeKind.TEMPLATE:
                text.append(self.wtp.node_to_wikitext(node))
                continue
            name = self.canonical(self.wtp, node)
            args = template_args(self.wtp, node)
            values = positional(args)
            if name in cfg.qualifiers:
                line_labels += self._qualifier(name, values)
            elif name in cfg.senses:
                gloss = plain_text(values[0]) if values else ""
            elif name in cfg.links:
                listed += self._linked(name, args, values)
            elif name in cfg.alternatives:
                listed += self._alternatives(values)
            elif name in cfg.columns:
                for item in values[1:]:
                    listed += self._column_item(item)
            elif name in cfg.rendered:
                listed += self._rendered(node)
            elif name in cfg.collocations:
                kind = pb.Example.Kind.KIND_COLLOCATION
                if example := self.example(kind, args):
                    found.examples.append(example)
            elif name in cfg.not_terms or name.startswith(cfg.not_term_prefixes):
                self.stats[f"relation.not_terms.{name}"] += 1
            else:
                self.stats[f"relation.template.unknown.{name}"] += 1
        # "* {{alt|pl|Starenga}} (rare)": a written-out qualifier.
        line_labels += [
            t for m in _PARENTHETICAL.findall(plain_text("".join(text))) if (t := m)
        ]
        if listed and not type_name:
            self.stats["relation.in_collocations"] += len(listed)
            return
        for t in listed:
            t.labels = [*line_labels, *t.labels]
            t.gloss = t.gloss or gloss
            if relation := _relation(type_name, t, self.drop, self.stats):
                found.relations.append(relation)
        if not listed and plain_text("".join(text)) and type_name:
            self.stats["relation.line.untemplated"] += 1

    def _qualifier(self, name: str, values: list[str]) -> list[str]:
        if name == "label":  # {{lb|pl|colloquial}}: the language first
            return [lab.name for lab in self.labels.parse_args(values[1:], self.stats)]
        return [t for v in values if (t := plain_text(v))]

    def _linked(self, name: str, args: dict[str, str], values: list[str]) -> list[Term]:
        if not values or values[0] != LANG:
            self.stats["relation.other_language"] += 1
            return []
        if name in ("link", "mention"):  # {{l|pl|term|display|gloss}}
            if len(values) < 2:
                return []
            t = _modified(values[1], self.labels, self.stats)
            t.gloss = t.gloss or plain_text(
                args.get("t")
                or args.get("gloss")
                or (values[3] if len(values) > 3 else "")
            )
            return self._kept([t])
        return self._kept([_modified(v, self.labels, self.stats) for v in values[1:]])

    def _alternatives(self, values: list[str]) -> list[Term]:
        """{{alter|pl|dil|dyl||dialectal}}: terms, then labels after the gap."""
        rest = values[1:]
        gap = rest.index("") if "" in rest else len(rest)
        given = [
            lab.name for lab in self.labels.parse_args(rest[gap + 1 :], self.stats)
        ]
        found = [_modified(v, self.labels, self.stats) for v in rest[:gap]]
        for t in found:
            t.labels += given
        return self._kept(found)

    def _column_item(self, item: str) -> list[Term]:
        """`kotek<q:rare>`, or raw links: `[[biec]] {{g|impf}}, [[pobiec]] {{g|pf}}`."""
        if "[[" in item:
            return self._raw_links(item)
        if "{{" in item:
            self.stats["relation.column.templated_item"] += 1
            return self._kept(
                [Term(t) for t in rendered.terms(self._expand(item), LANG)]
            )
        return self._kept(
            [_modified(sub, self.labels, self.stats) for sub in subitems(item)]
        )

    def _raw_links(self, wikitext: str) -> list[Term]:
        out: list[Term] = []
        for target in _RAW_LINK.findall(wikitext):
            target = target.strip().lstrip(":").split("#", 1)[0]
            if ":" in target:  # [[Thesaurus:bić]], [[w:…]]: not a Polish term
                self.stats[f"relation.link.{target.split(':', 1)[0]}"] += 1
                continue
            out.append(Term(target))
        return self._kept(out)

    def _rendered(self, node: WikiNode) -> list[Term]:
        """A module-built list: each <li> holds terms and their qualifiers."""
        html = self._expand(self.wtp.node_to_wikitext(node))
        out: list[Term] = []
        for li in _LI.findall(html):
            for part in rendered.term_separator(LANG).split(li):
                if term := rendered.term_pattern(LANG).search(part):
                    out.append(Term(plain_text(term.group(1)), rendered.labels(part)))
        return self._kept(out)

    def _expand(self, wikitext: str) -> str:
        return expand_text(self.wtp, wikitext).text

    def _kept(self, found: list[Term]) -> list[Term]:
        out: list[Term] = []
        for t in found:
            if t.term in _NOT_A_TERM:
                continue
            if t.term.startswith("Thesaurus:"):
                self.stats["relation.thesaurus"] += 1
                continue
            out.append(t)
        return out


def subitems(item: str) -> list[str]:
    """`a,b` and `a~b` in a {{col}} item are two terms (Module:columns); `, ` is not a
    delimiter, nor is anything inside <…> modifiers."""
    parts, depth, start = [], 0, 0
    for i, char in enumerate(item):
        depth += (char == "<") - (char == ">")
        nxt = item[i + 1 : i + 2]
        if depth == 0 and (char == "~" or (char == "," and nxt and not nxt.isspace())):
            parts.append(item[start:i])
            start = i + 1
    return [p for p in (*parts, item[start:]) if p.strip()]


def _is_list(node: WikiNode | str) -> bool:
    return isinstance(node, WikiNode) and node.kind == NodeKind.LIST


def add_unique(
    entry: pb.Entry, relations: Sequence[pb.Relation], stats: Counter[str]
) -> None:
    """Appends each relation the entry doesn't already have (type, term, gloss)."""
    seen = {(r.type, r.term, r.gloss) for r in entry.relations}
    for relation in relations:
        key = (relation.type, relation.term, relation.gloss)
        if key in seen:
            stats["relation.duplicate"] += 1
            continue
        seen.add(key)
        entry.relations.append(relation)
