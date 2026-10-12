"""Maintains the golden corpus in tests/golden/ (R8.1). A dev tool, not pipeline code.

    uv run python tools/golden.py pull [--db data/pages.sqlite]

`pull` copies the raw wikitext of every page in tests/golden/pages.toml out of the page
store, records its ids and sha1 in manifest.json, creates a `"TODO"` expectation for
any new page, and deletes fixtures that are no longer listed. The store snapshot
(R8.1a, `snapshot`) needs the expansion recorder and arrives with M4.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sqlite3
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from polwikt.config import load_config  # noqa: E402

GOLDEN = REPO / "tests" / "golden"
TODO = '"TODO"\n'

log = logging.getLogger("golden")


class GoldenError(Exception):
    pass


@dataclass(frozen=True)
class Listed:
    title: str
    why: str

    @property
    def slug(self) -> str:
        return slug(self.title)


def slug(title: str) -> str:
    """A fixture file stem: the title with spaces as underscores, kept readable."""
    if "/" in title or title.startswith("."):
        raise GoldenError(f"{title!r} can't be a file name; give it an explicit slug")
    return title.replace(" ", "_")


def load_list(golden: Path) -> list[Listed]:
    with (golden / "pages.toml").open("rb") as f:
        data = tomllib.load(f)
    pages = [Listed(p["title"], p["why"]) for p in data.get("page", [])]
    seen: dict[str, str] = {}
    for page in pages:
        # Case-insensitive, so the corpus also checks out on macOS and Windows.
        key = page.slug.casefold()
        if key in seen:
            raise GoldenError(f"{page.title!r} collides with {seen[key]!r}")
        seen[key] = page.title
    return pages


def pull(db: Path, golden: Path) -> None:
    cfg = load_config(REPO)
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        meta = dict(conn.execute("SELECT key, value FROM scan_meta"))
        if meta.get("dump_sha1") != cfg.dump.sha1:
            raise GoldenError(
                f"{db} was not built from the pinned dump {cfg.dump.date}; "
                "fixtures must come from the pin (R8.1)"
            )
        listed = load_list(golden)
        (golden / "pages").mkdir(parents=True, exist_ok=True)
        (golden / "expected").mkdir(parents=True, exist_ok=True)
        manifest = []
        for page in listed:
            row = conn.execute(
                "SELECT p.body, m.page_id, m.revision_id FROM pages p "
                "JOIN page_meta m USING (title, namespace_id) "
                "WHERE p.title = ? AND p.namespace_id = 0",
                (page.title,),
            ).fetchone()
            if row is None:
                raise GoldenError(f"{page.title!r} is not a Polish page in {db}")
            body, page_id, revision_id = row
            (golden / "pages" / f"{page.slug}.wiki").write_text(body, encoding="utf-8")
            expected = golden / "expected" / f"{page.slug}.json"
            if not expected.exists():
                expected.write_text(TODO, encoding="utf-8")
            manifest.append(
                {
                    "title": page.title,
                    "slug": page.slug,
                    "page_id": page_id,
                    "revision_id": revision_id,
                    "sha1": hashlib.sha1(body.encode()).hexdigest(),
                }
            )
    finally:
        conn.close()
    _prune(golden, {p.slug for p in listed})
    doc = {"dump": {"date": cfg.dump.date, "sha1": cfg.dump.sha1}, "pages": manifest}
    (golden / "manifest.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    log.info("pulled %d pages into %s", len(manifest), golden)


def _prune(golden: Path, slugs: set[str]) -> None:
    for sub, suffix in (("pages", ".wiki"), ("expected", ".json")):
        for path in sorted((golden / sub).glob(f"*{suffix}")):
            if path.name.removesuffix(suffix) not in slugs:
                log.warning("removing %s: no longer in pages.toml", path)
                path.unlink()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_pull = sub.add_parser("pull", help="refresh fixtures from the page store")
    p_pull.add_argument("--db", type=Path, default=REPO / "data" / "pages.sqlite")
    sub.add_parser("snapshot", help="build store.sqlite.zst (PLAN.md M4)")
    args = parser.parse_args(argv)
    try:
        if args.command == "pull":
            pull(args.db, GOLDEN)
        else:
            raise GoldenError("snapshot needs the expansion recorder (PLAN.md M4)")
    except GoldenError as e:
        log.error("%s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
