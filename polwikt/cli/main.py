"""The `polwikt` command (R10.3). Unimplemented passes fail loudly, never no-op."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import NoReturn

import click

from polwikt.config import ConfigError, find_project_root, load_config

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
    )


@cli.command()
def config() -> None:
    """Print the resolved configuration from polwikt.toml."""
    try:
        cfg = load_config(find_project_root())
    except ConfigError as e:
        raise click.ClickException(str(e)) from e
    pin = cfg.dump
    click.echo(f"root:        {cfg.root}")
    click.echo(f"dump:        {pin.filename if pin.date else '(not pinned yet)'}")
    click.echo(f"dump sha1:   {pin.sha1 or '-'}")
    click.echo(f"languages:   {', '.join(cfg.languages)}")
    click.echo(f"drop_labels: {', '.join(cfg.drop_labels) or '-'}")


@cli.command()
def fetch() -> None:
    """Download and sha1-verify the pinned dump (R2.1, R2.1a)."""
    _todo("M2", "fetch")


@cli.command()
@click.option("--dump", "dump_path", type=click.Path(path_type=Path))
@click.option("--db", type=click.Path(path_type=Path))
def scan(dump_path: Path | None, db: Path | None) -> None:
    """P1: stream the dump into the page store, keeping only Polish ns-0 (R3.1-R3.5)."""
    _todo("M2", "scan")


@cli.command()
def subset() -> None:
    """P2: template/module closure. Deferred (REQUIREMENTS §3, decision 6)."""
    _todo("deferred P2", "subset")


@cli.command()
@click.option("--db", type=click.Path(path_type=Path))
@click.option("--out", type=click.Path(path_type=Path))
@click.option("--jobs", type=int)
@click.option("--limit", type=int)
@click.option("--pages", help="Comma-separated titles.")
def extract(
    db: Path | None,
    out: Path | None,
    jobs: int | None,
    limit: int | None,
    pages: str | None,
) -> None:
    """P3: expand and extract each Polish page into Word messages (R3.9-R3.12)."""
    _todo("M5", "extract")


@cli.command()
@click.option("--in", "in_dir", type=click.Path(path_type=Path))
@click.option("--out", type=click.Path(path_type=Path))
def finalize(in_dir: Path | None, out: Path | None) -> None:
    """P4: fold forms into lemmas, link, write the canonical corpus (R3.13-R3.16)."""
    _todo("M11", "finalize")


@cli.command()
@click.argument("title")
def inspect(title: str) -> None:
    """Show one entry: raw wikitext, node tree, and extracted proto (R8.5)."""
    _todo("M3", "inspect")


@cli.command(name="stats-diff")
@click.argument("old", type=click.Path(path_type=Path))
@click.argument("new", type=click.Path(path_type=Path))
def stats_diff(old: Path, new: Path) -> None:
    """Direction-aware regression check between two stats.json files (R8.3)."""
    _todo("M11", "stats-diff")


@cli.command()
def run() -> None:
    """Run every pass in order."""
    _todo("M12", "run")
