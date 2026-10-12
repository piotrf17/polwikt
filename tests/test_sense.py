"""Senses in detail (R6.6-R6.14), on the real label and tag data in the snapshot."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from polwikt.config import load_config
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.labels import split_on_comma
from polwikt.extract.page import PageResult, Settings, extract_record
from polwikt.proto import polwikt_pb2 as pb
from tests.golden_harness import fixtures

REPO = Path(__file__).resolve().parent.parent
SETTINGS = Settings.from_config(load_config(REPO))
FIX = {f.title: f for f in fixtures()}


@pytest.fixture(scope="module")
def wtp(golden_store: Path) -> Iterator[PolwiktWtp]:
    w = PolwiktWtp(golden_store)
    yield w
    w.close_db_conn()


def run(wtp: PolwiktWtp, body: str) -> PageResult:
    return extract_record(wtp, "test", "==Polish==\n===Noun===\n" + body, SETTINGS)


def first_sense(result: PageResult) -> pb.Sense:
    assert result.word is not None
    return result.word.entries[0].senses[0]


def test_labels_are_split_by_kind(wtp: PolwiktWtp) -> None:  # R6.7
    sense = first_sense(
        run(wtp, "# {{lb|pl|colloquial|hunting|Far Masovian|chiefly|Krotoszyn}} fox\n")
    )
    assert list(sense.labels) == ["colloquial"]
    assert list(sense.regions) == ["Far Masovian", "Krotoszyn"]  # town: by capital
    assert list(sense.topics) == ["hunting"]
    assert sense.gloss == "fox"  # labels never reach the gloss text


@pytest.mark.parametrize(
    ("written", "labels"),
    [
        ("of news, rumors, etc.", ["of news, rumors, etc."]),  # prose: not split
        ("dated,colloquial", ["dated", "colloquial"]),  # Module:labels splits this
        # Module:labels' own example: never inside <<...>> or [...]
        (
            "regional,older <<non-rhotic,and,non-hoarse-horse>> speakers",
            ["regional", "older <<non-rhotic,and,non-hoarse-horse>> speakers"],
        ),
    ],
)
def test_label_commas_follow_module_labels(written: str, labels: list[str]) -> None:
    assert split_on_comma(written) == labels


def test_aliases_resolve_through_wiktionary_data(wtp: PolwiktWtp) -> None:
    sense = first_sense(run(wtp, "# {{lb|pl|idiom}} x\n"))
    assert list(sense.labels) == ["idiomatic"]


def test_keywords_come_from_gloss_links_only(wtp: PolwiktWtp) -> None:  # R6.14
    sense = first_sense(
        run(
            wtp,
            "# {{lb|pl|hunting}} [[male]] [[fox]] {{gloss|of the genus "
            "{{taxfmt|Vulpes|genus}}}} [[w:Fox|wiki]]\n",
        )
    )
    assert [(k.text, k.taxonomic) for k in sense.keywords] == [
        ("male", False),
        ("fox", False),
        ("Vulpes", True),
    ]


def test_a_transcluded_gloss_keys_on_its_source(wtp: PolwiktWtp) -> None:  # R6.14
    # jabłko: "# {{tcl|pl|apple|id=Q89}}" shows English "apple"'s sense (R3.2b).
    result = extract_record(wtp, "Polska", FIX["Polska"].wikitext(), SETTINGS)
    assert result.word is not None
    sense = result.word.entries[0].senses[0]
    assert sense.keywords[0].text == "Poland"


def test_government(wtp: PolwiktWtp) -> None:  # R6.11
    sense = first_sense(
        run(wtp, "# x {{+obj|pl|:do(gen)<to what>}} {{+obj|pl|gen/inf<to do what>}}\n")
    )
    slots = [
        (g.preposition, g.grammatical_case, g.description) for g in sense.government
    ]
    assert slots == [
        ("do", pb.Case.CASE_GENITIVE, "to what"),
        ("", pb.Case.CASE_GENITIVE, "to do what"),
        ("", pb.Case.CASE_UNSPECIFIED, "inf: to do what"),  # kept, not dropped
    ]
    assert sense.gloss == "x"


def test_form_of_with_several_tag_sets(wtp: PolwiktWtp) -> None:  # R6.6
    call = "# {{inflection of|pl|mama||gen|s|;|nom//acc//voc|p}}\n"
    sense = first_sense(run(wtp, call))
    form = sense.form_of
    assert form.type == pb.FormOf.Type.TYPE_INFLECTION
    assert form.lemma == "mama"
    pairs = [(t.grammatical_case, t.number) for t in form.tag_sets]
    assert pairs == [
        (pb.Case.CASE_GENITIVE, pb.Number.NUMBER_SINGULAR),
        (pb.Case.CASE_NOMINATIVE, pb.Number.NUMBER_PLURAL),
        (pb.Case.CASE_ACCUSATIVE, pb.Number.NUMBER_PLURAL),
        (pb.Case.CASE_VOCATIVE, pb.Number.NUMBER_PLURAL),
    ]
    assert sense.gloss.startswith("inflection of mama:")


def test_derivations_and_alternative_forms_are_typed(wtp: PolwiktWtp) -> None:
    dim = first_sense(run(wtp, "# {{diminutive of|pl|kot}}\n")).form_of
    assert (dim.type, dim.lemma, list(dim.raw_tags)) == (
        pb.FormOf.Type.TYPE_DERIVATION,
        "kot",
        ["diminutive"],
    )
    alt = first_sense(run(wtp, "# {{alt sp|pl|keczup}}\n")).form_of
    assert (alt.type, alt.lemma) == (pb.FormOf.Type.TYPE_ALTERNATIVE_FORM, "keczup")
    vn = first_sense(run(wtp, "# {{verbal noun of|pl|robić}}\n")).form_of
    assert vn.tag_sets[0].verb_form == pb.VerbForm.VERB_FORM_VERBAL_NOUN


def test_unmapped_tags_are_raw_not_lost(wtp: PolwiktWtp) -> None:  # invariant 4
    form = first_sense(run(wtp, "# {{inflection of|pl|ten||short|gen|s}}\n")).form_of
    assert list(form.raw_tags) == ["short"]
    assert form.tag_sets[0].grammatical_case == pb.Case.CASE_GENITIVE


def test_examples_collocations_and_nyms(wtp: PolwiktWtp) -> None:  # R6.9, R6.12
    sense = first_sense(
        run(
            wtp,
            "# [[cat]]\n#: {{uxi|pl|'''Kot''' śpi.|The cat sleeps.|lit=Cat sleeps.}}\n"
            "#: {{coi|pl|czarny kot|black cat}}\n"
            "#: {{syn|pl|kocur<q:colloquial><t:tomcat>|Thesaurus:kot}}\n",
        )
    )
    kinds = [(e.kind, e.text, e.translation, e.literal) for e in sense.examples]
    assert kinds == [
        (pb.Example.Kind.KIND_EXAMPLE, "Kot śpi.", "The cat sleeps.", "Cat sleeps."),
        (pb.Example.Kind.KIND_COLLOCATION, "czarny kot", "black cat", ""),
    ]
    (synonym,) = sense.relations  # the Thesaurus link is counted, not a term
    assert (synonym.type, synonym.term, synonym.gloss, list(synonym.labels)) == (
        pb.Relation.Type.TYPE_SYNONYM,
        "kocur",
        "tomcat",
        ["colloquial"],
    )


def test_quotations_get_a_one_line_source(wtp: PolwiktWtp) -> None:  # R6.9
    sense = first_sense(
        run(
            wtp,
            "# [[cat]]\n#* {{quote-book|pl|year=1834|author=w:Adam Mickiewicz|"
            "title=Pan Tadeusz|passage=Rwał w pole|translation=He tore off}}\n",
        )
    )
    (quote,) = sense.examples
    assert quote.kind == pb.Example.Kind.KIND_QUOTATION
    assert (quote.text, quote.translation) == ("Rwał w pole", "He tore off")
    assert quote.source == "Adam Mickiewicz, Pan Tadeusz (1834)"


def test_entry_labels_topics_and_usage_notes(wtp: PolwiktWtp) -> None:
    result = run(
        wtp,
        "{{tlb|pl|colloquial}}\n# [[cat]]\n====Usage notes====\nUsed of '''cats'''.\n"
        "===Further reading===\n{{C|pl|Cats}}\n",
    )
    assert result.word is not None
    entry = result.word.entries[0]
    assert list(entry.labels) == ["colloquial"]
    assert list(entry.topics) == ["Cats"]  # the page's {{C}} (R6.10)
    assert entry.usage_notes == "Used of cats."


def test_middle_polish_cascade(wtp: PolwiktWtp) -> None:  # R6.6a, R6.6c
    result = run(
        wtp,
        "# {{lb|pl|Middle Polish}} [[old]]\n## [[older]]\n# [[new]]\n"
        "===Verb===\n# {{lb|pl|Middle Polish|Kraków}} [[go]]\n"
        "===Adjective===\n{{tlb|pl|Middle Polish}}\n# [[old]]\n",
    )
    assert result.word is not None
    assert [pb.Pos.Name(e.pos) for e in result.word.entries] == ["POS_NOUN"]
    assert [s.gloss for s in result.word.entries[0].senses] == ["new"]
    assert result.stats["dropped.sense.Middle Polish"] == 3  # 2 (with subsense) + 1
    assert result.stats["dropped.entry.Middle Polish"] == 2  # all-senses + {{tlb}}
    assert result.stats["dropped.sense.colabelled"] == 1  # Middle Polish + Kraków
    assert result.colabelled == ["test"]


# -- M6 exit on the golden set ----------------------------------------------------


def golden(wtp: PolwiktWtp, title: str) -> PageResult:
    return extract_record(wtp, title, FIX[title].wikitext(), SETTINGS)


def test_dobry_loses_its_middle_polish(wtp: PolwiktWtp) -> None:
    result = golden(wtp, "dobry")
    assert result.word is not None
    assert result.stats["dropped.sense.Middle Polish"] >= 1
    for entry in result.word.entries:
        for sense in entry.senses:
            assert "Middle Polish" not in [*sense.labels, *sense.regions]
        assert all("Middle Polish" not in p.labels for p in entry.pronunciations)


@pytest.mark.parametrize("title", ["kradźba", "barzo"])
def test_all_middle_polish_pages_yield_no_record(wtp: PolwiktWtp, title: str) -> None:
    result = golden(wtp, title)
    assert result.word is None
    assert result.stats["dropped.page.Middle Polish"] == 1


def test_barzo_is_counted_as_colabelled(wtp: PolwiktWtp) -> None:  # R6.6c
    result = golden(wtp, "barzo")
    assert result.stats["dropped.sense.colabelled"] == 1
    assert result.colabelled == ["barzo"]


def test_pies_has_a_taxonomic_keyword(wtp: PolwiktWtp) -> None:  # R6.14
    result = golden(wtp, "pies")
    assert result.word is not None
    sense = result.word.entries[0].senses[0]
    keywords = [(k.text, k.taxonomic) for k in sense.keywords]
    assert keywords == [("dog", False), ("Canis lupus familiaris", True)]


def test_chodzic_keeps_prose_qualifiers_whole(wtp: PolwiktWtp) -> None:
    # "{{lb|pl|intransitive|of news, rumors, etc.}}" — split on ", " this made "rumors"
    # and "etc." labels, and on iść turned "roads" into the topic "road transport".
    result = golden(wtp, "chodzić")
    assert result.word is not None
    labels = [list(s.labels) for s in result.word.entries[0].senses]
    assert ["intransitive", "of news, rumors, etc."] in labels
    assert ["intransitive", "of e.g. beer, dough"] in labels
    iść = golden(wtp, "iść")
    assert iść.word is not None
    for entry in iść.word.entries:
        for sense in entry.senses:
            assert "road transport" not in sense.topics
