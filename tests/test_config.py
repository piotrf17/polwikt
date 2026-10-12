"""polwikt.toml loading: the shipped file is valid, malformed files fail loudly."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from polwikt.config import (
    CONFIG_NAME,
    ConfigError,
    find_project_root,
    load_config,
)

REPO = Path(__file__).resolve().parent.parent

VALID = """
[dump]
date = "20261001"
sha1 = "F9ED426C69C6B21D026613BD0F200C2AAA1145E9"
url_base = "https://dumps.wikimedia.org/enwiktionary/"

[scan]
namespaces = [10, 828]

[extract]
languages = ["Polish"]
drop_labels = ["Middle Polish"]
"""


def _write(tmp_path: Path, text: str) -> Path:
    (tmp_path / CONFIG_NAME).write_text(text, encoding="utf-8")
    return tmp_path


def test_shipped_config_loads() -> None:
    cfg = load_config(REPO)
    assert cfg.languages == ("Polish",)
    assert cfg.drop_labels == ("Middle Polish",)  # R6.6b default


def test_valid_config_normalises(tmp_path: Path) -> None:
    cfg = load_config(_write(tmp_path, VALID))
    assert cfg.dump.is_pinned
    assert cfg.dump.sha1 == "f9ed426c69c6b21d026613bd0f200c2aaa1145e9"
    assert cfg.dump.url_base == "https://dumps.wikimedia.org/enwiktionary"
    assert cfg.dump.filename == "enwiktionary-20261001-pages-articles.xml.bz2"


def test_unpinned_dump_has_no_filename(tmp_path: Path) -> None:
    text = VALID.replace('"20261001"', '""').replace(
        '"F9ED426C69C6B21D026613BD0F200C2AAA1145E9"', '""'
    )
    cfg = load_config(_write(tmp_path, text))
    assert not cfg.dump.is_pinned
    with pytest.raises(ConfigError, match="no dump is pinned"):
        _ = cfg.dump.filename


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ('"20261001"', '"2026-10-01"', "YYYYMMDD"),
        ('"20261001"', "20261001", "must be a string"),
        ('"F9ED426C69C6B21D026613BD0F200C2AAA1145E9"', '"abc"', "40 hex"),
        ('"F9ED426C69C6B21D026613BD0F200C2AAA1145E9"', '""', "set together"),
        ('["Polish"]', "[]", "at least one language"),
        ('["Middle Polish"]', '"Middle Polish"', "list of strings"),
        ("[extract]", "[extraction]", r"missing \[extract\]"),
        ("[10, 828]", "[0, 10]", "must not list 0"),
        ("[10, 828]", '["10"]', "list of integers"),
        ("[dump]\n", "[dump\n", re.escape(CONFIG_NAME)),
    ],
)
def test_malformed_config_raises(
    tmp_path: Path, old: str, new: str, message: str
) -> None:
    assert old in VALID
    with pytest.raises(ConfigError, match=message):
        load_config(_write(tmp_path, VALID.replace(old, new, 1)))


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="does not exist"):
        load_config(tmp_path)


def test_find_project_root_walks_up(tmp_path: Path) -> None:
    _write(tmp_path, VALID)
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find_project_root(nested) == tmp_path.resolve()


def test_find_project_root_fails_without_config(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"no polwikt\.toml"):
        find_project_root(tmp_path)
