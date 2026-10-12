"""M4 exit: Polish templates expand from the golden snapshot, hermetically (R4.5)."""

from __future__ import annotations

import re
import socket
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from polwikt.expand.policy import canonical_name, load_policy
from polwikt.expand.run import expand_node, expand_text
from polwikt.expand.wtp import PolwiktWtp
from polwikt.parse.sections import language_section
from polwikt.parse.tree import iter_templates, template_name
from tests.golden_harness import Fixture, fixtures

FIXTURES = fixtures()
IDS = [f.slug for f in FIXTURES]

# PLAN.md M4 exit: these must expand without a single Lua error on every fixture.
MUST_EXPAND = re.compile(
    r"pl-decl-noun.*|pl-adecl|pl-conj-a[ip].*|pl-noun|pl-verb|pl-adj|pl-pr"
)

# Forms that only a working Lua module produces, one per template family.
SPOT_CHECKS = {
    ("kot", "pl-decl-noun-m-anml"): ["kotów", "kotami", "kocie"],
    ("kot", "pl-pr"): ["kɔt"],
    ("kot", "pl-noun"): ["kocica", "kotek"],
    ("dobry", "pl-adecl"): ["dobrego", "dobrymi", "dobrzy"],
    ("być", "pl-verb"): ["impf", "bywać"],
    ("czytać", "pl-conj-ai-am,asz"): ["czytam", "czytasz", "czytający"],
    ("zniknąć", "pl-conj-ap"): ["zniknę", "zniknąwszy"],
    ("ręka", "pl-decl-noun-f"): ["rękami"],
    ("drzwi", "pl-decl-noun-f"): ["drzwiami"],
}


@pytest.fixture(scope="module")
def wtp(golden_store: Path) -> Iterator[PolwiktWtp]:
    w = PolwiktWtp(golden_store)
    yield w
    w.close_db_conn()


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    attempts: list[Any] = []

    def connect(self: socket.socket, address: Any) -> None:
        attempts.append(address)
        raise OSError("network disabled in tests (R4.5)")

    monkeypatch.setattr(socket.socket, "connect", connect)
    yield
    assert attempts == [], "expansion reached for the network (R4.5)"


def _templates(wtp: PolwiktWtp, fixture: Fixture) -> list[tuple[str, Any]]:
    section = language_section(fixture.wikitext(), "Polish") or ""
    wtp.start_page(fixture.title)
    return [
        (canonical_name(wtp, template_name(node)), node)
        for node in iter_templates(wtp.parse(section))
    ]


@pytest.mark.parametrize("fixture", FIXTURES, ids=IDS)
def test_polish_templates_expand(wtp: PolwiktWtp, fixture: Fixture) -> None:
    for name, node in _templates(wtp, fixture):
        if not MUST_EXPAND.fullmatch(name):
            continue
        result = expand_node(wtp, node)
        assert result.ok, (name, result.errors)
        assert result.text.strip(), name
        for form in SPOT_CHECKS.get((fixture.title, name), []):
            assert form in result.text, (name, form)
    assert not wtp.stale_lookups, "snapshot is stale: run tools/golden.py snapshot"


def test_spot_checks_name_real_calls(wtp: PolwiktWtp) -> None:
    by_title = {f.title: f for f in FIXTURES}
    for title, name in SPOT_CHECKS:
        assert name in {n for n, _ in _templates(wtp, by_title[title])}, (title, name)


@pytest.mark.parametrize("fixture", FIXTURES, ids=IDS)
def test_whole_section_expands_inside_the_snapshot(
    wtp: PolwiktWtp, fixture: Fixture
) -> None:
    section = language_section(fixture.wikitext(), "Polish") or ""
    wtp.start_page(fixture.title)
    expand_text(wtp, section)  # errors here are page content (desctree etc.), not ours
    assert not wtp.stale_lookups, "snapshot is stale: run tools/golden.py snapshot"


def test_every_golden_template_has_a_policy(wtp: PolwiktWtp) -> None:  # R4.2, R4.6
    policy = load_policy()
    missing = {
        (name, fixture.title)
        for fixture in FIXTURES
        for name, _ in _templates(wtp, fixture)
        if policy.action(name) is None
    }
    assert not missing, sorted(missing)


def test_output_does_not_depend_on_the_previous_page(golden_store: Path) -> None:
    # Module:headword/page once cached the title across pages (G5, R3.11).
    def expand(order: list[tuple[str, str]]) -> str:
        w = PolwiktWtp(golden_store)
        try:
            out = ""
            for title, call in order:
                w.start_page(title)
                out = w.expand(call)
            return out
        finally:
            w.close_db_conn()

    alone = expand([("być", "{{pl-verb|impf}}")])
    after = expand([("kot", "{{pl-noun|m-anml}}"), ("być", "{{pl-verb|impf}}")])
    assert alone == after
    assert "|KOT]]" not in after
