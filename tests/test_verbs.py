"""Verbal inflection (M8: R6.2, R3.14) on the golden pages."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from polwikt.config import load_config
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.inflection import TableParser
from polwikt.extract.page import PageResult, Settings, extract_record
from polwikt.proto import polwikt_pb2 as pb
from tests.golden_harness import fixtures

REPO = Path(__file__).resolve().parent.parent
SETTINGS = Settings.from_config(load_config(REPO))
FIX = {f.title: f for f in fixtures()}
T, P, N, G = pb.Tense, pb.Person, pb.Number, pb.Gender
V, R = pb.VerbForm, pb.Relation.Type
CONJUGATION = pb.InflectionTable.Kind.KIND_CONJUGATION


@pytest.fixture(scope="module")
def wtp(golden_store: Path) -> Iterator[PolwiktWtp]:
    w = PolwiktWtp(golden_store)
    yield w
    w.close_db_conn()


def golden(wtp: PolwiktWtp, title: str) -> PageResult:
    return extract_record(wtp, title, FIX[title].wikitext(), SETTINGS)


def verb(wtp: PolwiktWtp, title: str, index: int = 0) -> pb.Entry:
    result = golden(wtp, title)
    assert result.word is not None
    entries = [e for e in result.word.entries if e.pos == pb.Pos.POS_VERB]
    return entries[index]


def find(e: pb.Entry, **tags: int) -> list[str]:
    return [
        f.form for f in e.forms if all(getattr(f.tags, k) == v for k, v in tags.items())
    ]


def relations(e: pb.Entry) -> list[tuple[int, str]]:
    return [(r.type, r.term) for r in e.relations]


@pytest.mark.parametrize(
    "title", ["być", "iść", "jeść", "chcieć", "robić", "zrobić", "mieć", "bać"]
)
def test_every_slot_is_tagged(wtp: PolwiktWtp, title: str) -> None:  # M8 exit
    e = verb(wtp, title)
    assert [t.kind for t in e.tables] == [CONJUGATION] * len(e.tables) and e.tables
    for form in e.forms:
        t = form.tags
        assert t.verb_form or t.tense or t.mood or "impersonal" in form.raw_tags, form
        if t.tense or t.mood:
            assert t.person or "impersonal" in form.raw_tags, form


def test_present_spans_all_genders_so_has_none(wtp: PolwiktWtp) -> None:
    robić = verb(wtp, "robić")
    first = [
        f
        for f in robić.forms
        if f.tags.tense == T.TENSE_PRESENT and f.tags.person == P.PERSON_FIRST
    ]
    assert [(f.form, f.tags.number, f.tags.gender) for f in first] == [
        ("robię", N.NUMBER_SINGULAR, 0),
        ("robimy", N.NUMBER_PLURAL, 0),
    ]
    assert find(robić, verb_form=V.VERB_FORM_INFINITIVE) == ["robić"]


def test_past_by_person_number_gender(wtp: PolwiktWtp) -> None:  # R6.2
    robić = verb(wtp, "robić")
    assert find(
        robić,
        tense=T.TENSE_PAST,
        person=P.PERSON_FIRST,
        number=N.NUMBER_PLURAL,
        gender=G.GENDER_NONVIRILE,
    ) == ["robiłyśmy"]
    assert find(robić, verb_form=V.VERB_FORM_IMPERSONAL_PAST) == ["robiono"]


def test_both_periphrastic_futures(wtp: PolwiktWtp) -> None:  # R6.2
    robić = verb(wtp, "robić")
    assert find(
        robić,
        tense=T.TENSE_FUTURE,
        person=P.PERSON_FIRST,
        number=N.NUMBER_SINGULAR,
        gender=G.GENDER_MASCULINE,
    ) == ["będę robił", "będę robić"]


def test_conditional_and_imperative(wtp: PolwiktWtp) -> None:
    robić = verb(wtp, "robić")
    assert find(
        robić,
        mood=pb.Mood.MOOD_CONDITIONAL,
        person=P.PERSON_THIRD,
        number=N.NUMBER_SINGULAR,
        gender=G.GENDER_FEMININE,
    ) == ["robiłaby", "by robiła"]
    assert find(
        robić,
        mood=pb.Mood.MOOD_IMPERATIVE,
        person=P.PERSON_SECOND,
        number=N.NUMBER_SINGULAR,
    ) == ["rób"]


def test_participles_and_verbal_noun(wtp: PolwiktWtp) -> None:  # R6.2
    robić = verb(wtp, "robić")
    active = V.VERB_FORM_ACTIVE_ADJECTIVAL_PARTICIPLE
    assert find(robić, verb_form=active, gender=G.GENDER_FEMININE) == ["robiąca"]
    passive = V.VERB_FORM_PASSIVE_ADJECTIVAL_PARTICIPLE
    assert find(robić, verb_form=passive, gender=G.GENDER_VIRILE) == ["robieni"]
    adverbial = V.VERB_FORM_CONTEMPORARY_ADVERBIAL_PARTICIPLE
    assert find(robić, verb_form=adverbial) == ["robiąc"]
    assert find(robić, verb_form=V.VERB_FORM_VERBAL_NOUN) == ["robienie"]


def test_detached_endings_are_not_forms(wtp: PolwiktWtp) -> None:
    result = golden(wtp, "być")
    assert result.word is not None
    forms = [f.form for e in result.word.entries for f in e.forms]
    assert not [f for f in forms if f.startswith("-")]
    assert "jestem" in forms
    assert result.stats["table.form.detached_ending"] > 0


def test_aspect_and_counterparts(wtp: PolwiktWtp) -> None:  # R3.14
    robić, zrobić = verb(wtp, "robić"), verb(wtp, "zrobić")
    assert robić.verb.aspect == pb.Aspect.ASPECT_IMPERFECTIVE
    assert (R.TYPE_PERFECTIVE_COUNTERPART, "zrobić") in relations(robić)
    assert zrobić.verb.aspect == pb.Aspect.ASPECT_PERFECTIVE
    aspect = [r for r in relations(zrobić) if r[0] != R.TYPE_DERIVED]  # M10: + derived
    assert aspect == [(R.TYPE_IMPERFECTIVE_COUNTERPART, "robić")]
    labelled = [(r.term, list(r.labels)) for r in robić.relations]
    assert ("robiwać", ["dialectal"]) in labelled  # freq=robiwać<l:dialectal>


def test_motion_verbs(wtp: PolwiktWtp) -> None:
    chodzić = verb(wtp, "chodzić")
    assert chodzić.verb.motion == pb.VerbInfo.Motion.MOTION_INDETERMINATE
    assert (R.TYPE_DETERMINATE_COUNTERPART, "iść") in relations(chodzić)
    bywać = verb(wtp, "bywać")
    assert bywać.verb.frequentative
    assert bywać.verb.motion == pb.VerbInfo.Motion.MOTION_INDETERMINATE


def test_biaspectual_and_two_titled_tables(wtp: PolwiktWtp) -> None:
    potrafić = verb(wtp, "potrafić")
    assert potrafić.verb.aspect == pb.Aspect.ASPECT_BIASPECTUAL
    # The page's one Conjugation section follows its second Verb (R5.2).
    second = verb(wtp, "potrafić", 1)
    assert [t.title for t in second.tables] == [
        "Conjugation of potrafić impf",
        "Conjugation of potrafić pf",
    ]
    assert {f.table for f in second.forms} == {0, 1}


def test_defective(wtp: PolwiktWtp) -> None:
    powinien = verb(wtp, "powinien")
    assert powinien.verb.defective
    assert powinien.forms


def test_pointer_tables_have_no_forms(wtp: PolwiktWtp) -> None:
    result = golden(wtp, "walić konia")
    assert result.stats["table.no_forms"] == 1
    assert result.word is not None
    assert not any(e.tables for e in result.word.entries)


@pytest.mark.parametrize("title", ["robić", "być", "potrafić", "dobry", "ten"])
def test_direct_links_match_module_links(
    wtp: PolwiktWtp, title: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Tables write plain {{l|pl|…}} calls directly instead of running Module:links;
    # both paths must give the same record.
    fast = golden(wtp, title)
    assert fast.stats["table.link.direct"] > 0 or title in ("dobry", "ten")
    monkeypatch.setattr(TableParser, "_plain_link", lambda self, name, args: None)
    slow = golden(wtp, title)
    assert fast.record.word == slow.record.word
