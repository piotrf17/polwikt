"""Config loading: the pipeline's scope knobs must be data, and must fail loudly."""

from __future__ import annotations

from pathlib import Path

import pytest

from polwikt.config import Config, ConfigError, find_project_root, load_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def cfg() -> Config:
    return load_config(PROJECT_ROOT)


def test_finds_project_root_from_a_subdirectory() -> None:
    assert find_project_root(Path(__file__).parent) == PROJECT_ROOT


def test_project_config_loads(cfg: Config) -> None:
    assert cfg.root == PROJECT_ROOT


def test_polish_is_in_scope_and_old_polish_is_not(cfg: Config) -> None:
    """Old Polish is a separate L2 section, deliberately out of scope (§12.5)."""
    assert "Polish" in cfg.languages
    assert "Old Polish" not in cfg.languages


def test_middle_polish_is_dropped_at_extraction(cfg: Config) -> None:
    """R6.6a: dropped by label, since it is not a separate section."""
    assert "Middle Polish" in cfg.drop_labels


def test_dump_is_not_pinned_yet(cfg: Config) -> None:
    """M2 sets the pin; until then `is_pinned` must be honest about it (R2.1a)."""
    assert not cfg.dump.is_pinned
    with pytest.raises(ConfigError, match="no dump pinned"):
        _ = cfg.dump.filename


def test_missing_config_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"no polwikt\.toml found"):
        find_project_root(tmp_path)


def test_malformed_config_raises(tmp_path: Path) -> None:
    (tmp_path / "polwikt.toml").write_text(
        '[dump]\ndate = 20260801\nsha1 = ""\nurl_base = ""\n'  # date unquoted
        '[extract]\nlanguages = ["Polish"]\ndrop_labels = []\n'
    )
    with pytest.raises(ConfigError, match=r"\[dump\].date must be a string"):
        load_config(tmp_path)


def test_missing_section_raises(tmp_path: Path) -> None:
    (tmp_path / "polwikt.toml").write_text(
        '[dump]\ndate = ""\nsha1 = ""\nurl_base = ""\n'
    )
    with pytest.raises(ConfigError, match=r"\[extract\] table is missing"):
        load_config(tmp_path)


def test_data_tables_are_readable(cfg: Config) -> None:
    """Stubs for now; each is filled in by the milestone that needs it (R10.5)."""
    for name in ("pos_headings", "sections", "labels", "templates"):
        assert isinstance(cfg.data_table(name), dict)
