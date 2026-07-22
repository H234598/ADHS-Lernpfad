#!/usr/bin/env python3
"""Create and update machine-readable automation run state."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "automation" / "runs"


def write_status(workflow: str, status: str, phase: str, completed: list[str], error: dict | None = None) -> Path:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    target = RUN_DIR / f"{timestamp}.json"
    payload = {
        "run_id": timestamp,
        "workflow": workflow,
        "status": status,
        "phase": {
            "current": phase,
            "completed": completed,
        },
        "failed_step": error,
    }
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow")
    parser.add_argument("phase")
    parser.add_argument("status")
    args = parser.parse_args()
    print(write_status(args.workflow, args.status, args.phase, []))
