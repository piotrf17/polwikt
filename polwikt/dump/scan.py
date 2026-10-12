"""P1: streams the dump into a Wtp-readable page store (R3.1-R3.5).

The store is upstream's own `pages` table, written through `Wtp.add_page` so template
bodies get upstream's `<noinclude>`/`<onlyinclude>` handling, plus our additive side
tables: `page_meta` (ids), `all_titles` (R3.2a) and `scan_meta` (R3.4/R3.5).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import subprocess
import time
from bz2 import BZ2File
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any

from lxml import etree
from wikitextprocessor import Wtp
from wikitextprocessor.dumpparser import add_default_templates, decompress_dump_file

from polwikt import __version__
from polwikt.config import Config

log = logging.getLogger(__name__)

# Bumped whenever the keep/skip rules change in a way the config doesn't capture, so an
# existing store built under the old rules is refused (R3.4).
PREDICATE_VERSION = 1

# Upstream's parse_dump_xml skips these silently; we skip them too, but count them.
# MediaWiki subpage conventions: template docs and test harnesses are never transcluded.
_SKIP_TITLE_SUFFIX = "/documentation"
_SKIP_TITLE_INFIX = "/testcases"
_KEPT_MODELS = ("wikitext", "Scribunto", "json")

_BATCH = 20_000
_REPORT_EVERY = 500_000

SIDE_TABLES = """
CREATE TABLE IF NOT EXISTS page_meta (
  title TEXT NOT NULL,
  namespace_id INTEGER NOT NULL,
  page_id INTEGER NOT NULL,
  revision_id INTEGER NOT NULL,
  PRIMARY KEY (title, namespace_id)
);
CREATE TABLE IF NOT EXISTS all_titles (
  page_id INTEGER PRIMARY KEY,
  ns INTEGER NOT NULL,
  title TEXT NOT NULL,
  redirect_to TEXT
);
CREATE TABLE IF NOT EXISTS scan_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""
_FINAL_INDEXES = """
CREATE UNIQUE INDEX IF NOT EXISTS all_titles_by_title ON all_titles (title, ns);
CREATE UNIQUE INDEX IF NOT EXISTS page_meta_by_id ON page_meta (page_id);
"""


class ScanError(Exception):
    """The dump could not be read, or an existing store doesn't match this scan."""


@dataclass(frozen=True)
class RawPage:
    page_id: int
    revision_id: int
    ns: int
    title: str
    redirect_to: str | None
    model: str
    text: str


@dataclass
class ScanCounters:
    """What P1 read and kept, per namespace, and why it skipped (R3.5)."""

    read: Counter[int] = field(default_factory=Counter)
    kept: Counter[int] = field(default_factory=Counter)
    skipped: Counter[str] = field(default_factory=Counter)
    kept_bytes: int = 0
    near_misses: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "read": {str(k): v for k, v in sorted(self.read.items())},
            "kept": {str(k): v for k, v in sorted(self.kept.items())},
            "skipped": dict(sorted(self.skipped.items())),
            "kept_bytes": self.kept_bytes,
            "near_misses": len(self.near_misses),
        }


def language_heading_re(languages: tuple[str, ...]) -> re.Pattern[str]:
    """An L2 heading line for any of `languages`, tolerating inner spaces (R3.2)."""
    names = "|".join(re.escape(lang) for lang in languages)
    return re.compile(rf"^==[ \t]*(?:{names})[ \t]*==[ \t]*$", re.MULTILINE)


def predicate(cfg: Config) -> dict[str, Any]:
    """Everything that decides what P1 keeps; its hash invalidates a stale store."""
    return {
        "version": PREDICATE_VERSION,
        "heading_re": language_heading_re(cfg.languages).pattern,
        "namespaces": sorted(cfg.scan_namespaces),
        "skip_title_suffix": _SKIP_TITLE_SUFFIX,
        "skip_title_infix": _SKIP_TITLE_INFIX,
        "models": list(_KEPT_MODELS),
    }


def fingerprint(obj: Any) -> str:
    return hashlib.sha1(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def iter_pages(stream: IO[bytes] | BZ2File) -> Iterator[RawPage]:
    """Yields every <page> of a MediaWiki XML export, freeing each as it goes."""
    for _, page in etree.iterparse(stream, events=("end",), tag="{*}page"):
        page_id = revision_id = ns = 0
        title = model = text = ""
        redirect_to: str | None = None
        for child in page:
            tag = _local(child.tag)
            if tag == "title":
                title = child.text or ""
            elif tag == "ns":
                ns = int(child.text or 0)
            elif tag == "id":
                page_id = int(child.text or 0)
            elif tag == "redirect":
                redirect_to = child.get("title", "")
            elif tag == "revision":
                for rev in child:
                    rtag = _local(rev.tag)
                    if rtag == "id":
                        revision_id = int(rev.text or 0)
                    elif rtag == "model":
                        model = rev.text or ""
                    elif rtag == "text":
                        text = rev.text or ""
        yield RawPage(page_id, revision_id, ns, title, redirect_to, model, text)
        # clear() alone leaves an empty element per page on the root: 10^7 of them.
        page.clear(keep_tail=True)
        while page.getprevious() is not None:
            del page.getparent()[0]


def _local(tag: Any) -> str:
    name = str(tag)
    return name[name.rfind("}") + 1 :]


def read_scan_meta(db: Path) -> dict[str, str]:
    """The `scan_meta` table of a finished store, or {} if it has none."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return dict(conn.execute("SELECT key, value FROM scan_meta"))
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()


@dataclass(frozen=True)
class ScanResult:
    db: Path
    skipped_existing: bool
    meta: dict[str, str]


def scan(
    cfg: Config,
    dump: Path,
    db: Path,
    *,
    dump_sha1: str,
    force: bool = False,
) -> ScanResult:
    """Builds `db` from `dump` unless a finished store for the same dump and predicate
    already exists (R3.4). The build goes to `<db>.part` and is renamed on success; a
    leftover `.part` from an interrupted scan is discarded, since resuming a stream
    mid-file would still decompress and parse everything before the cut."""
    pred = predicate(cfg)
    pred_fp = fingerprint(pred)
    if db.exists() and not force:
        meta = read_scan_meta(db)
        if meta.get("dump_sha1") == dump_sha1 and meta.get("predicate_fp") == pred_fp:
            log.info("%s is current for this dump and predicate; skipping P1", db)
            return ScanResult(db, True, meta)
        raise ScanError(
            f"{db} was built from another dump or filter predicate "
            f"(dump {meta.get('dump_sha1', '?')}, predicate "
            f"{meta.get('predicate_fp', '?')}); rerun with --force to rebuild it"
        )

    part = db.with_name(db.name + ".part")
    for stale in db.parent.glob(part.name + "*"):
        log.warning("discarding %s from an interrupted scan", stale)
        stale.unlink()
    db.parent.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    counters = _build(cfg, dump, part)
    elapsed = time.monotonic() - started

    meta = {
        "dump_file": dump.name,
        "dump_sha1": dump_sha1,
        "pinned": json.dumps(dump_sha1 == cfg.dump.sha1),
        "predicate": json.dumps(pred, sort_keys=True),
        "predicate_fp": pred_fp,
        "counters": json.dumps(counters.to_json(), sort_keys=True),
        "near_misses": json.dumps(counters.near_misses),
        "polwikt_version": __version__,
        "elapsed_s": f"{elapsed:.0f}",
    }
    conn = sqlite3.connect(part)
    try:
        with conn:
            conn.executemany("INSERT INTO scan_meta VALUES (?, ?)", meta.items())
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()
    for suffix in ("-wal", "-shm"):
        Path(f"{part}{suffix}").unlink(missing_ok=True)
    if db.exists():
        db.unlink()
    part.rename(db)
    _log_summary(counters, elapsed)
    return ScanResult(db, False, meta)


def _build(cfg: Config, dump: Path, part: Path) -> ScanCounters:
    wtp = Wtp(db_path=part, quiet=True)
    try:
        return _fill(cfg, dump, wtp)
    finally:
        wtp.close_db_conn()


def _fill(cfg: Config, dump: Path, wtp: Wtp) -> ScanCounters:
    heading = language_heading_re(cfg.languages)
    # A cheap substring test before the regex; the near-miss check below reuses it.
    needles = tuple(f"={lang}" for lang in cfg.languages) + tuple(
        f"= {lang}" for lang in cfg.languages
    )
    namespaces = frozenset(cfg.scan_namespaces)
    counters = ScanCounters()
    conn = wtp.db_conn
    conn.executescript(SIDE_TABLES)
    # A crash restarts the scan from scratch, so durability buys nothing here.
    conn.execute("PRAGMA synchronous = OFF")
    titles: list[tuple[int, int, str, str | None]] = []
    metas: list[tuple[str, int, int, int]] = []

    def flush() -> None:
        conn.executemany("INSERT INTO all_titles VALUES (?, ?, ?, ?)", titles)
        conn.executemany("INSERT INTO page_meta VALUES (?, ?, ?, ?)", metas)
        conn.commit()
        titles.clear()
        metas.clear()

    source = decompress_dump_file(str(dump))
    stream: IO[bytes] | BZ2File
    if isinstance(source, subprocess.Popen):
        assert source.stdout is not None
        stream = source.stdout
    else:
        stream = source
    try:
        for n, page in enumerate(iter_pages(stream), 1):
            counters.read[page.ns] += 1
            titles.append((page.page_id, page.ns, page.title, page.redirect_to))
            if _keep(page, namespaces, heading, needles, counters):
                wtp.add_page(
                    page.title,
                    page.ns,
                    body=None if page.redirect_to is not None else page.text,
                    redirect_to=page.redirect_to,
                    model=page.model,
                )
                metas.append((page.title, page.ns, page.page_id, page.revision_id))
                counters.kept[page.ns] += 1
                counters.kept_bytes += len(page.text.encode())
            if len(titles) >= _BATCH:
                flush()
            if n % _REPORT_EVERY == 0:
                log.info(
                    "  %d pages read, %d kept (%d ns-0)",
                    n,
                    sum(counters.kept.values()),
                    counters.kept[0],
                )
        flush()
    except etree.XMLSyntaxError as e:
        raise ScanError(f"{dump}: malformed XML: {e}") from e
    finally:
        if isinstance(source, subprocess.Popen):
            stream.close()
            returncode = source.wait()
        else:
            source.close()
            returncode = 0
    if returncode != 0:
        raise ScanError(f"decompressing {dump} failed (exit {returncode})")

    add_default_templates(wtp)  # {{!}}, {{=}}: magic words upstream stores as pages
    conn.executescript(_FINAL_INDEXES)
    conn.commit()
    return counters


def _keep(
    page: RawPage,
    namespaces: frozenset[int],
    heading: re.Pattern[str],
    needles: tuple[str, ...],
    counters: ScanCounters,
) -> bool:
    """R3.2/R3.3: Polish-heading ns-0 pages and every page of the R2.2 namespaces."""
    if page.ns == 0:
        if page.redirect_to is not None or not any(n in page.text for n in needles):
            return False
        if heading.search(page.text):
            return True
        # "==Polish" somewhere but no L2 heading line: an L3+ heading, a trailing
        # comment, or a predicate bug. Kept out, but listed so it can be audited (R3.5).
        counters.near_misses.append(page.title)
        return False
    if page.ns not in namespaces:
        return False
    if page.title.endswith(_SKIP_TITLE_SUFFIX) or _SKIP_TITLE_INFIX in page.title:
        counters.skipped["subpage"] += 1
        return False
    if page.redirect_to is None and page.model not in _KEPT_MODELS:
        counters.skipped[f"model:{page.model}"] += 1
        return False
    return True


def _log_summary(counters: ScanCounters, elapsed: float) -> None:
    read0, kept0 = counters.read[0], counters.kept[0]
    log.info(
        "P1 done in %.0f min: ns-0 kept %d of %d (%.2f%%), %d near misses",
        elapsed / 60,
        kept0,
        read0,
        100 * kept0 / max(read0, 1),
        len(counters.near_misses),
    )
    for ns in sorted(counters.kept):
        log.info("  ns %d: kept %d of %d", ns, counters.kept[ns], counters.read[ns])
    for reason, count in sorted(counters.skipped.items()):
        log.info("  skipped %s: %d", reason, count)
