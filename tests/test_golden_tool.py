"""tools/golden.py pull: copies listed pages verbatim, keeps blessed expectations."""

from __future__ import annotations

import bz2
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from polwikt.config import load_config
from polwikt.dump.scan import scan
from tests.test_scan import dump_xml

REPO = Path(__file__).resolve().parent.parent


def _load_tool() -> ModuleType:
    path = REPO / "tools" / "golden.py"
    spec = importlib.util.spec_from_file_location("golden", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # @dataclass looks its module up there
    spec.loader.exec_module(module)
    return module


golden = _load_tool()


def _store(tmp_path: Path, sha1: str) -> Path:
    tmp_path.mkdir(exist_ok=True)
    dump = tmp_path / "dump.xml.bz2"
    dump.write_bytes(bz2.compress(dump_xml()))
    db = tmp_path / "pages.sqlite"
    scan(load_config(REPO), dump, db, dump_sha1=sha1)
    return db


def _golden(tmp_path: Path, *titles: str) -> Path:
    root = tmp_path / "golden"
    root.mkdir(exist_ok=True)
    entries = "".join(f'[[page]]\ntitle = "{t}"\nwhy = "test"\n' for t in titles)
    (root / "pages.toml").write_text(entries, encoding="utf-8")
    return root


@pytest.fixture
def pinned_store(tmp_path: Path) -> Path:
    return _store(tmp_path, load_config(REPO).dump.sha1)


def test_pull_writes_fixtures_and_manifest(tmp_path: Path, pinned_store: Path) -> None:
    root = _golden(tmp_path, "kot", "pies")
    golden.pull(pinned_store, root)
    assert (root / "pages" / "kot.wiki").read_text().startswith("==Polish==")
    assert (root / "expected" / "pies.json").read_text() == golden.TODO
    manifest = json.loads((root / "manifest.json").read_text())
    assert [p["title"] for p in manifest["pages"]] == ["kot", "pies"]
    assert manifest["pages"][0]["page_id"] == 1


def test_pull_keeps_blessed_expectations_and_prunes(
    tmp_path: Path, pinned_store: Path
) -> None:
    root = _golden(tmp_path, "kot", "pies")
    golden.pull(pinned_store, root)
    (root / "expected" / "kot.json").write_text("null\n")
    _golden(tmp_path, "kot")
    golden.pull(pinned_store, root)
    assert (root / "expected" / "kot.json").read_text() == "null\n"
    assert not (root / "pages" / "pies.wiki").exists()
    assert not (root / "expected" / "pies.json").exists()


def test_pull_refuses_non_polish_and_unpinned(
    tmp_path: Path, pinned_store: Path
) -> None:
    with pytest.raises(golden.GoldenError, match="not a Polish page"):
        golden.pull(pinned_store, _golden(tmp_path, "cat"))
    unpinned = _store(tmp_path / "other", "1" * 40)
    with pytest.raises(golden.GoldenError, match="pinned dump"):
        golden.pull(unpinned, _golden(tmp_path, "kot"))


def test_slugs() -> None:
    assert golden.slug("dzień dobry") == "dzień_dobry"
    with pytest.raises(golden.GoldenError):
        golden.slug("a/b")


def test_case_colliding_titles_are_refused(tmp_path: Path) -> None:
    with pytest.raises(golden.GoldenError, match="collides"):
        golden.load_list(_golden(tmp_path, "DNA", "dna"))
