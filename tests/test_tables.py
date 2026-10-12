"""The table grid (parse/tables.py): spans laid out as a browser does."""

from __future__ import annotations

from pathlib import Path

from polwikt.expand.wtp import PolwiktWtp
from polwikt.parse.tables import cell_wikitext, tables

TABLE = """<div class="NavFrame"><div class="NavHead">Declension of x</div>
<div class="NavContent">
{|
! rowspan=2 |
! colspan=2 | singular
|-
! m !! f
|-
! nom
| colspan=2 | a
|-
! gen
| b
| rowspan=2 | c
|-
! dat
| d
|}</div></div>"""


def test_spans_and_headers(golden_store: Path) -> None:
    wtp = PolwiktWtp(golden_store)
    wtp.start_page("x")
    (table,) = tables(wtp, wtp.parse(TABLE))
    assert table.title == "Declension of x"
    data = {cell_wikitext(wtp, c).strip(): c for c in table.cells if not c.header}

    def headers(text: str, position: int = 0) -> list[str]:
        row, col = data[text].positions()[position]
        found = table.row_headers(row, col) + table.col_headers(row, col)
        return [cell_wikitext(wtp, h).strip() for h in found]

    assert data["a"].positions() == [(2, 1), (2, 2)]
    assert headers("a", 1) == ["nom", "singular", "f"]
    assert headers("c", 1) == ["dat", "singular", "f"]  # rowspan reaches the next row
    assert headers("d") == ["dat", "singular", "m"]
    wtp.close_db_conn()
