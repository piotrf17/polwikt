"""The `polwikt` command (R10.3). Unimplemented passes fail loudly, never no-op."""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import NoReturn

import click
from wikitextprocessor import Wtp

from polwikt.config import Config, ConfigError, find_project_root, load_config
from polwikt.dump.fetch import FetchError, sha1_of
from polwikt.dump.fetch import fetch as fetch_dump
from polwikt.dump.scan import ScanError
from polwikt.dump.scan import scan as scan_dump
from polwikt.dump.store import read_page, unpack_store
from polwikt.expand.run import expand_text
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.p3 import P3Error, read_source, run_p3
from polwikt.extract.page import Settings, extract_page
from polwikt.finalize.release import ReleaseError
from polwikt.finalize.release import package as release_package
from polwikt.finalize.run import P4Error, run_p4
from polwikt.finalize.stats_diff import diff_files, report
from polwikt.parse.sections import language_section
from polwikt.parse.tree import format_tree
from polwikt.proto.io import CorpusError, read_corpus, to_json

log = logging.getLogger("polwikt")


def _todo(milestone: str, what: str) -> NoReturn:
    raise click.ClickException(f"{what} is not implemented yet (PLAN.md {milestone})")


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Debug logging.")
def cli(verbose: bool) -> None:
    """Extract Polish entries from an English Wiktionary dump into protobuf."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,  # wikitextprocessor calls basicConfig at import time
    )


@cli.command()
def config() -> None:
    """Print the resolved configuration from polwikt.toml."""
    cfg = _config()
    pin = cfg.dump
    click.echo(f"root:        {cfg.root}")
    click.echo(f"dump:        {pin.filename if pin.date else '(not pinned yet)'}")
    click.echo(f"dump sha1:   {pin.sha1 or '-'}")
    click.echo(f"languages:   {', '.join(cfg.languages)}")
    click.echo(f"drop_labels: {', '.join(cfg.drop_labels) or '-'}")


def _config() -> Config:
    try:
        return load_config(find_project_root())
    except ConfigError as e:
        raise click.ClickException(str(e)) from e


@cli.command()
@click.option(
    "--dest",
    type=click.Path(path_type=Path),
    help="Directory to download into [default: <root>/data].",
)
def fetch(dest: Path | None) -> None:
    """Download and sha1-verify the pinned dump (R2.1, R2.1a)."""
    cfg = _config()
    try:
        path = fetch_dump(cfg.dump, dest or cfg.root / "data")
    except FetchError as e:
        raise click.ClickException(str(e)) from e
    click.echo(path)


@cli.command()
@click.option(
    "--dump",
    "dump_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Dump file [default: the pinned one under <root>/data].",
)
@click.option(
    "--db",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Page store to build [default: <root>/data/pages.sqlite].",
)
@click.option("--no-verify", is_flag=True, help="Accept a dump that isn't the pin.")
@click.option("--force", is_flag=True, help="Rebuild even if the store is current.")
def scan(dump_path: Path | None, db: Path | None, no_verify: bool, force: bool) -> None:
    """P1: stream the dump into the page store, keeping only Polish ns-0 (R3.1-R3.5)."""
    cfg = _config()
    data = cfg.root / "data"
    _keep_temp_files_in(data / "tmp")
    dump = dump_path or data / cfg.dump.filename
    if not dump.exists():
        raise click.ClickException(f"{dump} does not exist; run `polwikt fetch`")
    log.info("hashing %s", dump)
    sha1 = sha1_of(dump)
    if sha1 != cfg.dump.sha1:
        if not no_verify:
            raise click.ClickException(
                f"{dump}: sha1 {sha1} is not the pinned {cfg.dump.sha1} (R2.1); "
                "pass --no-verify to scan it anyway"
            )
        log.warning("%s is not the pinned dump; the store is marked unpinned", dump)
    try:
        result = scan_dump(
            cfg, dump, db or data / "pages.sqlite", dump_sha1=sha1, force=force
        )
    except ScanError as e:
        raise click.ClickException(str(e)) from e
    click.echo(result.db)


def _keep_temp_files_in(tmp: Path) -> None:
    """SQLite and lbzcat spill to $TMPDIR, which defaults to the 6 GB root fs (§9)."""
    tmp.mkdir(parents=True, exist_ok=True)
    for var in ("TMPDIR", "SQLITE_TMPDIR"):
        os.environ.setdefault(var, str(tmp))
    tempfile.tempdir = None  # re-read TMPDIR


@cli.command()
def subset() -> None:
    """P2: template/module closure. Deferred (REQUIREMENTS §3, decision 6)."""
    _todo("deferred P2", "subset")


@cli.command()
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Page store [default: <root>/data/pages.sqlite].",
)
@click.option(
    "--out",
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory [default: <root>/data/out].",
)
@click.option("--jobs", type=click.IntRange(min=1), default=2, show_default=True)
@click.option("--limit", type=click.IntRange(min=1), help="First N pages by page id.")
@click.option("--pages", help="Comma-separated titles.")
@click.option(
    "--max-error-rate", type=float, default=0.01, show_default=True, help="R3.12"
)
def extract(
    db: Path | None,
    out: Path | None,
    jobs: int,
    limit: int | None,
    pages: str | None,
    max_error_rate: float,
) -> None:
    """P3: expand and extract each Polish page into Word messages (R3.9-R3.12)."""
    cfg = _config()
    data = cfg.root / "data"
    _keep_temp_files_in(data / "tmp")
    store = db or data / "pages.sqlite"
    if not store.exists():
        raise click.ClickException(f"{store} does not exist; run `polwikt scan`")
    titles = [t.strip() for t in pages.split(",") if t.strip()] if pages else None
    try:
        summary = run_p3(
            Settings.from_config(cfg),
            store,
            out or data / "out",
            jobs=jobs,
            titles=titles,
            limit=limit,
            max_error_rate=max_error_rate,
        )
    except (P3Error, CorpusError) as e:
        raise click.ClickException(str(e)) from e
    done = " (already complete)" if summary.skipped else ""
    click.echo(
        f"{summary.pages} pages, {summary.stats['entries']} entries, "
        f"{summary.errors} errors in {summary.seconds:.0f} s{done}"
    )


@cli.command()
@click.option(
    "--in",
    "in_dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="P3 output [default: <root>/data/out].",
)
@click.option(
    "--out",
    type=click.Path(file_okay=False, path_type=Path),
    help="Corpus directory [default: <root>/data/corpus].",
)
def finalize(in_dir: Path | None, out: Path | None) -> None:
    """P4: fold forms into lemmas, link, write the canonical corpus (R3.13-R3.16)."""
    cfg = _config()
    data = cfg.root / "data"
    _keep_temp_files_in(data / "tmp")
    in_dir = in_dir or data / "out"
    try:
        summary = run_p4(
            in_dir,
            out or data / "corpus",
            source=read_source(in_dir),
            drop_labels=list(cfg.drop_labels),
        )
    except (P3Error, P4Error, CorpusError) as e:
        raise click.ClickException(str(e)) from e
    if summary.skipped:
        click.echo("already complete")
        return
    click.echo(
        f"{summary.words} words, {summary.folded} entries folded, "
        f"{summary.unresolved} unresolved, in {summary.seconds:.0f} s"
    )


@cli.command()
@click.option(
    "--corpus",
    type=click.Path(file_okay=False, path_type=Path),
    help="Finished corpus [default: <root>/data/corpus].",
)
@click.option(
    "--out",
    type=click.Path(file_okay=False, path_type=Path),
    help="Where the tar goes [default: <root>/data/release].",
)
def package(corpus: Path | None, out: Path | None) -> None:
    """Pack a finished corpus into polwikt-<dump>-schema<N>.tar (R7.9)."""
    cfg = _config()
    data = cfg.root / "data"
    try:
        release = release_package(
            corpus or data / "corpus",
            cfg.root / "proto" / "polwikt.proto",
            out or data / "release",
        )
    except (ReleaseError, CorpusError) as e:
        raise click.ClickException(str(e)) from e
    click.echo(f"{release.path}\nsha256 {release.sha256}")


@cli.command()
@click.argument("title")
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Page store [default: <root>/data/pages.sqlite].",
)
@click.option(
    "--golden", is_flag=True, help="Read the page from tests/golden/ (no dump needed)."
)
@click.option("--full", is_flag=True, help="Show every language, not just Polish.")
def inspect(title: str, db: Path | None, golden: bool, full: bool) -> None:
    """Show one entry: raw wikitext, node tree, and extracted proto (R8.5)."""
    cfg = _config()
    language = cfg.languages[0]
    if golden:
        path = (
            cfg.root / "tests" / "golden" / "pages" / f"{title.replace(' ', '_')}.wiki"
        )
        if not path.exists():
            raise click.ClickException(f"{title!r} is not a golden fixture ({path})")
        text, origin = path.read_text(encoding="utf-8"), str(path)
        store: Path | None = None
    else:
        store = db or cfg.root / "data" / "pages.sqlite"
        if not store.exists():
            raise click.ClickException(f"{store} does not exist; run `polwikt scan`")
        page = read_page(store, title)
        if page is None:
            raise click.ClickException(f"{title!r} is not a {language} page in {store}")
        text = page.body
        origin = f"{store}, page {page.page_id}, revision {page.revision_id}"

    section = text if full else language_section(text, language)
    if section is None:
        raise click.ClickException(f"{title!r} has no =={language}== section")
    click.echo(f"=== {title}  ({origin})")
    click.echo(f"--- raw wikitext{'' if full else f' ({language} section)'} ---")
    click.echo(section.rstrip("\n"))
    with ExitStack() as stack:
        snapshot = cfg.root / "tests" / "golden" / "store.sqlite.zst"
        if store is None and snapshot.exists():  # --golden: expand from the snapshot
            tmp = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            store = unpack_store(snapshot, tmp)
        wtp: Wtp = PolwiktWtp(store) if store is not None else Wtp(quiet=True)
        stack.callback(wtp.close_db_conn)
        wtp.start_page(title)
        # The unexpanded tree is what R4.2.1 retains: template calls as nodes.
        click.echo("--- node tree (unexpanded) ---")
        click.echo(format_tree(wtp.parse(section)))
        click.echo("--- expanded wikitext ---")
        if isinstance(wtp, PolwiktWtp):
            result = expand_text(wtp, section)
            click.echo(result.text.rstrip("\n"))
            for error in result.errors:
                click.echo(f"!! {error}")
            if wtp.stats:
                click.echo(f"(counted: {dict(sorted(wtp.stats.items()))})")
        else:
            click.echo("(no golden snapshot: run tools/golden.py snapshot)")
        click.echo("--- proto ---")
        try:
            if not isinstance(wtp, PolwiktWtp):
                raise NotImplementedError(
                    "extraction needs a page store or the snapshot"
                )
            word = extract_page(wtp, title, text, Settings.from_config(cfg))
        except NotImplementedError as e:
            click.echo(f"({e})")
        else:
            click.echo(to_json(word, indent=1) if word is not None else "(no record)")


@cli.command()
@click.argument(
    "corpus", required=False, type=click.Path(file_okay=False, path_type=Path)
)
@click.option("--lemma", "lemmas", multiple=True, help="Only these words (repeatable).")
def jsonl(corpus: Path | None, lemmas: tuple[str, ...]) -> None:
    """Print a corpus as JSON Lines, one Word per line [default: <root>/data/corpus]
    (R7.5)."""
    corpus = corpus or _config().root / "data" / "corpus"
    try:
        for word in read_corpus(corpus):
            if not lemmas or word.lemma in lemmas:
                click.echo(to_json(word))
    except CorpusError as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="stats-diff")
@click.argument("old", type=click.Path(path_type=Path))
@click.argument("new", type=click.Path(path_type=Path))
def stats_diff(old: Path, new: Path) -> None:
    """Direction-aware regression check between two stats.json files (R8.3).

    Exits 1 when a coverage counter drops, or a failure counter rises, by more than
    the threshold in data/stats.toml.
    """
    changes = diff_files(old, new)
    click.echo(report(changes))
    if any(c.regression for c in changes):
        sys.exit(1)


@cli.command()
@click.option("--jobs", type=click.IntRange(min=1), default=2, show_default=True)
@click.pass_context
def run(ctx: click.Context, jobs: int) -> None:
    """Run every pass in order: fetch, scan, extract, finalize (R9.4: each one skips
    work already done, and an interrupted extract resumes)."""
    ctx.invoke(fetch)
    ctx.invoke(scan)
    ctx.invoke(extract, jobs=jobs)
    ctx.invoke(finalize)
    ctx.invoke(package)
