"""P4 on the golden corpus (M11: R3.13-R3.16, R7.3, R7.4, R11.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from polwikt.config import load_config
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.page import Settings, extract_record
from polwikt.finalize.fold import renumber_etymologies, tags_match
from polwikt.finalize.run import P4Error, P4Summary, run_p4
from polwikt.proto import polwikt_pb2 as pb
from polwikt.proto.io import (
    ShardWriter,
    read_corpus,
    read_corpus_meta,
)
from tests.golden_harness import fixtures

REPO = Path(__file__).resolve().parent.parent
CFG = load_config(REPO)
SETTINGS = Settings.from_config(CFG)
C, N = pb.Case, pb.Number
R = pb.Relation.Type


def _p3(golden_store: Path, out: Path) -> None:
    wtp = PolwiktWtp(golden_store)
    try:
        with ShardWriter(out, prefix="p3") as writer:
            for page_id, fixture in enumerate(fixtures(), 1):
                result = extract_record(
                    wtp, fixture.title, fixture.wikitext(), SETTINGS, page_id=page_id
                )
                writer.write(result.record)
    finally:
        wtp.close_db_conn()


def _p4(p3_dir: Path, out: Path) -> P4Summary:
    return run_p4(
        p3_dir, out, dump_date=CFG.dump.date, drop_labels=list(CFG.drop_labels)
    )


@pytest.fixture(scope="module")
def p3_dir(golden_store: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("p3")
    _p3(golden_store, out)
    return out


@pytest.fixture(scope="module")
def corpus(p3_dir: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("corpus")
    _p4(p3_dir, out)
    return out


@pytest.fixture(scope="module")
def words(corpus: Path) -> dict[str, pb.Word]:
    return {w.lemma: w for w in read_corpus(corpus)}


def hits(
    words: dict[str, pb.Word], surface: str
) -> list[tuple[str, int, pb.GrammaticalTags]]:
    """Where a surface form lands: the lemma entries whose Forms spell it (R3.13b)."""
    return [
        (lemma, i, f.tags)
        for lemma, word in sorted(words.items())
        for i, entry in enumerate(word.entries)
        for f in entry.forms
        if f.form == surface
    ]


def test_lemma_and_form_pages_keep_only_their_lemma_half(  # R3.13a, per POS entry
    words: dict[str, pb.Word], corpus: Path
) -> None:
    bez = words["bez"]
    assert not any(
        s.HasField("form_of") and s.form_of.lemma == "beza"
        for e in bez.entries
        for s in e.senses
    )
    assert ("beza", 0) in [(lemma, i) for lemma, i, _ in hits(words, "bez")]
    mieć = words["mieć"]
    assert [e.pos for e in mieć.entries] == [pb.Pos.POS_VERB]
    assert "mieść" in [lemma for lemma, _, _ in hits(words, "mieć")]


def test_a_page_of_forms_yields_no_record_and_resolves_to_both_lemmas(
    words: dict[str, pb.Word], corpus: Path
) -> None:
    assert "mamy" not in words and "kotów" not in words
    found = hits(words, "mamy")
    assert {lemma for lemma, _, _ in found} == {"mieć", "mama"}
    mama = [t for lemma, _, t in found if lemma == "mama"]
    wanted = pb.GrammaticalTags(
        grammatical_case=C.CASE_GENITIVE, number=N.NUMBER_SINGULAR
    )
    assert any(tags_match(wanted, t) for t in mama)
    (kot,) = {(lemma, i) for lemma, i, _ in hits(words, "kotów")}
    assert kot == ("kot", 0)


def test_unfoldable_form_of_entry_is_emitted(words: dict[str, pb.Word]) -> None:
    dna = words["DNA"]  # an abbreviation, never folded
    assert dna.entries[0].senses[0].form_of.lemma == "kwas dezoksyrybonukleinowy"


def test_folded_comparative_brings_its_declension(
    words: dict[str, pb.Word], corpus: Path
) -> None:
    assert "lepszy" not in words
    dobry = words["dobry"].entries[0]
    titles = [t.title for t in dobry.tables]
    assert "Declension of lepszy (hard)" in titles
    moved = [f for f in dobry.forms if f.form == "lepszego"]
    assert moved and all(f.tags.degree == pb.Degree.DEGREE_COMPARATIVE for f in moved)
    assert "dobry" in [lemma for lemma, _, _ in hits(words, "lepszego")]


def test_paradigm_forms_resolve(words: dict[str, pb.Word]) -> None:  # R3.13b
    found = hits(words, "robiłem")
    assert found and found[0][0] == "robić"
    assert found[0][2].tense == pb.Tense.TENSE_PAST


def test_inverse_relations(words: dict[str, pb.Word]) -> None:  # R3.14
    iść = next(e for e in words["iść"].entries if e.pos == pb.Pos.POS_VERB)
    assert (R.TYPE_INDETERMINATE_COUNTERPART, "chodzić") in [
        (r.type, r.term) for r in iść.relations
    ]


def test_corpus_metadata_and_license(corpus: Path, words: dict[str, pb.Word]) -> None:
    meta = read_corpus_meta(corpus)  # R7.4
    assert meta.dump_date == CFG.dump.date
    assert list(meta.drop_labels) == ["Middle Polish"]
    assert meta.word_count == len(words)
    assert meta.license == "CC BY-SA 4.0"
    assert "English Wiktionary" in meta.attribution
    assert "CC BY-SA 4.0" in (corpus / "LICENSE-DATA").read_text()  # R11.1


def test_stats_and_unresolved_report(corpus: Path) -> None:
    import json

    stats = json.loads((corpus / "stats.json").read_text())
    assert stats["counts"]["finalize.entries.folded"] > 0
    assert "lemma_entries_with_sense" in stats["coverage"]
    rows = [json.loads(line) for line in (corpus / "unresolved_forms.jsonl").open()]
    assert all({"title", "lemma", "reason"} <= set(r) for r in rows)


def test_finalize_is_deterministic(p3_dir: Path, corpus: Path, tmp_path: Path) -> None:
    _p4(p3_dir, tmp_path)  # G5
    for name in (
        "words-00000-of-00001.pb.zst",
        "corpus.meta.pb",
        "stats.json",
        "unresolved_forms.jsonl",
    ):
        assert (tmp_path / name).read_bytes() == (corpus / name).read_bytes(), name


def test_renumber_etymologies() -> None:
    word = pb.Word(
        etymologies=[pb.Etymology(text="a"), pb.Etymology(text="b")],
        entries=[pb.Entry(etymology=1)],
    )
    renumber_etymologies(word)
    assert [e.text for e in word.etymologies] == ["b"]
    assert word.entries[0].etymology == 0


def test_finalize_skips_a_complete_run_and_redoes_an_interrupted_one(
    p3_dir: Path, corpus: Path, tmp_path: Path
) -> None:  # R9.4
    out = tmp_path / "c"
    _p4(p3_dir, out)
    shard = (out / "words-00000-of-00001.pb.zst").read_bytes()
    assert _p4(p3_dir, out).skipped
    (out / "finalize.json").write_text('{"run": "x", "complete": false}')  # stale
    (out / "index.sqlite").write_bytes(b"partial")
    assert not _p4(p3_dir, out).skipped
    assert (out / "words-00000-of-00001.pb.zst").read_bytes() == shard
    stray = tmp_path / "stray"
    stray.mkdir()
    (stray / "stats.json").write_text("{}")
    with pytest.raises(P4Error, match="did not write"):
        _p4(p3_dir, stray)
