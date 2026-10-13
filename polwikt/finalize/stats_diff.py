"""Direction-aware regression check between two stats.json files (R8.3).

Counters are classed by `data/stats.toml`: a coverage counter falling, or a failure
counter rising, by more than the threshold is a regression; anything else that moves
is reported as a change. A counter that appears or vanishes counts as moving from or
to zero. The R8.4 percentages under `coverage` are coverage too.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from fnmatch import fnmatchcase
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any


class Kind(StrEnum):
    COVERAGE = "coverage"
    FAILURE = "failure"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class Change:
    name: str
    kind: Kind
    old: float
    new: float
    regression: bool

    @property
    def percent(self) -> float:
        if self.old == 0:
            return float("inf") if self.new else 0.0
        return 100 * (self.new - self.old) / self.old


@cache
def _config() -> dict[str, Any]:
    path = resources.files("polwikt.data").joinpath("stats.toml")
    return tomllib.loads(path.read_text("utf-8"))


def classify(name: str) -> Kind:
    cfg = _config()
    if any(fnmatchcase(name, p) for p in cfg["failure"]):
        return Kind.FAILURE
    if any(fnmatchcase(name, p) for p in cfg["coverage"]):
        return Kind.COVERAGE
    return Kind.NEUTRAL


def _flat(summary: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, value in summary.items():
        if key == "counts":
            out.update(value)
        elif key == "coverage":
            out.update({f"coverage%.{k}": v for k, v in value.items()})
        elif isinstance(value, int | float):
            out[key] = value
    return out


def diff(old: dict[str, Any], new: dict[str, Any]) -> list[Change]:
    """Every counter that moved, regressions first, then by name."""
    threshold = float(_config()["threshold"])
    a, b = _flat(old), _flat(new)
    changes: list[Change] = []
    for name in sorted(a.keys() | b.keys()):
        before, after = a.get(name, 0), b.get(name, 0)
        if before == after:
            continue
        kind = Kind.COVERAGE if name.startswith("coverage%.") else classify(name)
        moved = 100 * abs(after - before) / before if before else float("inf")
        regression = moved > threshold and (
            (kind is Kind.COVERAGE and after < before)
            or (kind is Kind.FAILURE and after > before)
        )
        changes.append(Change(name, kind, before, after, regression))
    changes.sort(key=lambda c: (not c.regression, c.name))
    return changes


def diff_files(old: Path, new: Path) -> list[Change]:
    return diff(json.loads(old.read_text("utf-8")), json.loads(new.read_text("utf-8")))


def report(changes: list[Change]) -> str:
    if not changes:
        return "no counter moved"
    lines = []
    for c in changes:
        mark = "REGRESSION" if c.regression else c.kind.value
        pct = "new" if c.old == 0 else f"{c.percent:+.2f}%"
        lines.append(f"{mark:10s} {c.name}: {c.old:g} -> {c.new:g} ({pct})")
    regressions = sum(c.regression for c in changes)
    lines.append(f"{regressions} regression(s), {len(changes)} counter(s) moved")
    return "\n".join(lines)
