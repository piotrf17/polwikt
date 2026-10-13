"""CI's regression gate: the golden run's stats.json (R8.3).

Every golden page's extraction counters are summed and compared with the committed
tests/golden/stats.json by `stats-diff`'s rules: a coverage counter falling, or a
failure counter rising, by more than the threshold fails with the report. Any other
movement fails too until it is blessed with --update-golden, so the committed file
always describes the code next to it.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from polwikt.config import load_config
from polwikt.expand.wtp import PolwiktWtp
from polwikt.extract.page import Settings, extract_record
from polwikt.finalize.stats_diff import diff, report
from tests.golden_harness import GOLDEN, fixtures

STATS = GOLDEN / "stats.json"
SETTINGS = Settings.from_config(load_config(GOLDEN.parent.parent))


def golden_stats(store: Path) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    unhandled: Counter[str] = Counter()
    wtp = PolwiktWtp(store)
    try:
        for fixture in fixtures():
            before = Counter(wtp.stats)
            result = extract_record(wtp, fixture.title, fixture.wikitext(), SETTINGS)
            counts.update(result.stats)
            counts.update(Counter(wtp.stats) - before)
            unhandled.update(result.unhandled)
    finally:
        wtp.close_db_conn()
    return {
        "counts": dict(sorted(counts.items())),
        "unhandled_templates": len(unhandled),
        "unhandled_uses": sum(unhandled.values()),
    }


def test_golden_stats_do_not_regress(golden_store: Path, update_golden: bool) -> None:
    current = golden_stats(golden_store)
    if update_golden or not STATS.exists():
        STATS.write_text(
            json.dumps(current, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return
    changes = diff(json.loads(STATS.read_text("utf-8")), current)
    regressions = [c for c in changes if c.regression]
    assert not regressions, "golden stats regressed (R8.3):\n" + report(regressions)
    assert not changes, (
        "golden stats moved; review and bless with --update-golden:\n" + report(changes)
    )
