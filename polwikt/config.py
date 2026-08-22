"""Load pipeline configuration from data files.

Wiktionary conventions (POS headings, labels, section names, template policy) and the
dump pin live in TOML, never in Python (R10.5). Everything here validates loudly: a
malformed or missing key raises rather than defaulting, so a typo in a config table
cannot quietly change what gets extracted.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"
PROJECT_CONFIG = "polwikt.toml"


class ConfigError(Exception):
    """Configuration file is missing, malformed, or has the wrong shape."""


@dataclass(frozen=True, slots=True)
class DumpPin:
    """The single dump every dev run and golden test uses (R2.1a).

    An empty `date` means the project has not pinned a dump yet; M2 fills it in on the
    first fetch. Running against an unpinned dump is allowed but is recorded in the
    output `Corpus` metadata (R7.4).
    """

    date: str
    sha1: str
    url_base: str

    @property
    def is_pinned(self) -> bool:
        return bool(self.date and self.sha1)

    @property
    def filename(self) -> str:
        if not self.date:
            raise ConfigError("no dump pinned in polwikt.toml ([dump].date is empty)")
        return f"enwiktionary-{self.date}-pages-articles.xml.bz2"


@dataclass(frozen=True, slots=True)
class Config:
    dump: DumpPin
    #: Sense labels whose senses are dropped at extraction, cascading sense -> entry ->
    #: page (R6.6a-c). Default drops Middle Polish.
    drop_labels: frozenset[str]
    #: Wiktionary L2 language headings to extract. Old Polish is deliberately absent.
    languages: frozenset[str]
    root: Path

    def data_table(self, name: str) -> Mapping[str, Any]:
        """Load a config table from `polwikt/data/<name>.toml`."""
        return _load_toml(DATA_DIR / f"{name}.toml")


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default: cwd) looking for polwikt.toml."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / PROJECT_CONFIG).is_file():
            return candidate
    raise ConfigError(f"no {PROJECT_CONFIG} found at or above {here}")


@cache
def load_config(root: Path | None = None) -> Config:
    """Load `polwikt.toml`. Cached: config is read-only for the life of a process."""
    project_root = root or find_project_root()
    raw = _load_toml(project_root / PROJECT_CONFIG)
    dump = _table(raw, "dump")
    extract = _table(raw, "extract")
    return Config(
        dump=DumpPin(
            date=_str(dump, "date", "dump"),
            sha1=_str(dump, "sha1", "dump"),
            url_base=_str(dump, "url_base", "dump"),
        ),
        drop_labels=frozenset(_str_list(extract, "drop_labels", "extract")),
        languages=frozenset(_str_list(extract, "languages", "extract")),
        root=project_root,
    )


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except FileNotFoundError as exc:
        raise ConfigError(f"missing config file: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"malformed TOML in {path}: {exc}") from exc


def _table(raw: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"{PROJECT_CONFIG}: [{key}] table is missing or not a table")
    return value


def _str(table: Mapping[str, Any], key: str, section: str) -> str:
    value = table.get(key)
    if not isinstance(value, str):
        raise ConfigError(f"{PROJECT_CONFIG}: [{section}].{key} must be a string")
    return value


def _str_list(table: Mapping[str, Any], key: str, section: str) -> tuple[str, ...]:
    value = table.get(key)
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(
            f"{PROJECT_CONFIG}: [{section}].{key} must be a list of strings"
        )
    return tuple(value)
