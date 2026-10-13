"""Corpus files: varint-framed `Word` shards in zstd, and metadata (R7.2-R7.5).

A shard is a sequence of independent zstd frames, each holding up to
`records_per_frame` length-delimited records. A `Location` names a frame by its byte
offset in the compressed file plus the record's index inside it, so one record can be
read by seeking to its frame and decompressing only that frame.

Output is deterministic (G5): records are serialized with `deterministic=True`,
compression is single-threaded at a fixed level, and the shard count lives in the file
names (resolved at close), never in a timestamped header.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import IO, Self

import zstandard
from google.protobuf import json_format
from google.protobuf.message import DecodeError, Message

from polwikt.proto.polwikt_pb2 import Corpus, Word

SCHEMA_VERSION = "1"
META_NAME = "corpus.meta.pb"
DEFAULT_PREFIX = "words"
ZSTD_LEVEL = 10
_READ_CHUNK = 1 << 20

_SHARD_RE = re.compile(r"(?P<prefix>.+)-(?P<i>\d{5})-of-(?P<n>\d{5})\.pb\.zst")


class CorpusError(Exception):
    """A corpus file is truncated, corrupt, incomplete or inconsistent."""


@dataclass(frozen=True, order=True)
class Location:
    """Where one record lives: shard number, frame byte offset, index in the frame."""

    shard: int
    frame_offset: int
    index: int


def shard_name(prefix: str, shard: int, total: int) -> str:
    return f"{prefix}-{shard:05d}-of-{total:05d}.pb.zst"


# ---------------------------------------------------------------------------
# Varint framing
# ---------------------------------------------------------------------------


def encode_varint(value: int) -> bytes:
    """Unsigned LEB128, as protobuf uses for length prefixes."""
    if value < 0:
        raise ValueError(f"varint must be non-negative, got {value}")
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def decode_varint(buf: bytes | bytearray, pos: int) -> tuple[int, int]:
    """Decodes one varint at `pos`; returns (value, position after it)."""
    value = 0
    shift = 0
    while True:
        if pos >= len(buf):
            raise CorpusError("truncated varint")
        byte = buf[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, pos
        shift += 7
        if shift > 63:
            raise CorpusError("varint longer than 64 bits")


def _split_records(data: bytes) -> Iterator[bytes]:
    """Yields the payloads of a complete buffer of length-delimited records."""
    pos = 0
    while pos < len(data):
        size, pos = decode_varint(data, pos)
        end = pos + size
        if end > len(data):
            raise CorpusError(f"truncated record: need {size} bytes at offset {pos}")
        yield data[pos:end]
        pos = end


def _parse[M: Message](payload: bytes, message_type: type[M]) -> M:
    record = message_type()
    try:
        record.ParseFromString(payload)
    except DecodeError as e:
        name = message_type.DESCRIPTOR.name
        raise CorpusError(f"corrupt {name} record: {e}") from e
    return record


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


class ShardWriter:
    """Writes `Word`s into numbered shards under `out_dir`.

    Shards are written as `.part` files and renamed to their final
    `<prefix>-NNNNN-of-MMMMM.pb.zst` names on a clean close, so a directory never holds
    a complete-looking set from a run that failed. Leaving the `with` block on an
    exception deletes the partial output.
    """

    def __init__(
        self,
        out_dir: Path,
        *,
        prefix: str = DEFAULT_PREFIX,
        records_per_shard: int = 4096,
        records_per_frame: int = 64,
        resume: int = 0,
        keep_finished: bool = False,
    ) -> None:
        """`resume=k` continues a run that checkpointed after k complete shards: their
        `.part` files are kept, anything written after them is discarded (R9.4).
        `keep_finished` makes an aborted run keep its finished shards for that."""
        if records_per_shard < 1 or records_per_frame < 1:
            raise ValueError("records_per_shard and records_per_frame must be >= 1")
        self._dir = out_dir
        self._prefix = prefix
        self._per_shard = records_per_shard
        self._per_frame = records_per_frame
        self._compressor = zstandard.ZstdCompressor(
            level=ZSTD_LEVEL, write_checksum=True, write_content_size=True, threads=0
        )
        self._parts: list[Path] = []
        self._file: IO[bytes] | None = None
        self._frame = bytearray()
        self._frame_records = 0
        self._shard_records = 0
        self._closed = False
        self._keep_finished = keep_finished
        self._finished = resume
        out_dir.mkdir(parents=True, exist_ok=True)
        existing = sorted(p.name for p in out_dir.glob(f"{prefix}-*.pb.zst*"))
        if resume:
            kept = [f"{prefix}-{i:05d}.pb.zst.part" for i in range(resume)]
            missing = [name for name in kept if name not in existing]
            if missing:
                raise CorpusError(f"cannot resume {out_dir}: {missing[0]} is missing")
            for name in existing:
                if name not in kept:
                    (out_dir / name).unlink()  # written after the last checkpoint
            self._parts = [out_dir / name for name in kept]
        elif existing:
            raise CorpusError(f"{out_dir} already holds shards: {existing[:3]}")

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is None:
            self.close()
        else:
            self.abort()

    def write(self, record: Message) -> Location:
        """Appends one record (a `Word`, or P3's `PageRecord`) and returns its place."""
        return self.write_serialized(record.SerializeToString(deterministic=True))

    def write_serialized(self, payload: bytes) -> Location:
        """Appends a record a worker already serialized with deterministic=True."""
        if self._closed:
            raise CorpusError("write() on a closed ShardWriter")
        if self._file is None or self._shard_records == self._per_shard:
            self._start_shard()
        assert self._file is not None
        shard = len(self._parts) - 1
        location = Location(shard, self._file.tell(), self._frame_records)
        self._frame += encode_varint(len(payload))
        self._frame += payload
        self._frame_records += 1
        self._shard_records += 1
        if self._frame_records == self._per_frame:
            self._flush_frame()
        return location

    def finish_full_shard(self) -> int | None:
        """If the current shard is full, finishes it now rather than at the next write,
        and returns how many shards are complete on disk — a checkpoint (R9.4)."""
        if self._file is None or self._shard_records < self._per_shard:
            return None
        self._finish_shard()
        return len(self._parts)

    def close(self) -> list[Path]:
        """Finishes the last shard and renames every `.part` to its final name."""
        if self._closed:
            raise CorpusError("ShardWriter closed twice")
        if self._file is None and not self._parts:
            self._start_shard()  # an empty corpus is one empty shard, not none
        if self._file is not None:
            self._finish_shard()
        self._closed = True
        total = len(self._parts)
        final = []
        for i, part in enumerate(self._parts):
            target = self._dir / shard_name(self._prefix, i, total)
            os.replace(part, target)
            final.append(target)
        return final

    def abort(self) -> None:
        """Discards everything written so far, or with `keep_finished` only the shard
        in progress."""
        if self._file is not None:
            self._file.close()
            self._file = None
        keep = self._finished if self._keep_finished else 0
        for part in self._parts[keep:]:
            part.unlink(missing_ok=True)
        self._closed = True

    def _start_shard(self) -> None:
        if self._file is not None:
            self._finish_shard()
        self._shard_records = 0
        part = self._dir / f"{self._prefix}-{len(self._parts):05d}.pb.zst.part"
        self._parts.append(part)
        self._file = part.open("wb")
        self._shard_records = 0

    def _flush_frame(self) -> None:
        if self._frame_records:
            assert self._file is not None
            self._file.write(self._compressor.compress(bytes(self._frame)))
        self._frame.clear()
        self._frame_records = 0

    def _finish_shard(self) -> None:
        self._flush_frame()
        assert self._file is not None
        self._file.close()
        self._file = None
        self._finished = len(self._parts)


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def shard_paths(corpus_dir: Path, prefix: str = DEFAULT_PREFIX) -> list[Path]:
    """The complete, ordered shard set; raises if any shard is missing or stray."""
    found: dict[int, Path] = {}
    totals: set[int] = set()
    for path in corpus_dir.glob(f"{prefix}-*.pb.zst"):
        m = _SHARD_RE.fullmatch(path.name)
        if not m or m["prefix"] != prefix:
            continue
        found[int(m["i"])] = path
        totals.add(int(m["n"]))
    if not found:
        raise CorpusError(f"no {prefix}-*.pb.zst shards in {corpus_dir}")
    if len(totals) != 1:
        raise CorpusError(f"shards disagree on the total: {sorted(totals)}")
    (total,) = totals
    missing = sorted(set(range(total)) - found.keys())
    if missing or len(found) != total:
        raise CorpusError(f"incomplete shard set in {corpus_dir}: missing {missing}")
    return [found[i] for i in range(total)]


def _frames(f: IO[bytes], where: str, *, limit: int | None = None) -> Iterator[bytes]:
    """Yields each zstd frame's decompressed bytes, failing on a frame cut short.

    zstandard's stream reader treats a truncated final frame as a clean end of input,
    which would turn a damaged shard into a silently shorter one; this checks that every
    frame that starts also finishes.
    """
    decoder = zstandard.ZstdDecompressor().decompressobj()
    out = bytearray()
    started = False
    emitted = 0
    while limit is None or emitted < limit:
        chunk = f.read(_READ_CHUNK)
        if not chunk:
            break
        while chunk:
            started = True
            try:
                out += decoder.decompress(chunk)
            except zstandard.ZstdError as e:
                raise CorpusError(f"{where}: {e}") from e
            if not decoder.eof:
                break
            yield bytes(out)
            emitted += 1
            if limit is not None and emitted == limit:
                return
            chunk = decoder.unused_data
            decoder = zstandard.ZstdDecompressor().decompressobj()
            out.clear()
            started = False
    if started:
        raise CorpusError(f"{where}: truncated zstd frame")


def read_shard(path: Path) -> Iterator[Word]:
    """Streams every `Word` in one shard in write order, one frame at a time."""
    return read_records(path, Word)


def read_records[M: Message](path: Path, message_type: type[M]) -> Iterator[M]:
    """Streams every record of one shard as `message_type`, in write order."""
    with path.open("rb") as f:
        for frame in _frames(f, str(path)):
            for payload in _split_records(frame):
                yield _parse(payload, message_type)


def read_corpus(corpus_dir: Path, prefix: str = DEFAULT_PREFIX) -> Iterator[Word]:
    """Streams every `Word` in the corpus, shard by shard, in write order.

    When `corpus.meta.pb` is present its `word_count` is checked at the end: a shard cut
    exactly at a frame boundary is still valid zstd, so only the count can catch it.
    """
    count = 0
    for path in shard_paths(corpus_dir, prefix):
        for word in read_shard(path):
            count += 1
            yield word
    if (corpus_dir / META_NAME).exists():
        expected = read_corpus_meta(corpus_dir).word_count
        if count != expected:
            raise CorpusError(
                f"{corpus_dir}: read {count} words, metadata says {expected}"
            )


def read_at(corpus_dir: Path, location: Location, prefix: str = DEFAULT_PREFIX) -> Word:
    """Reads one record by decompressing only its frame."""
    paths = shard_paths(corpus_dir, prefix)
    if not 0 <= location.shard < len(paths):
        raise CorpusError(f"{location} is outside the {len(paths)}-shard corpus")
    with paths[location.shard].open("rb") as f:
        f.seek(location.frame_offset)
        frame = next(_frames(f, str(location), limit=1), b"")
    for i, payload in enumerate(_split_records(frame)):
        if i == location.index:
            return _parse(payload, Word)
    raise CorpusError(f"{location}: frame has no record {location.index}")


# ---------------------------------------------------------------------------
# Metadata and JSON view
# ---------------------------------------------------------------------------


def write_corpus_meta(corpus_dir: Path, meta: Corpus) -> Path:
    path = corpus_dir / META_NAME
    path.write_bytes(meta.SerializeToString(deterministic=True))
    return path


def read_corpus_meta(corpus_dir: Path) -> Corpus:
    path = corpus_dir / META_NAME
    meta = Corpus()
    try:
        meta.ParseFromString(path.read_bytes())
    except FileNotFoundError as e:
        raise CorpusError(f"{path} does not exist") from e
    except DecodeError as e:
        raise CorpusError(f"{path}: {e}") from e
    return meta


def to_json(message: Message, indent: int | None = None) -> str:
    """JSON for `--format=jsonl` and diffing (R7.5); one line unless `indent`."""
    rendered: str = json_format.MessageToJson(
        message,
        indent=indent,
        preserving_proto_field_name=True,
        sort_keys=True,
        ensure_ascii=False,
    )
    return rendered
