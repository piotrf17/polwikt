"""Pronunciation sections and frequency (M9: R6.5, R6.13) on the golden pages."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from polwikt.config import load_config
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.page import PageResult, Settings, extract_record
from polwikt.parse.text import plain_text
from polwikt.proto import polwikt_pb2 as pb
from tests.golden_harness import fixtures

REPO = Path(__file__).resolve().parent.parent
SETTINGS = Settings.from_config(load_config(REPO))
FIX = {f.title: f for f in fixtures()}
HOMOPHONE = pb.Relation.Type.TYPE_HOMOPHONE


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


def prons(e: pb.Entry) -> list[tuple[str, list[str]]]:
    return [(p.ipa, list(p.labels)) for p in e.pronunciations]


def audio(e: pb.Entry) -> list[tuple[str, str, list[str]]]:
    return [(a.file, a.label, list(a.labels)) for a in e.audio]


def homophones(e: pb.Entry) -> list[tuple[str, list[str]]]:
    return [(r.term, list(r.labels)) for r in e.relations if r.type == HOMOPHONE]


def test_qualifier_after_the_marker_labels_its_transcription(wtp: PolwiktWtp) -> None:
    assert prons(entry(wtp, "grapefruit")) == [
        ("/\u02c8\u0261r\u025bjp.frut/", []),  # /ˈgrɛjp.frut/ with IPA script g
        ("/\u02c8\u0261r\u025bj.frut/", ["colloquial"]),
    ]


def test_identical_dialect_transcriptions_share_one_pronunciation(
    wtp: PolwiktWtp,
) -> None:
    robic = prons(entry(wtp, "robić"))
    assert robic[0] == ("/ˈrɔ.bit͡ɕ/", [])
    assert len(robic) == 2
    assert robic[1][0] == "[ˈrɔ.bit͡ɕ]"
    assert robic[1][1][:2] == ["Kuyavia", "Central Greater Poland"]
    assert "Middle Polish" not in robic[1][1]  # the mp= line is dropped (R6.6a)


def test_literal_ipa_template(wtp: PolwiktWtp) -> None:
    assert prons(entry(wtp, "a-moll")) == [("/ˈa‿mɔl/", [])]


def test_audio_spoken_text_and_qualifiers(wtp: PolwiktWtp) -> None:
    assert audio(entry(wtp, "robić")) == [
        ("Pl-robić.ogg", "", []),  # <text:#> is the lemma itself
        ("LL-Q809 (pol)-Poemat-robić się.wav", "robić się", []),
    ]
    assert audio(entry(wtp, "bać"))[0] == ("Pl-bać się.ogg", "bać się", [])  # <cap:~>
    assert audio(entry(wtp, "Bergamo"))[1] == (
        "Pl-Bergamo-second-syllable.ogg",
        "",
        ["colloquial"],
    )
    assert audio(entry(wtp, "od"))[0] == ("Pl-od.ogg", "", ["isolated"])


def test_audio_named_twice_is_one_recording(wtp: PolwiktWtp) -> None:
    result = golden(wtp, "siekierka")
    assert result.word is not None
    assert len(result.word.entries[0].audio) == 1
    assert result.stats["pronunciation.audio.duplicate"] == 1


def test_syllabification(wtp: PolwiktWtp) -> None:
    assert entry(wtp, "robić").syllabification == "ro‧bić"
    assert entry(wtp, "zoo").syllabification == "zo‧o, zoo"  # h=zo.o,zoo


def test_homophones_are_relations(wtp: PolwiktWtp) -> None:
    assert homophones(entry(wtp, "kot")) == [("kod", []), ("Kot", [])]
    assert homophones(entry(wtp, "od")) == [("od-", []), ("ot", []), ("-ot", [])]
    assert homophones(entry(wtp, "nałóg")) == [("nauk", ["for some speakers"])]


def test_no_golden_pronunciation_line_is_unknown(wtp: PolwiktWtp) -> None:
    unknown = [
        title for title in FIX if golden(wtp, title).stats["pronunciation.line.unknown"]
    ]
    assert not unknown


def test_frequency_of_the_word_not_another_term(wtp: PolwiktWtp) -> None:  # R6.13
    co = golden(wtp, "co")
    assert co.word is not None
    assert (co.word.frequency.rank, co.word.frequency.count) == (19, 2224)
    assert co.word.frequency.source.startswith("Słownik frekwencyjny")
    znalezc = golden(wtp, "znaleźć")
    assert znalezc.word is not None
    assert znalezc.word.frequency.rank == 287  # not "znaleźć się"'s 764
    assert znalezc.stats["frequency.other_term"] == 1
    kot = golden(wtp, "kot")
    assert kot.word is not None
    assert not kot.word.HasField("frequency")


def test_request_boxes_are_not_text() -> None:
    box = (
        '<div class="noprint request-box">\n{|\n|This section or entry lacks '
        "references or sources.\n|}</div>"
    )
    line = '<span class="maintenance-line"><i>This etymology is incomplete.</i></span>'
    assert plain_text(f"Uncertain.{box}") == "Uncertain."
    assert plain_text(f"From X. {line}") == "From X."
