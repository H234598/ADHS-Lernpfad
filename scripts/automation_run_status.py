#!/usr/bin/env python3
"""Small atomic runtime status writer used by automation jobs."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone


def write_status(path: Path, status: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(status)
    payload.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".status-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


if __name__ == "__main__":
    target = Path("automation/runtime-status.json")
    write_status(target, {
        "run_id": "manual",
        "workflow": "manual",
        "status": "started",
        "phase": "initialization"
    })
    print(target)
