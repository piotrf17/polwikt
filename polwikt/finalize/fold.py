"""The folding rules, as pure functions over Entry messages (R3.13a, R3.14).

An entry is a *candidate* when every sense is a form-of sense of a folding type
(`{{inflection of}}` …) and its part of speech may fold. A candidate folds when every
sense resolves: its lemma has a record in the corpus, and one of that record's lemma
entries — the same part of speech first — has a Form spelled like the candidate's
title. Otherwise it is emitted as it is, with its `form_of` senses, and logged with
the reason (R3.13c).
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
from typing import Any

from polwikt.proto import polwikt_pb2 as pb


@dataclass(frozen=True)
class Config:
    fold_types: frozenset[int]
    never_pos: frozenset[int]
    inverse: dict[int, int]
    license: str
    attribution: str
    coverage_tables: tuple[int, ...]


@cache
def config() -> Config:
    path = resources.files("polwikt.data").joinpath("finalize.toml")
    data: dict[str, Any] = tomllib.loads(path.read_text("utf-8"))
    form_type = pb.FormOf.Type.Value
    relation_type = pb.Relation.Type.Value
    return Config(
        fold_types=frozenset(form_type(t) for t in data["fold"]["types"]),
        never_pos=frozenset(pb.Pos.Value(p) for p in data["fold"]["never_pos"]),
        inverse={
            relation_type(k): relation_type(v) for k, v in data["inverse"].items()
        },
        license=data["corpus"]["license"],
        attribution=data["corpus"]["attribution"],
        coverage_tables=tuple(pb.Pos.Value(p) for p in data["coverage"]["tables"]),
    )


def is_candidate(entry: pb.Entry) -> bool:
    """Every sense an inflectional form-of sense, of a part of speech that folds."""
    cfg = config()
    return (
        entry.pos not in cfg.never_pos
        and len(entry.senses) > 0
        and all(
            s.HasField("form_of") and s.form_of.type in cfg.fold_types
            for s in entry.senses
        )
    )


@dataclass(frozen=True)
class LemmaEntry:
    """One lemma entry of a target page, as pass 1 recorded it."""

    index: int
    pos: int
    has_surface: bool


def choose_entry(pos: int, entries: Sequence[LemmaEntry]) -> int | None:
    """The target entry holding the surface: same part of speech first, then any."""
    holding = [e for e in entries if e.has_surface]
    for e in holding:
        if e.pos == pos:
            return e.index
    return holding[0].index if holding else None


def tags_match(wanted: pb.GrammaticalTags, form: pb.GrammaticalTags) -> bool:
    """Every feature the form-of tag set states, the Form has too."""
    return all(getattr(form, f.name) == value for f, value in wanted.ListFields())


@dataclass
class Fold:
    """One resolved form-of sense: where the candidate's surface lives."""

    lemma: str
    entry: int  # the target's entry index before P4 removed anything
    tag_sets: list[pb.GrammaticalTags]
    raw_tags: list[str]
    labels: list[str]  # the sense's labels and regions: carried onto the Form


@dataclass
class Transfer:
    """What a folded candidate leaves on its lemma's entry (R3.13a)."""

    surface: str
    folds: list[Fold]
    tables: list[pb.InflectionTable] = field(default_factory=list)
    forms: list[pb.Form] = field(default_factory=list)
    # The candidate's one tag set, when it has exactly one ("comparative"): moved
    # Forms gain the features it states.
    common: pb.GrammaticalTags | None = None


def carry_labels(entry: pb.Entry, surface: str, fold: Fold) -> int:
    """Puts the form-of sense's labels on the lemma's matching Forms; counts them."""
    if not fold.labels:
        return 0
    hit = 0
    for form in entry.forms:
        if form.form != surface:
            continue
        if fold.tag_sets and not any(tags_match(t, form.tags) for t in fold.tag_sets):
            continue
        for label in fold.labels:
            if label not in form.labels:
                form.labels.append(label)
        hit += 1
    return hit


def transfer_tables(entry: pb.Entry, transfer: Transfer) -> int:
    """Appends the candidate's own tables to the lemma entry; Forms it already has
    (same spelling and tags) are skipped. A single form-of tag set ("comparative") is
    added to each moved Form's tags where the Form leaves that feature unset."""
    if not transfer.tables:
        return 0
    common = transfer.common
    have = {(f.form, f.tags.SerializeToString(deterministic=True)) for f in entry.forms}
    base = len(entry.tables)
    entry.tables.extend(transfer.tables)
    moved = 0
    for form in transfer.forms:
        new = pb.Form()
        new.CopyFrom(form)
        new.table = base + form.table
        if common is not None:
            for f, value in common.ListFields():
                if not getattr(new.tags, f.name):  # proto3: unset is 0
                    setattr(new.tags, f.name, value)
        key = (new.form, new.tags.SerializeToString(deterministic=True))
        if key in have:
            continue
        have.add(key)
        entry.forms.append(new)
        moved += 1
    return moved


def add_inverse(
    entry: pb.Entry, kind: int, term: str, existing: Iterable[pb.Relation] = ()
) -> bool:
    """Adds `term` as a relation of `kind` unless the entry already states it."""
    for r in [*entry.relations, *existing]:
        if r.type == kind and r.term == term:
            return False
    entry.relations.append(pb.Relation(type=kind, term=term))  # type: ignore[arg-type]
    return True


def renumber_etymologies(word: pb.Word) -> None:
    """Keeps the etymology groups some entry still points at, in order (R5.1)."""
    used = sorted({e.etymology for e in word.entries})
    if used == list(range(len(word.etymologies))):
        return
    renumber = {old: new for new, old in enumerate(used)}
    kept = [word.etymologies[i] for i in used]
    del word.etymologies[:]
    word.etymologies.extend(kept)
    for e in word.entries:
        e.etymology = renumber[e.etymology]
