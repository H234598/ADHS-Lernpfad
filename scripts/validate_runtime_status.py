#!/usr/bin/env python3
"""Validate automation runtime status JSON against its schema."""

from __future__ import annotations

import json
from pathlib import Path
import sys

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"jsonschema fehlt: {exc}")

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "automation" / "runtime-status.json"
SCHEMA = ROOT / "automation" / "schema" / "run-status.schema.json"


def main() -> int:
    if not STATUS.exists():
        print(f"Runtime status fehlt: {STATUS}")
        return 1
    if not SCHEMA.exists():
        print(f"Runtime schema fehlt: {SCHEMA}")
        return 1

    status = json.loads(STATUS.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(status, schema)
    print("Runtime status valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
