"""The golden corpus (R8.1): fixtures are intact, extraction matches expectations."""

from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path

import pytest
from google.protobuf import json_format
from wikitextprocessor import Wtp

from polwikt.config import load_config
from polwikt.extract.page import extract_page
from polwikt.parse.sections import language_section
from polwikt.proto import polwikt_pb2 as pb
from polwikt.proto.io import to_json
from tests.golden_harness import (
    GOLDEN,
    TODO,
    Fixture,
    fixtures,
    manifest,
)

REPO = GOLDEN.parent.parent
FIXTURES = fixtures()
IDS = [f.slug for f in FIXTURES]

# CLAUDE.md "Testing": the negative and edge cases the set must never lose.
REQUIRED = {
    "dobry",
    "kradźba",
    "barzo",
    "bez",
    "mieć",
    "mamy",
    "kotów",
    "zamek",
    "drzwi",
    "być",
    "iść",
    "jeść",
    "chcieć",
    "DNA",
    "ketchup",
    "zniknąć",
    "pies",
}


def test_manifest_matches_the_list() -> None:
    with (GOLDEN / "pages.toml").open("rb") as f:
        listed = [p["title"] for p in tomllib.load(f)["page"]]
    assert [f.title for f in FIXTURES] == listed, "run `make golden-pull`"
    for sub, suffix in (("pages", ".wiki"), ("expected", ".json")):
        on_disk = {p.name for p in (GOLDEN / sub).glob(f"*{suffix}")}
        assert on_disk == {f"{f.slug}{suffix}" for f in FIXTURES}, sub


def test_fixtures_come_from_the_pinned_dump() -> None:  # R8.1
    assert manifest()["dump"]["sha1"] == load_config(REPO).dump.sha1


def test_required_cases_are_present() -> None:
    assert {f.title for f in FIXTURES} >= REQUIRED


@pytest.mark.parametrize("fixture", FIXTURES, ids=IDS)
def test_fixture_is_intact(fixture: Fixture) -> None:
    text = fixture.wikitext()
    assert hashlib.sha1(text.encode()).hexdigest() == fixture.sha1, "edited by hand?"
    assert language_section(text, "Polish") is not None


@pytest.mark.parametrize("fixture", FIXTURES, ids=IDS)
def test_expectation_is_well_formed(fixture: Fixture) -> None:
    expected = fixture.expected()
    if expected == TODO or expected is None:
        return
    word = json_format.ParseDict(expected, pb.Word())
    assert word.lemma == fixture.title


@pytest.mark.parametrize("fixture", FIXTURES, ids=IDS)
def test_extraction_matches_golden(
    fixture: Fixture, golden_store: Path, update_golden: bool
) -> None:
    if fixture.expected() == TODO and not update_golden:
        pytest.skip("expectation is TODO; bless it with --update-golden")
    wtp = Wtp(db_path=golden_store, quiet=True)
    try:
        word = extract_page(wtp, fixture.title, fixture.wikitext())
    finally:
        wtp.close_db_conn()
    actual = (to_json(word, indent=1) if word is not None else "null") + "\n"
    if update_golden:
        fixture.expected_path.write_text(actual, encoding="utf-8")
        return
    assert actual == fixture.expected_path.read_text(encoding="utf-8")
