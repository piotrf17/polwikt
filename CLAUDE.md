# CLAUDE.md — working rules for polwikt

Pipeline that extracts Polish lexical data from the **English** Wiktionary dump into
protobuf, **for applications** — a dictionary app, a flashcard generator — not as a
mirror of Wiktionary (decision 11). Full spec: **`REQUIREMENTS.md`** — read it before changing pipeline behaviour;
requirement IDs (`R3.2`, `R6.6a`, …) are stable, cite them in comments and commit
messages when code implements or changes one.

---

## Dev setup

Toolchain is **`uv` + `make`** (and `gcc` from `build-essential`, so a dependency
without a prebuilt wheel compiles instead of failing). uv installs the pinned Python from
`.python-version` (3.13) itself — the system `python3` (3.14) is not used, and there is no
`pip`.

```bash
make sync          # .venv from uv.lock, incl. the dev dependency group
make check         # ruff lint + format check, mypy --strict, pytest — what CI runs
make fmt           # apply ruff fixes + formatting
make help          # everything else
uv run polwikt --help
```

Every target is `uv run --locked …`, so `make` and CI run identical commands.

- **Upstream is git-pinned, not PyPI.** `wikitextprocessor` (runtime) and `wiktextract`
  (dev group, oracle only) are installed from GitHub at exact commit SHAs. Their PyPI
  releases are years stale — the published `wikitextprocessor` has the old pickle
  `cache_file` API and imports the removed `pkg_resources` — while this project is built
  on the SQLite `Wtp(db_path=...)` design that exists only on git main. Upgrading means
  bumping **both** SHAs together, `make lock`, and `make check`: they break in lockstep,
  and `tests/test_upstream.py` smoke-tests the API we rely on.
- **No system `protoc`.** From M1, codegen goes through `grpcio-tools` (locked in
  `uv.lock`) via `make proto`; generated `*_pb2.py` / `*_pb2.pyi` are committed, and CI
  fails if regenerating them changes the tree.
- `uv.lock` is committed; CI runs `uv sync --locked` and fails if it drifts.
- Dumps and pipeline outputs are large: keep them **out of the repo** (`data/`, gitignored).
  Scratch files go in the session scratchpad dir, not `/tmp`, not the project.

### Running the pipeline

```bash
export TMPDIR=$PWD/data/tmp SQLITE_TMPDIR=$PWD/data/tmp   # `/` has only ~6 GB free
polwikt fetch                      # the pinned dump -> data/, sha1-verified
polwikt scan                       # -> data/pages.sqlite (~12 min; skipped when current)
polwikt extract  --db data/pages.sqlite --out data/out/ --jobs 2
polwikt finalize --in data/out/ --out data/corpus/   # shards + meta + stats
polwikt stats-diff old/stats.json new/stats.json   # R8.3; exit 1 on a regression
polwikt inspect <title>            # one entry, expanded wikitext + node tree + proto
polwikt extract --pages kot,mamy,zamek   # the fast debug loop; seconds, not minutes
```

`scan` is the slow pass (~12 min) and runs once per dump; **never re-run it to test an
extraction change** — iterate on `pages.sqlite` with `--pages` / `--limit`. There is no
`subset` pass: P2 is deferred (REQUIREMENTS §3, decision 6) and its command is a stub.

This box is 2 cores / 5 GB RAM: `--jobs 2` is the ceiling and each worker must stay
under 1.5 GB RSS (R9.3).

The dump is **pinned** (`polwikt.toml`: `[dump].date`, `[dump].sha1`, R2.1a). Don't fetch
`latest`; moving the pin is its own commit with the `stats.json` diff reviewed in it, and
it regenerates the golden store snapshot.

**Wiktionary names come from the pinned dump, not memory.** Several template and module
names in the first draft of the spec (`{{pl-p}}`, `{{pl-IPA}}`, `Module:pl-verb`) didn't
exist. Before writing code against a template, check it in `pages.sqlite` (or the
golden store).

---

## Invariants — don't break these without changing `REQUIREMENTS.md` first

1. **ns-0 is filtered at scan time** (R3.2). Only pages with a `==Polish==` L2 heading are
   stored — plus, from a second pass, the pages their `{{transclude}}` calls pull a
   definition from (R3.2b), which are expansion inputs and never extracted. Never assume an arbitrary ns-0 page's text is available — links out of Polish
   entries are stored as **titles** and must not be dereferenced. Existence checks use the
   title-only `all_titles` table (R3.2a).
2. **Never drop data silently.** Anything the output schema has a place for but we
   failed to fill — unhandled template, unresolved form-of, label-filtered sense, Lua
   failure — is **counted in `stats.json`** and logged
   (`unhandled.jsonl`, `unresolved_forms.jsonl`, `errors.jsonl`). A silent `continue` or a
   bare `except: pass` is a bug, not a shortcut.
3. **Determinism** (G5). Same dump + same code ⇒ byte-identical output. No wall-clock, no
   randomness, no dict-iteration-order dependence, no network at runtime — and upstream
   *does* reach the network (live Wikidata queries from `mw.wikibase`), so those entry
   points stay stubbed and counted (R4.5). Output order is by page id regardless of
   `--jobs` (R3.11).
4. **Lossy is worse than untyped.** When a grammatical feature or template arg doesn't
   map to a known enum, put the literal string in `raw_tags` / `raw_*` — never discard
   it. Usage labels never need this: they are strings in `labels` to begin with.
5. **The output is for apps, not a Wiktionary mirror** (G1, decision 11). Before adding
   an output field, name the app feature that reads it — poldict (`~/projects/poldict`)
   is the reference consumer (decision 12). Template calls, markup, page ids,
   maintenance categories and reference lists stay out; a schema test enforces it.
   English link targets in glosses are *in*, as search `keywords` (R6.14).
6. **Raw template calls are retained inside the pipeline** (R4.2.1) — in P3's
   intermediate records and `polwikt inspect` — as the escape hatch when parsing is
   wrong. Not in the output corpus.
7. **The corpus holds lemmas, not inflected forms.** Inflected-form entries fold into the
   lemma at P4 and emit no record (R3.13a) — when that is safe: the lemma exists and its
   forms contain the string. An entry that can't fold is emitted with `form_of` senses,
   never just dropped. Folding is **per POS entry, not per page** — `bez` and `mieć`
   are simultaneously lemmas and forms; `mamy` is two forms and folds into two lemmas.
   Only *inflectional* form-of folds: participles, `{{syn of}}` and `{{alt form}}`
   entries stay records.
8. **Middle Polish is dropped at extraction** (R6.6a) via the config `drop_labels`, with
   the sense → entry → page cascade and per-label counts — and not just senses: `mp=`
   pronunciations, qualified alternative forms and `{{pl-mid-decl-noun}}` tables go
   too, each counted by kind. Old Polish never
   enters (R3.2).
9. **One page's failure must not kill a run** (R3.12). Catch per page, log with title +
   traceback, continue; `--max-error-rate` aborts the run.

---

## Code conventions

- **Python 3.13** (pinned in `.python-version`, managed by uv), fully type-annotated. `mypy --strict` on `polwikt/` must be clean.
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
    finalize/    P4: folding, cross-page relations, corpus, stats-diff
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
  tense, mood, aspect, degree) are **enums**, with unmapped values in `raw_tags`. Open
  vocabularies — usage labels, dialects, topics — are plain strings (`labels`), never an
  enum we would have to keep in sync with Wiktionary.
- Forms are a **flat tagged list**, never a fixed 7×2 table message (R7.8) — Polish
  paradigms are too irregular for a fixed shape.
- `proto/polwikt.proto` is the contract; `REQUIREMENTS.md` §7 only describes its shape
  and rationale. Schema gaps found by the spec review are part of PLAN.md M1.

---

## Testing

- **Tests must not require a dump.** Everything runs off the golden corpus: raw wikitext
  fixtures taken from the pinned dump + expected output, plus a committed store snapshot
  of exactly the templates/modules those fixtures touch, all in `tests/golden/`
  (R8.1, R8.1a). The snapshot is regenerated by tool, never hand-edited.
- Adding support for a template or section? **Add the fixture first**, then the code:
  list it in `tests/golden/pages.toml`, `make golden-pull`, then bless with
  `pytest tests/test_golden.py --update-golden` and review the diff
  (`tests/golden/README.md`).
- The golden set must keep covering the negative cases: `dobry` (Middle Polish in every
  R6.6a position, dropped), an all-Middle-Polish page (no record), lemma-and-form pages
  `bez`/`mieć` (lemma half only), `mamy` (no record, two lemmas), a multi-etymology page
  (`zamek`), defective/pluralia-tantum nouns, irregular verbs (`być`, `iść`, `jeść`,
  `chcieć`).
- `stats.json` is the primary quality signal (R8.4). Compare it across runs; a >1% drop in
  a coverage count or a >1% rise in a failure count is a regression, not noise (R8.3).
- **Never report coverage numbers you didn't measure.** Run the pipeline, read
  `stats.json`, quote it. If a change is untested against real data, say so.

---

## Licensing

Wiktionary content is **CC BY-SA 4.0** (R11). Generated corpora carry the license notice
and attribution to English Wiktionary in the `Corpus` metadata message and a
`LICENSE-DATA` file. Pipeline code is MIT; ideas from wiktextract/wikitextprocessor are
fine to follow, but **check the license before copying their code** rather than concepts.
