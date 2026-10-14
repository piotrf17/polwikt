"""The CLI exposes the R10.3 surface; unimplemented passes fail loudly (exit != 0)."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from click.testing import CliRunner

from polwikt.cli.main import cli

REPO = Path(__file__).resolve().parent.parent

SUBPACKAGES = [
    "cli",
    "dump",
    "subset",
    "expand",
    "parse",
    "extract",
    "finalize",
    "proto",
]
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
    "package",
}
IMPLEMENTED = {
    "config",
    "fetch",
    "scan",
    "inspect",
    "extract",
    "finalize",
    "stats-diff",
    "run",
    "package",
}
STUB_INVOCATIONS = [
    ["subset"],
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


def test_inspect_reads_the_page_store(golden_store: Path) -> None:
    result = CliRunner().invoke(cli, ["inspect", "kot", "--db", str(golden_store)])
    assert result.exit_code == 0, result.output
    assert "page 50282, revision 92535143" in result.output
    assert "TEMPLATE pl-decl-noun-m-anml" in result.output
    missing = CliRunner().invoke(cli, ["inspect", "cat", "--db", str(golden_store)])
    assert missing.exit_code != 0
    assert "not a Polish page" in missing.output


@pytest.mark.parametrize("jobs", ["1", "2"])
def test_extract_writes_shards_and_reports(
    tmp_path: Path, golden_store: Path, jobs: str
) -> None:
    out = tmp_path / "out"
    argv = ["extract", "--db", str(golden_store), "--out", str(out), "--jobs", jobs]
    argv += ["--pages", "kot,mamy,kradźba"]
    result = CliRunner().invoke(cli, argv)
    assert result.exit_code == 0, result.output
    assert "3 pages, 3 entries, 0 errors" in result.output  # kradźba: no record (R6.6a)
    assert sorted(p.name for p in out.iterdir()) == [
        "dropped_colabelled.jsonl",
        "errors.jsonl",
        "p3-00000-of-00001.pb.zst",
        "p3.checkpoint.json",
        "source.json",
        "stats.json",
        "title_only.jsonl",
        "unhandled.jsonl",
    ]
    shard = (out / "p3-00000-of-00001.pb.zst").read_bytes()
    again = CliRunner().invoke(cli, argv)  # the same run, complete: skipped (R9.4)
    assert again.exit_code == 0, again.output
    assert "already complete" in again.output
    assert (out / "p3-00000-of-00001.pb.zst").read_bytes() == shard
    other = CliRunner().invoke(cli, [*argv[:-1], "kot"])  # another run: refused
    assert other.exit_code != 0
    assert "holds another P3 run" in other.output
    corpus, release = tmp_path / "corpus", tmp_path / "release"
    done = CliRunner().invoke(cli, ["finalize", "--in", str(out), "--out", str(corpus)])
    assert done.exit_code == 0, done.output
    packed = CliRunner().invoke(
        cli, ["package", "--corpus", str(corpus), "--out", str(release)]
    )
    assert packed.exit_code == 0, packed.output
    assert (release / "polwikt-20261001-schema1.tar").exists()  # R7.9
