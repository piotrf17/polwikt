"""Interrupted P3 runs resume to byte-identical output (R9.4, G5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from polwikt.config import load_config
from polwikt.extract import p3
from polwikt.extract.p3 import CHECKPOINT, P3Error, run_p3
from polwikt.extract.page import Settings
from polwikt.proto.io import shard_paths

REPO = Path(__file__).resolve().parent.parent
SETTINGS = Settings.from_config(load_config(REPO))
PAGES = ["kot", "pies", "dom", "mamy", "bez", "mieć", "zamek", "robić", "dobry", "być"]


def _files(out: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(out.iterdir())}


def test_interrupted_run_resumes_to_the_same_bytes(
    golden_store: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(p3, "RECORDS_PER_SHARD", 3)
    whole = tmp_path / "whole"
    run_p3(SETTINGS, golden_store, whole, jobs=1, titles=PAGES)

    resumed = tmp_path / "resumed"
    real = p3._extract
    calls = {"n": 0}

    def flaky(ref: p3.PageRef) -> p3.PageOutcome:
        calls["n"] += 1
        if calls["n"] == 8:  # after two checkpoints (3 and 6 pages), mid-shard
            raise KeyboardInterrupt
        return real(ref)

    monkeypatch.setattr(p3, "_extract", flaky)
    with pytest.raises(KeyboardInterrupt):
        run_p3(SETTINGS, golden_store, resumed, jobs=1, titles=PAGES)
    parts = sorted(p.name for p in resumed.glob("p3-*.part"))
    assert parts == ["p3-00000.pb.zst.part", "p3-00001.pb.zst.part"]  # kept

    seen: list[str] = []

    def recording(ref: p3.PageRef) -> p3.PageOutcome:
        seen.append(ref.title)
        return real(ref)

    monkeypatch.setattr(p3, "_extract", recording)
    run_p3(SETTINGS, golden_store, resumed, jobs=1, titles=PAGES)
    assert seen == _in_order(golden_store)[6:]  # only the unfinished pages
    assert _files(resumed) == _files(whole)
    assert len(shard_paths(resumed, "p3")) == 4


def _in_order(store: Path) -> list[str]:
    return [r.title for r in p3.polish_pages(store, PAGES, None)]


def test_complete_run_is_skipped_and_other_runs_refused(
    golden_store: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    run_p3(SETTINGS, golden_store, out, jobs=1, titles=PAGES[:2])
    assert (out / CHECKPOINT).exists()
    assert run_p3(SETTINGS, golden_store, out, jobs=1, titles=PAGES[:2]).skipped
    with pytest.raises(P3Error, match="another P3 run"):
        run_p3(SETTINGS, golden_store, out, jobs=1, titles=PAGES[:3])


def test_output_does_not_depend_on_jobs(golden_store: Path, tmp_path: Path) -> None:
    """R3.11: records are written in page-id order however the pages were scheduled."""
    one, two = tmp_path / "one", tmp_path / "two"
    run_p3(SETTINGS, golden_store, one, jobs=1, titles=PAGES)
    run_p3(SETTINGS, golden_store, two, jobs=2, titles=PAGES)
    assert _files(one) == _files(two)
