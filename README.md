# polwikt

Extracts Polish lexical data — senses, inflection, pronunciation, etymology, relations —
from the **English** Wiktionary dump into Protocol Buffers, for applications: a
dictionary app, a flashcard generator. The reference consumer is poldict, an offline
Polish↔English dictionary.

- **`REQUIREMENTS.md`** — the spec; requirement IDs (`R3.2`, …) are cited from code.
- **`PLAN.md`** — implementation milestones M0–M14.
- **`CLAUDE.md`** — dev setup and the invariants not to break.

## What you get

One `Word` per Polish lemma page: its entries (one per part of speech and etymology),
each with senses (gloss, labels, regions, topics, English search keywords, examples,
sense-level relations), a flat tagged list of inflected forms grouped into tables,
pronunciation and audio, and typed relations (aspect partners, diminutives, synonyms,
…). Inflected-form pages (`kotów`, `mamy`) are folded into their lemmas; their
spellings are the lemma's Forms. The schema, with comments, is
[`proto/polwikt.proto`](proto/polwikt.proto).

The full run over the 2026-10-01 dump gives **109,673 words** in 25 MB:

| Coverage (`stats.json`, R8.4) | |
|---|---|
| lemma entries with a sense | 99.98% |
| verbs with a conjugation table | 94.10% of those that have one to find |
| nouns with a declension table | 93.11% of those that have one to find |
| adjectives with a declension table | 95.08% |
| words with a pronunciation | 99.5% |

## Building a corpus

Needs [`uv`](https://docs.astral.sh/uv/), `make` and a C compiler (`build-essential`);
uv installs the pinned Python itself. The dump is 1.6 GB, the page store 1.5 GB, and a
full run takes about 3 hours on 2 cores and 5 GB of RAM.

```bash
git clone <this repo> polwikt && cd polwikt
make sync                       # .venv from uv.lock
mkdir -p data/tmp && export TMPDIR=$PWD/data/tmp SQLITE_TMPDIR=$PWD/data/tmp  # off a small /
uv run polwikt run --jobs 2     # all passes, below, in order
```

`polwikt run` is these steps, each of which skips work already done (an interrupted
`extract` resumes from its last shard):

```bash
uv run polwikt fetch      # the pinned dump -> data/, sha1-verified (R2.1)
uv run polwikt scan       # P1: Polish pages + templates/modules -> data/pages.sqlite (~20 min)
uv run polwikt extract    # P3: every Polish page -> data/out/ (~3 h at --jobs 2)
uv run polwikt finalize   # P4: fold, link -> data/corpus/ (~1 min)
uv run polwikt package    # data/corpus -> data/release/polwikt-20261001-schema1.tar
```

The dump is **pinned** in `polwikt.toml` (date and sha1), so the same commit always
builds the same corpus, byte for byte. Other useful commands:

```bash
uv run polwikt extract --pages kot,mamy --out data/try   # a few pages, in seconds
uv run polwikt inspect kot             # one page: wikitext, node tree, extracted proto
uv run polwikt jsonl --lemma kot       # a finished corpus's Words as JSON Lines
uv run polwikt stats-diff old/stats.json new/stats.json   # exit 1 on a regression
```

## The release file

`polwikt-<dump date>-schema<N>.tar` (a corpus from any other dump than the pin is named
`…-unpinned`), with its `.sha256` beside it, holds:

| File | |
|---|---|
| `words-NNNNN-of-MMMMM.pb.zst` | the `Word` records, in page order |
| `corpus.meta.pb` | a `Corpus` message: schema version, dump date and sha1, pipeline version, word count, what was excluded (`drop_labels`), license |
| `polwikt.proto` | the schema that reads them |
| `stats.json` | the run's counters and coverage |
| `LICENSE-DATA` | CC BY-SA 4.0 and the attribution to English Wiktionary |

Each shard is zstd, and the decompressed stream is `Word` messages each prefixed by its
length as a varint. The corpus ships no lookup index: an app builds the one it needs.
[`examples/lookup.py`](examples/lookup.py) reads the shards with only `zstandard` and
`protobuf` and builds a spelling → entry index from the lemmas and their Forms:

```console
$ uv run python examples/lookup.py data/corpus kotów mamy
kotów: genitive plural of kot (noun)
mamy: nominative plural of mama (noun)
mamy: genitive singular of mama (noun)
…
mamy: plural first person present of mieć (verb)
```

Outside this repository, generate the Python module from the release's schema with
`protoc --python_out=. polwikt.proto` (or `python -m grpc_tools.protoc`) and import
`polwikt_pb2` instead of `polwikt.proto.polwikt_pb2`.

## Development

```bash
make check    # ruff lint + format check, mypy --strict, pytest — what CI runs
make help     # every target
```

Tests never need a dump: they run off the golden corpus in `tests/golden/`, 120 pages
with their expected output and a snapshot of exactly the templates and modules their
expansion touches (see [`tests/golden/README.md`](tests/golden/README.md)). An
extraction change is checked against the full run with `polwikt stats-diff`.

### Moving the dump pin

Wikimedia publishes the English Wiktionary dump on the 1st of each month and keeps
about ten months of them, so the pin has to move before it expires (R2.1a). Moving it
is a commit of its own, with no code change in it, so that every count that moves is
Wiktionary's doing:

1. Pick the newest complete dump at <https://dumps.wikimedia.org/enwiktionary/> and
   take the sha1 of `enwiktionary-<date>-pages-articles.xml.bz2` from its
   `enwiktionary-<date>-sha1sums.txt`. Set `[dump].date` and `[dump].sha1` in
   `polwikt.toml`.
2. Keep the old run's `stats.json`, then rebuild into fresh directories:
   `polwikt fetch`, `polwikt scan --force`, `polwikt extract --out data/<date>/p3`,
   `polwikt finalize --in data/<date>/p3 --out data/<date>/corpus`.
3. `polwikt stats-diff <old>/stats.json data/<date>/corpus/stats.json` and review every
   regression it reports: a page rewritten upstream, or a template renamed under us.
   Fixing one is a separate commit, before or after the pin.
4. Regenerate the golden corpus from the new store: `make golden-pull`,
   `make golden-snapshot`, then
   `uv run pytest tests/test_golden.py tests/test_golden_stats.py --update-golden`, and
   review the diff of `tests/golden/`.
5. Re-run the wiktextract cross-check:
   `uv run python tools/oracle.py generate && uv run python tools/oracle.py diff` must
   report 0 unexplained.
6. `make check`, then commit `polwikt.toml` and `tests/golden/` together, with the
   stats-diff summary in the commit message (`stats.json` itself is not committed).

## License

Code: MIT ([`LICENSE`](LICENSE)). Generated corpora contain Wiktionary content and are
CC BY-SA 4.0, with attribution to English Wiktionary (R11); every corpus carries a
`LICENSE-DATA` saying so.
