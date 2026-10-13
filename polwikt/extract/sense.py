"""One sense list item to a Sense: gloss, labels, keywords, examples, nyms (R6.6-R6.14).

Labels come from `{{lb}}` and qualifiers inside the item and are split by kind (R6.7);
keywords are the gloss's own links, taxonomic ones flagged (R6.14); `{{+obj}}` is
government (R6.11); form-of templates fill `form_of` (R6.6). `#:` lines carry
examples, collocations and sense-scoped nyms (R6.9, R6.12, R6.4); `#*` lines
quotations. A sense with a `drop_labels` label is dropped whole, subsenses included
(R6.6a), and reported to the caller.
"""

from __future__ import annotations

import re
import tomllib
from collections import Counter
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
from typing import Any

from wikitextprocessor import NodeKind, WikiNode

from polwikt.expand.policy import Policy
from polwikt.expand.run import expand_text
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.labels import Kind, Label, LabelIndex, topic_categories
from polwikt.extract.tags import TagIndex, to_grammatical
from polwikt.parse.text import one_line, plain_text
from polwikt.proto import polwikt_pb2 as pb

_FORM_TYPES = {
    "inflection": pb.FormOf.Type.TYPE_INFLECTION,
    "alternative_form": pb.FormOf.Type.TYPE_ALTERNATIVE_FORM,
    "synonym": pb.FormOf.Type.TYPE_SYNONYM,
    "abbreviation": pb.FormOf.Type.TYPE_ABBREVIATION,
    "derivation": pb.FormOf.Type.TYPE_DERIVATION,
}
_LABEL_TEMPLATES = frozenset({"label", "term-label"})
_QUALIFIER_TEMPLATES = frozenset({"qualifier", "sense"})
_EXAMPLE_TEMPLATES = frozenset({"ux", "uxi", "uxa"})
_COLLOCATION_TEMPLATES = frozenset({"coi", "collocation", "coa"})
_NYMS = {
    "synonyms": pb.Relation.Type.TYPE_SYNONYM,
    "parasynonyms": pb.Relation.Type.TYPE_SYNONYM,
    "antonyms": pb.Relation.Type.TYPE_ANTONYM,
    "hypernyms": pb.Relation.Type.TYPE_HYPERNYM,
    "hyponyms": pb.Relation.Type.TYPE_HYPONYM,
    "coordinate terms": pb.Relation.Type.TYPE_COORDINATE,
    "meronyms": pb.Relation.Type.TYPE_MERONYM,
    "holonyms": pb.Relation.Type.TYPE_HOLONYM,
    "inline alt forms": pb.Relation.Type.TYPE_ALTERNATIVE_FORM,
}
_TAXONOMIC_TEMPLATES = frozenset({"taxfmt", "taxlink"})
_LINK_TEMPLATES = frozenset({"link", "mention"})
_CASES = {
    "nom": pb.Case.CASE_NOMINATIVE,
    "gen": pb.Case.CASE_GENITIVE,
    "dat": pb.Case.CASE_DATIVE,
    "acc": pb.Case.CASE_ACCUSATIVE,
    "ins": pb.Case.CASE_INSTRUMENTAL,
    "loc": pb.Case.CASE_LOCATIVE,
    "voc": pb.Case.CASE_VOCATIVE,
}
# A {{+obj}} slot without its <…> groups: ":do(gen)", "acc", "inf".
_OBJ = re.compile(r"^(?::(?P<prep>[^()<>]+)\((?P<case>[^()]*)\)|(?P<bare>[^<>]*))$")
_KEYED = re.compile(r"^\w+:")  # <q:stylized>, <l:Kraków>: modifiers, not the slot
_OBJ_CONNECTORS = frozenset({"or", "and", "_", ",", ";"})
# Inline modifiers on a term: "kocur<q:colloquial><t:tomcat>".
_MODIFIER = re.compile(r"<(\w+):([^<>]*)>")
_WIKIPEDIA_PREFIX = re.compile(r"^w:(?:[a-z-]+:)?")
_QUOTE_TEXT = ("passage", "text")
_QUOTE_TRANSLATION = ("translation", "t")
_RQ_TEXT = re.compile(r"textparam\s*=\s*([^|}\s]+)")
_RQ_TRANSLATION = re.compile(r"\|\s*(?:t|translation)\s*=\s*\{\{\{([^|}]+)")


@dataclass(frozen=True)
class FormOfRule:
    type: pb.FormOf.Type
    lemma: str
    tags_from: int | None
    tags: tuple[str, ...]
    raw: tuple[str, ...]
    raw_from: str | None
    append: tuple[str, ...] = ()


@cache
def form_of_rules() -> dict[str, FormOfRule]:
    text = resources.files("polwikt.data").joinpath("form_of.toml").read_text("utf-8")
    return {
        name: FormOfRule(
            type=_FORM_TYPES[rule["type"]],
            lemma=rule["lemma"],
            tags_from=rule.get("tags_from"),
            tags=tuple(rule.get("tags", ())),
            raw=tuple(rule.get("raw", ())),
            raw_from=rule.get("raw_from"),
            append=tuple(rule.get("append", ())),
        )
        for name, rule in tomllib.loads(text)["templates"].items()
    }


@dataclass
class Indexes:
    """Wiktionary data the sense parser reads; built once per worker, before a page."""

    labels: LabelIndex
    tags: TagIndex
    drop: frozenset[str]  # drop_labels, canonicalised through the label data (R6.6b)


def indexes(wtp: PolwiktWtp, drop_labels: frozenset[str]) -> Indexes:
    cached: Indexes | None = wtp.extract_cache.get("indexes")
    if cached is None or cached.drop != _canonical_drop(cached.labels, drop_labels):
        labels = LabelIndex(wtp)
        cached = Indexes(labels, TagIndex(wtp), _canonical_drop(labels, drop_labels))
        wtp.extract_cache["indexes"] = cached
    return cached


def _canonical_drop(labels: LabelIndex, drop_labels: frozenset[str]) -> frozenset[str]:
    return frozenset(labels.classify(d).name for d in drop_labels)


@dataclass
class Dropped:
    """A sense removed by drop_labels (R6.6a), for the caller's counts and report."""

    labels: list[str]
    colabelled: bool  # it carried another label too (R6.6c)
    senses: int  # itself plus its subsenses


@dataclass
class SenseParser:
    wtp: PolwiktWtp
    policy: Policy
    index: Indexes
    stats: Counter[str]
    canonical: Any  # (wtp, node) -> canonical template name
    dropped: list[Dropped] = field(default_factory=list)

    def parse(self, item: WikiNode) -> pb.Sense | None:
        sense = pb.Sense()
        parts: list[str] = []
        labels: list[Label] = []
        sub_items: list[WikiNode] = []
        for child in item.children:
            if isinstance(child, str):
                parts.append(child)
                continue
            if child.kind == NodeKind.LIST:
                self._sublist(sense, item, child, sub_items)
                continue
            if child.kind == NodeKind.LINK:
                self._keyword_from_link(sense, child)
            elif child.kind == NodeKind.TEMPLATE:
                name = self.canonical(self.wtp, child)
                args = template_args(self.wtp, child)
                if name in _QUALIFIER_TEMPLATES and plain_text("".join(parts)).strip():
                    # After gloss text a qualifier qualifies the word before it ("he
                    # (for animate nouns), it (…)"): it stays in the text (R6.7).
                    inline = ", ".join(
                        t for v in positional(args) if (t := plain_text(v))
                    )
                    parts.append(f"({inline})")
                    self.stats["sense.qualifier.inline"] += 1
                    continue
                if not self._template(sense, labels, name, args, child):
                    continue  # not part of the gloss text
            parts.append(self.wtp.node_to_wikitext(child))

        expanded = expand_text(self.wtp, "".join(parts)).text
        sense.gloss = one_line(plain_text(expanded))
        for topic in topic_categories(expanded):  # {{place}}, {{tcl}} (R6.10)
            if topic not in sense.topics:
                sense.topics.append(topic)
        self._labels(sense, labels)
        hit = sorted(self.index.drop.intersection(_names(labels)))
        if hit:
            others = [n for n in _names(labels) if n not in self.index.drop]
            self.dropped.append(Dropped(hit, bool(others), 1 + _count(sub_items)))
            return None
        for sub in sub_items:
            if (child_sense := self.parse(sub)) is not None:
                sense.subsenses.append(child_sense)
        if not sense.gloss and not sense.subsenses:
            self.stats["sense.empty"] += 1
            return None
        self.stats["senses" if len(item.sarg) == 1 else "subsenses"] += 1
        return sense

    # -- the gloss line -----------------------------------------------------------

    def _template(
        self,
        sense: pb.Sense,
        labels: list[Label],
        name: str,
        args: dict[str, str],
        node: WikiNode,
    ) -> bool:
        """Takes what a gloss-line template carries; True if it stays in the text."""
        if name in _LABEL_TEMPLATES:
            labels.extend(
                self.index.labels.parse_args(positional(args)[1:], self.stats)
            )
        elif name in _QUALIFIER_TEMPLATES:
            labels.extend(
                Label(plain_text(v), Kind.LABEL, False) for v in positional(args) if v
            )
        elif name == "+obj":
            sense.government.extend(self._government(positional(args)[1:]))
        elif name in _TAXONOMIC_TEMPLATES:
            if text := plain_text(positional(args)[0] if positional(args) else ""):
                _add_keyword(sense, text, taxonomic=True)
        elif name == "transclude":  # {{tcl|pl|apple|id=Q89}}: the gloss *is* "apple"
            values = positional(args)
            if len(values) >= 2 and values[1]:
                source = plain_text(values[1].split("#", 1)[0])
                _add_keyword(sense, source, taxonomic=False)
        elif name in _LINK_TEMPLATES:
            values = positional(args)
            if len(values) >= 2 and values[0] == "en" and values[1]:
                _add_keyword(sense, plain_text(values[1]), taxonomic=False)
        elif (rule := form_of_rules().get(name)) is not None:
            self._form_of(sense, rule, args)
        if name in ("gloss", "non-gloss"):
            self._taxonomic_inside(sense, node)  # scientific names in a parenthesis
        return self.policy.in_gloss(name)

    def _labels(self, sense: pb.Sense, labels: list[Label]) -> None:
        for label in labels:
            if label.kind is Kind.TOPIC:  # "music" files the sense under "Music"
                for topic in label.topics:
                    if topic not in sense.topics:
                        sense.topics.append(topic)
                continue
            target = sense.regions if label.kind is Kind.REGION else sense.labels
            if label.name and label.name not in target:
                target.append(label.name)

    def _keyword_from_link(self, sense: pb.Sense, node: WikiNode) -> None:
        target = "".join(p for p in node.largs[0] if isinstance(p, str)).strip()
        page, _, anchor = target.partition("#")
        page = page.strip()
        if not page or ":" in page:  # w:Poland, Appendix:Glossary — not English terms
            return
        _add_keyword(sense, page, taxonomic=anchor.strip() == "Translingual")

    def _taxonomic_inside(self, sense: pb.Sense, node: WikiNode) -> None:
        for arg in node.largs[1:]:
            for part in arg:
                if isinstance(part, WikiNode) and part.kind == NodeKind.TEMPLATE:
                    inner = self.canonical(self.wtp, part)
                    if inner in _TAXONOMIC_TEMPLATES:
                        values = positional(template_args(self.wtp, part))
                        if values and (text := plain_text(values[0])):
                            _add_keyword(sense, text, taxonomic=True)

    def _government(self, values: list[str]) -> list[pb.Government]:
        """{{+obj}} slots. " + " joins objects taken together, "/" alternatives:
        "dat<to whom> + :o(loc)<about what>", ":z(gen)/:w(loc)<at what>"."""
        out: list[pb.Government] = []
        for written in values:
            written = written.strip()
            if not written or written in _OBJ_CONNECTORS:
                continue
            for joint in _split_outside_angles(written, "+"):
                alternatives = [a.strip() for a in _split_outside_angles(joint, "/")]
                _, shared = _angle_groups(alternatives[-1])
                for alternative in alternatives:
                    base, groups = _angle_groups(alternative)
                    out.append(self._slot(base, groups or shared))
        return out

    def _slot(self, base: str, groups: list[str]) -> pb.Government:
        """One slot: "acc" + ["what"], ":do(gen)" + ["to what"], "ins" + ["q:stylized"].
        Groups written `key:value` are modifiers (q, qq, t, l), not the description."""
        modifiers = {
            g.split(":", 1)[0]: g.split(":", 1)[1] for g in groups if _KEYED.match(g)
        }
        description = " ".join(g for g in groups if not _KEYED.match(g)).strip()
        m = _OBJ.match(base.strip())
        case_name = (m.group("case") or m.group("bare") or "").strip() if m else ""
        gov = pb.Government(
            preposition=(m.group("prep") or "").strip() if m else "",
            description=plain_text(description or modifiers.get("t", "")),
        )
        if case_name in _CASES:
            gov.grammatical_case = _CASES[case_name]
        else:  # "inf", ":że": no case enum; keep the slot as written (invariant 4)
            written = case_name or base.strip()
            gov.description = (
                f"{written}: {gov.description}" if gov.description else written
            )
            self.stats["government.no_case"] += 1
        return gov

    def _form_of(self, sense: pb.Sense, rule: FormOfRule, args: dict[str, str]) -> None:
        lemma = plain_text(split_modifiers(args.get(rule.lemma, ""))[0])  # bać<id:…>
        lemma = _WIKIPEDIA_PREFIX.sub("", lemma)  # {{acronym of|pl|w:pl:Naczelna …}}
        if not lemma:
            self.stats["form_of.no_lemma"] += 1
            return
        form = pb.FormOf(type=rule.type, lemma=lemma)
        raw: list[str] = list(rule.raw)
        if rule.raw_from and (desc := plain_text(args.get(rule.raw_from, ""))):
            raw.append(desc)
        if rule.tags_from is not None:
            values = positional(args)[rule.tags_from - 1 :]
            parsed = self.index.tags.parse(values, append=rule.append)
            form.tag_sets.extend(parsed.sets)
            raw.extend(parsed.raw)
        if rule.tags:
            fixed, unmapped = to_grammatical(list(rule.tags))
            form.tag_sets.append(fixed)
            raw.extend(unmapped)
        form.raw_tags.extend(dict.fromkeys(raw))
        if form.raw_tags:
            self.stats["form_of.raw_tags"] += len(form.raw_tags)
        sense.form_of.CopyFrom(form)
        self.stats[f"form_of.{pb.FormOf.Type.Name(rule.type)}"] += 1

    # -- lines under the sense ----------------------------------------------------

    def _sublist(
        self, sense: pb.Sense, item: WikiNode, node: WikiNode, sub_items: list[WikiNode]
    ) -> None:
        marker = node.sarg
        items = [c for c in node.children if isinstance(c, WikiNode)]
        if re.fullmatch(r"#+", marker) and len(marker) > len(item.sarg):
            sub_items.extend(c for c in items if c.kind == NodeKind.LIST_ITEM)
        elif marker.endswith(":") and not marker.endswith("*:"):
            for line in items:
                self._example_line(sense, line)
        elif marker.endswith("*"):
            for line in items:
                self._quotation_line(sense, line)

    def _example_line(self, sense: pb.Sense, line: WikiNode) -> None:
        templates = [
            c
            for c in line.children
            if isinstance(c, WikiNode) and c.kind == NodeKind.TEMPLATE
        ]
        handled = False
        for node in templates:
            name = self.canonical(self.wtp, node)
            args = template_args(self.wtp, node)
            if name in _EXAMPLE_TEMPLATES or name in _COLLOCATION_TEMPLATES:
                kind = (
                    pb.Example.Kind.KIND_EXAMPLE
                    if name in _EXAMPLE_TEMPLATES
                    else pb.Example.Kind.KIND_COLLOCATION
                )
                if example := self.example(kind, args):
                    sense.examples.append(example)
                handled = True
            elif name in _NYMS:
                sense.relations.extend(self._nyms(_NYMS[name], args))
                handled = True
        if not handled and not templates:  # a hand-written example: "''Pies.'' ― Dog."
            text = one_line(plain_text(self.wtp.node_to_wikitext(line)))
            if text:
                polish, _, english = text.partition("―")
                sense.examples.append(
                    pb.Example(
                        kind=pb.Example.Kind.KIND_EXAMPLE,
                        text=polish.strip(),
                        translation=english.strip(),
                    )
                )
                self.stats["example.untemplated"] += 1

    def example(self, kind: pb.Example.Kind, args: dict[str, str]) -> pb.Example | None:
        values = positional(args)
        text = self._text(values[1] if len(values) > 1 else "")
        if not text:
            return None
        translation = (
            args.get("t")
            or args.get("translation")
            or (values[2] if len(values) > 2 else "")
        )
        return pb.Example(
            kind=kind,
            text=text,
            translation=self._text(translation),
            literal=self._text(args.get("lit", "")),
        )

    def _quotation_line(self, sense: pb.Sense, line: WikiNode) -> None:
        for node in line.children:
            if not isinstance(node, WikiNode) or node.kind != NodeKind.TEMPLATE:
                continue
            name = self.canonical(self.wtp, node)
            if not (
                name.startswith("quote-") or name.startswith("RQ:") or name == "quote"
            ):
                continue
            args = template_args(self.wtp, node)
            text_keys, translation_keys = self._quote_params(name)
            text = self._text(next((args[k] for k in text_keys if args.get(k)), ""))
            if not text:
                self.stats["quotation.no_text"] += 1
                continue
            translation = next(
                (
                    args[k]
                    for k in translation_keys
                    if args.get(k) not in ("", "-", None)
                ),
                "",
            )
            sense.examples.append(
                pb.Example(
                    kind=pb.Example.Kind.KIND_QUOTATION,
                    text=text,
                    translation=self._text(translation),
                    literal=self._text(args.get("lit", "")),
                    source=self._source(name, args, node),
                )
            )

    def _quote_params(self, name: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Where a quotation template takes its passage and translation. An
        {{RQ:pl:…}} declares it in its call to Module:quote (`textparam=2`,
        `t={{{4|}}}`); read once per template and cached for the worker."""
        if not name.startswith("RQ:"):
            return _QUOTE_TEXT, _QUOTE_TRANSLATION
        cache: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = (
            self.wtp.extract_cache.setdefault("rq_params", {})
        )
        if name not in cache:
            page = self.wtp.get_page(name, 10)
            body = (page.body if page is not None else "") or ""
            text = _RQ_TEXT.search(body)
            trans = _RQ_TRANSLATION.search(body)
            cache[name] = (
                ((text.group(1),) if text else ()) + _QUOTE_TEXT,
                ((trans.group(1),) if trans else ()) + _QUOTE_TRANSLATION,
            )
        return cache[name]

    def _source(self, name: str, args: dict[str, str], node: WikiNode) -> str:
        """A one-line citation: "Henryk Sienkiewicz, Potop (1886)" (R6.9)."""
        if name.startswith(
            "RQ:"
        ):  # the work is in the template; render it sans passage
            text_keys, translation_keys = self._quote_params(name)
            kept = {
                k: v for k, v in args.items() if k not in text_keys + translation_keys
            }
            call = (
                "{{"
                + _written_name(node)
                + "".join(f"|{k}={v}" for k, v in kept.items())
                + "}}"
            )
            return (
                one_line(plain_text(expand_text(self.wtp, call).text))
                .rstrip(":")
                .strip()
            )
        author = _no_wiki_prefix(
            self._text(args.get("author") or args.get("last") or "")
        )
        work = self._text(
            args.get("title") or args.get("work") or args.get("journal") or ""
        )
        year = self._text(args.get("year") or args.get("date") or "")
        if (
            not (author or work or year) and "2" in args
        ):  # quote-book|pl|YEAR|AUTHOR|TITLE
            year = self._text(args.get("2", ""))
            author = self._text(args.get("3", ""))
            work = self._text(args.get("4", ""))
        head = ", ".join(p for p in (author, work) if p)
        return f"{head} ({year})" if year and head else head or year

    def _nyms(self, kind: pb.Relation.Type, args: dict[str, str]) -> list[pb.Relation]:
        out: list[pb.Relation] = []
        for value in positional(args)[1:]:
            term, modifiers = split_modifiers(value)
            if not term or term in ("_", ";", ","):
                continue
            if term.startswith("Thesaurus:"):
                self.stats["relation.thesaurus"] += 1
                continue
            relation = pb.Relation(type=kind, term=plain_text(term))
            relation.gloss = plain_text(
                modifiers.get("t", "") or modifiers.get("gloss", "")
            )
            for key in ("q", "qq"):
                if modifiers.get(key):
                    relation.labels.append(plain_text(modifiers[key]))
            out.append(relation)
        return out

    def _text(self, wikitext: str) -> str:
        if not wikitext:
            return ""
        if "{{" in wikitext:
            wikitext = expand_text(self.wtp, wikitext).text
        return one_line(plain_text(wikitext))


def template_args(wtp: PolwiktWtp, node: WikiNode) -> dict[str, str]:
    """A call's arguments as raw wikitext, positional ones keyed "1", "2", …"""
    out: dict[str, str] = {}
    position = 0
    for arg in node.largs[1:]:
        raw = "".join(p if isinstance(p, str) else wtp.node_to_wikitext(p) for p in arg)
        key, sep, value = raw.partition("=")
        if sep and key.strip() and not any(c in key for c in "{}[]|<\n"):
            out[key.strip()] = value.strip()
        else:
            position += 1
            out[str(position)] = raw.strip()
    return out


def positional(args: dict[str, str]) -> list[str]:
    numbered = sorted((int(k), v) for k, v in args.items() if k.isdigit())
    return [v for _, v in numbered]


def split_modifiers(value: str) -> tuple[str, dict[str, str]]:
    """'kocur<q:colloquial><t:tomcat>' -> ('kocur', {'q': …, 't': 'tomcat'})."""
    modifiers = {m.group(1): m.group(2) for m in _MODIFIER.finditer(value)}
    return _MODIFIER.sub("", value).strip(), modifiers


def _no_wiki_prefix(text: str) -> str:
    """`author=w:Adam Mickiewicz` is Wikipedia-link shorthand, not part of the name."""
    return re.sub(r"^(?:w|wikipedia):", "", text)


def _angle_groups(text: str) -> tuple[str, list[str]]:
    """'dat<l:Kraków,from <<German>>><to what>' -> ('dat', ['l:…', 'to what'])."""
    base: list[str] = []
    groups: list[str] = []
    depth, start = 0, 0
    for i, char in enumerate(text):
        if char == "<":
            if depth == 0:
                start = i + 1
            depth += 1
        elif char == ">" and depth:
            depth -= 1
            if depth == 0:
                groups.append(text[start:i])
        elif depth == 0:
            base.append(char)
    return "".join(base), groups


def _split_outside_angles(text: str, separator: str) -> list[str]:
    parts, depth, start = [], 0, 0
    for i, char in enumerate(text):
        depth += (char == "<") - (char == ">")
        if char == separator and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    return [*parts, text[start:]]


def _written_name(node: WikiNode) -> str:
    return "".join(p for p in node.largs[0] if isinstance(p, str)).strip()


def _names(labels: list[Label]) -> list[str]:
    return [label.name for label in labels]


def _count(items: list[WikiNode]) -> int:
    total = 0
    for item in items:
        total += 1
        for child in item.children:
            if (
                isinstance(child, WikiNode)
                and child.kind == NodeKind.LIST
                and re.fullmatch(r"#+", child.sarg)
            ):
                total += _count([c for c in child.children if isinstance(c, WikiNode)])
    return total


def _add_keyword(sense: pb.Sense, text: str, *, taxonomic: bool) -> None:
    text = " ".join(text.split())
    if text and all(k.text != text for k in sense.keywords):
        sense.keywords.append(pb.Keyword(text=text, taxonomic=taxonomic))
