"""Corpus I/O: varint-delimited, zstd-compressed protobuf shards (R7.2).

The corpus must stream — a single monolithic message is forbidden — so records are
framed as `varint(length) || bytes` inside a zstd stream, split across shards named
`words-00000-of-00064.pb.zst`.

Everything here is deterministic (G5): messages serialize with `deterministic=True`,
shard boundaries depend only on the record count, and no timestamps are written. The
one non-deterministic field in the schema, `Corpus.generated_at`, lives in a separate
metadata file so the shards stay byte-identical across runs.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import IO, BinaryIO, Final, Self

import zstandard
from google.protobuf.json_format import MessageToJson

from polwikt.proto.polwikt_pb2 import Corpus, EntryRef, Word

SCHEMA_VERSION: Final = "1"
SHARD_PREFIX: Final = "words"
SHARD_SUFFIX: Final = ".pb.zst"
META_FILENAME: Final = "corpus.meta.pb"
DEFAULT_RECORDS_PER_SHARD: Final = 50_000
DEFAULT_COMPRESSION_LEVEL: Final = 10


class CorpusError(Exception):
    """Corpus file is truncated, malformed, or written in an unexpected order."""


@dataclass(frozen=True, slots=True)
class Location:
    """Where a record landed: shard, index within it, and uncompressed byte offset."""

    shard: int
    record: int
    offset: int


# --------------------------------------------------------------------------- framing


def _write_varint(out: IO[bytes], value: int) -> int:
    """Write an unsigned LEB128 varint; return the number of bytes written."""
    if value < 0:
        raise ValueError(f"varint must be non-negative, got {value}")
    written = 0
    while True:
        byte = value & 0x7F
        value >>= 7
        out.write(bytes([byte | 0x80]) if value else bytes([byte]))
        written += 1
        if not value:
            return written


def _read_varint(src: IO[bytes]) -> int | None:
    """Read an unsigned LEB128 varint. Returns None at a clean end of stream."""
    shift = 0
    result = 0
    while True:
        chunk = src.read(1)
        if not chunk:
            if shift:
                raise CorpusError("truncated varint at end of shard")
            return None
        byte = chunk[0]
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result
        shift += 7
        if shift > 63:
            raise CorpusError("varint too long; shard is corrupt")


# ---------------------------------------------------------------------------- writer


class ShardWriter:
    """Write `Word` records into sharded, compressed files.

    Shards are written under provisional names and renamed to their final
    `-of-<total>` form on close, since the total is not known until then.
    """

    def __init__(
        self,
        out_dir: Path,
        *,
        records_per_shard: int = DEFAULT_RECORDS_PER_SHARD,
        compression_level: int = DEFAULT_COMPRESSION_LEVEL,
        prefix: str = SHARD_PREFIX,
    ) -> None:
        if records_per_shard < 1:
            raise ValueError("records_per_shard must be >= 1")
        self.out_dir = out_dir
        self.records_per_shard = records_per_shard
        self.compression_level = compression_level
        self.prefix = prefix
        self.record_count = 0
        self._shard_index = -1
        self._records_in_shard = 0
        self._offset = 0
        self._raw: BinaryIO | None = None
        self._stream: IO[bytes] | None = None
        self._parts: list[Path] = []
        out_dir.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def write(self, word: Word) -> Location:
        if self._stream is None or self._records_in_shard >= self.records_per_shard:
            self._open_next_shard()
        assert self._stream is not None
        payload = word.SerializeToString(deterministic=True)
        location = Location(self._shard_index, self._records_in_shard, self._offset)
        self._offset += _write_varint(self._stream, len(payload))
        self._stream.write(payload)
        self._offset += len(payload)
        self._records_in_shard += 1
        self.record_count += 1
        return location

    def write_all(self, words: Iterable[Word]) -> None:
        for word in words:
            self.write(word)

    def close(self) -> list[Path]:
        """Finish the current shard and rename every part to its final name."""
        self._close_stream()
        total = len(self._parts)
        final: list[Path] = []
        for index, part in enumerate(self._parts):
            target = self.out_dir / shard_name(index, total, self.prefix)
            part.replace(target)
            final.append(target)
        self._parts = []
        return final

    def _open_next_shard(self) -> None:
        self._close_stream()
        self._shard_index += 1
        self._records_in_shard = 0
        self._offset = 0
        part = self.out_dir / f"{self.prefix}-{self._shard_index:05d}.part"
        self._raw = part.open("wb")
        self._stream = zstandard.ZstdCompressor(
            level=self.compression_level
        ).stream_writer(self._raw)
        self._parts.append(part)

    def _close_stream(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None
        if self._raw is not None:
            self._raw.close()
            self._raw = None


def shard_name(index: int, total: int, prefix: str = SHARD_PREFIX) -> str:
    return f"{prefix}-{index:05d}-of-{total:05d}{SHARD_SUFFIX}"


# ---------------------------------------------------------------------------- reader


def read_shard(path: Path) -> Iterator[Word]:
    """Yield every `Word` in one shard, in write order."""
    with path.open("rb") as raw, zstandard.ZstdDecompressor().stream_reader(raw) as src:
        while (length := _read_varint(src)) is not None:
            payload = src.read(length)
            if len(payload) != length:
                raise CorpusError(f"{path}: truncated record ({len(payload)}/{length})")
            word = Word()
            word.ParseFromString(payload)
            yield word


def shard_paths(corpus_dir: Path, prefix: str = SHARD_PREFIX) -> list[Path]:
    """Every shard of a corpus directory, in shard order."""
    return sorted(corpus_dir.glob(f"{prefix}-*{SHARD_SUFFIX}"))


def read_corpus(corpus_dir: Path, prefix: str = SHARD_PREFIX) -> Iterator[Word]:
    """Stream a whole corpus directory shard by shard."""
    for path in shard_paths(corpus_dir, prefix):
        yield from read_shard(path)


# -------------------------------------------------------------------------- metadata


def write_corpus_meta(corpus_dir: Path, meta: Corpus) -> Path:
    path = corpus_dir / META_FILENAME
    path.write_bytes(meta.SerializeToString(deterministic=True))
    return path


def read_corpus_meta(corpus_dir: Path) -> Corpus:
    meta = Corpus()
    meta.ParseFromString((corpus_dir / META_FILENAME).read_bytes())
    return meta


def to_json(word: Word) -> str:
    """The JSON view of R7.5. Protobuf is the contract; this is for eyeballing."""
    rendered: str = MessageToJson(word, sort_keys=True, indent=2)
    return rendered


# ----------------------------------------------------------------------------- index


class CorpusIndex:
    """`title -> (shard, offset)` plus the surface-form map of R3.13b.

    Inflected-form pages produce no record of their own, so this index is the only way
    back from a surface form such as `kotów` to its lemma `kot` (R3.13a-b).
    """

    SCHEMA: Final = """
        CREATE TABLE IF NOT EXISTS words (
            title   TEXT PRIMARY KEY,
            shard   INTEGER NOT NULL,
            record  INTEGER NOT NULL,
            offset  INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS forms (
            form            TEXT NOT NULL,
            lemma           TEXT NOT NULL,
            etymology_index INTEGER NOT NULL DEFAULT 0,
            pos_index       INTEGER NOT NULL DEFAULT 0,
            tags            TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS forms_by_form ON forms (form);
        CREATE INDEX IF NOT EXISTS forms_by_lemma ON forms (lemma);
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.executescript(self.SCHEMA)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def add_word(self, title: str, location: Location) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO words VALUES (?, ?, ?, ?)",
            (title, location.shard, location.record, location.offset),
        )

    def add_form(self, form: str, target: EntryRef, tags: str = "") -> None:
        """Record a folded surface form so lookups of it still resolve (R3.13b)."""
        self.conn.execute(
            "INSERT INTO forms VALUES (?, ?, ?, ?, ?)",
            (form, target.title, target.etymology_index, target.pos_index, tags),
        )

    def locate(self, title: str) -> Location | None:
        row = self.conn.execute(
            "SELECT shard, record, offset FROM words WHERE title = ?", (title,)
        ).fetchone()
        return None if row is None else Location(*row)

    def resolve_form(self, form: str) -> list[EntryRef]:
        """Every lemma entry the surface form belongs to; empty if unknown."""
        rows = self.conn.execute(
            "SELECT lemma, etymology_index, pos_index FROM forms "
            "WHERE form = ? ORDER BY lemma, etymology_index, pos_index",
            (form,),
        ).fetchall()
        return [
            EntryRef(title=title, etymology_index=etym, pos_index=pos)
            for title, etym, pos in rows
        ]

    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()
