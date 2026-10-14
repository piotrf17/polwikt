"""The release artifact: a finished corpus as one versioned tar file (R7.9).

`polwikt-<dump date>-schema<N>.tar` holds, under a directory of the same name, the
Word shards, `corpus.meta.pb`, `LICENSE-DATA`, `stats.json` and the `polwikt.proto`
that reads them. A corpus from an unpinned dump is named `…-unpinned` (R2.1a). The
shards are zstd already, so the tar is not compressed again. Members are sorted and
carry no owner or timestamp: one corpus always packs to the same bytes (G5).
"""

from __future__ import annotations

import hashlib
import io
import tarfile
from dataclasses import dataclass
from pathlib import Path

from polwikt import checkpoint
from polwikt.finalize.run import MARKER
from polwikt.proto.io import META_NAME, read_corpus_meta, shard_paths


class ReleaseError(Exception):
    """The corpus is missing, incomplete, or not packable."""


@dataclass(frozen=True)
class Release:
    path: Path
    sha256: str
    members: int


def release_name(corpus_dir: Path) -> str:
    meta = read_corpus_meta(corpus_dir)
    if not meta.dump_date:
        raise ReleaseError(f"{corpus_dir}: the corpus has no dump date")
    name = f"polwikt-{meta.dump_date}-schema{meta.schema_version}"
    return name if meta.pinned else f"{name}-unpinned"


def package(corpus_dir: Path, schema: Path, out_dir: Path) -> Release:
    """Packs a complete corpus and its schema into `out_dir`, with a .sha256 beside."""
    marker = checkpoint.read(corpus_dir / MARKER)
    if marker is None or not marker.get("complete"):
        raise ReleaseError(f"{corpus_dir} holds no complete `polwikt finalize` run")
    name = release_name(corpus_dir)
    members = [
        *shard_paths(corpus_dir),
        corpus_dir / META_NAME,
        corpus_dir / "LICENSE-DATA",
        corpus_dir / "stats.json",
        schema,
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.tar"
    part = path.with_name(path.name + ".part")
    with tarfile.open(part, "w", format=tarfile.PAX_FORMAT) as tar:
        for member in sorted(members, key=lambda p: p.name):
            info = tarfile.TarInfo(f"{name}/{member.name}")
            data = member.read_bytes()
            info.size, info.mode = len(data), 0o644
            tar.addfile(info, io.BytesIO(data))
    digest = hashlib.sha256(part.read_bytes()).hexdigest()
    part.replace(path)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return Release(path, digest, len(members))
