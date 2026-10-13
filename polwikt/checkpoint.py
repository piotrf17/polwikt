"""Checkpoints for resumable passes (R9.4): what a run was, and how far it got.

A pass's output directory holds a checkpoint naming the run's *fingerprint* — the
pages it covers plus the pipeline's own source, config and lock file — so a rerun
resumes only the run it would have been, and a code change can never mix two runs'
output in one directory. Checkpoints are written atomically.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable
from functools import cache
from pathlib import Path
from typing import Any

_PACKAGE = Path(__file__).resolve().parent
_SOURCE_SUFFIXES = frozenset({".py", ".pyi", ".toml", ".lua", ".json"})


@cache
def code_fingerprint() -> str:
    """sha256 of the package's source and data files, and the checkout's uv.lock."""
    digest = hashlib.sha256()
    files = sorted(
        p
        for p in _PACKAGE.rglob("*")
        if p.is_file() and p.suffix in _SOURCE_SUFFIXES and "__pycache__" not in p.parts
    )
    lock = _PACKAGE.parent / "uv.lock"
    for path in [*files, *([lock] if lock.exists() else [])]:
        digest.update(str(path.relative_to(_PACKAGE.parent)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def fingerprint(parts: Iterable[str]) -> str:
    """sha256 of the run's inputs (one string each) plus the code fingerprint."""
    digest = hashlib.sha256(code_fingerprint().encode())
    for part in parts:
        digest.update(b"\n")
        digest.update(part.encode())
    return digest.hexdigest()


def read(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data: dict[str, Any] = json.loads(path.read_text("utf-8"))
    return data


def write(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(tmp, path)
