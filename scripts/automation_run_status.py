#!/usr/bin/env python3
"""Atomic, schema-compatible runtime status management for automation jobs.

The public functions are deliberately scheduler-independent.  A standalone
generator starts and finishes its own run.  With ``RUNTIME_STATUS_MANAGED=1``
an outer workflow owns that lifecycle, while generators continue to call
``update_status`` for their real phases and metrics.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Mapping
from uuid import uuid4


DEFAULT_STATUS_PATH = Path("build/runtime-status.json")
PHASES = {
    "initialization",
    "load_content",
    "build_nodes",
    "build_edges",
    "validate_graph",
    "export",
    "success",
    "failed",
}
STATUSES = {"started", "running", "success", "failed", "blocked", "recovered"}
FINAL_STATUSES = {"success", "failed", "recovered"}
_TRUE_VALUES = {"1", "true", "yes", "on"}
_UNSET = object()


def utc_now() -> str:
    """Return an RFC 3339 UTC timestamp with an explicit ``Z`` suffix."""

    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def status_is_managed(env: Mapping[str, str] | None = None) -> bool:
    """Whether an outer workflow owns start/finish lifecycle updates."""

    values = os.environ if env is None else env
    return values.get("RUNTIME_STATUS_MANAGED", "").strip().lower() in _TRUE_VALUES


def _timestamp(value: str) -> datetime:
    if "T" not in value:
        raise ValueError("date-time separator missing")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone missing")
    return parsed


def _new_run_id() -> str:
    external = os.environ.get("GITHUB_RUN_ID") or os.environ.get("CI_PIPELINE_ID")
    if external:
        attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
        return f"{external}-{attempt}" if attempt else external
    return f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"


def _default_git_sha(value: Any = None) -> str:
    candidate = value or os.environ.get("GITHUB_SHA")
    if not candidate:
        try:
            candidate = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=Path(__file__).resolve().parents[1],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            candidate = "unknown"
    if not isinstance(candidate, str):
        return "unknown"
    candidate = candidate.strip()
    if candidate == "unknown":
        return candidate
    if 7 <= len(candidate) <= 64 and all(char in "0123456789abcdefABCDEF" for char in candidate):
        return candidate
    return "unknown"


def _canonical_phase(phase: Any, status: str) -> str:
    if isinstance(phase, str) and phase in PHASES:
        return phase
    if status == "success":
        return "success"
    if status == "failed":
        return "failed"
    return "initialization"


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_artifacts(value: Any) -> list[str]:
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, (list, tuple, set)):
        candidates = value
    else:
        candidates = []
    return list(dict.fromkeys(str(item) for item in candidates if str(item).strip()))


def _duration(started_at: str, ended_at: str) -> float:
    try:
        return round(max(0.0, (_timestamp(ended_at) - _timestamp(started_at)).total_seconds()), 3)
    except (TypeError, ValueError):
        return 0.0


def _normalise(payload: Mapping[str, Any], *, now: str | None = None) -> dict[str, Any]:
    """Complete partial input without ever persisting a partial document."""

    current_time = now or utc_now()
    raw_status = payload.get("status")
    status = raw_status if isinstance(raw_status, str) and raw_status in STATUSES else "running"
    started_at = payload.get("started_at")
    try:
        _timestamp(started_at)
    except (AttributeError, TypeError, ValueError):
        started_at = current_time

    ended_at = payload.get("ended_at")
    duration = payload.get("duration_seconds")
    if status in FINAL_STATUSES:
        try:
            _timestamp(ended_at)
        except (AttributeError, TypeError, ValueError):
            ended_at = current_time
        if (
            not isinstance(duration, (int, float))
            or isinstance(duration, bool)
            or not math.isfinite(duration)
            or duration < 0
        ):
            duration = _duration(started_at, ended_at)
    else:
        ended_at = None
        duration = None

    error_class = payload.get("error_class")
    error_message = payload.get("error_message")
    recovery_action = payload.get("recovery_action")
    if status == "failed":
        error_class = str(error_class or "unknown_error")
        error_message = str(error_message or "Automation failed without an error message")
        recovery_action = str(recovery_action or "inspect_logs")
    else:
        error_class = str(error_class) if error_class else None
        error_message = str(error_message) if error_message else None
        recovery_action = str(recovery_action) if recovery_action else None

    return {
        "run_id": str(payload.get("run_id") or _new_run_id()),
        "workflow": str(payload.get("workflow") or os.environ.get("GITHUB_WORKFLOW") or "knowledge-graph"),
        "git_sha": _default_git_sha(payload.get("git_sha")),
        "status": status,
        "phase": _canonical_phase(payload.get("phase"), status),
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": duration,
        "updated_at": current_time,
        "metrics": _safe_mapping(payload.get("metrics")),
        "artifacts": _safe_artifacts(payload.get("artifacts")),
        "error_class": error_class,
        "error_message": error_message,
        "recovery_action": recovery_action,
    }


def validate_status(status: Mapping[str, Any]) -> list[str]:
    """Return contract violations using no third-party runtime dependency."""

    errors: list[str] = []
    required = {
        "run_id", "workflow", "git_sha", "status", "phase", "started_at",
        "ended_at", "duration_seconds", "updated_at", "metrics", "artifacts",
        "error_class", "error_message", "recovery_action",
    }
    missing = sorted(required - set(status))
    if missing:
        errors.append("missing required fields: " + ", ".join(missing))
    unknown = sorted(set(status) - required)
    if unknown:
        errors.append("unknown fields: " + ", ".join(unknown))
    if not isinstance(status.get("run_id"), str) or not status.get("run_id"):
        errors.append("run_id must be a non-empty string")
    if not isinstance(status.get("workflow"), str) or not status.get("workflow"):
        errors.append("workflow must be a non-empty string")
    if _default_git_sha(status.get("git_sha")) != status.get("git_sha"):
        errors.append("git_sha must be 'unknown' or a 7-64 character hexadecimal SHA")
    if not isinstance(status.get("status"), str) or status.get("status") not in STATUSES:
        errors.append("status is not supported")
    if not isinstance(status.get("phase"), str) or status.get("phase") not in PHASES:
        errors.append("phase is not supported")
    parsed_times: dict[str, datetime] = {}
    for field in ("started_at", "updated_at"):
        try:
            parsed_times[field] = _timestamp(status.get(field))
        except (AttributeError, TypeError, ValueError):
            errors.append(f"{field} must be an RFC 3339 date-time")
    if status.get("status") in FINAL_STATUSES:
        try:
            parsed_times["ended_at"] = _timestamp(status.get("ended_at"))
        except (AttributeError, TypeError, ValueError):
            errors.append("ended_at must be an RFC 3339 date-time for a final status")
        duration = status.get("duration_seconds")
        if (
            not isinstance(duration, (int, float))
            or isinstance(duration, bool)
            or not math.isfinite(duration)
            or duration < 0
        ):
            errors.append("duration_seconds must be non-negative for a final status")
    elif status.get("ended_at") is not None or status.get("duration_seconds") is not None:
        errors.append("non-final status must not have an end time or duration")
    started_at = parsed_times.get("started_at")
    updated_at = parsed_times.get("updated_at")
    ended_at = parsed_times.get("ended_at")
    if started_at is not None and updated_at is not None and updated_at < started_at:
        errors.append("updated_at must not be before started_at")
    if started_at is not None and ended_at is not None and ended_at < started_at:
        errors.append("ended_at must not be before started_at")
    if ended_at is not None and updated_at is not None and updated_at < ended_at:
        errors.append("updated_at must not be before ended_at")
    if not isinstance(status.get("metrics"), dict):
        errors.append("metrics must be an object")
    else:
        try:
            json.dumps(status["metrics"], ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError):
            errors.append("metrics must contain only JSON-compatible values")
    artifacts = status.get("artifacts")
    if not isinstance(artifacts, list) or any(not isinstance(item, str) or not item for item in artifacts):
        errors.append("artifacts must contain non-empty strings")
    elif len(artifacts) != len(set(artifacts)):
        errors.append("artifacts must be unique")
    for field in ("error_class", "error_message", "recovery_action"):
        value = status.get(field)
        if value is not None and (not isinstance(value, str) or not value):
            errors.append(f"{field} must be null or a non-empty string")
    if status.get("status") == "failed":
        for field in ("error_class", "error_message", "recovery_action"):
            if not isinstance(status.get(field), str) or not status.get(field):
                errors.append(f"{field} must be set for a failed status")
    elif status.get("status") == "success":
        for field in ("error_class", "error_message", "recovery_action"):
            if status.get(field) is not None:
                errors.append(f"{field} must be null for a successful status")
    return errors


def _atomic_dump(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def write_status(path: Path, status: Mapping[str, Any]) -> dict[str, Any]:
    """Normalise, validate and atomically replace a status document."""

    payload = _normalise(status)
    errors = validate_status(payload)
    if errors:  # Defensive: normalisation should always produce valid data.
        raise ValueError("Invalid runtime status: " + "; ".join(errors))
    _atomic_dump(Path(path), payload)
    return payload


def _read_status(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def start_run(
    path: Path,
    workflow: str,
    *,
    phase: str = "initialization",
    git_sha: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Create a new run, intentionally replacing any previous lifecycle."""

    now = utc_now()
    return write_status(Path(path), {
        "run_id": run_id,
        "workflow": workflow,
        "git_sha": git_sha,
        "status": "started",
        "phase": phase,
        "started_at": now,
        "updated_at": now,
        "metrics": {},
        "artifacts": [],
    })


def update_status(
    path: Path,
    *,
    status: str | None = None,
    phase: str | None = None,
    workflow: str | None = None,
    run_id: str | None = None,
    git_sha: str | None = None,
    metrics: Mapping[str, Any] | None = None,
    artifacts: list[str] | tuple[str, ...] | None = None,
    error_class: str | None | object = _UNSET,
    error_message: str | None | object = _UNSET,
    recovery_action: str | None | object = _UNSET,
) -> dict[str, Any]:
    """Merge a phase update while preserving run identity and start time."""

    target = Path(path)
    existing = _normalise(_read_status(target))
    merged = dict(existing)
    for key, value in {
        "status": status,
        "phase": phase,
        "workflow": workflow,
        "run_id": run_id,
        "git_sha": git_sha,
    }.items():
        if value is not None:
            merged[key] = value
    if metrics is not None:
        merged["metrics"] = {**_safe_mapping(existing.get("metrics")), **_safe_mapping(metrics)}
    if artifacts is not None:
        merged["artifacts"] = _safe_artifacts([
            *_safe_artifacts(existing.get("artifacts")),
            *_safe_artifacts(artifacts),
        ])
    for key, value in {
        "error_class": error_class,
        "error_message": error_message,
        "recovery_action": recovery_action,
    }.items():
        if value is not _UNSET:
            merged[key] = value
    # A resumed phase is not final even when a stale final file was loaded.
    if merged.get("status") not in FINAL_STATUSES:
        merged["ended_at"] = None
        merged["duration_seconds"] = None
    return write_status(target, merged)


def finish_run(
    path: Path,
    *,
    success: bool,
    phase: str | None = None,
    metrics: Mapping[str, Any] | None = None,
    artifacts: list[str] | tuple[str, ...] | None = None,
    error_class: str | None = None,
    error_message: str | None = None,
    recovery_action: str | None = None,
) -> dict[str, Any]:
    """Finish a run and calculate its wall-clock duration."""

    target = Path(path)
    existing = _normalise(_read_status(target))
    now = utc_now()
    existing.update({
        "status": "success" if success else "failed",
        "phase": phase or ("success" if success else existing.get("phase") or "failed"),
        "ended_at": now,
        "duration_seconds": _duration(existing["started_at"], now),
    })
    if metrics is not None:
        existing["metrics"] = {**_safe_mapping(existing.get("metrics")), **_safe_mapping(metrics)}
    if artifacts is not None:
        existing["artifacts"] = _safe_artifacts([
            *_safe_artifacts(existing.get("artifacts")),
            *_safe_artifacts(artifacts),
        ])
    if success:
        existing.update(error_class=None, error_message=None, recovery_action=None)
    else:
        existing.update(
            error_class=error_class or existing.get("error_class") or "unknown_error",
            error_message=error_message or existing.get("error_message") or "Automation failed without an error message",
            recovery_action=recovery_action or existing.get("recovery_action") or "inspect_logs",
        )
    return write_status(target, existing)


if __name__ == "__main__":
    target = DEFAULT_STATUS_PATH
    start_run(target, "manual", run_id="manual")
    print(target)
