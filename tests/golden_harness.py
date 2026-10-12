"""Loads the golden corpus (R8.1) and its store snapshot (R8.1a) for tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from polwikt.dump.store import unpack_store

GOLDEN = Path(__file__).resolve().parent / "golden"
SNAPSHOT = GOLDEN / "store.sqlite.zst"
TODO = "TODO"


@dataclass(frozen=True)
class Fixture:
    """One golden page: raw wikitext from the pinned dump plus its expectation.

    The expectation is the page's P3 `Word` as indented JSON, `null` when the page
    yields no record (an all-Middle-Polish page), or `"TODO"` until it is blessed.
    Folding (`kotów`, `mamy` → no record) is P4's, checked over the whole corpus.
    """

    title: str
    slug: str
    page_id: int
    revision_id: int
    sha1: str

    @property
    def wiki_path(self) -> Path:
        return GOLDEN / "pages" / f"{self.slug}.wiki"

    @property
    def expected_path(self) -> Path:
        return GOLDEN / "expected" / f"{self.slug}.json"

    def wikitext(self) -> str:
        return self.wiki_path.read_text(encoding="utf-8")

    def expected(self) -> Any:
        return json.loads(self.expected_path.read_text(encoding="utf-8"))


def manifest() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (GOLDEN / "manifest.json").read_text(encoding="utf-8")
    )
    return data


def fixtures() -> list[Fixture]:
    return [Fixture(**page) for page in manifest()["pages"]]


def unpack_snapshot(dest: Path) -> Path:
    """Decompresses store.sqlite.zst into `dest`, ready for `Wtp(db_path=…)`."""
    return unpack_store(SNAPSHOT, dest)
