"""P3 driver: every Polish page through extract_record, in page-id order (R3.9-R3.12).

Workers each hold one PolwiktWtp over the read-only store (R3.10). Results come back in
page-id order whatever `jobs` is (R3.11), so the shards are byte-identical across runs.
A page that raises is logged with its traceback and skipped (R3.12); the run aborts
once errors exceed `max_error_rate` of the planned pages.

Outputs in `out_dir`:
- `p3-NNNNN-of-MMMMM.pb.zst`: one `PageRecord` per page (proto/p3.proto)
- `stats.json`: deterministic counters (no timings, G5)
- `unhandled.jsonl`: templates no policy entry covers, with an example page (R4.6)
- `errors.jsonl`: pages that raised, with the traceback (R3.12)
- `title_only.jsonl`: pages whose expansion read a title-only page (R3.2a)
- `dropped_colabelled.jsonl`: pages that lost a co-labelled Middle Polish sense (R6.6c)
"""

from __future__ import annotations

import json
import logging
import multiprocessing
import resource
import sqlite3
import time
import traceback
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from polwikt import checkpoint
from polwikt.dump.store import read_page
from polwikt.expand.policy import Unhandled
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.page import Settings, extract_record
from polwikt.proto.io import ShardWriter, shard_paths

log = logging.getLogger(__name__)

PREFIX = "p3"
RECORDS_PER_SHARD = 4096  # a checkpoint falls at every shard boundary (R9.4)
_CHUNK = 8


class P3Error(Exception):
    """The run aborted: too many page errors, or bad arguments."""


@dataclass(frozen=True)
class PageRef:
    page_id: int
    revision_id: int
    title: str


@dataclass
class PageOutcome:
    ref: PageRef
    record: bytes = b""
    stats: Counter[str] = field(default_factory=Counter)
    unhandled: list[str] = field(default_factory=list)
    title_only: list[str] = field(default_factory=list)
    colabelled: int = 0
    error: str = ""
    rss_kb: int = 0  # the worker's peak RSS so far (R9.3)


@dataclass
class P3Summary:
    pages: int
    errors: int
    stats: Counter[str]
    seconds: float
    peak_rss_kb: int = 0
    skipped: bool = False  # the run was already complete (R9.4)


def polish_pages(
    db: Path, titles: list[str] | None, limit: int | None
) -> list[PageRef]:
    """P3's pages in page-id order: stored ns-0 pages minus transclusion targets."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        query = (
            "SELECT page_id, revision_id, title FROM page_meta WHERE namespace_id = 0 "
            "AND title NOT IN (SELECT title FROM transclusion_targets)"
        )
        args: list[Any] = []
        if titles is not None:
            query += f" AND title IN ({','.join('?' * len(titles))})"
            args.extend(titles)
        query += " ORDER BY page_id"
        if limit is not None:
            query += " LIMIT ?"
            args.append(limit)
        refs = [PageRef(*row) for row in conn.execute(query, args)]
    finally:
        conn.close()
    if titles is not None:
        missing = sorted(set(titles) - {r.title for r in refs})
        if missing:
            raise P3Error(f"not Polish pages in {db}: {', '.join(missing)}")
    return refs


# -- worker ---------------------------------------------------------------------------

_state: tuple[PolwiktWtp, Settings, Path] | None = None


def _init_worker(db: Path, settings: Settings) -> None:
    global _state
    _state = (PolwiktWtp(db), settings, db)


def _extract(ref: PageRef) -> PageOutcome:
    assert _state is not None, "worker not initialised"
    wtp, settings, db = _state
    outcome = PageOutcome(ref)
    outcome.rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    before = Counter(wtp.stats)
    wtp.title_only_reads.clear()
    try:
        page = read_page(db, ref.title)
        if page is None:
            raise LookupError(f"{ref.title!r} vanished from the store")
        result = extract_record(
            wtp,
            ref.title,
            page.body,
            settings,
            page_id=ref.page_id,
            revision_id=ref.revision_id,
        )
    except Exception:  # R3.12: one page must not kill the run
        outcome.error = traceback.format_exc()
        return outcome
    outcome.record = result.record.SerializeToString(deterministic=True)
    outcome.stats = result.stats
    outcome.stats.update(Counter(wtp.stats) - before)
    outcome.unhandled = result.unhandled
    outcome.title_only = sorted(wtp.title_only_reads)
    outcome.colabelled = len(result.colabelled)
    return outcome


def _outcomes(
    db: Path, settings: Settings, refs: list[PageRef], jobs: int
) -> Iterator[PageOutcome]:
    if jobs == 1:
        _init_worker(db, settings)
        yield from map(_extract, refs)
        return
    context = multiprocessing.get_context("spawn")
    with context.Pool(jobs, initializer=_init_worker, initargs=(db, settings)) as pool:
        yield from pool.imap(_extract, refs, chunksize=_CHUNK)  # ordered (R3.11)


# -- driver ---------------------------------------------------------------------------


def run_p3(
    settings: Settings,
    db: Path,
    out_dir: Path,
    *,
    jobs: int,
    titles: list[str] | None = None,
    limit: int | None = None,
    max_error_rate: float = 0.01,
) -> P3Summary:
    """Extracts every selected page; resumes from, or skips after, its checkpoint."""
    if jobs < 1:
        raise P3Error("--jobs must be at least 1")
    refs = polish_pages(db, titles, limit)
    run_id = _fingerprint(db, settings, refs)
    state = _Progress.start(out_dir, run_id)
    if state.complete:
        log.info("P3: %s is already complete for this run; nothing to do", out_dir)
        return P3Summary(len(refs), len(state.errors), state.stats, 0.0, skipped=True)
    todo = refs[state.pages_done :]
    log.info(
        "P3: %d pages, %d worker(s)%s",
        len(refs),
        jobs,
        f", resuming after {state.pages_done}" if state.pages_done else "",
    )
    started = time.monotonic()
    budget = max_error_rate * len(refs)
    peak_rss = 0
    try:
        with ShardWriter(
            out_dir,
            prefix=PREFIX,
            records_per_shard=RECORDS_PER_SHARD,
            resume=state.shards,
            keep_finished=True,
        ) as writer:
            outcomes = _outcomes(db, settings, todo, jobs)
            for n, outcome in enumerate(outcomes, state.pages_done + 1):
                peak_rss = max(peak_rss, outcome.rss_kb)
                state.add(outcome, writer)
                if len(state.errors) > budget:
                    raise P3Error(
                        f"{len(state.errors)} page errors exceed --max-error-rate "
                        f"{max_error_rate} of {len(refs)} pages (R3.12)"
                    )
                if (shards := writer.finish_full_shard()) is not None:
                    state.checkpoint(n, shards)
                if n % 5000 == 0:
                    rate = (n - state.resumed_at) / (time.monotonic() - started)
                    log.info("  %d / %d pages, %.1f pages/s", n, len(refs), rate)
        state.finish()
    finally:
        state.write_reports()
    seconds = time.monotonic() - started
    log.info(
        "P3 done: %d pages in %.0f s (%.1f pages/s), %d errors, peak RSS %d MB "
        "per worker",
        len(todo),
        seconds,
        len(todo) / max(seconds, 1e-9),
        len(state.errors),
        peak_rss // 1024,
    )
    return P3Summary(len(refs), len(state.errors), state.stats, seconds, peak_rss)


CHECKPOINT = "p3.checkpoint.json"


def _fingerprint(db: Path, settings: Settings, refs: list[PageRef]) -> str:
    """The run: the store's dump and filter, the extraction settings, the pages."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        meta = dict(
            conn.execute(
                "SELECT key, value FROM scan_meta"
                " WHERE key IN ('dump_sha1', 'predicate_fp')"
            ).fetchall()
        )
    finally:
        conn.close()
    head = [
        meta.get("dump_sha1", ""),
        meta.get("predicate_fp", ""),
        settings.language,
        ",".join(sorted(settings.drop_labels)),
    ]
    pages = (f"{r.page_id}\t{r.revision_id}\t{r.title}" for r in refs)
    return checkpoint.fingerprint([*head, *pages])


@dataclass
class _Progress:
    """Everything a P3 run accumulates, and its checkpoint (R9.4)."""

    out_dir: Path
    run_id: str
    pages_done: int = 0
    shards: int = 0
    complete: bool = False
    resumed_at: int = 0
    stats: Counter[str] = field(default_factory=Counter)
    unhandled: Unhandled = field(default_factory=Unhandled)
    errors: list[dict[str, Any]] = field(default_factory=list)
    title_only: list[dict[str, Any]] = field(default_factory=list)
    colabelled: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def start(cls, out_dir: Path, run_id: str) -> _Progress:
        saved = checkpoint.read(out_dir / CHECKPOINT)
        if saved is None:
            return cls(out_dir, run_id)
        if saved["run"] != run_id:
            raise P3Error(
                f"{out_dir} holds another P3 run (different pages, store or code); "
                "remove it or choose another --out"
            )
        state = cls(
            out_dir,
            run_id,
            pages_done=saved["pages_done"],
            shards=saved["shards"],
            complete=saved["complete"],
            resumed_at=saved["pages_done"],
            stats=Counter(saved["stats"]),
            unhandled=Unhandled(
                Counter(saved["unhandled"]["counts"]), saved["unhandled"]["examples"]
            ),
            errors=saved["errors"],
            title_only=saved["title_only"],
            colabelled=saved["colabelled"],
        )
        if state.complete:
            shard_paths(out_dir, PREFIX)  # raises if the shard set is not intact
        return state

    def add(self, outcome: PageOutcome, writer: ShardWriter) -> None:
        ref = outcome.ref
        if outcome.error:
            self.errors.append(
                {"title": ref.title, "page_id": ref.page_id, "traceback": outcome.error}
            )
            self.stats["pages.error"] += 1
            log.error("%s: %s", ref.title, outcome.error.splitlines()[-1])
            return
        writer.write_serialized(outcome.record)
        self.stats.update(outcome.stats)
        for name in outcome.unhandled:
            self.unhandled.add(name, ref.title)
        if outcome.colabelled:
            self.colabelled.append({"page": ref.title, "senses": outcome.colabelled})
        if outcome.title_only:
            self.title_only.append({"page": ref.title, "titles": outcome.title_only})

    def checkpoint(self, pages_done: int, shards: int) -> None:
        self.pages_done, self.shards = pages_done, shards
        self._save()

    def finish(self) -> None:
        self.complete = True
        self._save()

    def _save(self) -> None:
        checkpoint.write(
            self.out_dir / CHECKPOINT,
            {
                "run": self.run_id,
                "pages_done": self.pages_done,
                "shards": self.shards,
                "complete": self.complete,
                "stats": dict(self.stats),
                "unhandled": {
                    "counts": dict(self.unhandled.counts),
                    "examples": self.unhandled.examples,
                },
                "errors": self.errors,
                "title_only": self.title_only,
                "colabelled": self.colabelled,
            },
        )

    def write_reports(self) -> None:
        _write_reports(
            self.out_dir,
            self.stats,
            self.unhandled,
            self.errors,
            self.title_only,
            self.colabelled,
        )


def _write_reports(
    out_dir: Path,
    stats: Counter[str],
    unhandled: Unhandled,
    errors: list[dict[str, Any]],
    title_only: list[dict[str, Any]],
    colabelled: list[dict[str, Any]],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "counts": dict(sorted(stats.items())),
        "unhandled_templates": len(unhandled.counts),
        "unhandled_uses": sum(unhandled.counts.values()),
    }
    (out_dir / "stats.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _jsonl(out_dir / "unhandled.jsonl", unhandled.rows())
    _jsonl(out_dir / "errors.jsonl", errors)
    _jsonl(out_dir / "title_only.jsonl", title_only)
    _jsonl(out_dir / "dropped_colabelled.jsonl", colabelled)


def _jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
