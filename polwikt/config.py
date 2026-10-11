"""Loads and validates `polwikt.toml` (R10.5); malformed config fails loudly."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

CONFIG_NAME = "polwikt.toml"
_DATE_RE = re.compile(r"\d{8}")
_SHA1_RE = re.compile(r"[0-9a-f]{40}")


class ConfigError(Exception):
    """`polwikt.toml` is missing, unparsable, or has a wrong-typed or invalid value."""


@dataclass(frozen=True)
class DumpPin:
    """The pinned dump (R2.1a). Empty `date`/`sha1` means not yet pinned (pre-M2)."""

    date: str
    sha1: str
    url_base: str

    @property
    def is_pinned(self) -> bool:
        return bool(self.date and self.sha1)

    @property
    def filename(self) -> str:
        if not self.date:
            raise ConfigError("no dump is pinned: [dump].date is empty")
        return f"enwiktionary-{self.date}-pages-articles.xml.bz2"


@dataclass(frozen=True)
class Config:
    dump: DumpPin
    languages: tuple[str, ...]
    drop_labels: tuple[str, ...]
    root: Path


def find_project_root(start: Path | None = None) -> Path:
    """Walks up from `start` (default: cwd) to the directory holding polwikt.toml."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / CONFIG_NAME).is_file():
            return candidate
    raise ConfigError(f"no {CONFIG_NAME} found in {here} or any parent")


@cache
def load_config(root: Path) -> Config:
    """Parses `<root>/polwikt.toml`; every key is required and type-checked."""
    data = _load_toml(root / CONFIG_NAME)
    dump = _table(data, "dump")
    extract = _table(data, "extract")
    pin = DumpPin(
        date=_str(dump, "dump", "date"),
        sha1=_str(dump, "dump", "sha1").lower(),
        url_base=_str(dump, "dump", "url_base").rstrip("/"),
    )
    if pin.date and not _DATE_RE.fullmatch(pin.date):
        raise ConfigError(f"[dump].date must be YYYYMMDD, got {pin.date!r}")
    if pin.sha1 and not _SHA1_RE.fullmatch(pin.sha1):
        raise ConfigError(f"[dump].sha1 must be 40 hex digits, got {pin.sha1!r}")
    if bool(pin.date) != bool(pin.sha1):
        raise ConfigError("[dump].date and [dump].sha1 must be set together (R2.1a)")
    languages = _str_list(extract, "extract", "languages")
    if not languages:
        raise ConfigError("[extract].languages must name at least one language")
    return Config(
        dump=pin,
        languages=languages,
        drop_labels=_str_list(extract, "extract", "drop_labels"),
        root=root,
    )


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except FileNotFoundError as e:
        raise ConfigError(f"{path} does not exist") from e
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: {e}") from e


def _table(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    if not isinstance(value, dict):
        raise ConfigError(f"missing [{name}] table")
    return value


def _str(table: dict[str, Any], section: str, key: str) -> str:
    value = table.get(key)
    if not isinstance(value, str):
        raise ConfigError(f"[{section}].{key} must be a string, got {value!r}")
    return value


def _str_list(table: dict[str, Any], section: str, key: str) -> tuple[str, ...]:
    value = table.get(key)
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"[{section}].{key} must be a list of strings, got {value!r}")
    return tuple(value)
