"""The wiktextract cross-check (decision 1, §12.1). A dev tool, not pipeline code.

    uv run python tools/oracle.py generate [--db data/pages.sqlite]
    uv run python tools/oracle.py diff [--all]

`generate` runs wiktextract's English extractor over every golden page, with the same
hermetic PolwiktWtp over the full local store (the golden snapshot holds only what
*our* expansion touches; wiktextract expands more), and writes its JSON to
data/oracle/<slug>.json. Local only: CI has no store.

`diff` compares that JSON with our P3 output for the page (tests/golden/expected),
field by field, as sets of normalised items per page: parts of speech, glosses, form
spellings, IPA, audio files, homophones, syllabifications, etymology texts and
relations. Every item found on one side only must be explained by a rule in
tests/golden/oracle_triage.toml — their flattening, a deliberate difference, or a
known bug of ours — and `diff` exits 1 while any is unexplained (M13's exit).
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import tomllib
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from tests.golden_harness import fixtures  # noqa: E402

GOLDEN = REPO / "tests" / "golden"
TRIAGE = GOLDEN / "oracle_triage.toml"
OUT = REPO / "data" / "oracle"
_SPACE = re.compile(r"\s+")
# Their rendering of a {{pl-derived verbs}} cell: "[dojść pf]".
_BRACKETED = re.compile(r"^\[(.+?)(?: (?:pf|impf|biasp))?\]$")

log = logging.getLogger("oracle")


# -- generate -------------------------------------------------------------------------


def generate(db: Path) -> None:
    from wiktextract.config import WiktionaryConfig
    from wiktextract.page import parse_page
    from wiktextract.thesaurus import init_thesaurus_db
    from wiktextract.wxr_context import WiktextractContext

    from polwikt.expand.wtp import PolwiktWtp

    OUT.mkdir(parents=True, exist_ok=True)
    wtp = PolwiktWtp(db)
    config = WiktionaryConfig(
        dump_file_lang_code="en",
        capture_language_codes=["pl"],
        capture_translations=False,
        capture_descendants=False,
    )
    config.extract_thesaurus_pages = False  # it would write a db beside the store
    wxr = WiktextractContext(wtp, config)
    # Linkages to Thesaurus: pages still query it: an empty one of our own.
    wxr.thesaurus_db_conn = init_thesaurus_db(OUT / "thesaurus.sqlite")
    for fixture in fixtures():
        data = parse_page(wxr, fixture.title, fixture.wikitext())
        path = OUT / f"{fixture.slug}.json"
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        log.info("%s: %d entries", fixture.title, len(data))


# -- normalised items -----------------------------------------------------------------


@dataclass(frozen=True)
class Item:
    field: str
    key: str
    context: str = ""  # what triage rules may also match: their tags, our type

    def text(self) -> str:
        return f"{self.key} | {self.context}" if self.context else self.key


def norm(text: str) -> str:
    """Letters and digits only, casefolded: "sługa / służący" and "sługa /służący"
    are one gloss."""
    return "".join(c for c in text.casefold() if c.isalnum())


def _context(*parts: Any) -> str:
    return ",".join(str(p) for part in parts for p in (part or []) if p)


def _walk_senses(senses: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    for s in senses:
        yield s
        yield from _walk_senses(s.get("subsenses", []))


def ours(word: dict[str, Any] | None, cfg: dict[str, Any]) -> set[Item]:
    items: set[Item] = set()
    if word is None:  # the page yields no record (all Middle Polish, R6.6a)
        return items
    for e in word.get("etymologies", []):
        if e.get("text"):
            items.add(Item("etymology", norm(e["text"])))
    rel_names = {v: k for k, v in cfg["relations"].items()}
    for entry in word.get("entries", []):
        pos = entry["pos"].removeprefix("POS_")
        items.add(Item("pos", pos))
        for s in _walk_senses(entry.get("senses", [])):
            if s.get("gloss"):
                items.add(Item("gloss", norm(s["gloss"])))
            for r in s.get("relations", []):
                kind = r["type"].removeprefix("TYPE_")
                items.add(Item("relation", f"{rel_names.get(kind, kind)}:{r['term']}"))
        for f in entry.get("forms", []):
            items.add(Item("form", f["form"]))
        for p in entry.get("pronunciations", []):
            items.add(Item("ipa", p["ipa"], ",".join(p.get("labels", []))))
        for a in entry.get("audio", []):
            items.add(Item("audio", a["file"]))
        for syl in filter(None, entry.get("syllabification", "").split(", ")):
            items.add(Item("hyphenation", syl))
        for r in entry.get("relations", []):
            kind = r["type"].removeprefix("TYPE_")
            if kind == "HOMOPHONE":
                items.add(Item("homophone", r["term"]))
            else:
                items.add(Item("relation", f"{rel_names.get(kind, kind)}:{r['term']}"))
    return items


def theirs(entries: list[dict[str, Any]], cfg: dict[str, Any]) -> set[Item]:
    items: set[Item] = set()
    skip_tags = set(cfg["form_skip_tags"])
    for e in entries:
        # An entry all of whose senses are Middle Polish: we drop it (R6.6a).
        senses = e.get("senses", [])
        mp = (
            ["middle-polish"]
            if senses
            and all({"Middle", "Polish"} <= set(s.get("tags", [])) for s in senses)
            else []
        )
        items.add(Item("pos", cfg["pos"].get(e["pos"], e["pos"]), _context(mp)))
        if e.get("etymology_text"):
            items.add(Item("etymology", norm(e["etymology_text"]), _context(mp)))
        for s in senses:
            for gloss in s.get("glosses") or []:  # a parent's gloss heads its children
                items.add(Item("gloss", norm(gloss), _context(mp, s.get("tags"))))
            items |= _relations(s, cfg, [*mp, *s.get("tags", [])])
        for f in e.get("forms", []):
            tags = f.get("tags", [])
            if skip_tags.intersection(tags) or not f.get("form"):
                continue
            if "canonical" in tags:  # the headword itself
                continue
            kind = None if "source" in f else _headword_kind(tags, cfg)
            context = _context(mp, tags, f.get("raw_tags"))
            if kind:
                items.add(Item("relation", f"{kind}:{f['form']}", context))
            else:
                items.add(Item("form", f["form"], context))
        for snd in e.get("sounds", []):
            context = _context(
                mp, snd.get("tags"), snd.get("raw_tags"), [snd.get("note")]
            )
            if snd.get("ipa"):
                items.add(Item("ipa", snd["ipa"], context))
            if snd.get("audio"):
                items.add(Item("audio", snd["audio"], context))
            if snd.get("homophone"):
                items.add(Item("homophone", snd["homophone"], context))
        for h in e.get("hyphenations", []):
            items.add(Item("hyphenation", "‧".join(h.get("parts", [])), _context(mp)))
        items |= _relations(e, cfg, mp)
    return items


def _headword_kind(tags: list[str], cfg: dict[str, Any]) -> str | None:
    """A headword-line form ("kotek", tagged diminutive) as our Relation type."""
    for pair in cfg["headword_forms"]:
        if set(pair["tags"]) <= set(tags):
            return str(pair["type"])
    return None


def _relations(data: dict[str, Any], cfg: dict[str, Any], mp: list[str]) -> set[Item]:
    out: set[Item] = set()
    for name in cfg["relations"]:
        for r in data.get(name, []):
            if word := _BRACKETED.sub(r"\1", r.get("word", "")):
                context = _context(mp, r.get("tags"), r.get("raw_tags"))
                out.add(Item("relation", f"{name}:{word}", context))
    return out


# -- diff -----------------------------------------------------------------------------


@dataclass
class Rule:
    field: str
    side: str  # "ours" | "theirs" | "both"
    match: re.Pattern[str]
    kind: str  # their-flattening | deliberate | our-bug
    why: str
    pages: frozenset[str] = frozenset()
    used: int = 0

    def explains(self, page: str, side: str, item: Item) -> bool:
        return (
            self.field in (item.field, "*")
            and self.side in (side, "both")
            and (not self.pages or page in self.pages)
            and bool(self.match.search(item.text()))
        )


def load_triage() -> tuple[dict[str, Any], list[Rule]]:
    data = tomllib.loads(TRIAGE.read_text("utf-8"))
    rules = [
        Rule(
            r["field"],
            r["side"],
            re.compile(r.get("match", "")),
            r["kind"],
            r["why"],
            frozenset(r.get("pages", [])),
        )
        for r in data.get("rule", [])
    ]
    return data["map"], rules


def _pair_etymologies(mine: set[Item], other: set[Item]) -> None:
    """Their text starts with the flattened "Etymology tree" box: one etymology when
    ours ends theirs."""
    for a in [i for i in mine if i.field == "etymology"]:
        for b in [i for i in other if i.field == "etymology"]:
            if a.key != b.key and b.key.endswith(a.key):
                other.discard(b)
                other.add(Item("etymology", a.key, b.context))


def diff(show_all: bool) -> int:
    cfg, rules = load_triage()
    unexplained: dict[str, list[tuple[str, str, Item]]] = defaultdict(list)
    totals: Counter[str] = Counter()
    for fixture in fixtures():
        path = OUT / f"{fixture.slug}.json"
        if not path.exists():
            raise SystemExit(f"{path} is missing: run `tools/oracle.py generate`")
        mine = ours(json.loads((GOLDEN / "expected" / path.name).read_text()), cfg)
        other = theirs(json.loads(path.read_text()), cfg)
        _pair_etymologies(mine, other)
        for side, only in (("ours", mine - other), ("theirs", other - mine)):
            # A key the other side has under another context is not a divergence.
            other_keys = {(i.field, i.key) for i in (other if side == "ours" else mine)}
            for item in sorted(only, key=Item.text):
                if (item.field, item.key) in other_keys:
                    continue
                totals[f"{item.field}.{side}"] += 1
                rule = next(
                    (r for r in rules if r.explains(fixture.title, side, item)), None
                )
                if rule is None:
                    unexplained[item.field].append((fixture.title, side, item))
                else:
                    rule.used += 1
                    totals[f"explained.{rule.kind}"] += 1
    for name, n in sorted(totals.items()):
        print(f"{name:32s} {n}")
    for rule in rules:
        if rule.used == 0:
            print(f"unused rule: {rule.field} {rule.side} {rule.match.pattern!r}")
    count = sum(len(v) for v in unexplained.values())
    for field, rows in sorted(unexplained.items()):
        print(f"\n== {field}: {len(rows)} unexplained")
        for page, side, item in rows if show_all else rows[:15]:
            print(f"  only {side:6s} {page}: {item.text()}")
    print(f"\n{count} unexplained")
    return 1 if count else 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--db", type=Path, default=REPO / "data" / "pages.sqlite")
    dif = sub.add_parser("diff")
    dif.add_argument("--all", action="store_true", help="list every unexplained item")
    args = parser.parse_args()
    if args.command == "generate":
        generate(args.db)
        return 0
    return diff(args.all)


if __name__ == "__main__":
    sys.exit(main())
