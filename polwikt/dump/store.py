"""Read access to a P1 page store (R3.1): page text with its dump ids."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredPage:
    title: str
    namespace_id: int
    page_id: int
    revision_id: int
    body: str


def read_page(db: Path, title: str, namespace_id: int = 0) -> StoredPage | None:
    """One page's wikitext and ids, opened read-only; None when it isn't stored."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT p.body, m.page_id, m.revision_id FROM pages p "
            "JOIN page_meta m USING (title, namespace_id) "
            "WHERE p.title = ? AND p.namespace_id = ?",
            (title, namespace_id),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    body, page_id, revision_id = row
    return StoredPage(title, namespace_id, page_id, revision_id, body or "")
