"""Relations and the remaining sections (M10: R3.14, R5.5, R6.4, R6.10, R6.12)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from polwikt.config import load_config
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.page import PageResult, Settings, extract_record
from polwikt.extract.relations import subitems
from polwikt.proto import polwikt_pb2 as pb
from tests.golden_harness import fixtures

REPO = Path(__file__).resolve().parent.parent
SETTINGS = Settings.from_config(load_config(REPO))
FIX = {f.title: f for f in fixtures()}
T = pb.Relation.Type


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


def related(e: pb.Entry, kind: int) -> list[str]:
    return [r.term for r in e.relations if r.type == kind]


def test_derived_verbs_are_read_from_the_module_rendering(wtp: PolwiktWtp) -> None:
    # {{pl-derived verbs|scentrować/-|*centrować/centrowywać|do|prze|roz|wy}}
    derived = related(entry(wtp, "centrować"), T.TYPE_DERIVED)
    assert derived[:2] == ["docentrować", "docentrowywać"]
    assert "scentrować" in derived and "wycentrowywać" in derived
    assert len(derived) == 9


def test_column_items(wtp: PolwiktWtp) -> None:
    bieg = entry(wtp, "bieg")
    assert {"biec", "pobiec"} <= set(related(bieg, T.TYPE_RELATED))  # raw links
    assert related(bieg, T.TYPE_RELATED_ADJECTIVE) == ["biegowy"]  # adj=
    zero = related(entry(wtp, "zero"), T.TYPE_DERIVED)
    assert "zero bezwzględne" in zero and "zero absolutne" in zero  # a,b


def test_subitem_delimiters() -> None:
    assert subitems("a,b") == ["a", "b"]
    assert subitems("a~b") == ["a", "b"]
    assert subitems("of news, rumors") == ["of news, rumors"]
    assert subitems("kot<q:a,b>") == ["kot<q:a,b>"]


def test_alternative_forms(wtp: PolwiktWtp) -> None:  # R5.5
    mi = entry(wtp, "mi")
    assert [(r.term, list(r.labels)) for r in mi.relations] == [("mnie", ["stressed"])]
    assert related(entry(wtp, "jemu"), T.TYPE_ALTERNATIVE_FORM) == ["mu", "niemu"]
    alt = [
        (r.term, list(r.labels))
        for r in entry(wtp, "Staręga").relations
        if r.type == T.TYPE_ALTERNATIVE_FORM
    ]
    assert alt == [("Starenga", ["rare"])]


def test_middle_polish_alternative_forms_are_dropped(wtp: PolwiktWtp) -> None:
    for title, count in (("łyżka", 3), ("dobry", 1)):
        result = golden(wtp, title)
        assert result.word is not None
        assert not any(
            r.type == T.TYPE_ALTERNATIVE_FORM
            for e in result.word.entries
            for r in e.relations
        )
        assert result.stats["dropped.alternative_form.Middle Polish"] == count


def test_sense_gloss_on_a_relation_line(wtp: PolwiktWtp) -> None:
    kled = entry(wtp, "kleć")
    syn = [(r.term, r.gloss) for r in kled.relations if r.type == T.TYPE_SYNONYM]
    assert syn[0] == ("spichlerz", "granary")


def test_antonyms_and_coordinate_terms(wtp: PolwiktWtp) -> None:
    assert related(entry(wtp, "wielka"), T.TYPE_ANTONYM) == ["mała", "niewielka"]
    coord = related(entry(wtp, "piątkowy"), T.TYPE_COORDINATE)
    assert coord[0] == "poniedziałkowy" and len(coord) == 6
    assert not related(entry(wtp, "piątkowy"), T.TYPE_RELATED_ADVERB)  # adv=-


def test_navboxes_and_category_lists_are_counted_not_terms(wtp: PolwiktWtp) -> None:
    zero = golden(wtp, "zero")
    assert zero.stats["relation.not_terms.pl-cardinals"] == 1
    assert zero.word is not None
    assert not related(zero.word.entries[0], T.TYPE_COORDINATE)
    assert golden(wtp, "do-").stats["relation.not_terms.prefixsee"] == 1


def test_headword_relations(wtp: PolwiktWtp) -> None:  # R3.14
    ulica = entry(wtp, "ulica")
    assert related(ulica, T.TYPE_DIMINUTIVE) == ["uliczka"]
    assert related(ulica, T.TYPE_ABBREVIATION) == ["ul."]
    lodz = entry(wtp, "Łódź")
    assert related(lodz, T.TYPE_DEMONYM) == ["łodzianin"]
    assert related(lodz, T.TYPE_FEMALE_DEMONYM) == ["łodzianka"]
    staręga = entry(wtp, "Staręga", 1)
    assert related(staręga, T.TYPE_MARRIED_FORM) == ["Starężyna"]
    assert related(staręga, T.TYPE_UNMARRIED_FORM) == ["Starężanka"]


def test_collocations_section_becomes_examples(wtp: PolwiktWtp) -> None:  # R6.12
    absurd = entry(wtp, "absurd")
    collocations = [
        (x.text, x.translation)
        for x in absurd.examples
        if x.kind == pb.Example.Kind.KIND_COLLOCATION
    ]
    assert collocations[0] == ("kompletny absurd", "complete absurdity")
    assert len(entry(wtp, "akt").examples) > 100  # inside {{col-top}} groups


def test_topics_are_category_names(wtp: PolwiktWtp) -> None:  # R6.10
    pies = golden(wtp, "pies").word
    assert pies is not None
    sense_topics = {t for e in pies.entries for s in e.senses for t in s.topics}
    assert "Music" in sense_topics and "music" not in sense_topics  # {{lb|pl|music}}
    warszawa = entry(wtp, "Warszawa")
    assert "National capitals" in warszawa.senses[0].topics  # emitted by {{place}}


def test_no_golden_relation_template_is_unknown(wtp: PolwiktWtp) -> None:
    unknown = {
        (title, key)
        for title in FIX
        for key in golden(wtp, title).stats
        if key.startswith(("relation.template.unknown.", "relation.line.untemplated"))
    }
    assert not unknown
