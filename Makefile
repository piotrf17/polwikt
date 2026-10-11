# Entry points for dev work. Every target runs through uv against uv.lock, so `make`
# and CI execute exactly the same commands.

UV ?= uv
RUN := $(UV) run --locked

.PHONY: help sync lint fmt typecheck test check lock clean

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

lock:  ## Re-resolve uv.lock after editing pyproject.toml
	$(UV) lock

clean:  ## Remove caches (keeps .venv and data/)
	rm -rf .mypy_cache .pytest_cache .ruff_cache
	find . -name __pycache__ -not -path './.venv/*' -prune -exec rm -rf {} +
