"""Filesystem cache for fetched PDFs.

Layout:
  scrapers/{jurisdiction}/.cache/{sha256}.pdf
  scrapers/{jurisdiction}/.cache/metadata.json

Cache entries expire after `ttl_days` (default 7). The metadata maps URL
-> {sha256, fetched_at, content_type} so callers can cheaply see whether
a cached copy is fresh.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


class Cache:
    def __init__(self, base_dir: Path, ttl_days: int = 7) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)
        self._ttl = timedelta(days=ttl_days)
        self._meta_path = self._base / "metadata.json"
        self._meta: dict[str, dict] = {}
        if self._meta_path.exists():
            try:
                self._meta = json.loads(self._meta_path.read_text())
            except json.JSONDecodeError:
                log.warning("cache metadata is corrupt at %s; resetting", self._meta_path)
                self._meta = {}

    def _flush(self) -> None:
        self._meta_path.write_text(json.dumps(self._meta, indent=2, sort_keys=True))

    def _path_for(self, sha: str) -> Path:
        return self._base / f"{sha}.pdf"

    def get(self, url: str) -> Optional[bytes]:
        entry = self._meta.get(url)
        if not entry:
            return None
        try:
            fetched_at = datetime.fromisoformat(entry["fetched_at"])
        except (KeyError, ValueError):
            return None
        if datetime.now(timezone.utc) - fetched_at > self._ttl:
            return None
        path = self._path_for(entry["sha256"])
        if not path.exists():
            return None
        return path.read_bytes()

    def put(self, url: str, content: bytes, content_type: str = "") -> str:
        sha = hashlib.sha256(content).hexdigest()
        path = self._path_for(sha)
        path.write_bytes(content)
        self._meta[url] = {
            "sha256": sha,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "content_type": content_type,
            "size": len(content),
        }
        self._flush()
        return sha

    def clear(self) -> None:
        for p in self._base.glob("*.pdf"):
            p.unlink()
        self._meta = {}
        if self._meta_path.exists():
            self._meta_path.unlink()
