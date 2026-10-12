"""The CLI exposes the R10.3 surface; unimplemented passes fail loudly (exit != 0)."""

from __future__ import annotations

import importlib

import pytest
from click.testing import CliRunner

from polwikt.cli.main import cli

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
IMPLEMENTED = {"config", "fetch", "scan"}
STUB_INVOCATIONS = [
    ["subset"],
    ["extract"],
    ["finalize"],
    ["inspect", "kot"],
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
