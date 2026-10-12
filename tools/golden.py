"""Maintains the golden corpus in tests/golden/ (R8.1). A dev tool, not pipeline code.

    uv run python tools/golden.py pull [--db data/pages.sqlite]

    uv run python tools/golden.py snapshot [--db data/pages.sqlite]

`pull` copies the raw wikitext of every page in tests/golden/pages.toml out of the page
store, records its ids and sha1 in manifest.json, creates a `"TODO"` expectation for
any new page, and deletes fixtures that are no longer listed.

`snapshot` fully expands each fixture's Polish section against the real store with the
lookup recorder on, then writes tests/golden/store.sqlite.zst (R8.1a): the fixtures,
every page and title the expansion touched, and the list of lookups it made, so a
test whose expansion strays outside the snapshot reports it as stale.
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

import zstandard

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from polwikt.config import load_config  # noqa: E402
from polwikt.expand.policy import canonical_name  # noqa: E402
from polwikt.expand.run import expand_text  # noqa: E402
from polwikt.expand.wtp import PolwiktWtp  # noqa: E402
from polwikt.parse.sections import language_section  # noqa: E402
from polwikt.parse.tree import iter_templates, template_name  # noqa: E402

GOLDEN = REPO / "tests" / "golden"
TODO = '"TODO"\n'
SNAPSHOT = "store.sqlite.zst"
ZSTD_LEVEL = 19

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


def snapshot(db: Path, golden: Path, out_dir: Path) -> Path:
    """Builds the golden store snapshot from what expanding the fixtures touches."""
    pages = json.loads((golden / "manifest.json").read_text(encoding="utf-8"))["pages"]
    wtp = PolwiktWtp(db, record=True)
    try:
        for page in pages:
            path = golden / "pages" / f"{page['slug']}.wiki"
            text = path.read_text(encoding="utf-8")
            section = language_section(text, "Polish") or ""
            wtp.start_page(page["title"])
            for node in iter_templates(wtp.parse(section)):
                canonical_name(wtp, template_name(node))  # policy lookups (R4.2)
            result = expand_text(wtp, section)
            if result.errors:
                log.warning("%s: %d errors", page["title"], len(result.errors))
            wtp.found_pages.add((page["title"], 0))
        lookups, found_pages, found_titles = (
            wtp.lookups,
            wtp.found_pages,
            wtp.found_titles | wtp.found_pages,
        )
        stats = dict(wtp.stats)
    finally:
        wtp.close_db_conn()
    raw = out_dir / "store.sqlite"
    raw.unlink(missing_ok=True)
    _write_snapshot(db, raw, lookups, found_pages, found_titles)
    target = golden / SNAPSHOT
    with raw.open("rb") as src, target.open("wb") as dst:
        zstandard.ZstdCompressor(level=ZSTD_LEVEL).copy_stream(src, dst)
    log.info(
        "snapshot: %d pages, %d titles, %d lookups; %.1f MB raw, %.1f MB zst; %s",
        len(found_pages),
        len(found_titles),
        len(lookups),
        raw.stat().st_size / 1e6,
        target.stat().st_size / 1e6,
        stats,
    )
    raw.unlink()
    return target


def _write_snapshot(
    src: Path,
    dst: Path,
    lookups: set[tuple[str, int | None, bool]],
    pages: set[tuple[str, int]],
    titles: set[tuple[str, int]],
) -> None:
    """Copies the touched rows into a fresh store with the source's own schema."""
    conn = sqlite3.connect(f"file:{dst}", uri=True)
    try:
        conn.execute("ATTACH DATABASE ? AS src", (f"file:{src}?mode=ro",))
        tables = ("pages", "page_meta", "all_titles", "scan_meta")
        for (sql,) in conn.execute(
            "SELECT sql FROM src.sqlite_master WHERE type = 'table' AND name IN "
            f"({','.join('?' * len(tables))}) ORDER BY name",
            tables,
        ).fetchall():
            conn.execute(sql)
        conn.execute(
            "CREATE TABLE snapshot_lookups (title TEXT NOT NULL, ns INTEGER, "
            "no_redirect INTEGER NOT NULL)"
        )
        conn.execute("CREATE TEMP TABLE want_pages (title TEXT, ns INTEGER)")
        conn.execute("CREATE TEMP TABLE want_titles (title TEXT, ns INTEGER)")
        conn.executemany("INSERT INTO want_pages VALUES (?, ?)", sorted(pages))
        conn.executemany("INSERT INTO want_titles VALUES (?, ?)", sorted(titles))
        # Sorted inserts keep the file stable across regenerations of the same pin.
        conn.execute(
            "INSERT INTO pages SELECT p.* FROM src.pages p JOIN want_pages w "
            "ON p.title = w.title AND p.namespace_id = w.ns "
            "ORDER BY p.namespace_id, p.title"
        )
        conn.execute(
            "INSERT INTO page_meta SELECT m.* FROM src.page_meta m JOIN want_pages w "
            "ON m.title = w.title AND m.namespace_id = w.ns ORDER BY m.page_id"
        )
        conn.execute(
            "INSERT INTO all_titles SELECT a.* FROM src.all_titles a "
            "JOIN want_titles w ON a.title = w.title AND a.ns = w.ns ORDER BY a.page_id"
        )
        conn.execute("INSERT INTO scan_meta SELECT * FROM src.scan_meta ORDER BY key")
        conn.execute("INSERT INTO scan_meta VALUES ('snapshot', 'golden (R8.1a)')")
        ordered = sorted(lookups, key=_lookup_order)
        conn.executemany("INSERT INTO snapshot_lookups VALUES (?, ?, ?)", ordered)
        conn.execute(
            "CREATE UNIQUE INDEX all_titles_by_title ON all_titles (title, ns)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX snapshot_lookups_key ON snapshot_lookups "
            "(title, ns, no_redirect)"
        )
        conn.commit()
        conn.execute("DETACH DATABASE src")
        conn.execute("VACUUM")
    finally:
        conn.close()


def _lookup_order(key: tuple[str, int | None, bool]) -> tuple[str, int, bool]:
    title, ns, no_redirect = key
    return title, -1 if ns is None else ns, no_redirect


def _prune(golden: Path, slugs: set[str]) -> None:
    for sub, suffix in (("pages", ".wiki"), ("expected", ".json")):
        for path in sorted((golden / sub).glob(f"*{suffix}")):
            if path.name.removesuffix(suffix) not in slugs:
                log.warning("removing %s: no longer in pages.toml", path)
                path.unlink()


def main(argv: list[str] | None = None) -> int:
    # force: wikitextprocessor already called basicConfig when it was imported.
    fmt = "%(levelname)s %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt, force=True)
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_pull = sub.add_parser("pull", help="refresh fixtures from the page store")
    p_pull.add_argument("--db", type=Path, default=REPO / "data" / "pages.sqlite")
    p_snap = sub.add_parser("snapshot", help="rebuild store.sqlite.zst (R8.1a)")
    p_snap.add_argument("--db", type=Path, default=REPO / "data" / "pages.sqlite")
    p_snap.add_argument("--tmp", type=Path, default=REPO / "data" / "tmp")
    args = parser.parse_args(argv)
    try:
        if args.command == "pull":
            pull(args.db, GOLDEN)
        else:
            args.tmp.mkdir(parents=True, exist_ok=True)
            snapshot(args.db, GOLDEN, args.tmp)
    except GoldenError as e:
        log.error("%s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
