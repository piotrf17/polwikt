# CLAUDE.md — working rules for polwikt

Pipeline that extracts Polish lexical data from the **English** Wiktionary dump into
protobuf. Full spec: **`REQUIREMENTS.md`** — read it before changing pipeline behaviour;
requirement IDs (`R3.2`, `R6.6a`, …) are stable, cite them in comments and commit
messages when code implements or changes one.

---

## Dev setup

Not a git repo yet — `git init` first if you're about to commit.

```bash
python3 -m venv .venv && . .venv/bin/activate      # Python ≥ 3.11 (3.13 local)
pip install -e '.[dev]'                            # deps pinned in pyproject.toml
make proto                                         # regenerate polwikt/proto/*_pb2.py
pytest                                             # must pass without a dump present
```

- **No system `protoc` required.** Protobuf codegen goes through `grpcio-tools`
  (`python -m grpc_tools.protoc`), driven by `make proto`.
- **Generated `*_pb2.py` / `*_pb2.pyi` are committed**, so consumers need no toolchain.
  CI re-runs `make proto` and fails if the tree is dirty — regenerate and commit whenever
  you touch `proto/polwikt.proto`.
- Pinned deps: `wikitextprocessor`, `lupa`, `protobuf`, `zstandard`, `click`, plus dev
  `pytest`, `mypy`, `ruff`. `wiktextract` is **dev-only** — it is the cross-check oracle
  (§12.1), never imported by pipeline code.
- Dumps and pipeline outputs are large: keep them **out of the repo** (`data/`, gitignored).
  Scratch files go in the session scratchpad dir, not `/tmp`, not the project.

### Running the pipeline

```bash
polwikt scan     --dump data/enwiktionary-<pinned>.xml.bz2 --db data/pages.sqlite
polwikt subset   --db data/pages.sqlite --out data/subset.sqlite
polwikt extract  --db data/subset.sqlite --out data/out/ --jobs 8
polwikt finalize --in data/out/ --out data/polwikt.pb.zst
polwikt inspect <title>            # one entry, expanded wikitext + node tree + proto
polwikt extract --pages kot,mamy,zamek   # the fast debug loop; seconds, not minutes
```

`scan` is the hour-long pass and runs once per dump; **never re-run it to test an
extraction change** — iterate on `subset.sqlite` with `--pages` / `--limit`.

The dump is **pinned** (`polwikt.toml`: `dump_date`, `dump_sha1`, R2.1a). Don't fetch
`latest`; moving the pin is its own commit with the `stats.json` diff reviewed in it.

---

## Invariants — don't break these without changing `REQUIREMENTS.md` first

1. **ns-0 is filtered at scan time** (R3.2). Only pages with a `==Polish==` L2 heading are
   stored. Never assume an arbitrary ns-0 page's text is available — links out of Polish
   entries are stored as **titles** and must not be dereferenced. Existence checks use the
   title-only `all_titles` table (R3.2a).
2. **Never drop data silently.** Anything discarded — unhandled template, unresolved
   form-of, label-filtered sense, Lua failure — is **counted in `stats.json`** and logged
   (`unhandled.jsonl`, `unresolved_forms.jsonl`, `errors.jsonl`). A silent `continue` or a
   bare `except: pass` is a bug, not a shortcut.
3. **Determinism** (G5). Same dump + same code ⇒ byte-identical output. No wall-clock, no
   randomness, no dict-iteration-order dependence, no network at runtime. Output order is
   by page id regardless of `--jobs` (R3.11).
4. **Lossy is worse than untyped.** When a label, tag or template arg doesn't map to a
   known enum, put the literal string in `raw_tags` / `raw_*` — never discard it.
5. **Raw template calls are retained** for headword, inflection and etymology templates
   (R4.2.1). They are the escape hatch when our parsing is wrong; don't "clean them up".
6. **Codepoint offsets, never byte offsets** (R7.6a). Polish text is non-ASCII;
   `LinkSpan.start/end` index Python `str`.
7. **The corpus holds lemmas only.** Inflected-form entries fold into the lemma at P4 and
   emit no record (R3.13a). Folding is **per POS entry, not per page** — `mamy` and `piec`
   are simultaneously lemmas and forms.
8. **Middle Polish is dropped at extraction** (R6.6a) via the config `drop_labels`, with
   the sense → entry → page cascade and per-label counts. Old Polish never enters (R3.2).
9. **One page's failure must not kill a run** (R3.12). Catch per page, log with title +
   traceback, continue; `--max-error-rate` aborts the run.

---

## Code conventions

- **Python ≥ 3.11**, fully type-annotated. `mypy --strict` on `polwikt/` must be clean.
- **`ruff check` + `ruff format`** (defaults). No hand-formatting; don't fight the tool.
- **Config, not constants.** POS heading maps, label→tag maps, section names, template
  policy, `drop_labels`, the dump pin live in data files (R10.5). If you're about to add a
  Python `dict` of Wiktionary strings, it belongs in `polwikt/data/*.toml` instead.
- **Layout** (R10.4) — Polish knowledge stays under `extract/`; the layers below it are
  language-agnostic:
  ```
  polwikt/
    dump/        XML streaming, page store, P1 filter
    subset/      template/module closure (P2)
    expand/      wikitextprocessor wiring, expansion policy
    parse/       WikiNode tree helpers, section walking
    extract/     noun, verb, adj, sense, etymology, pronunciation  ← Polish-specific
    proto/       polwikt.proto + generated modules + read/write helpers
    data/        config tables
    cli/
  ```
- Prefer **pure functions over classes** for extraction: `wikitext → message`. They are
  trivially testable against fixtures; stateful extractors are not.
- Workers are **stateless** apart from a read-only store handle (R3.10). Don't add
  cross-page mutable state in P3 — cross-page work belongs in P4.
- Docstrings: one line saying what it extracts and from which section/template. Cite the
  requirement ID for non-obvious rules. Don't comment the obvious.
- Log with the stdlib `logging` module, structured fields, never `print`.

### Protobuf rules

- **Never renumber or reuse a field number.** Removing a field means `reserved N;` +
  `reserved "name";`. Additive changes only.
- proto3. Message and enum names `CamelCase`, fields `snake_case`, enum values
  `UPPER_SNAKE` with a `_UNSPECIFIED = 0` zero value.
- Grammatical categories that are genuinely closed (case, number, gender, animacy, person,
  tense, mood, aspect, degree) are **enums**; everything else is a string in `raw_tags`.
- Forms are a **flat tagged list**, never a fixed 7×2 table message (R7.8) — Polish
  paradigms are too irregular for a fixed shape.
- The schema in `REQUIREMENTS.md` §7 is a **sketch**, not the contract;
  `proto/polwikt.proto` is the contract.

---

## Testing

- **Tests must not require a dump.** Everything runs off the golden corpus: raw wikitext
  fixtures + expected output, checked into `tests/golden/` (R8.1).
- Adding support for a template or section? **Add the fixture first**, then the code.
- The golden set must keep covering the negative cases: a page with Middle Polish senses
  (dropped), an all-Middle-Polish page (no record), a lemma-and-form page (lemma half
  only), a multi-etymology page (`zamek`), defective/pluralia-tantum nouns, irregular
  verbs (`być`, `iść`, `jeść`, `chcieć`).
- `stats.json` is the primary quality signal (R8.4). Compare it across runs; a >1% drop in
  any count is a regression, not noise.
- **Never report coverage numbers you didn't measure.** Run the pipeline, read
  `stats.json`, quote it. If a change is untested against real data, say so.

---

## Licensing

Wiktionary content is **CC BY-SA 4.0** (R11). Generated corpora carry the license notice
and attribution to English Wiktionary in the `Corpus` metadata message and a
`LICENSE-DATA` file. Pipeline code is MIT; ideas from wiktextract/wikitextprocessor are
fine to follow, but **check the license before copying their code** rather than concepts.
