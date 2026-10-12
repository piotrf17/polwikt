"""The CLI exposes the R10.3 surface; unimplemented passes fail loudly (exit != 0)."""

from __future__ import annotations

import bz2
import importlib
from pathlib import Path

import pytest
from click.testing import CliRunner

from polwikt.cli.main import cli
from polwikt.config import load_config
from polwikt.dump.scan import scan
from tests.test_scan import dump_xml

REPO = Path(__file__).resolve().parent.parent

SUBPACKAGES = ["cli", "dump", "subset", "expand", "parse", "extract", "proto"]
COMMANDS = {
    "config",
    "fetch",
    "scan",
    "subset",
    "extract",
    "finalize",
    "inspect",
    "stats-diff",
    "run",
}
IMPLEMENTED = {"config", "fetch", "scan", "inspect", "extract"}
STUB_INVOCATIONS = [
    ["subset"],
    ["finalize"],
    ["stats-diff", "a.json", "b.json"],
    ["run"],
]


@pytest.mark.parametrize("name", SUBPACKAGES)
def test_subpackage_imports_and_is_documented(name: str) -> None:
    assert importlib.import_module(f"polwikt.{name}").__doc__  # R10.4 layout


def test_cli_exposes_every_documented_command() -> None:
    assert set(cli.commands) == COMMANDS


def test_stubs_cover_every_pass() -> None:
    assert {argv[0] for argv in STUB_INVOCATIONS} == COMMANDS - IMPLEMENTED


@pytest.mark.parametrize("argv", STUB_INVOCATIONS)
def test_unimplemented_pass_fails_loudly(argv: list[str]) -> None:
    result = CliRunner().invoke(cli, argv)
    assert result.exit_code != 0
    assert "not implemented yet" in result.output
    assert "PLAN.md" in result.output


def test_config_command_prints_resolved_config() -> None:
    result = CliRunner().invoke(cli, ["config"])
    assert result.exit_code == 0, result.output
    assert "languages:   Polish" in result.output
    assert "drop_labels: Middle Polish" in result.output


def test_inspect_golden_shows_wikitext_and_tree() -> None:  # R8.5
    result = CliRunner().invoke(cli, ["inspect", "--golden", "mamy"])
    assert result.exit_code == 0, result.output
    assert "{{inflection of|pl|mama||gen|s|;|nom//acc//voc|p}}" in result.output
    assert "LEVEL2 Polish" in result.output
    assert "TEMPLATE inflection of | pl | mieć" in result.output
    assert "--- expanded wikitext ---" in result.output  # from the golden snapshot
    assert 'class="headword-line"' in result.output
    assert '"lemma": "mamy"' in result.output  # the extracted Word


def test_inspect_unknown_title_fails() -> None:
    result = CliRunner().invoke(cli, ["inspect", "--golden", "nie ma takiego"])
    assert result.exit_code != 0
    assert "not a golden fixture" in result.output


def test_inspect_reads_the_page_store(tmp_path: Path) -> None:
    dump = tmp_path / "dump.xml.bz2"
    dump.write_bytes(bz2.compress(dump_xml()))
    db = tmp_path / "pages.sqlite"
    scan(load_config(REPO), dump, db, dump_sha1="0" * 40)
    result = CliRunner().invoke(cli, ["inspect", "kot", "--db", str(db)])
    assert result.exit_code == 0, result.output
    assert "page 1, revision 100" in result.output
    assert "TEMPLATE greet | kocie" in result.output
    missing = CliRunner().invoke(cli, ["inspect", "cat", "--db", str(db)])
    assert missing.exit_code != 0
    assert "not a Polish page" in missing.output


@pytest.mark.parametrize("jobs", ["1", "2"])
def test_extract_writes_shards_and_reports(tmp_path: Path, jobs: str) -> None:
    dump = tmp_path / "dump.xml.bz2"
    dump.write_bytes(bz2.compress(dump_xml()))
    db = tmp_path / "pages.sqlite"
    scan(load_config(REPO), dump, db, dump_sha1="0" * 40)
    out = tmp_path / "out"
    argv = ["extract", "--db", str(db), "--out", str(out), "--jobs", jobs]
    result = CliRunner().invoke(cli, argv)
    assert result.exit_code == 0, result.output
    assert "2 pages, 2 entries, 0 errors" in result.output  # kot, pies (R3.9)
    assert sorted(p.name for p in out.iterdir()) == [
        "errors.jsonl",
        "p3-00000-of-00001.pb.zst",
        "stats.json",
        "title_only.jsonl",
        "unhandled.jsonl",
    ]
    again = CliRunner().invoke(cli, argv)  # never overwrites a finished run
    assert again.exit_code != 0
    assert "already holds shards" in again.output
