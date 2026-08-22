"""Corpus I/O: framing, sharding, determinism, and the index (R7.2, R7.3, G5)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
import zstandard

from polwikt.proto import (
    Aspect,
    Case,
    Corpus,
    EntryRef,
    EtymologyGroup,
    Form,
    Gender,
    GrammaticalTags,
    LinkSpan,
    Number,
    Pos,
    PosEntry,
    Sense,
    Word,
)
from polwikt.proto.io import (
    SCHEMA_VERSION,
    CorpusError,
    CorpusIndex,
    Location,
    ShardWriter,
    _read_varint,
    _write_varint,
    read_corpus,
    read_corpus_meta,
    read_shard,
    shard_paths,
    to_json,
    write_corpus_meta,
)


def rich_word(title: str = "kot") -> Word:
    """A Word exercising nesting, Polish text and codepoint offsets."""
    gloss = "a cat, an animal of the family Kotowate"
    return Word(
        title=title,
        page_id=42,
        revision_id=7,
        lang_code="pl",
        etymology_groups=[
            EtymologyGroup(
                etymology_text="Inherited from Proto-Slavic *kotъ.",
                entries=[
                    PosEntry(
                        pos=Pos.POS_NOUN,
                        headword="kot",
                        senses=[
                            Sense(
                                glosses=[gloss],
                                gloss_links=[
                                    LinkSpan(
                                        start=gloss.index("Kotowate"),
                                        end=gloss.index("Kotowate") + len("Kotowate"),
                                        target="Kotowate",
                                        display="Kotowate",
                                        lang_code="pl",
                                    )
                                ],
                            )
                        ],
                        forms=[
                            Form(
                                form="kotów",
                                tags=GrammaticalTags(
                                    grammatical_case=Case.CASE_GENITIVE,
                                    number=Number.NUMBER_PLURAL,
                                    gender=Gender.GENDER_MASCULINE,
                                ),
                                source=Form.Source.SOURCE_DECLENSION_TABLE,
                                has_own_page=True,
                            )
                        ],
                    )
                ],
            )
        ],
    )


# ------------------------------------------------------------------------- framing


@pytest.mark.parametrize("value", [0, 1, 127, 128, 300, 16383, 16384, 2**31, 2**62])
def test_varint_round_trip(value: int) -> None:
    buf = io.BytesIO()
    written = _write_varint(buf, value)
    assert written == len(buf.getvalue())
    buf.seek(0)
    assert _read_varint(buf) == value


def test_varint_rejects_negative() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        _write_varint(io.BytesIO(), -1)


def test_read_varint_returns_none_at_clean_eof() -> None:
    assert _read_varint(io.BytesIO(b"")) is None


def test_truncated_record_is_an_error(tmp_path: Path) -> None:
    """A short read must raise, never silently yield a partial corpus (invariant 2)."""
    shard = tmp_path / "words-00000-of-00001.pb.zst"
    shard.write_bytes(zstandard.compress(b"\x0a" + b"abc"))  # claims 10 bytes, has 3
    with pytest.raises(CorpusError, match="truncated record"):
        list(read_shard(shard))


# ------------------------------------------------------------------- write and read


def test_round_trip_preserves_everything(tmp_path: Path) -> None:
    original = rich_word()
    with ShardWriter(tmp_path) as writer:
        writer.write(original)
    (word,) = list(read_corpus(tmp_path))
    assert word == original


def test_link_spans_are_codepoint_offsets(tmp_path: Path) -> None:
    """R7.6a: offsets index the Python str, so non-ASCII glosses stay correct."""
    gloss = "łóżko — a bed, from Proto-Slavic"
    span = LinkSpan(start=gloss.index("bed"), end=gloss.index("bed") + 3, display="bed")
    word = Word(
        title="łóżko",
        etymology_groups=[
            EtymologyGroup(
                entries=[PosEntry(senses=[Sense(glosses=[gloss], gloss_links=[span])])]
            )
        ],
    )
    with ShardWriter(tmp_path) as writer:
        writer.write(word)
    (read_back,) = list(read_corpus(tmp_path))
    got = read_back.etymology_groups[0].entries[0].senses[0]
    link = got.gloss_links[0]
    assert got.glosses[0][link.start : link.end] == link.display == "bed"


def test_sharding_splits_and_names_correctly(tmp_path: Path) -> None:
    """M1 exit criterion: 50k records shard, keep order, and get -of-<total> names."""
    count = 50_000
    with ShardWriter(tmp_path, records_per_shard=7_000, compression_level=1) as writer:
        writer.write_all(Word(title=f"w{i:05d}", page_id=i) for i in range(count))
        assert writer.record_count == count
    paths = shard_paths(tmp_path)
    assert len(paths) == 8
    assert paths[0].name == "words-00000-of-00008.pb.zst"
    assert paths[-1].name == "words-00007-of-00008.pb.zst"
    assert not list(tmp_path.glob("*.part"))
    titles = [w.title for w in read_corpus(tmp_path)]
    assert titles == [f"w{i:05d}" for i in range(count)]


def test_locations_are_reported_per_shard(tmp_path: Path) -> None:
    with ShardWriter(tmp_path, records_per_shard=2, compression_level=1) as writer:
        locations = [writer.write(Word(title=f"w{i}")) for i in range(5)]
    assert [(loc.shard, loc.record) for loc in locations] == [
        (0, 0),
        (0, 1),
        (1, 0),
        (1, 1),
        (2, 0),
    ]
    assert locations[0].offset == 0
    assert locations[1].offset > 0  # second record starts after the first


def test_empty_corpus_writes_no_shards(tmp_path: Path) -> None:
    with ShardWriter(tmp_path):
        pass
    assert shard_paths(tmp_path) == []
    assert list(read_corpus(tmp_path)) == []


# -------------------------------------------------------------------- determinism


def test_output_is_byte_identical_across_runs(tmp_path: Path) -> None:
    """G5. Any timestamp or map ordering leaking into a shard breaks this."""
    words = [rich_word(f"kot{i}") for i in range(200)]
    digests = []
    for run in ("a", "b"):
        out = tmp_path / run
        with ShardWriter(out, records_per_shard=64, compression_level=3) as writer:
            writer.write_all(words)
        digests.append([p.read_bytes() for p in shard_paths(out)])
    assert digests[0] == digests[1]


# ---------------------------------------------------------------------- metadata


def test_metadata_lives_outside_the_shards(tmp_path: Path) -> None:
    """`generated_at` is the one non-deterministic field, so it stays out of band."""
    with ShardWriter(tmp_path) as writer:
        writer.write(rich_word())
    meta = Corpus(
        schema_version=SCHEMA_VERSION,
        dump_date="20260801",
        dump_pinned=True,
        generated_at="2026-08-22T12:00:00Z",
        drop_labels=["Middle Polish"],
        word_count=1,
        shard_count=1,
        license="CC BY-SA 4.0",
    )
    path = write_corpus_meta(tmp_path, meta)
    assert path.name not in {p.name for p in shard_paths(tmp_path)}
    assert read_corpus_meta(tmp_path) == meta


def test_json_view_is_stable(tmp_path: Path) -> None:
    rendered = to_json(rich_word())
    assert '"title": "kot"' in rendered
    assert rendered == to_json(rich_word())


# ------------------------------------------------------------------------- index


def test_index_locates_words_and_resolves_folded_forms(tmp_path: Path) -> None:
    """R3.13b: `kotów` has no record of its own but must still resolve to `kot`."""
    with CorpusIndex(tmp_path / "index.sqlite") as index:
        index.add_word("kot", Location(shard=0, record=3, offset=128))
        target = EntryRef(title="kot", etymology_index=0, pos_index=0)
        index.add_form("kotów", target, tags="genitive|plural")
        index.add_form("mamy", EntryRef(title="mama", pos_index=0))
        index.add_form("mamy", EntryRef(title="mieć", pos_index=0))

        assert index.locate("kot") == Location(0, 3, 128)
        assert index.locate("nieistniejące") is None
        assert index.resolve_form("kotów") == [target]
        # A surface form belonging to two lemmas resolves to both (R3.13a).
        assert [ref.title for ref in index.resolve_form("mamy")] == ["mama", "mieć"]
        assert index.resolve_form("brak") == []


def test_index_survives_reopen(tmp_path: Path) -> None:
    path = tmp_path / "index.sqlite"
    with CorpusIndex(path) as index:
        index.add_word("być", Location(1, 0, 0))
    with CorpusIndex(path) as index:
        assert index.locate("być") == Location(1, 0, 0)


def test_aspect_enum_survives_serialization(tmp_path: Path) -> None:
    word = rich_word()
    word.etymology_groups[0].entries[0].verb.aspect = Aspect.ASPECT_PERFECTIVE
    with ShardWriter(tmp_path) as writer:
        writer.write(word)
    (read_back,) = list(read_corpus(tmp_path))
    entry = read_back.etymology_groups[0].entries[0]
    assert entry.WhichOneof("detail") == "verb"
    assert entry.verb.aspect == Aspect.ASPECT_PERFECTIVE
