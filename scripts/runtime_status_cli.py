#!/usr/bin/env python3
"""Small command-line helpers for automation runtime status files.

The command is intentionally independent from the scheduler. It only manages
well-formed status documents and can therefore be used from GitHub Actions,
local runs or future recovery tooling.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(path: Path, status: str, workflow: str, phase: str) -> None:
    payload = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "workflow": workflow,
        "status": status,
        "phase": phase,
        "updated_at": utc_now(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write automation runtime status")
    parser.add_argument("path", type=Path)
    parser.add_argument("--workflow", default="unknown")
    parser.add_argument("--status", default="running")
    parser.add_argument("--phase", default="unknown")
    args = parser.parse_args()

    write_status(args.path, args.status, args.workflow, args.phase)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
