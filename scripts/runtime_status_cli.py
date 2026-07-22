#!/usr/bin/env python3
"""Command-line interface for the automation runtime status contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

try:  # Support both ``python scripts/...`` and package imports in tests.
    from .automation_run_status import (
        DEFAULT_STATUS_PATH,
        PHASES,
        STATUSES,
        finish_run,
        start_run,
        update_status,
    )
except ImportError:  # pragma: no cover - exercised by command-line use
    from automation_run_status import (
        DEFAULT_STATUS_PATH,
        PHASES,
        STATUSES,
        finish_run,
        start_run,
        update_status,
    )


def _json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("metrics must be a JSON object")
    return parsed


def _metric(value: str) -> tuple[str, Any]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("metric must use KEY=JSON_VALUE")
    key, raw = value.split("=", 1)
    if not key:
        raise argparse.ArgumentTypeError("metric key must not be empty")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = raw
    return key, parsed


def _metrics(args: argparse.Namespace) -> dict[str, Any] | None:
    result: dict[str, Any] = {}
    if args.metrics_json:
        result.update(args.metrics_json)
    result.update(dict(args.metric or []))
    return result or None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Atomically write a schema-valid automation runtime status"
    )
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_STATUS_PATH)
    parser.add_argument("--workflow", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--git-sha", default=None)
    parser.add_argument("--status", choices=sorted(STATUSES), default="running")
    parser.add_argument("--phase", choices=sorted(PHASES), default=None)
    parser.add_argument("--new-run", action="store_true", help="replace any previous lifecycle")
    parser.add_argument("--finish", choices=("success", "failed"), default=None)
    parser.add_argument("--metric", action="append", type=_metric, default=[])
    parser.add_argument("--metrics-json", type=_json_object, default=None)
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--error-class", default=None)
    parser.add_argument("--error-message", default=None)
    parser.add_argument("--recovery-action", default=None)
    parser.add_argument("--print", dest="print_payload", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    metrics = _metrics(args)
    artifacts = args.artifact or None
    if args.new_run:
        payload = start_run(
            args.path,
            args.workflow or "knowledge-graph",
            phase=args.phase or "initialization",
            git_sha=args.git_sha,
            run_id=args.run_id,
        )
        if metrics or artifacts:
            payload = update_status(args.path, metrics=metrics, artifacts=artifacts)
    elif args.finish:
        payload = finish_run(
            args.path,
            success=args.finish == "success",
            phase=args.phase,
            metrics=metrics,
            artifacts=artifacts,
            error_class=args.error_class,
            error_message=args.error_message,
            recovery_action=args.recovery_action,
        )
    else:
        payload = update_status(
            args.path,
            status=args.status,
            phase=args.phase,
            workflow=args.workflow,
            run_id=args.run_id,
            git_sha=args.git_sha,
            metrics=metrics,
            artifacts=artifacts,
            error_class=args.error_class if args.error_class is not None else None,
            error_message=args.error_message if args.error_message is not None else None,
            recovery_action=args.recovery_action if args.recovery_action is not None else None,
        )
    if args.print_payload:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(args.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
