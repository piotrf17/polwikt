"""The R10.4 package layout imports, and the R10.3 CLI surface is wired."""

from __future__ import annotations

import importlib

import pytest
from click.testing import CliRunner

from polwikt.cli import main

SUBPACKAGES = ["dump", "subset", "expand", "parse", "extract", "proto", "cli"]
COMMANDS = {
    "fetch",
    "scan",
    "subset",
    "extract",
    "finalize",
    "inspect",
    "run",
    "config",
}


@pytest.mark.parametrize("name", SUBPACKAGES)
def test_subpackage_imports(name: str) -> None:
    assert importlib.import_module(f"polwikt.{name}").__doc__


def test_cli_exposes_every_documented_command() -> None:
    assert set(main.commands) == COMMANDS


def test_cli_help_runs() -> None:
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Wiktionary" in result.output


def test_config_command_reports_scope() -> None:
    result = CliRunner().invoke(main, ["config"])
    assert result.exit_code == 0
    assert "Polish" in result.output
    assert "(unpinned)" in result.output


@pytest.mark.parametrize("command", ["fetch", "inspect"])
def test_unimplemented_commands_fail_loudly(command: str) -> None:
    """A stub must never look like a successful no-op (CLAUDE.md invariant 2)."""
    args = [command, "x"] if command == "inspect" else [command]
    result = CliRunner().invoke(main, args)
    assert result.exit_code != 0
    assert isinstance(result.exception, NotImplementedError)
    assert "milestone M" in str(result.exception)
