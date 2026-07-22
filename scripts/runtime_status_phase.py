#!/usr/bin/env python3
"""Update a real graph-build phase from Python or the command line.

``runtime_phase`` can wrap a standalone stage.  In managed mode the outer
orchestrator retains lifecycle ownership, so successful phase completion is
not mistaken for successful completion of the complete workflow.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

try:  # Support both ``python scripts/...`` and package imports in tests.
    from .automation_run_status import (
        DEFAULT_STATUS_PATH,
        PHASES,
        finish_run,
        start_run,
        status_is_managed,
        update_status,
    )
except ImportError:  # pragma: no cover - exercised by command-line use
    from automation_run_status import (
        DEFAULT_STATUS_PATH,
        PHASES,
        finish_run,
        start_run,
        status_is_managed,
        update_status,
    )


def update_phase(
    status_file: Path,
    phase: str,
    *,
    workflow: str = "knowledge-graph",
    metrics: Mapping[str, Any] | None = None,
    artifacts: list[str] | None = None,
) -> dict[str, Any]:
    """Start an unmanaged file if necessary, then persist a phase update."""

    target = Path(status_file)
    if not status_is_managed() and not target.exists():
        start_run(target, workflow)
    return update_status(
        target,
        status="running",
        phase=phase,
        workflow=workflow,
        metrics=metrics,
        artifacts=artifacts,
    )


@contextmanager
def runtime_phase(
    status_file: Path,
    phase: str,
    *,
    workflow: str = "knowledge-graph",
    metrics: Mapping[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Track one stage and finish only when it owns a standalone lifecycle.

    Callers can add measurements to the yielded dictionary.  Exceptions are
    recorded with their class and message, then re-raised unchanged.
    """

    managed = status_is_managed()
    target = Path(status_file)
    if not managed:
        start_run(target, workflow, phase=phase)
    payload = update_status(target, status="running", phase=phase, metrics=metrics)
    collected: dict[str, Any] = {}
    try:
        yield collected
    except Exception as exc:
        finish_run(
            target,
            success=False,
            phase=phase,
            metrics=collected,
            error_class=type(exc).__name__,
            error_message=str(exc) or type(exc).__name__,
            recovery_action="inspect_logs_and_retry",
        )
        raise
    else:
        if collected:
            payload = update_status(target, metrics=collected)
        if not managed:
            finish_run(target, success=True, metrics=payload.get("metrics"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update an ADHS graph runtime phase")
    parser.add_argument("status_file", nargs="?", type=Path, default=DEFAULT_STATUS_PATH)
    parser.add_argument("--phase", required=True, choices=sorted(PHASES))
    parser.add_argument("--workflow", default="knowledge-graph")
    parser.add_argument("--status", default="running")
    parser.add_argument("--artifact", action="append", default=[])
    args = parser.parse_args(argv)

    if args.status == "success":
        finish_run(args.status_file, success=True, phase=args.phase, artifacts=args.artifact)
    elif args.status == "failed":
        finish_run(args.status_file, success=False, phase=args.phase, artifacts=args.artifact)
    else:
        update_phase(
            args.status_file,
            args.phase,
            workflow=args.workflow,
            artifacts=args.artifact,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
