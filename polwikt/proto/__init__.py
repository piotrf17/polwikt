"""The protobuf schema, generated modules and corpus read/write helpers (§7)."""

from polwikt.proto.io import (
    META_NAME,
    SCHEMA_VERSION,
    CorpusError,
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

__all__ = [
    "META_NAME",
    "SCHEMA_VERSION",
    "CorpusError",
    "Location",
    "ShardWriter",
    "read_at",
    "read_corpus",
    "read_corpus_meta",
    "read_shard",
    "shard_paths",
    "to_json",
    "write_corpus_meta",
]
