"""Headword-line grammar from the call's arguments (R4.2 "both", R6.1, R6.3).

{{pl-noun}} / {{pl-proper noun}}: genders with animacy, plurale tantum, indeclinable.
{{pl-adj}} / {{pl-adv}}: comparison as Module:zlw-lch-headword builds it — the
comparatives in arg 1 (`-` alone: not comparable; `peri`: periphrastic), the
superlatives in `sup=` or derived from each comparative — as Forms of a comparison
table, so `lepszy` is searchable like any declined form.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from polwikt.extract.inflection import config
from polwikt.extract.labels import LabelIndex, split_on_comma
from polwikt.extract.relations import numbered, terms
from polwikt.extract.sense import positional, split_modifiers
from polwikt.extract.tags import to_grammatical
from polwikt.proto import polwikt_pb2 as pb

NOUN_TEMPLATES = frozenset({"pl-noun", "pl-proper noun"})


def comparison_templates() -> frozenset[str]:
    return frozenset(config().headword["comparison"]["templates"])


def verb_templates() -> frozenset[str]:
    return frozenset(config().headword["verb"]["templates"])


def truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() not in ("", "0", "no", "false")


def noun_info(args: dict[str, str], stats: Counter[str]) -> pb.NounInfo:
    """`m-anml,m-in` -> two genders; `nv-p` -> nonvirile, plurale tantum (R6.1)."""
    cfg = config().headword
    info = pb.NounInfo(indeclinable=truthy(args.get("indecl")))
    spec = positional(args)[0] if positional(args) else ""
    for written in (c.strip() for c in split_on_comma(spec)):
        code, modifiers = split_modifiers(written)  # f<l:proscribed>
        if not code:
            continue
        if modifiers:
            stats["headword.gender.qualified"] += 1  # NounInfo has no labels
        unattested = code.endswith("!")
        parts = code.rstrip("!").split("-")
        tags: list[str] = []
        for i, part in enumerate(parts):
            if i == 0 and part in cfg["genders"]:
                tags.append(cfg["genders"][part])
            elif i > 0 and part in cfg["animacy"] and not unattested:
                tags.append(cfg["animacy"][part])
            elif i > 0 and part == "p":
                info.plurale_tantum = True
            elif not (unattested and part in cfg["animacy"]):
                stats[f"headword.gender.unknown.{code}"] += 1
        if unattested:
            stats["headword.animacy_unattested"] += 1
        grammatical, _ = to_grammatical(tags)
        pair = pb.GenderAnimacy(gender=grammatical.gender, animacy=grammatical.animacy)
        if pair.gender and pair not in info.genders:
            info.genders.append(pair)
    return info


def verb(
    args: dict[str, str],
    labels: LabelIndex,
    drop: frozenset[str],
    stats: Counter[str],
) -> tuple[pb.VerbInfo, list[pb.Relation]]:
    """{{pl-verb|impf|pf=zrobić}} -> aspect, motion, counterparts (R6.2, R3.14)."""
    cfg = config().headword["verb"]
    info = pb.VerbInfo(defective=truthy(args.get("def")))
    aspects: list[str] = []
    for spec, _ in _terms(args.get("1", ""), labels, stats):
        if spec == "?":
            continue
        if spec not in cfg["aspects"]:
            stats[f"headword.aspect.unknown.{spec}"] += 1
            continue
        aspects.append(cfg["aspects"][spec])
        if spec in cfg["motion"]:
            motion = cfg["motion"][spec]
            info.MergeFrom(pb.VerbInfo(motion=f"MOTION_{motion.upper()}"))
        if spec in cfg["frequentative"]:
            info.frequentative = True
    distinct = set(aspects)
    if len(distinct) > 1:
        distinct = {"biaspectual"}  # {{pl-verb|impf,pf}}
    if distinct:
        info.aspect = to_grammatical(list(distinct))[0].aspect
    relations: list[pb.Relation] = []
    for param, type_name in cfg["relations"].items():
        for key in numbered(args, param):
            for t in terms(args[key], labels, stats):
                term, term_labels, gloss = t.term, t.labels, t.gloss
                if hit := sorted(drop.intersection(term_labels)):
                    for label in hit:
                        stats[f"dropped.relation.{label}"] += 1
                    continue
                relations.append(
                    pb.Relation(
                        type=type_name,
                        term=term,
                        gloss=gloss,
                        labels=list(dict.fromkeys(term_labels)),
                    )
                )
    return info, relations


@dataclass
class Comparison:
    info: pb.AdjectiveInfo
    forms: list[pb.Form] = field(default_factory=list)

    def table(self) -> pb.InflectionTable:
        return pb.InflectionTable(
            kind=pb.InflectionTable.Kind.KIND_COMPARISON,
            title=config().headword["comparison"]["title"],
        )


def comparison(
    lemma: str,
    args: dict[str, str],
    labels: LabelIndex,
    drop: frozenset[str],
    stats: Counter[str],
) -> Comparison:
    """{{pl-adj|lepszy|sup=…}} -> comparative and superlative Forms (R6.3)."""
    cfg = config().headword["comparison"]
    out = Comparison(pb.AdjectiveInfo(indeclinable=truthy(args.get("indecl"))))
    comps = _terms(args.get("1", ""), labels, stats)
    if comps and comps[0][0] == "-":
        if len(comps) == 1:
            out.info.not_comparable = True
        else:
            stats["comparison.not_generally"] += 1
        comps = comps[1:]
    defaults: list[tuple[str, list[str]]] = []
    for i, (term, term_labels) in enumerate(comps):
        if term == "peri":
            term = f"{cfg['periphrastic']} {lemma}"
            comps[i] = (term, term_labels)
        defaults.append((f"{cfg['superlative']}{term}", term_labels))
    sups = _terms(args.get("sup", ""), labels, stats)
    if not sups and not truthy(args.get("nodefsup")):
        sups = [("+", [])]
    combined: list[tuple[str, list[str]]] = []
    for term, term_labels in sups:
        if term == "+":
            combined += [(d, [*dl, *term_labels]) for d, dl in defaults]
        else:
            combined.append((term, term_labels))
    for degree, listed in (("comparative", comps), ("superlative", combined)):
        grammatical, _ = to_grammatical([degree])
        for term, term_labels in listed:
            if hit := sorted(drop.intersection(term_labels)):
                for label in hit:
                    stats[f"dropped.form.{label}"] += 1
                continue
            unique = list(dict.fromkeys(term_labels))
            out.forms.append(pb.Form(form=term, tags=grammatical, labels=unique))
    for arg, label in cfg["dropped_args"].items():
        if dropped := _terms(args.get(arg, ""), labels, stats):
            stats[f"dropped.form.{label}"] += len(dropped)
    return out


def _terms(
    value: str, labels: LabelIndex, stats: Counter[str]
) -> list[tuple[str, list[str]]]:
    return [(t.term, t.labels) for t in terms(value, labels, stats)]
