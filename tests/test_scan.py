"""P1 against a synthetic dump: what is kept, what is title-only, and Wtp reads it."""

from __future__ import annotations

import bz2
import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from xml.sax.saxutils import escape

import pytest
from wikitextprocessor import Wtp

from polwikt.config import load_config
from polwikt.dump.scan import ScanError, language_heading_re, read_scan_meta, scan

REPO = Path(__file__).resolve().parent.parent
SHA1 = "0" * 40

# (page_id, ns, title, redirect target, model, text)
PAGES = [
    (1, 0, "kot", None, "wikitext", "==Polish==\n===Noun===\n{{greet|kocie}}\n"),
    (2, 0, "cat", None, "wikitext", "==English==\n* Polish: {{t|pl|kot}}\n"),
    (3, 0, "pies", None, "wikitext", "==Czech==\n\n== Polish ==\n===Noun===\n"),
    (4, 0, "kotek", "kot", "wikitext", "#REDIRECT [[kot]]"),
    (5, 0, "ptak", None, "wikitext", "==Slovak==\n===Polish===\nsomething\n"),
    (
        10,
        10,
        "Template:greet",
        None,
        "wikitext",
        "Hi {{{1}}}<noinclude>doc</noinclude>",
    ),
    (
        11,
        10,
        "Template:hello",
        "Template:greet",
        "wikitext",
        "#REDIRECT [[Template:greet]]",
    ),
    (12, 10, "Template:greet/documentation", None, "wikitext", "docs"),
    (13, 828, "Module:echo", None, "Scribunto", "return {}"),
    (14, 828, "Module:echo/testcases", None, "Scribunto", "return {}"),
    (15, 828, "Module:style.css", None, "sanitized-css", "a{}"),
    (16, 114, "Citations:kot", None, "wikitext", "==Polish==\n"),
    (
        17,
        118,
        "Reconstruction:Proto-Slavic/kotъ",
        None,
        "wikitext",
        "==Proto-Slavic==\n",
    ),
]


def _dump_xml() -> bytes:
    pages = []
    for page_id, ns, title, redirect, model, text in PAGES:
        redirect_xml = f'<redirect title="{escape(redirect)}" />' if redirect else ""
        pages.append(
            f"<page><title>{escape(title)}</title><ns>{ns}</ns><id>{page_id}</id>"
            f"{redirect_xml}<revision><id>{page_id * 100}</id><model>{model}</model>"
            f'<text bytes="{len(text)}" xml:space="preserve">{escape(text)}</text>'
            "</revision></page>"
        )
    return (
        '<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.11/" xml:lang="en">'
        "<siteinfo><sitename>Wiktionary</sitename></siteinfo>"
        + "".join(pages)
        + "</mediawiki>"
    ).encode()


@pytest.fixture
def dump(tmp_path: Path) -> Path:
    path = tmp_path / "enwiktionary-test-pages-articles.xml.bz2"
    path.write_bytes(bz2.compress(_dump_xml()))
    return path


@pytest.fixture
def store(tmp_path: Path, dump: Path) -> Path:
    db = tmp_path / "pages.sqlite"
    scan(load_config(REPO), dump, db, dump_sha1=SHA1)
    return db


def _rows(db: Path, sql: str) -> list[tuple[object, ...]]:
    conn = sqlite3.connect(db)
    try:
        return list(conn.execute(sql))
    finally:
        conn.close()


def test_heading_predicate() -> None:  # R3.2
    heading = language_heading_re(("Polish",))
    assert heading.search("x\n==Polish==\ny")
    assert heading.search("== Polish ==  ")
    assert not heading.search("===Polish===")
    assert not heading.search("==Middle Polish==")
    assert not heading.search("* Polish: {{t|pl|kot}}")


def test_only_polish_ns0_and_r2_2_namespaces_are_stored(store: Path) -> None:
    kept = {t for (t,) in _rows(store, "SELECT title FROM pages")}
    assert kept == {
        "kot",
        "pies",
        "Template:greet",
        "Template:hello",
        "Module:echo",
        "Reconstruction:Proto-Slavic/kotъ",
        # upstream's magic-word templates
        "Template:!",
        "Template:=",
        "Template:((",
        "Template:))",
    }


def test_every_page_has_a_title_row(store: Path) -> None:  # R3.2a, R2.3
    rows = _rows(store, "SELECT page_id, ns, title, redirect_to FROM all_titles")
    assert len(rows) == len(PAGES)
    assert (4, 0, "kotek", "kot") in rows
    assert (16, 114, "Citations:kot", None) in rows


def test_page_meta_keeps_ids(store: Path) -> None:  # R3.1
    rows = _rows(
        store, "SELECT title, namespace_id, page_id, revision_id FROM page_meta"
    )
    assert ("kot", 0, 1, 100) in rows
    assert ("Module:echo", 828, 13, 1300) in rows
    assert len(rows) == 6


def test_counters_and_near_misses(store: Path) -> None:  # R3.5
    meta = read_scan_meta(store)
    counters = json.loads(meta["counters"])
    assert counters["read"]["0"] == 5
    assert counters["kept"]["0"] == 2
    assert counters["skipped"] == {"model:sanitized-css": 1, "subpage": 2}
    assert json.loads(meta["near_misses"]) == ["ptak"]
    assert meta["dump_sha1"] == SHA1
    assert meta["pinned"] == "false"


def test_wtp_reads_the_store_directly(store: Path) -> None:  # R3.1
    wtp = Wtp(db_path=store, quiet=True)
    try:
        wtp.start_page("kot")
        assert wtp.expand("{{greet|kocie}}") == "Hi kocie"  # <noinclude> stripped
        assert wtp.expand("{{hello|psie}}") == "Hi psie"  # template redirect
        page = wtp.get_page("kot", 0)
        assert page is not None and page.body is not None
        assert page.body.startswith("==Polish==")
    finally:
        wtp.close_db_conn()


def test_rescan_is_skipped_when_current(tmp_path: Path, dump: Path) -> None:  # R3.4
    cfg = load_config(REPO)
    db = tmp_path / "pages.sqlite"
    assert not scan(cfg, dump, db, dump_sha1=SHA1).skipped_existing
    assert scan(cfg, dump, db, dump_sha1=SHA1).skipped_existing
    with pytest.raises(ScanError, match="another dump"):
        scan(cfg, dump, db, dump_sha1="1" * 40)
    changed = replace(cfg, languages=("Polish", "Kashubian"))
    with pytest.raises(ScanError, match="filter predicate"):
        scan(changed, dump, db, dump_sha1=SHA1)
    assert not scan(changed, dump, db, dump_sha1=SHA1, force=True).skipped_existing


def test_interrupted_scan_leaves_no_store(tmp_path: Path) -> None:
    db = tmp_path / "pages.sqlite"
    broken = tmp_path / "broken.xml.bz2"
    broken.write_bytes(bz2.compress(_dump_xml()[:-200]))
    with pytest.raises(ScanError):
        scan(load_config(REPO), broken, db, dump_sha1=SHA1)
    assert not db.exists()
