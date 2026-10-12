"""Downloads the pinned dump and verifies its sha1 (R2.1, R2.1a)."""

from __future__ import annotations

import hashlib
import logging
import urllib.request
from pathlib import Path

from polwikt import __version__
from polwikt.config import DumpPin

log = logging.getLogger(__name__)

_CHUNK = 1 << 20


class FetchError(Exception):
    """The download failed or the file does not match the pinned sha1."""


def user_agent() -> str:
    # dumps.wikimedia.org answers 403 without a descriptive User-Agent (R2.1).
    return f"polwikt/{__version__} (Polish lexical data extraction; Python urllib)"


def sha1_of(path: Path, start: hashlib._Hash | None = None) -> str:
    """sha1 of a file, streamed; `start` continues an existing hash."""
    digest = start or hashlib.sha1()
    with path.open("rb") as f:
        while chunk := f.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, pin: DumpPin) -> None:
    """Refuses a dump whose sha1 is not the pinned one (R2.1)."""
    actual = sha1_of(path)
    if actual != pin.sha1:
        raise FetchError(f"{path}: sha1 {actual} does not match the pin {pin.sha1}")


def fetch(pin: DumpPin, dest_dir: Path) -> Path:
    """Downloads the pinned dump into `dest_dir`, resuming a partial `.part` file."""
    if not pin.is_pinned:
        raise FetchError("no dump is pinned in polwikt.toml (R2.1a)")
    dest = dest_dir / pin.filename
    if dest.exists():
        log.info("verifying existing %s", dest)
        verify(dest, pin)
        return dest
    dest_dir.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    digest = hashlib.sha1()
    offset = 0
    if part.exists():
        sha1_of(part, digest)
        offset = part.stat().st_size
    url = f"{pin.url_base}/{pin.date}/{pin.filename}"
    request = urllib.request.Request(url, headers={"User-Agent": user_agent()})
    if offset:
        request.add_header("Range", f"bytes={offset}-")
    log.info("downloading %s from byte %d", url, offset)
    with urllib.request.urlopen(request) as response:
        if offset and response.status != 206:
            raise FetchError(
                f"server ignored the resume range (HTTP {response.status})"
            )
        total = offset + int(response.headers.get("Content-Length", 0))
        with part.open("ab") as out:
            done = offset
            next_report = done + (100 << 20)
            while chunk := response.read(_CHUNK):
                out.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if done >= next_report:
                    log.info("  %d / %d MB", done >> 20, total >> 20)
                    next_report += 100 << 20
    if digest.hexdigest() != pin.sha1:
        raise FetchError(
            f"{part}: sha1 {digest.hexdigest()} does not match the pin {pin.sha1}; "
            "delete it and fetch again"
        )
    part.rename(dest)
    return dest
