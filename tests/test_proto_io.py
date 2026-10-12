"""Corpus I/O: framing, sharding, random access, determinism, metadata, index."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from polwikt.proto import (
    META_NAME,
    CorpusError,
    CorpusIndex,
    Location,
    ShardWriter,
    read_at,
    read_corpus,
    read_corpus_meta,
    read_shard,
    shard_paths,
    to_json,
    write_corpus_meta,
)
from polwikt.proto import polwikt_pb2 as pb
from polwikt.proto.io import decode_varint, encode_varint


def _word(i: int) -> pb.Word:
    return pb.Word(lemma=f"słowo{i}")


def _rich_word() -> pb.Word:
    """`kot`, hand-built to touch every level of the schema."""
    sense = pb.Sense(
        gloss="cat (domestic animal)",
        labels=["colloquial"],
        regions=["Far Masovian"],
        topics=["zoology"],
        keywords=[
            pb.Keyword(text="cat"),
            pb.Keyword(text="Felis catus", taxonomic=True),
        ],
        examples=[
            pb.Example(
                kind=pb.Example.Kind.KIND_EXAMPLE,
                text="Mam kota.",
                translation="I have a cat.",
            )
        ],
        relations=[pb.Relation(type=pb.Relation.Type.TYPE_SYNONYM, term="kocur")],
        government=[
            pb.Government(
                preposition="do",
                grammatical_case=pb.Case.CASE_GENITIVE,
                description="to what",
            )
        ],
        subsenses=[pb.Sense(gloss="tomcat")],
    )
    entry = pb.Entry(
        pos=pb.Pos.POS_NOUN,
        etymology=0,
        senses=[sense],
        forms=[
            pb.Form(
                form="kotów",
                tags=pb.GrammaticalTags(
                    grammatical_case=pb.Case.CASE_GENITIVE,
                    number=pb.Number.NUMBER_PLURAL,
                ),
                table=0,
            )
        ],
        tables=[
            pb.InflectionTable(
                kind=pb.InflectionTable.Kind.KIND_DECLENSION, title="Declension"
            )
        ],
        pronunciations=[pb.Pronunciation(ipa="/kɔt/")],
        audio=[pb.Audio(file="Pl-kot.ogg")],
        relations=[pb.Relation(type=pb.Relation.Type.TYPE_DIMINUTIVE, term="kotek")],
        topics=["Cats"],
        noun=pb.NounInfo(
            genders=[
                pb.GenderAnimacy(
                    gender=pb.Gender.GENDER_MASCULINE,
                    animacy=pb.Animacy.ANIMACY_ANIMATE,
                )
            ]
        ),
    )
    # A second homograph: an unfoldable form-of entry, emitted because its lemma is
    # missing from the corpus (R3.13a).
    form_entry = pb.Entry(
        pos=pb.Pos.POS_NOUN,
        etymology=1,
        senses=[
            pb.Sense(
                gloss="genitive plural of kota",
                form_of=pb.FormOf(
                    type=pb.FormOf.Type.TYPE_INFLECTION,
                    lemma="kota",
                    tag_sets=[
                        pb.GrammaticalTags(
                            grammatical_case=pb.Case.CASE_GENITIVE,
                            number=pb.Number.NUMBER_PLURAL,
                        )
                    ],
                ),
            )
        ],
    )
    # Comparison forms live in their own table (R6.3).
    adjective = pb.Entry(
        pos=pb.Pos.POS_ADJECTIVE,
        forms=[
            pb.Form(
                form="kocszy",
                tags=pb.GrammaticalTags(degree=pb.Degree.DEGREE_COMPARATIVE),
                labels=["humorous"],
            )
        ],
        tables=[pb.InflectionTable(kind=pb.InflectionTable.Kind.KIND_COMPARISON)],
        adjective=pb.AdjectiveInfo(not_comparable=False, indeclinable=True),
    )
    return pb.Word(
        lemma="kot",
        etymologies=[
            pb.Etymology(text="Inherited from Proto-Slavic *kotъ."),
            pb.Etymology(),
        ],
        entries=[entry, form_entry, adjective],
        frequency=pb.Frequency(rank=1234, count=56, source="SFPW 1990"),
    )


def _write(
    out: Path,
    words: list[pb.Word],
    *,
    records_per_shard: int = 4096,
    records_per_frame: int = 64,
) -> list[Location]:
    with ShardWriter(
        out, records_per_shard=records_per_shard, records_per_frame=records_per_frame
    ) as writer:
        return [writer.write(w) for w in words]


# --- varint framing --------------------------------------------------------


@pytest.mark.parametrize("value", [0, 1, 127, 128, 300, 2**14, 2**32, 2**63 - 1])
def test_varint_round_trip(value: int) -> None:
    encoded = encode_varint(value)
    assert decode_varint(encoded, 0) == (value, len(encoded))


def test_varint_rejects_negative() -> None:
    with pytest.raises(ValueError):
        encode_varint(-1)


def test_truncated_varint_raises() -> None:
    with pytest.raises(CorpusError, match="truncated varint"):
        decode_varint(b"\x80\x80", 0)


# --- round trip and layout -------------------------------------------------


def test_rich_word_round_trips(tmp_path: Path) -> None:
    word = _rich_word()
    _write(tmp_path, [word])
    (back,) = read_corpus(tmp_path)
    assert back == word
    assert back.entries[0].WhichOneof("detail") == "noun"
    assert back.entries[0].senses[0].keywords[1].taxonomic
    assert back.entries[1].senses[0].form_of.lemma == "kota"


def test_sharding_preserves_order_and_names(tmp_path: Path) -> None:
    words = [_word(i) for i in range(50_000)]
    locations = _write(tmp_path, words, records_per_shard=7_000, records_per_frame=100)
    paths = shard_paths(tmp_path)
    assert [p.name for p in paths] == [
        f"words-{i:05d}-of-00008.pb.zst" for i in range(8)
    ]
    assert not list(tmp_path.glob("*.part"))
    assert [w.lemma for w in read_corpus(tmp_path)] == [w.lemma for w in words]
    assert locations[6_999].shard == 0 and locations[7_000].shard == 1
    assert sum(1 for _ in read_shard(paths[-1])) == 50_000 - 7 * 7_000


def test_read_at_decodes_only_the_addressed_record(tmp_path: Path) -> None:
    words = [_word(i) for i in range(1_000)]
    locations = _write(tmp_path, words, records_per_shard=300, records_per_frame=16)
    for i in (0, 15, 16, 299, 300, 517, 999):
        assert read_at(tmp_path, locations[i]) == words[i]
    assert locations[16].frame_offset > locations[15].frame_offset
    assert locations[17].frame_offset == locations[16].frame_offset


def test_read_at_rejects_bad_locations(tmp_path: Path) -> None:
    _write(tmp_path, [_word(0)])
    with pytest.raises(CorpusError, match="outside"):
        read_at(tmp_path, Location(shard=3, frame_offset=0, index=0))
    with pytest.raises(CorpusError, match="no record 5"):
        read_at(tmp_path, Location(shard=0, frame_offset=0, index=5))


def test_empty_corpus_is_one_empty_shard(tmp_path: Path) -> None:
    _write(tmp_path, [])
    assert [p.name for p in shard_paths(tmp_path)] == ["words-00000-of-00001.pb.zst"]
    assert list(read_corpus(tmp_path)) == []


def test_output_is_byte_identical_across_runs(tmp_path: Path) -> None:  # G5
    words = [_rich_word(), *(_word(i) for i in range(3_000))]

    def digest(out: Path) -> list[str]:
        _write(out, words, records_per_shard=1_000, records_per_frame=50)
        return [hashlib.sha256(p.read_bytes()).hexdigest() for p in shard_paths(out)]

    assert digest(tmp_path / "a") == digest(tmp_path / "b")


def test_failed_run_leaves_no_shards(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError), ShardWriter(tmp_path, records_per_shard=2) as w:
        for i in range(5):
            w.write(_word(i))
        raise RuntimeError("worker crashed")
    assert list(tmp_path.iterdir()) == []


def test_writer_refuses_a_dirty_directory(tmp_path: Path) -> None:
    _write(tmp_path, [_word(0)])
    with pytest.raises(CorpusError, match="already holds shards"):
        ShardWriter(tmp_path)


# --- corrupt or incomplete input -------------------------------------------


def test_missing_shard_is_detected(tmp_path: Path) -> None:
    _write(tmp_path, [_word(i) for i in range(10)], records_per_shard=3)
    shard_paths(tmp_path)[1].unlink()
    with pytest.raises(CorpusError, match=r"missing \[1\]"):
        list(read_corpus(tmp_path))


def test_truncated_shard_is_detected(tmp_path: Path) -> None:
    _write(tmp_path, [_rich_word()] * 20, records_per_frame=5)
    (path,) = shard_paths(tmp_path)
    path.write_bytes(path.read_bytes()[:-40])
    with pytest.raises(CorpusError):
        list(read_shard(path))


def test_frame_aligned_truncation_is_caught_by_the_count(tmp_path: Path) -> None:
    locations = _write(tmp_path, [_word(i) for i in range(20)], records_per_frame=5)
    write_corpus_meta(tmp_path, pb.Corpus(word_count=20))
    (path,) = shard_paths(tmp_path)
    path.write_bytes(path.read_bytes()[: locations[15].frame_offset])  # drop last frame
    assert len(list(read_shard(path))) == 15  # still valid zstd on its own
    with pytest.raises(CorpusError, match="read 15 words, metadata says 20"):
        list(read_corpus(tmp_path))


def test_no_shards_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="no words-"):
        shard_paths(tmp_path)


# --- metadata and JSON -----------------------------------------------------


def test_metadata_lives_beside_the_shards(tmp_path: Path) -> None:  # R7.4
    words = [_word(i) for i in range(3)]
    _write(tmp_path, words)
    meta = pb.Corpus(
        schema_version="1",
        dump_date="20261001",
        drop_labels=["Middle Polish"],
        word_count=3,
        license="CC BY-SA 4.0",
    )
    write_corpus_meta(tmp_path, meta)
    assert read_corpus_meta(tmp_path) == meta
    assert (tmp_path / META_NAME).exists()
    assert list(read_corpus(tmp_path)) == words  # shards don't see it


def test_missing_metadata_raises(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="does not exist"):
        read_corpus_meta(tmp_path)


def test_json_view_is_one_stable_line() -> None:  # R7.5
    rendered = to_json(_rich_word())
    assert "\n" not in rendered
    assert rendered == to_json(_rich_word())
    data = json.loads(rendered)
    assert data["lemma"] == "kot"
    assert data["entries"][0]["pos"] == "POS_NOUN"
    assert "łóżko" in to_json(pb.Word(lemma="łóżko"))  # not \u-escaped


# --- index.sqlite ----------------------------------------------------------


def test_index_locates_lemmas_and_resolves_forms(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    words = [pb.Word(lemma=t) for t in ("kot", "mama", "mieć")]
    locations = _write(corpus, words)
    gen_pl = pb.GrammaticalTags(
        grammatical_case=pb.Case.CASE_GENITIVE, number=pb.Number.NUMBER_PLURAL
    )
    with CorpusIndex(tmp_path / "index.sqlite") as index:
        for word, loc in zip(words, locations, strict=True):
            index.add_word(word.lemma, loc)
        index.add_form("kotów", "kot", None, gen_pl)
        # mamy: a form of two lemmas, and a lemma of nothing on its own (R3.13a).
        index.add_form(
            "mamy",
            "mieć",
            0,
            pb.GrammaticalTags(
                person=pb.Person.PERSON_FIRST, tense=pb.Tense.TENSE_PRESENT
            ),
        )
        index.add_form(
            "mamy",
            "mama",
            0,
            pb.GrammaticalTags(grammatical_case=pb.Case.CASE_GENITIVE),
            raw_tags=["depreciative"],
        )

    with CorpusIndex(tmp_path / "index.sqlite") as index:  # survives reopening
        found = index.locate("mieć")
        assert found is not None
        assert read_at(corpus, found).lemma == "mieć"
        assert index.locate("kotów") is None  # forms are not records (R7.7a)

        (kotow,) = index.resolve_form("kotów")
        assert (kotow.lemma, kotow.entry_index, kotow.tags) == ("kot", None, gen_pl)

        mamy = index.resolve_form("mamy")
        assert [(h.lemma, h.entry_index) for h in mamy] == [("mieć", 0), ("mama", 0)]
        assert mamy[1].raw_tags == ("depreciative",)
        assert index.resolve_form("pies") == []


def test_index_rejects_duplicate_lemmas(tmp_path: Path) -> None:
    with CorpusIndex(tmp_path / "index.sqlite") as index:
        index.add_word("kot", Location(0, 0, 0))
        with pytest.raises(CorpusError, match="duplicate"):
            index.add_word("kot", Location(0, 0, 1))
