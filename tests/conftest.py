"""Shared pytest options."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.golden_harness import SNAPSHOT, unpack_snapshot


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-golden",
        action="store_true",
        help="Re-bless tests/golden/expected/ from the current extraction output.",
    )


@pytest.fixture
def update_golden(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--update-golden"))


@pytest.fixture(scope="session")
def golden_store(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """The golden store snapshot (R8.1a), unpacked once per test session."""
    if not SNAPSHOT.exists():
        pytest.skip("needs tests/golden/store.sqlite.zst (tools/golden.py snapshot)")
    yield unpack_snapshot(tmp_path_factory.mktemp("golden"))
