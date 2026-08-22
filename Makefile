# Convenience wrapper. `uv` is the actual toolchain — every target below is a one-line
# `uv run`, so nothing here is required (and `make` need not be installed).
.PHONY: help venv proto lint format typecheck test check clean

help:
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

venv: ## Create .venv and install the package with dev extras
	uv sync --extra dev

proto: ## Regenerate protobuf modules (commit the result; CI checks it is clean)
	uv run python -m grpc_tools.protoc -Iproto \
		--python_out=polwikt/proto --pyi_out=polwikt/proto proto/*.proto

lint: ## ruff check + format check
	uv run ruff check .
	uv run ruff format --check .

format: ## Apply ruff formatting and safe fixes
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## mypy --strict
	uv run mypy

test: ## pytest (never requires a dump)
	uv run pytest

check: lint typecheck test ## Everything CI runs

clean:
	rm -rf .mypy_cache .ruff_cache .pytest_cache
