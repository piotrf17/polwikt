"""`polwikt fetch`: User-Agent, resume, refusing a file that isn't the pin (R2.1)."""

from __future__ import annotations

import hashlib
import io
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from polwikt.config import DumpPin
from polwikt.dump.fetch import FetchError, fetch, verify

BODY = b"<mediawiki>" + bytes(range(256)) * 50 + b"</mediawiki>"
PIN = DumpPin(
    date="20261001",
    sha1=hashlib.sha1(BODY).hexdigest(),
    url_base="https://dumps.example/enwiktionary",
)


class _Response(io.BytesIO):
    def __init__(self, body: bytes, status: int) -> None:
        super().__init__(body)
        self.status = status
        self.headers = {"Content-Length": str(len(body))}


@pytest.fixture
def requests(monkeypatch: pytest.MonkeyPatch) -> list[urllib.request.Request]:
    seen: list[urllib.request.Request] = []

    def urlopen(request: urllib.request.Request, *_: Any) -> _Response:
        seen.append(request)
        start = 0
        if (range_header := request.get_header("Range")) is not None:
            start = int(range_header.removeprefix("bytes=").rstrip("-"))
        return _Response(BODY[start:], 206 if start else 200)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return seen


def test_downloads_and_verifies(tmp_path: Path, requests: list[Any]) -> None:
    path = fetch(PIN, tmp_path)
    assert path.read_bytes() == BODY
    assert path.name == PIN.filename
    (request,) = requests
    assert request.full_url.endswith(f"/20261001/{PIN.filename}")
    assert request.get_header("User-agent").startswith("polwikt/")


def test_resumes_a_partial_download(tmp_path: Path, requests: list[Any]) -> None:
    (tmp_path / f"{PIN.filename}.part").write_bytes(BODY[:1000])
    assert fetch(PIN, tmp_path).read_bytes() == BODY
    assert requests[0].get_header("Range") == "bytes=1000-"


def test_existing_file_is_verified_not_refetched(
    tmp_path: Path, requests: list[Any]
) -> None:
    (tmp_path / PIN.filename).write_bytes(BODY)
    fetch(PIN, tmp_path)
    assert requests == []
    (tmp_path / PIN.filename).write_bytes(BODY + b"x")
    with pytest.raises(FetchError, match="does not match the pin"):
        fetch(PIN, tmp_path)


def test_corrupt_download_is_not_renamed(tmp_path: Path, requests: list[Any]) -> None:
    bad = DumpPin(date=PIN.date, sha1="0" * 40, url_base=PIN.url_base)
    with pytest.raises(FetchError, match="does not match the pin"):
        fetch(bad, tmp_path)
    assert not (tmp_path / PIN.filename).exists()


def test_verify(tmp_path: Path) -> None:
    path = tmp_path / "dump.bz2"
    path.write_bytes(BODY)
    verify(path, PIN)
    path.write_bytes(BODY[:-1])
    with pytest.raises(FetchError):
        verify(path, PIN)
