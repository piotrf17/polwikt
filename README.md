# polwikt

Extracts Polish lexical data — senses, inflection, pronunciation, etymology, relations —
from the **English** Wiktionary dump into Protocol Buffers.

- **`REQUIREMENTS.md`** — the spec; requirement IDs (`R3.2`, …) are cited from code.
- **`PLAN.md`** — implementation milestones M0–M14.
- **`CLAUDE.md`** — dev setup and the invariants not to break.

Status: **M1** — protobuf schema (`proto/polwikt.proto`) and corpus I/O
(`polwikt/proto/io.py`). The pipeline passes start at M2; every pass command still fails
loudly with the milestone that delivers it.

## Quick start

Needs [`uv`](https://docs.astral.sh/uv/) and `make`. uv installs the pinned Python
(`.python-version`) itself.

```bash
make sync     # .venv from uv.lock, incl. dev tools
make check    # lint + format check + mypy --strict + tests
uv run polwikt --help
```

## License

Code: MIT. Generated corpora contain Wiktionary content and are CC BY-SA 4.0 (R11).
