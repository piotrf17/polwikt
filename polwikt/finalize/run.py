"""P4 driver: P3's PageRecords -> the canonical corpus (R3.13-R3.16, R7.2-R7.4).

Two streaming passes over the P3 shards, with what lies between them in an on-disk
SQLite staging file, so memory holds only the fold decisions (R9.3):

1. Record each page's entries, the spellings of every lemma entry's Forms, the fold
   candidates, and the relations whose inverse is implied (R3.14).
2. Decide each candidate (fold.py). Then write the Words in page order, without the
   folded entries (a page left with none yields no record), with what they left on
   their lemmas. A folded spelling stays findable as one of its lemma's Forms (R3.13b).

Outputs in `out_dir`: `words-NNNNN-of-MMMMM.pb.zst`, `corpus.meta.pb`,
`LICENSE-DATA`, `stats.json` (P3's counts plus P4's and the R8.4 coverage) and
`unresolved_forms.jsonl` (R3.13c).
"""

from __future__ import annotations

import json
import logging
import resource
import sqlite3
import time
from collections import Counter, defaultdict
from collections.abc import Iterator
from contextlib import closing
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any

from polwikt import checkpoint
from polwikt.extract.p3 import CHECKPOINT as P3_CHECKPOINT
from polwikt.extract.p3 import DumpSource
from polwikt.finalize.fold import (
    Fold,
    LemmaEntry,
    Transfer,
    add_inverse,
    carry_labels,
    choose_entry,
    config,
    is_candidate,
    renumber_etymologies,
    transfer_tables,
)
from polwikt.proto import p3_pb2 as p3
from polwikt.proto import polwikt_pb2 as pb
from polwikt.proto.io import (
    META_NAME,
    SCHEMA_VERSION,
    ShardWriter,
    read_records,
    shard_paths,
    write_corpus_meta,
)

log = logging.getLogger(__name__)

P3_PREFIX = "p3"
STAGE_NAME = ".finalize-stage.sqlite"
_BATCH = 2000


class P4Error(Exception):
    """Bad input or output directory."""


@dataclass
class P4Summary:
    words: int
    folded: int
    unresolved: int
    stats: Counter[str]
    seconds: float
    skipped: bool = False  # the run was already complete (R9.4)


@dataclass
class Plan:
    """The decisions pass 2 applies."""

    folded: dict[tuple[str, int], list[Fold]] = field(default_factory=dict)
    transfers: dict[tuple[str, int], list[Transfer]] = field(
        default_factory=lambda: defaultdict(list)
    )
    inverse: dict[str, list[tuple[int, int, str]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    titles: frozenset[str] = frozenset()
    unresolved: list[dict[str, Any]] = field(default_factory=list)


def run_p4(
    in_dir: Path, out_dir: Path, *, source: DumpSource, drop_labels: list[str]
) -> P4Summary:
    """Finalizes `in_dir`; skipped when `out_dir` already holds this run (R9.4)."""
    started = time.monotonic()
    paths = shard_paths(in_dir, P3_PREFIX)
    run_id = _fingerprint(in_dir, paths, source, drop_labels)
    if _prepare(in_dir, out_dir, run_id):
        log.info("P4: %s is already complete for this run; nothing to do", out_dir)
        return P4Summary(0, 0, 0, Counter(), 0.0, skipped=True)
    checkpoint.write(out_dir / MARKER, {"run": run_id, "complete": False})
    stage = out_dir / STAGE_NAME
    stage.unlink(missing_ok=True)
    stats: Counter[str] = Counter()
    try:
        with closing(sqlite3.connect(stage)) as db:
            _schema(db)
            _pass1(paths, db)
            plan = _decide(db, stats)
        words = _pass2(paths, plan, out_dir, stats)
    finally:
        stage.unlink(missing_ok=True)
    cfg = config()
    write_corpus_meta(
        out_dir,
        pb.Corpus(
            schema_version=SCHEMA_VERSION,
            dump_date=source.date,
            dump_sha1=source.sha1,
            pinned=source.pinned,
            pipeline_version=metadata.version("polwikt"),
            word_count=words,
            drop_labels=sorted(drop_labels),
            license=cfg.license,
            attribution=cfg.attribution,
        ),
    )
    (out_dir / "LICENSE-DATA").write_text(
        f"License: {cfg.license}\n\n{cfg.attribution}\n", encoding="utf-8"
    )
    _write_stats(in_dir, out_dir, stats)
    _jsonl(out_dir / "unresolved_forms.jsonl", plan.unresolved)
    checkpoint.write(out_dir / MARKER, {"run": run_id, "complete": True})
    seconds = time.monotonic() - started
    log.info(
        "P4 done: %d words, %d entries folded, %d unresolved, in %.0f s, "
        "peak RSS %d MB",
        words,
        stats["finalize.entries.folded"],
        len(plan.unresolved),
        seconds,
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024,
    )
    return P4Summary(
        words, stats["finalize.entries.folded"], len(plan.unresolved), stats, seconds
    )


MARKER = "finalize.json"
# Every file P4 writes: what an interrupted or superseded run leaves to clear.
_OWNED = (
    "words-*.pb.zst",
    "words-*.pb.zst.part",
    "index.sqlite",  # written by runs before the index was dropped (R7.3)
    "index.sqlite-journal",
    META_NAME,
    "LICENSE-DATA",
    "stats.json",
    "unresolved_forms.jsonl",
    STAGE_NAME,
)


def _fingerprint(
    in_dir: Path, paths: list[Path], source: DumpSource, drop_labels: list[str]
) -> str:
    """The run: P3's own run id when it checkpointed, else its files; the settings."""
    saved = checkpoint.read(in_dir / P3_CHECKPOINT)
    if saved is not None and saved.get("complete"):
        inputs = [saved["run"]]
    else:
        inputs = [f"{p.name}:{p.stat().st_size}" for p in paths]
    return checkpoint.fingerprint(
        [*inputs, repr(source), ",".join(sorted(drop_labels))]
    )


def _prepare(in_dir: Path, out_dir: Path, run_id: str) -> bool:
    """True when `out_dir` already holds this run; otherwise leaves it ready."""
    if out_dir.resolve() == in_dir.resolve():
        raise P4Error("--out must not be P3's directory")
    out_dir.mkdir(parents=True, exist_ok=True)
    owned = sorted({p for pattern in _OWNED for p in out_dir.glob(pattern)})
    saved = checkpoint.read(out_dir / MARKER)
    if saved is None:
        if owned:
            raise P4Error(f"{out_dir} holds files P4 did not write: {owned[0].name}")
        return False
    if saved["run"] == run_id and saved["complete"]:
        shard_paths(out_dir)  # raises if the shard set is not intact
        return True
    log.info(
        "P4: clearing %s (%s)",
        out_dir,
        "interrupted run" if saved["run"] == run_id else "another run",
    )
    for path in owned:
        path.unlink()
    return False


def _records(paths: list[Path]) -> Iterator[tuple[str, pb.Word]]:
    for path in paths:
        for record in read_records(path, p3.PageRecord):
            if record.word:
                yield record.title, pb.Word.FromString(record.word)


# -- pass 1 ---------------------------------------------------------------------------


def _schema(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        PRAGMA journal_mode = OFF;
        PRAGMA synchronous = OFF;
        CREATE TABLE pages (title TEXT PRIMARY KEY, ord INTEGER NOT NULL);
        CREATE TABLE entries (
            title TEXT, idx INTEGER, pos INTEGER, candidate INTEGER,
            PRIMARY KEY (title, idx)
        ) WITHOUT ROWID;
        CREATE TABLE surfaces (
            lemma TEXT, surface TEXT, idx INTEGER,
            PRIMARY KEY (lemma, surface, idx)
        ) WITHOUT ROWID;
        CREATE TABLE candidates (
            ord INTEGER, title TEXT, idx INTEGER, pos INTEGER, entry BLOB
        );
        CREATE TABLE inverse (
            ord INTEGER, source TEXT, pos INTEGER, type INTEGER, target TEXT
        );
        """
    )


def _pass1(paths: list[Path], db: sqlite3.Connection) -> None:
    inverse = config().inverse
    rows: dict[str, list[tuple[Any, ...]]] = defaultdict(list)
    for order, (title, word) in enumerate(_records(paths)):
        rows["pages"].append((title, order))
        for idx, entry in enumerate(word.entries):
            candidate = is_candidate(entry)
            rows["entries"].append((title, idx, entry.pos, int(candidate)))
            if candidate:
                blob = entry.SerializeToString(deterministic=True)
                rows["candidates"].append((order, title, idx, entry.pos, blob))
                continue
            for surface in sorted({f.form for f in entry.forms}):
                rows["surfaces"].append((title, surface, idx))
            for r in entry.relations:
                if r.type in inverse:
                    rows["inverse"].append((order, title, entry.pos, r.type, r.term))
        if len(rows["surfaces"]) > _BATCH * 10 or len(rows["pages"]) > _BATCH:
            _flush(db, rows)
    _flush(db, rows)
    db.commit()


def _flush(db: sqlite3.Connection, rows: dict[str, list[tuple[Any, ...]]]) -> None:
    for table, values in rows.items():
        if values:
            marks = ", ".join("?" * len(values[0]))
            db.executemany(f"INSERT INTO {table} VALUES ({marks})", values)
    rows.clear()


# -- decisions ------------------------------------------------------------------------


def _decide(db: sqlite3.Connection, stats: Counter[str]) -> Plan:
    plan = Plan(titles=frozenset(t for (t,) in db.execute("SELECT title FROM pages")))
    for title, idx, pos, blob in db.execute(
        "SELECT title, idx, pos, entry FROM candidates ORDER BY ord, idx"
    ).fetchall():
        entry = pb.Entry.FromString(blob)
        folds, reason = _resolve(db, plan.titles, title, pos, entry)
        if reason is not None:
            why, lemma = reason
            stats[f"finalize.unfoldable.{why}"] += 1
            plan.unresolved.append(
                {
                    "title": title,
                    "entry": idx,
                    "pos": pb.Pos.Name(pos),
                    "lemma": lemma,
                    "reason": why,
                }
            )
            continue
        plan.folded[(title, idx)] = folds
        common = None
        if len(entry.senses) == 1 and len(entry.senses[0].form_of.tag_sets) == 1:
            common = entry.senses[0].form_of.tag_sets[0]
        for i, f in enumerate(folds):
            first = i == 0
            plan.transfers[(f.lemma, f.entry)].append(
                Transfer(
                    title,
                    [f],
                    list(entry.tables) if first else [],
                    list(entry.forms) if first else [],
                    common,
                )
            )
    for _order, source, pos, kind, target in db.execute(
        "SELECT ord, source, pos, type, target FROM inverse ORDER BY ord, rowid"
    ):
        if target in plan.titles and target != source:
            plan.inverse[target].append((pos, config().inverse[kind], source))
        else:
            stats["finalize.inverse.target_missing"] += 1
    return plan


def _resolve(
    db: sqlite3.Connection,
    titles: frozenset[str],
    title: str,
    pos: int,
    entry: pb.Entry,
) -> tuple[list[Fold], tuple[str, str] | None]:
    folds: list[Fold] = []
    for sense in entry.senses:
        lemma = sense.form_of.lemma
        if lemma == title:
            return [], ("self", lemma)
        if lemma not in titles:
            return [], ("lemma_missing", lemma)
        lemmas = [
            LemmaEntry(i, p, bool(has))
            for i, p, has in db.execute(
                "SELECT e.idx, e.pos, EXISTS (SELECT 1 FROM surfaces s"
                " WHERE s.lemma = e.title AND s.surface = ? AND s.idx = e.idx)"
                " FROM entries e WHERE e.title = ? AND e.candidate = 0 ORDER BY e.idx",
                (title, lemma),
            )
        ]
        if not lemmas:
            return [], ("lemma_not_a_lemma", lemma)  # its own entries are all forms
        target = choose_entry(pos, lemmas)
        if target is None:
            return [], ("form_missing", lemma)  # DNA -> kwas dezoksyrybonukleinowy
        folds.append(
            Fold(
                lemma,
                target,
                list(sense.form_of.tag_sets),
                list(sense.form_of.raw_tags),
                [*sense.labels, *sense.regions],
            )
        )
    return folds, None


# -- pass 2 ---------------------------------------------------------------------------


def _pass2(paths: list[Path], plan: Plan, out_dir: Path, stats: Counter[str]) -> int:
    words = 0
    with ShardWriter(out_dir) as writer:
        for title, word in _records(paths):
            kept = [
                (idx, e)
                for idx, e in enumerate(word.entries)
                if (title, idx) not in plan.folded
            ]
            stats["finalize.entries.folded"] += len(word.entries) - len(kept)
            if not kept:
                stats["finalize.pages.folded_away"] += 1
                continue
            out = pb.Word()
            out.CopyFrom(word)
            del out.entries[:]
            out.entries.extend(e for _, e in kept)
            for new, (old, _) in enumerate(kept):
                _apply_transfers(
                    out.entries[new], plan.transfers.get((title, old), []), stats
                )
            _apply_inverse(out, plan.inverse.get(title, []), stats)
            renumber_etymologies(out)
            _count_links(out, plan.titles, stats)
            writer.write(out)
            _coverage(out, stats)
            words += 1
    return words


def _apply_transfers(
    entry: pb.Entry, transfers: list[Transfer], stats: Counter[str]
) -> None:
    for t in transfers:
        for f in t.folds:
            if f.labels:
                if carry_labels(entry, t.surface, f):
                    stats["finalize.labels.carried"] += 1
                else:
                    stats["finalize.labels.unmatched"] += 1
        if t.tables:
            stats["finalize.tables.transferred"] += len(t.tables)
            stats["finalize.forms.transferred"] += transfer_tables(entry, t)


def _apply_inverse(
    word: pb.Word, inverse: list[tuple[int, int, str]], stats: Counter[str]
) -> None:
    for pos, kind, source in inverse:
        target = next((e for e in word.entries if e.pos == pos), None)
        if target is None:
            stats["finalize.inverse.no_entry"] += 1
        elif add_inverse(target, kind, source):
            stats["finalize.inverse.added"] += 1
        else:
            stats["finalize.inverse.already_stated"] += 1


def _count_links(word: pb.Word, titles: frozenset[str], stats: Counter[str]) -> None:
    """Targets outside the corpus: counted, never removed (an app may show them)."""
    for entry in word.entries:
        for sense in entry.senses:
            if sense.HasField("form_of"):
                kind = pb.FormOf.Type.Name(sense.form_of.type)
                stats[f"finalize.form_of.{kind}"] += 1
                if sense.form_of.lemma not in titles:
                    stats[f"finalize.form_of.{kind}.target_missing"] += 1
        for r in entry.relations:
            if r.term not in titles:
                stats["finalize.relation.target_missing"] += 1
        stats["finalize.relations"] += len(entry.relations)


def _coverage(word: pb.Word, stats: Counter[str]) -> None:
    """R8.4: lemma entries with senses and with tables, pages with pronunciation."""
    stats["finalize.words"] += 1
    stats["finalize.words.with_pronunciation"] += any(
        e.pronunciations for e in word.entries
    )
    for entry in word.entries:
        stats["finalize.entries"] += 1
        stats["finalize.forms"] += len(entry.forms)
        if any(s.HasField("form_of") for s in entry.senses):
            continue  # an unfoldable form or an alternative spelling, not a lemma
        pos = pb.Pos.Name(entry.pos)
        stats["coverage.lemma_entries"] += 1
        stats["coverage.lemma_entries.with_sense"] += bool(entry.senses)
        if entry.pos in config().coverage_tables:
            stats[f"coverage.{pos}"] += 1
            stats[f"coverage.{pos}.with_table"] += bool(entry.tables)
            if not entry.tables and _no_table_expected(entry):
                stats[f"table.not_expected.{pos}"] += 1


def _no_table_expected(entry: pb.Entry) -> bool:
    """An indeclinable noun, or a phrase whose table is another lemma's (R8.4)."""
    return (entry.HasField("noun") and entry.noun.indeclinable) or any(
        r.type == pb.Relation.TYPE_INFLECTED_LIKE for r in entry.relations
    )


def _write_stats(in_dir: Path, out_dir: Path, stats: Counter[str]) -> None:
    p3_path = in_dir / "stats.json"
    summary: dict[str, Any] = (
        json.loads(p3_path.read_text("utf-8")) if p3_path.exists() else {"counts": {}}
    )
    counts = Counter(summary.get("counts", {}))
    counts.update(stats)
    summary["counts"] = dict(sorted(counts.items()))
    summary["coverage"] = _percentages(counts)
    (out_dir / "stats.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _percentages(counts: Counter[str]) -> dict[str, float]:
    """R8.4's ratios, rounded so the file stays stable across platforms."""
    out: dict[str, float] = {}

    def ratio(name: str, part: str, whole: str) -> None:
        if counts[whole]:
            out[name] = round(100 * counts[part] / counts[whole], 2)

    ratio(
        "lemma_entries_with_sense",
        "coverage.lemma_entries.with_sense",
        "coverage.lemma_entries",
    )
    for pos in config().coverage_tables:
        name = pb.Pos.Name(pos)
        tables, every = (
            counts[f"coverage.{name}.with_table"],
            counts[f"coverage.{name}"],
        )
        # The target is of the entries that can have a table; the other, of all.
        if tableable := every - counts[f"table.not_expected.{name}"]:
            out[f"{name}_with_table"] = round(100 * tables / tableable, 2)
        if every:
            out[f"{name}_with_table_of_all"] = round(100 * tables / every, 2)
    ratio(
        "words_with_pronunciation",
        "finalize.words.with_pronunciation",
        "finalize.words",
    )
    folded = counts["finalize.entries.folded"]
    unfoldable = sum(
        v for k, v in counts.items() if k.startswith("finalize.unfoldable.")
    )
    if folded + unfoldable:
        out["form_entries_folded"] = round(100 * folded / (folded + unfoldable), 2)
    return out


def _jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
