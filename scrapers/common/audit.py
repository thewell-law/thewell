"""Per-jurisdiction audit log.

One JSONL file per day under scrapers/{jurisdiction}/.audit/.
Each line records a single scrape event: URL, HTTP status, content hash,
which extractors fired, and any validation errors.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def log_scrape_event(jurisdiction_dir: Path, event: dict[str, Any]) -> None:
    audit_dir = Path(jurisdiction_dir) / ".audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    path = audit_dir / f"{now.date().isoformat()}.jsonl"
    payload = {"timestamp": now.isoformat(), **event}
    with path.open("a") as f:
        f.write(json.dumps(payload, default=str) + "\n")
