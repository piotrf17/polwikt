# polwikt

Extract Polish lexical data from the **English** Wiktionary dump into structured
Google Protocol Buffers — senses, part of speech, full declensions and conjugations,
pronunciation, etymology, and lexical relations.

- **`REQUIREMENTS.md`** — the spec. Requirement IDs (`R3.2`, `R6.6a`) are stable and are
  cited from code and commits.
- **`PLAN.md`** — implementation milestones M0–M14.
- **`CLAUDE.md`** — dev setup and the invariants not to break.

Status: **M0** — skeleton and tooling. No pipeline code yet.

## Quick start

Toolchain is [`uv`](https://docs.astral.sh/uv/) (no `pip`/`make` needed):

```bash
uv sync --extra dev            # .venv from uv.lock
uv run ruff check . && uv run mypy && uv run pytest
uv run polwikt --help
uv run polwikt config          # show resolved scope + dump pin
```

`make venv|lint|typecheck|test|check|proto` wrap the same commands if you have `make`.

Template and Lua expansion is done by
[`wikitextprocessor`](https://github.com/tatuylonen/wikitextprocessor); the extraction
on top of it is ours.
[`wiktextract`](https://github.com/tatuylonen/wiktextract) is installed as a dev-only
cross-check oracle and is never imported by pipeline code.

Both are installed **from git, pinned to exact commits** — their PyPI releases are years
stale and expose a different (pre-SQLite) API. See `pyproject.toml`.

## Data license

Wiktionary content is **CC BY-SA 4.0**. Generated corpora carry attribution to English
Wiktionary in their `Corpus` metadata and a `LICENSE-DATA` file, and must be shared
alike. The pipeline code is MIT.
