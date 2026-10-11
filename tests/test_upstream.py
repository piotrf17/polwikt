"""Smoke-tests the git-pinned wikitextprocessor API this project is built on (R10.2).

A failure here after bumping the pin means the upstream design moved under us — read
the upstream diff before patching our side.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from wikitextprocessor import Wtp, dumpparser


def test_sqlite_page_store_api() -> None:
    assert "db_path" in inspect.signature(Wtp.__init__).parameters  # R3.1
    for name in ("start_page", "expand", "parse", "add_page", "get_page"):
        assert callable(getattr(Wtp, name)), name


def test_dump_primitives_exist() -> None:
    # M2 streams the dump through these rather than process_dump(), which has no
    # per-page content filter and drops page/revision ids (R3.1, R3.2).
    assert callable(dumpparser.decompress_dump_file)


def test_template_and_lua_expansion(tmp_path: Path) -> None:
    wtp = Wtp(db_path=tmp_path / "pages.db", quiet=True)
    try:
        wtp.add_page("Template:greet", 10, body="Witaj, {{{1|świecie}}}!")
        wtp.add_page(
            "Module:echo",
            828,
            body="local p = {}\n"
            "function p.up(frame) return mw.ustring.upper(frame.args[1]) end\n"
            "return p",
            model="Scribunto",
        )
        wtp.db_conn.commit()
        wtp.start_page("kot")
        assert wtp.expand("{{greet|kocie}}") == "Witaj, kocie!"
        assert wtp.expand("{{greet}}") == "Witaj, świecie!"
        assert wtp.expand("{{#if:x|tak|nie}}") == "tak"
        assert wtp.expand("{{#invoke:echo|up|łóżko}}") == "ŁÓŻKO"
    finally:
        wtp.close_db_conn()
