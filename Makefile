# Entry points for dev work. Every target runs through uv against uv.lock, so `make`
# and CI execute exactly the same commands.

UV ?= uv
RUN := $(UV) run --locked

.PHONY: help sync lint fmt typecheck test check proto golden-pull golden-snapshot lock clean

help:  ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

sync:  ## Create/refresh .venv from uv.lock (incl. dev tools)
	$(UV) sync --locked

lint:  ## ruff lint + format check
	$(RUN) ruff check .
	$(RUN) ruff format --check .

fmt:  ## Apply ruff fixes and formatting
	$(RUN) ruff check --fix .
	$(RUN) ruff format .

typecheck:  ## mypy --strict
	$(RUN) mypy

test:  ## pytest (never needs a dump)
	$(RUN) pytest

check: lint typecheck test  ## Everything CI runs

proto:  ## Regenerate polwikt/proto/*_pb2.py[i] from proto/polwikt.proto (commit the result)
	$(RUN) python -m grpc_tools.protoc -Iproto --python_out=polwikt/proto --pyi_out=polwikt/proto proto/polwikt.proto

golden-pull:  ## Refresh tests/golden/ fixtures from data/pages.sqlite (R8.1)
	$(RUN) python tools/golden.py pull

golden-snapshot:  ## Rebuild tests/golden/store.sqlite.zst from data/pages.sqlite (R8.1a)
	$(RUN) python tools/golden.py snapshot

lock:  ## Re-resolve uv.lock after editing pyproject.toml
	$(UV) lock

clean:  ## Remove caches (keeps .venv and data/)
	rm -rf .mypy_cache .pytest_cache .ruff_cache
	find . -name __pycache__ -not -path './.venv/*' -prune -exec rm -rf {} +
