#!/usr/bin/env python3
"""Small helper to update runtime status phases from build scripts.

This module deliberately does not contain workflow logic. It only provides a
stable command interface for future build stages.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from automation_run_status import update_status


def main() -> int:
    parser = argparse.ArgumentParser(description="Update ADHS runtime status phase")
    parser.add_argument("status_file", type=Path)
    parser.add_argument("--status", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--workflow", default="knowledge-graph")
    args = parser.parse_args()

    update_status(
        args.status_file,
        workflow=args.workflow,
        status=args.status,
        phase=args.phase,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
