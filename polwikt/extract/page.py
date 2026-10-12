"""P3 for one page: raw wikitext to a `Word`, or None when nothing survives (R3.9)."""

from __future__ import annotations

from wikitextprocessor import Wtp

from polwikt.proto import polwikt_pb2 as pb


def extract_page(wtp: Wtp, title: str, wikitext: str) -> pb.Word | None:
    """Expands, parses and walks the Polish section of `title` into one Word."""
    raise NotImplementedError("page extraction is not implemented yet (PLAN.md M5)")
