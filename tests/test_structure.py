"""Section walking (R5.1-R5.5) on synthetic pages, and the M5 exit on golden ones."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from polwikt.config import load_config
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.page import PageResult, Settings, extract_page, extract_record
from polwikt.proto import polwikt_pb2 as pb
from tests.golden_harness import fixtures

REPO = Path(__file__).resolve().parent.parent
SETTINGS = Settings.from_config(load_config(REPO))
FIX = fixtures()


@pytest.fixture(scope="module")
def wtp(golden_store: Path) -> Iterator[PolwiktWtp]:
    # The snapshot carries the label and form-of data every page now needs (R6.7).
    w = PolwiktWtp(golden_store)
    yield w
    w.close_db_conn()


def run(wtp: PolwiktWtp, body: str, title: str = "test") -> PageResult:
    return extract_record(wtp, title, "==Polish==\n" + body, SETTINGS)


def pos_and_group(result: PageResult) -> list[tuple[str, int]]:
    assert result.word is not None
    return [(pb.Pos.Name(e.pos), e.etymology) for e in result.word.entries]


def test_numbered_etymologies_hold_their_own_entries(wtp: PolwiktWtp) -> None:
    result = run(
        wtp,
        "===Etymology 1===\nfrom A\n\n====Noun====\n# [[lock]]\n"
        "===Etymology 2===\nfrom B\n\n====Noun====\n# [[castle]]\n====Verb====\n# x\n",
    )
    assert pos_and_group(result) == [("POS_NOUN", 0), ("POS_NOUN", 1), ("POS_VERB", 1)]
    assert result.word is not None
    assert [e.text for e in result.word.etymologies] == ["from A", "from B"]
    assert result.word.entries[1].senses[0].gloss == "castle"  # R5.1: never merged


def test_unnumbered_etymology_covers_its_sibling_entries(wtp: PolwiktWtp) -> None:
    result = run(wtp, "===Etymology===\nfrom A\n===Noun===\n# a\n===Verb===\n# b\n")
    assert pos_and_group(result) == [("POS_NOUN", 0), ("POS_VERB", 0)]


def test_entries_without_an_etymology_share_one_empty_group(wtp: PolwiktWtp) -> None:
    result = run(wtp, "===Noun===\n# a\n===Adjective===\n# b\n")
    assert pos_and_group(result) == [("POS_NOUN", 0), ("POS_ADJECTIVE", 0)]
    assert result.word is not None
    assert [e.text for e in result.word.etymologies] == [""]


def test_groups_without_entries_are_removed_and_renumbered(wtp: PolwiktWtp) -> None:
    result = run(
        wtp,
        "===Etymology 1===\nfrom A\n====Postposition====\n# a\n"
        "===Etymology 2===\nfrom B\n====Noun====\n# b\n",
    )
    assert pos_and_group(result) == [("POS_NOUN", 0)]
    assert result.word is not None
    assert [e.text for e in result.word.etymologies] == ["from B"]
    assert result.stats["pos.not_emitted.Postposition"] == 1


def test_depth_is_not_semantic(wtp: PolwiktWtp) -> None:  # R5.2
    # A Declension at L3 is a sibling of its Noun, not a child: it still attaches.
    result = run(
        wtp,
        "===Noun===\n{{pl-noun|m-anml}}\n# a\n"
        "===Declension===\n{{pl-decl-noun-m-anml}}\n",
    )
    (calls,) = result.record.entry_calls
    assert [c.name for c in calls.headword] == ["pl-noun"]
    assert [c.name for c in calls.inflection] == ["pl-decl-noun-m-anml"]
    assert [(a.key, a.value) for a in calls.headword[0].args] == [("1", "m-anml")]


def test_pronunciation_split_holds_entries(wtp: PolwiktWtp) -> None:
    result = run(
        wtp,
        "===Pronunciation 1===\n====Noun====\n# a\n===Pronunciation 2===\n"
        "====Verb====\n# b\n",
    )
    assert pos_and_group(result) == [("POS_NOUN", 0), ("POS_VERB", 0)]


def test_senses_nest(wtp: PolwiktWtp) -> None:  # R5.4
    result = run(
        wtp,
        "===Noun===\n# [[limb]]\n## [[arm]]\n### [[upper arm]]\n## [[hand]]\n"
        "#: {{uxi|pl|ręka|hand}}\n# [[style]]\n",
    )
    assert result.word is not None
    senses = result.word.entries[0].senses
    assert [s.gloss for s in senses] == ["limb", "style"]
    assert [s.gloss for s in senses[0].subsenses] == ["arm", "hand"]
    assert senses[0].subsenses[0].subsenses[0].gloss == "upper arm"
    assert (result.stats["senses"], result.stats["subsenses"]) == (2, 3)


def test_gloss_leaves_labels_to_their_own_field(wtp: PolwiktWtp) -> None:
    result = run(wtp, "===Noun===\n# {{lb|pl|dated}} [[cat]] {{R:pl:PWN}}\n")
    assert result.word is not None
    assert result.word.entries[0].senses[0].gloss == "cat"


def test_empty_senses_are_dropped_and_counted(wtp: PolwiktWtp) -> None:
    result = run(wtp, "===Noun===\n# {{rfdef|pl}}\n# [[cat]]\n")
    assert result.word is not None
    assert [s.gloss for s in result.word.entries[0].senses] == ["cat"]
    assert result.stats["sense.empty"] == 1


def test_unknown_headings_are_counted_and_kept(wtp: PolwiktWtp) -> None:  # R5.3
    result = run(wtp, "===Noun===\n# a\n====Mystery====\nsome text\n")
    assert result.stats["heading.unknown.Mystery"] == 1
    (unknown,) = result.record.unknown_sections
    assert unknown.heading == "Mystery"
    assert "some text" in unknown.wikitext


def test_orphan_entry_sections_are_counted(wtp: PolwiktWtp) -> None:
    result = run(wtp, "===Declension===\n{{pl-decl-noun-f}}\n===Noun===\n# a\n")
    assert result.stats["section.orphan.Declension"] == 1


def test_bookkeeping_sections_are_not_output(wtp: PolwiktWtp) -> None:
    result = run(
        wtp,
        "===Noun===\n# a\n===References===\n<references/>\n===Further reading===\n"
        "* {{R:pl:PWN}}\n",
    )
    assert not result.record.unknown_sections
    assert pos_and_group(result) == [("POS_NOUN", 0)]


def test_pages_without_entries_yield_no_record(wtp: PolwiktWtp) -> None:
    assert run(wtp, "===Pronunciation===\n* x\n").word is None
    no_polish = extract_record(wtp, "x", "==English==\n===Noun===\n# a\n", SETTINGS)
    assert no_polish.word is None
    assert no_polish.stats["pages.no_language_section"] == 1


# -- M5 exit on the golden set -----------------------------------------------------


@pytest.fixture(scope="module")
def golden(golden_store: Path) -> Iterator[dict[str, pb.Word | None]]:
    w = PolwiktWtp(golden_store)
    words = {f.title: extract_page(w, f.title, f.wikitext(), SETTINGS) for f in FIX}
    yield words
    w.close_db_conn()


def entries(word: pb.Word | None) -> list[tuple[str, int]]:
    assert word is not None
    return [(pb.Pos.Name(e.pos)[4:], e.etymology) for e in word.entries]


def test_zamek_keeps_its_homographs_apart(golden: dict[str, pb.Word | None]) -> None:
    word = golden["zamek"]
    assert entries(word) == [("NOUN", 0), ("NOUN", 1)]
    assert word is not None
    lock, castle = word.entries
    assert lock.senses[0].gloss.startswith("lock")
    assert castle.senses[0].gloss.startswith("castle")


def test_page_pronunciation_is_copied_into_every_entry(
    golden: dict[str, pb.Word | None],
) -> None:  # R5.5
    word = golden["mieć"]
    assert entries(word) == [("VERB", 0), ("VERB", 1)]
    assert word is not None
    ipas = [[p.ipa for p in e.pronunciations] for e in word.entries]
    assert ipas == [["/ˈmjɛt͡ɕ/"], ["/ˈmjɛt͡ɕ/"]]  # the mp= line is dropped (R6.6a)


def test_golden_structures(golden: dict[str, pb.Word | None]) -> None:
    assert entries(golden["iść"]) == [("VERB", 0), ("VERB", 0)]  # two Verbs, one etym
    assert entries(golden["bez"]) == [
        ("NOUN", 0),
        ("PREPOSITION", 1),
        ("PREPOSITION", 2),
        ("NOUN", 3),
    ]
    assert entries(golden["mamy"]) == [("VERB", 0), ("NOUN", 0)]
    assert entries(golden["pies"]) == [("NOUN", 0)] * 3
    assert entries(golden["prosząc"]) == [("PARTICIPLE", 0)]
    assert entries(golden["ą"]) == [("LETTER", 0)]
    ręka = golden["ręka"]
    assert ręka is not None
    assert [s.gloss for s in ręka.entries[0].senses[0].subsenses] == ["arm", "hand"]
    polska = golden["Polska"]
    assert polska is not None  # {{transclude}} from English "Poland" (R3.2b)
    assert polska.entries[0].senses[0].gloss.startswith("Poland (a country")
