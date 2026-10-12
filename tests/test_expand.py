"""The expansion layer: hermetic (R4.5), title-aware (R3.2a), policy-driven (R4.2)."""

from __future__ import annotations

import bz2
import socket
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from polwikt.config import load_config
from polwikt.dump.scan import scan
from polwikt.expand import hermetic
from polwikt.expand.policy import (
    Action,
    PolicyError,
    Unhandled,
    canonical_name,
    load_policy,
)
from polwikt.expand.run import expand_text
from polwikt.expand.wtp import PolwiktWtp
from tests.test_scan import dump_xml

REPO = Path(__file__).resolve().parent.parent

PROBE = """local p = {}
function p.clock(frame)
  return os.date("%Y-%m-%d %H:%M") .. " " .. os.time() .. " " .. os.clock()
end
function p.rand(frame) return tostring(math.random(1000000)) end
function p.exists(frame) return tostring(mw.title.new(frame.args[1]).exists) end
function p.content(frame) return mw.title.new(frame.args[1]):getContent() or "nil" end
function p.label(frame) return "[" .. (mw.wikibase.getLabel("Q36") or "nil") .. "]" end
function p.entity(frame) return tostring(mw.wikibase.getEntity("Q36")) end
return p
"""


@pytest.fixture(scope="module")
def store(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp = tmp_path_factory.mktemp("expand")
    dump = tmp / "enwiktionary-20261001-pages-articles.xml.bz2"
    dump.write_bytes(bz2.compress(dump_xml()))
    db = tmp / "pages.sqlite"
    scan(load_config(REPO), dump, db, dump_sha1="0" * 40)
    return db


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    attempts: list[Any] = []

    def connect(self: socket.socket, address: Any) -> None:
        attempts.append(address)
        raise OSError("network disabled in tests (R4.5)")

    monkeypatch.setattr(socket.socket, "connect", connect)
    return attempts


@pytest.fixture
def wtp(store: Path, no_network: list[Any]) -> Iterator[PolwiktWtp]:
    w = PolwiktWtp(store, record=True)
    w.add_page("Module:probe", 828, body=PROBE, model="Scribunto")
    w.start_page("kot")
    yield w
    w.close_db_conn()
    assert no_network == []


def test_clock_is_frozen_at_the_dump_date(wtp: PolwiktWtp) -> None:  # R4.5
    today = wtp.expand("{{CURRENTYEAR}}-{{CURRENTMONTH}}-{{CURRENTDAY2}}")
    assert today == "2026-10-01"
    assert wtp.expand("{{#invoke:probe|clock}}") == "2026-10-01 00:00 1790812800 0"


def test_lua_randomness_is_seeded(wtp: PolwiktWtp) -> None:  # G5
    first = wtp.expand("{{#invoke:probe|rand}}")
    wtp.start_page("pies")  # a new page resets the Lua environment
    assert wtp.expand("{{#invoke:probe|rand}}") == first


def test_wikidata_is_stubbed_and_counted(wtp: PolwiktWtp) -> None:  # R4.5
    assert wtp.expand("{{#invoke:probe|label}}") == "[]"  # upstream's no-data answer
    # Upstream turns a missing entity into a Lua error (entity.create(nil)): visible
    # and counted twice over, never a network call.
    assert not expand_text(wtp, "{{#invoke:probe|entity}}").ok
    assert wtp.stats["wikidata.mw_wikibase_getlabel"] == 1
    assert wtp.stats["wikidata.mw_wikibase_getEntity"] == 1
    assert wtp.expand("{{#statements:P31|from=Q36}}") == ""
    assert wtp.stats["wikidata.statement_query"] == 1


def test_a_missed_network_path_raises(wtp: PolwiktWtp) -> None:
    with pytest.raises(hermetic.NetworkAttemptError):
        wtp.wikidata_session.get("https://query.wikidata.org/sparql")  # type: ignore[union-attr]


def test_existence_comes_from_all_titles(wtp: PolwiktWtp) -> None:  # R3.2a
    # "cat" is not Polish, so P1 kept only its title; "nonesuch" is in no table.
    assert wtp.expand("{{#ifexist:cat|yes|no}}") == "yes"
    assert wtp.expand("{{#ifexist:nonesuch|yes|no}}") == "no"
    assert wtp.expand("{{#ifexist:Citations:kot|yes|no}}") == "yes"
    assert wtp.expand("{{#invoke:probe|exists|cat}}") == "true"
    assert wtp.expand("{{#invoke:probe|exists|nonesuch}}") == "false"


def test_content_of_a_title_only_page_is_nil_and_counted(wtp: PolwiktWtp) -> None:
    result = expand_text(wtp, "{{#invoke:probe|content|cat}}")
    assert result.text == "nil"  # what modules expect for a missing page (R3.2a)
    assert result.ok
    assert wtp.stats["getContent.title_only"] == 1  # but never silent
    assert wtp.title_only_reads == {"cat"}
    assert expand_text(wtp, "{{#invoke:probe|content|kot}}").text.startswith("==Polish")


def test_transcluding_a_title_only_page(wtp: PolwiktWtp) -> None:  # R3.2a
    # In a named namespace upstream renders it as a missing page: a red link.
    assert wtp.expand("{{Citations:kot}}") == "[[:Template:Citations:kot]]"
    # Namespace-less lookups reach _template_to_body with no text; upstream asserts,
    # we render it empty and count it.
    assert wtp._template_to_body("Foo:bar", None) == ""
    assert wtp.stats["transclude.title_only"] == 1


def test_recorder_lists_what_expansion_touched(wtp: PolwiktWtp) -> None:  # R3.8a
    wtp.expand("{{hello|psie}}")  # a redirect to Template:greet
    assert ("Template:hello", 10) in wtp.found_pages
    assert ("Template:greet", 10) in wtp.found_pages
    wtp.expand("{{#ifexist:cat|yes|no}}")
    assert ("cat", 0) in wtp.found_titles


def test_policy_names_and_prefixes() -> None:  # R4.2
    policy = load_policy()
    assert policy.action("pl-decl-noun-m-anml") is Action.EXPAND
    assert policy.action("label") is Action.CAPTURE
    assert policy.action("pl-noun") is Action.BOTH
    assert policy.action("R:pl:PWN") is Action.IGNORE
    assert policy.action("no such template") is None
    longest = load_policy('[render]\nprefixes = ["a"]\n[ignore]\nprefixes = ["ab"]\n')
    assert longest.action("abc") is Action.IGNORE
    assert longest.action("acc") is Action.RENDER


def test_policy_refuses_a_name_under_two_actions() -> None:
    with pytest.raises(PolicyError, match="both"):
        load_policy('[render]\nnames = ["x"]\n[ignore]\nnames = ["x"]\n')
    with pytest.raises(PolicyError, match="unknown action"):
        load_policy('[explode]\nnames = ["x"]\n')


def test_canonical_name_follows_redirects(wtp: PolwiktWtp) -> None:
    assert canonical_name(wtp, "hello") == "greet"
    assert canonical_name(wtp, "tcl") == "transclude"
    assert canonical_name(wtp, "nonesuch") == "nonesuch"


def test_unhandled_rows_keep_the_first_example() -> None:  # R4.6
    unhandled = Unhandled()
    for page in ("kot", "pies", "kot"):
        unhandled.add("odd", page)
    unhandled.add("rare", "ptak")
    assert unhandled.rows() == [
        {"template": "odd", "count": 3, "example": "kot"},
        {"template": "rare", "count": 1, "example": "ptak"},
    ]


@pytest.mark.parametrize(
    ("wikitext", "expected"),
    [
        ("{{#if: x |yes|no}}", "yes"),
        ("{{#ifeq: a | a |same|diff}}", "same"),
        ("{{#switch: b | a=1 | b=2 | #default=3}}", "2"),
        ("{{#expr: 2 * 3 + 1}}", "7"),
        ("{{PAGENAME}} {{NAMESPACE}}", "kot "),
        ("{{SUBPAGENAME}}", "kot"),
        ("a<!-- hidden -->b", "ab"),
        ("<nowiki>{{greet}}</nowiki>", "&lbrace;&lbrace;greet&rbrace;&rbrace;"),
        ("{{greet}}", "Hi {{{1}}}"),
        ("{{greet|{{{1|domyślny}}}}}", "Hi domyślny"),
        ("{{DISPLAYTITLE:kot}}", ""),
    ],
)
def test_r4_4_wikitext_features(wtp: PolwiktWtp, wikitext: str, expected: str) -> None:
    assert wtp.expand(wikitext) == expected
