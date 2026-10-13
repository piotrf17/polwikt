"""`polwikt stats-diff`: direction-aware regression check (R8.3)."""

from __future__ import annotations

from polwikt.finalize.stats_diff import Kind, classify, diff, report


def test_classes() -> None:
    assert classify("pages.error") is Kind.FAILURE
    assert classify("heading.unknown.Trivia") is Kind.FAILURE
    assert classify("finalize.unfoldable.lemma_missing") is Kind.FAILURE
    assert classify("senses") is Kind.COVERAGE
    assert classify("pos.NOUN") is Kind.COVERAGE
    assert classify("dropped.sense.Middle Polish") is Kind.NEUTRAL


def test_direction_and_threshold() -> None:
    old = {"counts": {"senses": 1000, "pages.error": 10, "dropped.x": 5}}
    new = {"counts": {"senses": 995, "pages.error": 12, "dropped.x": 50}}
    changes = {c.name: c for c in diff(old, new)}
    assert not changes["senses"].regression  # -0.5%: within 1%
    assert changes["pages.error"].regression  # +20%
    assert not changes["dropped.x"].regression  # neutral never fails
    worse = diff(old, {"counts": {"senses": 900, "pages.error": 10, "dropped.x": 5}})
    assert [c.name for c in worse if c.regression] == ["senses"]


def test_better_is_not_a_regression() -> None:
    old = {"counts": {"senses": 100, "label.unrecognized": 50}}
    new = {"counts": {"senses": 200, "label.unrecognized": 10}}
    assert not any(c.regression for c in diff(old, new))


def test_new_failure_counter_and_coverage_percentages() -> None:
    old = {"counts": {}, "coverage": {"POS_NOUN_with_table": 95.0}}
    new = {
        "counts": {"relation.template.unknown.foo": 1},
        "coverage": {"POS_NOUN_with_table": 90.0},
    }
    names = [c.name for c in diff(old, new) if c.regression]
    assert names == ["coverage%.POS_NOUN_with_table", "relation.template.unknown.foo"]
    assert "2 regression(s)" in report(diff(old, new))
    assert report([]) == "no counter moved"
