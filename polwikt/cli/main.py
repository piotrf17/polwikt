"""`polwikt` command line.

The command surface is fixed by R10.3; each pass is implemented by its own milestone.
Stubs raise `NotImplementedError` naming the milestone rather than silently doing
nothing, so a half-wired pipeline can never be mistaken for a working one.
"""

from __future__ import annotations

import logging
from pathlib import Path

import click

from polwikt import __version__
from polwikt.config import ConfigError, load_config

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s %(message)s"


def _todo(milestone: str, what: str) -> None:
    raise NotImplementedError(f"{what} is implemented in milestone {milestone}")


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__)
@click.option("-v", "--verbose", is_flag=True, help="Debug-level logging.")
def main(verbose: bool) -> None:
    """Extract Polish lexical data from the English Wiktionary dump."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO, format=LOG_FORMAT
    )


@main.command()
def fetch() -> None:
    """Download and sha1-verify the pinned dump (R2.1, R2.1a)."""
    _todo("M2", "dump fetching")


@main.command()
@click.option("--dump", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--db", type=click.Path(path_type=Path), required=True)
def scan(dump: Path, db: Path) -> None:
    """P1: stream the dump into a page store, keeping Polish ns-0 pages only.

    R3.1-R3.5. The hour-long pass; runs once per dump. Iterate on `subset` instead.
    """
    _todo("M2", "the P1 dump scan")


@main.command()
@click.option("--db", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--out", type=click.Path(path_type=Path), required=True)
def subset(db: Path, out: Path) -> None:
    """P2: transitive template/module closure into a Polish-only subset (R3.6-R3.8)."""
    _todo("M4", "the P2 template closure")


@main.command()
@click.option("--db", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--out", type=click.Path(path_type=Path), required=True)
@click.option("--jobs", type=int, default=0, help="Worker processes (0 = CPU count).")
@click.option("--limit", type=int, default=0, help="Stop after N pages (0 = all).")
@click.option(
    "--pages", default="", help="Comma-separated titles; the fast debug loop."
)
@click.option("--max-error-rate", type=float, default=0.01, show_default=True)
def extract(
    db: Path, out: Path, jobs: int, limit: int, pages: str, max_error_rate: float
) -> None:
    """P3: expand, parse and extract entries into protobuf shards (R3.9-R3.12)."""
    _todo("M5", "the P3 extractor")


@main.command()
@click.option(
    "--in", "in_dir", type=click.Path(exists=True, path_type=Path), required=True
)
@click.option("--out", type=click.Path(path_type=Path), required=True)
def finalize(in_dir: Path, out: Path) -> None:
    """P4: fold forms into lemmas, link, and write the corpus (R3.13-R3.16)."""
    _todo("M11", "the P4 finalize pass")


@main.command()
@click.argument("title")
def inspect(title: str) -> None:
    """Print one entry's expanded wikitext, node tree and proto (R8.5)."""
    _todo("M3", "entry inspection")


@main.command(name="run")
@click.option("--dump", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--out", type=click.Path(path_type=Path), required=True)
def run_all(dump: Path, out: Path) -> None:
    """Run every pass end to end."""
    _todo("M12", "the end-to-end run")


@main.command()
def config() -> None:
    """Show the resolved configuration and whether a dump is pinned."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"project root : {cfg.root}")
    click.echo(f"dump         : {cfg.dump.date or '(unpinned)'}")
    click.echo(f"languages    : {', '.join(sorted(cfg.languages))}")
    click.echo(f"drop_labels  : {', '.join(sorted(cfg.drop_labels))}")
