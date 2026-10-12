"""Nominal inflection (M7: R6.1, R6.3, R6.4, R7.8) on the golden pages."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from polwikt.config import load_config
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.page import PageResult, Settings, extract_record
from polwikt.proto import polwikt_pb2 as pb
from tests.golden_harness import fixtures

REPO = Path(__file__).resolve().parent.parent
SETTINGS = Settings.from_config(load_config(REPO))
FIX = {f.title: f for f in fixtures()}
C, N, G, A = pb.Case, pb.Number, pb.Gender, pb.Animacy
DECLENSION = pb.InflectionTable.Kind.KIND_DECLENSION


@pytest.fixture(scope="module")
def wtp(golden_store: Path) -> Iterator[PolwiktWtp]:
    w = PolwiktWtp(golden_store)
    yield w
    w.close_db_conn()


def golden(wtp: PolwiktWtp, title: str) -> PageResult:
    return extract_record(wtp, title, FIX[title].wikitext(), SETTINGS)


def entry(wtp: PolwiktWtp, title: str, index: int = 0) -> pb.Entry:
    result = golden(wtp, title)
    assert result.word is not None
    return result.word.entries[index]


def cells(e: pb.Entry, table: int | None = None) -> list[tuple[str, int, int]]:
    """(form, case, number) in table order."""
    return [
        (f.form, f.tags.grammatical_case, f.tags.number)
        for f in e.forms
        if table is None or f.table == table
    ]


def find(e: pb.Entry, **tags: int) -> list[str]:
    return [
        f.form for f in e.forms if all(getattr(f.tags, k) == v for k, v in tags.items())
    ]


def test_kot_is_seven_cases_by_two_numbers(wtp: PolwiktWtp) -> None:
    kot = entry(wtp, "kot")
    assert [(t.kind, t.title) for t in kot.tables] == [
        (DECLENSION, "Declension of kot")
    ]
    assert len(kot.forms) == 14
    assert kot.forms[0].form == "kot"
    assert find(kot, grammatical_case=C.CASE_GENITIVE, number=N.NUMBER_PLURAL) == [
        "kotów"
    ]
    assert list(kot.noun.genders) == [
        pb.GenderAnimacy(gender=G.GENDER_MASCULINE, animacy=A.ANIMACY_ANIMATE)
    ]


def test_alternatives_are_adjacent_primary_first(wtp: PolwiktWtp) -> None:
    oko = entry(wtp, "oko")
    gen_pl = find(oko, grammatical_case=C.CASE_GENITIVE, number=N.NUMBER_PLURAL)
    assert gen_pl == ["oczu", "ócz", "oczów"]


def test_pluralia_tantum_have_no_singular(wtp: PolwiktWtp) -> None:  # R6.1
    for title in ("spodnie", "drzwi", "nożyczki"):
        e = entry(wtp, title)
        assert e.noun.plurale_tantum, title
        assert e.forms and all(f.tags.number == N.NUMBER_PLURAL for f in e.forms)


def test_adjective_cells_spanning_animacy_merge(wtp: PolwiktWtp) -> None:  # R6.3
    dobry = entry(wtp, "dobry")
    declension = next(i for i, t in enumerate(dobry.tables) if t.kind == DECLENSION)
    nom_m = [
        f
        for f in dobry.forms
        if f.table == declension
        and f.tags.grammatical_case == C.CASE_NOMINATIVE
        and f.tags.gender == G.GENDER_MASCULINE
    ]
    assert [(f.form, f.tags.animacy) for f in nom_m] == [("dobry", 0)]
    acc_m = find(dobry, grammatical_case=C.CASE_ACCUSATIVE, gender=G.GENDER_MASCULINE)
    assert acc_m == ["dobrego", "dobry"]  # animate, inanimate: kept apart
    assert find(dobry, grammatical_case=C.CASE_VOCATIVE, gender=G.GENDER_VIRILE) == [
        "dobrzy"  # "nominative/vocative" is one Form per case
    ]


def test_comparison_from_the_headword(wtp: PolwiktWtp) -> None:  # R6.3
    dobry = entry(wtp, "dobry")
    assert dobry.tables[0].kind == pb.InflectionTable.Kind.KIND_COMPARISON
    comparison = [(f.form, list(f.labels)) for f in dobry.forms if f.table == 0]
    assert comparison[0] == ("lepszy", [])
    assert ("lepsiejszy", ["humorous", "ironic"]) in comparison
    assert not dobry.adjective.not_comparable


def test_superlative_derived_and_middle_polish_dropped(wtp: PolwiktWtp) -> None:
    result = golden(wtp, "młody")
    assert result.word is not None
    e = result.word.entries[0]
    assert [f.form for f in e.forms if f.table == 0] == ["młodszy", "najmłodszy"]
    assert result.stats["dropped.form.Middle Polish"] == 1  # mpsup=namłodszy


def test_not_comparable(wtp: PolwiktWtp) -> None:
    cool = entry(wtp, "cool")
    assert cool.adjective.not_comparable
    assert not [t for t in cool.tables if t.kind != DECLENSION]


def test_pronoun_rowspans_and_animacy_rows(wtp: PolwiktWtp) -> None:  # R6.4
    ten = entry(wtp, "ten")
    acc = [
        (f.form, f.tags.gender, f.tags.animacy)
        for f in ten.forms
        if f.tags.grammatical_case == C.CASE_ACCUSATIVE
        and f.tags.number == N.NUMBER_SINGULAR
    ]
    assert ("tego", G.GENDER_MASCULINE, A.ANIMACY_ANIMATE) in acc
    assert ("ten", G.GENDER_MASCULINE, A.ANIMACY_INANIMATE) in acc
    assert ("to", G.GENDER_NEUTER, 0) in acc  # spans both rows: no animacy
    assert ("tą", G.GENDER_FEMININE, 0) in acc  # footnote digit stripped


def test_collective_numeral(wtp: PolwiktWtp) -> None:  # R6.4
    dwoje = entry(wtp, "dwoje")
    assert cells(dwoje)[1] == ("dwojga", C.CASE_GENITIVE, N.NUMBER_PLURAL)


def test_unmapped_header_meaning_is_a_raw_tag(wtp: PolwiktWtp) -> None:
    dwa = entry(wtp, "dwa")
    nom = next(f for f in dwa.forms if f.form == "dwa")
    assert nom.tags.gender == G.GENDER_MASCULINE
    assert list(nom.raw_tags) == ["nonpersonal"]  # invariant 4


def test_cell_qualifiers_become_labels(wtp: PolwiktWtp) -> None:
    familia = entry(wtp, "familia")
    labelled = [(f.form, list(f.labels)) for f in familia.forms if f.labels]
    assert labelled == [("familij", ["obsolete"])]
    down = entry(wtp, "down", 1)
    assert ("downy", ["deprecative"]) in [(f.form, list(f.labels)) for f in down.forms]


def test_combined_forms_table(wtp: PolwiktWtp) -> None:
    result = golden(wtp, "aż")
    assert result.word is not None
    tables = [t for e in result.word.entries for t in e.tables]
    assert [t.kind for t in tables] == [pb.InflectionTable.Kind.KIND_COMBINED_FORMS]


def test_middle_polish_and_kurpian_tables_are_dropped(wtp: PolwiktWtp) -> None:
    absent = golden(wtp, "absent")
    assert absent.stats["dropped.table.Middle Polish"] == 1
    assert absent.word is not None
    assert not any(e.forms or e.tables for e in absent.word.entries)
    agrest = golden(wtp, "agrest")
    assert agrest.stats["dropped.table.Kurpian"] >= 1


def test_unattested_animacy_stays_unset(wtp: PolwiktWtp) -> None:  # m-an!
    result = golden(wtp, "absent")
    assert result.word is not None
    (gender,) = result.word.entries[0].noun.genders
    assert (gender.gender, gender.animacy) == (G.GENDER_MASCULINE, 0)


def test_no_golden_header_is_unknown(wtp: PolwiktWtp) -> None:
    unknown = {
        (title, key)
        for title in FIX
        for key in golden(wtp, title).stats
        if key.startswith(("table.header.unknown.", "headword.gender.unknown."))
    }
    assert not unknown
