"""Tables in an expanded template, as a grid of header and data cells.

Rowspans and colspans are laid out the way a browser does, so a data cell knows the
headers to its left and above it. Titles come from the table caption or from the
`NavHead` of the collapsible box around it. Language-agnostic: what the headers mean
is the caller's business (extract/inflection.py).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from wikitextprocessor import NodeKind, WikiNode, Wtp

from polwikt.parse.text import plain_text

_CELLS = (NodeKind.TABLE_CELL, NodeKind.TABLE_HEADER_CELL)


@dataclass(eq=False)
class Cell:
    node: WikiNode
    header: bool
    row: int
    col: int
    rows: int = 1
    cols: int = 1

    def positions(self) -> list[tuple[int, int]]:
        return [
            (self.row + i, self.col + j)
            for i in range(self.rows)
            for j in range(self.cols)
        ]


@dataclass
class Table:
    title: str
    cells: list[Cell] = field(default_factory=list)  # source order
    grid: dict[tuple[int, int], Cell] = field(default_factory=dict)

    def row_headers(self, row: int, col: int) -> list[Cell]:
        """Header cells to the left of (row, col), outermost first."""
        return _unique(
            cell
            for c in range(col)
            if (cell := self.grid.get((row, c))) is not None and cell.header
        )

    def col_headers(self, row: int, col: int) -> list[Cell]:
        """Header cells above (row, col), outermost first."""
        return _unique(
            cell
            for r in range(row)
            if (cell := self.grid.get((r, col))) is not None and cell.header
        )


def tables(wtp: Wtp, root: WikiNode) -> list[Table]:
    """Every table under `root`, in document order, with its title."""
    found: list[Table] = []
    _walk(wtp, root, "", found)
    return found


def _walk(wtp: Wtp, node: WikiNode, title: str, found: list[Table]) -> str:
    for child in node.children:
        if not isinstance(child, WikiNode):
            continue
        if child.kind == NodeKind.HTML and "NavHead" in child.attrs.get("class", ""):
            title = plain_text(_wikitext(wtp, child))
        elif child.kind == NodeKind.TABLE:
            found.append(_grid(wtp, child, title))
            title = ""
        else:
            title = _walk(wtp, child, title, found)
    return title


def _grid(wtp: Wtp, node: WikiNode, title: str) -> Table:
    table = Table(title)
    row = 0
    for child in node.children:
        if not isinstance(child, WikiNode):
            continue
        if child.kind == NodeKind.TABLE_CAPTION:
            table.title = plain_text(_wikitext(wtp, child))
        elif child.kind == NodeKind.TABLE_ROW:
            cells = [c for c in child.children if isinstance(c, WikiNode)]
            cells = [c for c in cells if c.kind in _CELLS]
            if not cells:
                continue
            col = 0
            for cell_node in cells:
                while (row, col) in table.grid:
                    col += 1
                cell = Cell(
                    cell_node,
                    cell_node.kind == NodeKind.TABLE_HEADER_CELL,
                    row,
                    col,
                    _span(cell_node, "rowspan"),
                    _span(cell_node, "colspan"),
                )
                table.cells.append(cell)
                for position in cell.positions():
                    table.grid.setdefault(position, cell)
                col += cell.cols
            row += 1
    return table


def _span(node: WikiNode, attr: str) -> int:
    value = str(node.attrs.get(attr, "1")).strip().strip('"')
    return int(value) if value.isdigit() and 0 < int(value) < 100 else 1


def _unique(cells: Iterator[Cell]) -> list[Cell]:
    out: list[Cell] = []
    for cell in cells:
        if cell not in out:
            out.append(cell)
    return out


def cell_wikitext(wtp: Wtp, cell: Cell) -> str:
    """The cell's content as wikitext, links and inline HTML included."""
    return _wikitext(wtp, cell.node)


def _wikitext(wtp: Wtp, node: WikiNode) -> str:
    return "".join(
        c if isinstance(c, str) else wtp.node_to_wikitext(c) for c in node.children
    )
