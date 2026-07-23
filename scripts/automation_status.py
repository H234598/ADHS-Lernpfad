#!/usr/bin/env python3
"""Persistent, resumable automation status and recovery management.

The module has two deliberately separate uses:

* :class:`StatusStore` persists scheduler runs below
  ``automation/status/<workflow>/<run_id>.json`` and keeps a validated
  ``latest.json`` mirror.
* The compatibility functions ``start_run``, ``update_status`` and
  ``finish_run`` write the same strict contract to an arbitrary build path.
  Existing graph and export builders therefore use the recovery contract
  without committing transient build output to ``main``.

Only standard-library features are needed to write a status.  Full JSON Schema
validation remains a CI gate in ``validate_runtime_status.py``.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterator, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "3.0.0"
SCHEMA_PATH = ROOT / "automation" / "run-status.schema.json"
DEFAULT_STATUS_ROOT = Path("automation/status")
DEFAULT_STATUS_PATH = Path("build/runtime-status.json")

WORKFLOWS = {
    "generator",
    "repair-watcher",
    "merge-watcher",
    "knowledge-graph",
    "combined-document",
    "download-exports",
    "validate-graph-and-build",
    "pages-publication",
    "public-exports",
    "export-smoke",
    "runtime-contract",
    "status-persistence",
    "manual",
}
PHASES = {
    "initialize",
    "load_main",
    "check_previous_run",
    "check_existing_pr",
    "read_prompts",
    "research",
    "create_branch",
    "create_content",
    "generate_outputs",
    "validate",
    "commit",
    "push",
    "create_pr",
    "verify_pr",
    "wait_review",
    "repair",
    "ready_for_review",
    "verify_second_ci",
    "merge",
    "cleanup",
    "complete",
    "load_content",
    "build_nodes",
    "build_edges",
    "validate_graph",
    "export",
    "persist_status",
}
STATUSES = {
    "created",
    "running",
    "success",
    "blocked",
    "failed",
    "recovering",
    "recovered",
}
FINAL_STATUSES = {"success", "blocked", "failed", "recovered"}
ERROR_CLASSES = {
    "github_api_transient",
    "github_api_permission",
    "repository_state",
    "branch_conflict",
    "validation",
    "scientific_review",
    "external_service",
    "timeout",
    "rate_limit",
    "configuration",
    "security_policy",
    "unknown",
}
RECOVERY_LEVELS = {
    "retry_same_phase",
    "resume_from_artifact",
    "repair_existing_branch",
    "manual_intervention",
    "terminal_failure",
}
ARTIFACT_TYPES = {
    "branch",
    "commit",
    "pull_request",
    "workflow_run",
    "ci_job",
    "report",
    "graph",
    "export",
    "site",
    "diagnostic",
    "other",
}
ALLOWED_TRANSITIONS = {
    "created": {"created", "running", "blocked", "failed"},
    "running": {"running", "success", "blocked", "failed"},
    "success": {"success"},
    "blocked": {"blocked", "recovering", "failed"},
    "failed": {"failed", "recovering"},
    "recovering": {"recovering", "recovered", "blocked", "failed"},
    "recovered": {"recovered", "running", "success", "blocked", "failed"},
}

EXIT_SUCCESS = 0
EXIT_CONTINUE = 10
EXIT_BLOCKED = 20
EXIT_MANUAL = 30

_TRUE_VALUES = {"1", "true", "yes", "on"}
_UNSET = object()
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_CODE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,120}$")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{12,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)\S+"),
    re.compile(
        r"(?i)\b(token|password|passwd|secret|api[_-]?key|access[_-]?key)"
        r"\s*[:=]\s*([^\s,;]+)"
    ),
    re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
)
_LEGACY_PHASES = {
    "initialization": "initialize",
    "success": "complete",
    "failed": "complete",
    "unit-test": "initialize",
}


def cli_status_root() -> Path:
    """Resolve an optional status-branch worktree for CLI operations."""

    configured = os.environ.get("AUTOMATION_STATUS_ROOT")
    return Path(configured) if configured else DEFAULT_STATUS_ROOT


class AutomationStatusError(RuntimeError):
    """Base class for status errors with a concise CLI message."""


class InvalidTransition(AutomationStatusError):
    """The requested lifecycle transition is not allowed."""


class RevisionConflict(AutomationStatusError):
    """The caller attempted to update a stale status revision."""


class LockTimeout(AutomationStatusError):
    """A concurrent writer retained the process lock for too long."""


class UnresolvedPreviousRun(AutomationStatusError):
    """A new generator run would duplicate unresolved work."""

    def __init__(self, status: Mapping[str, Any]) -> None:
        self.status = dict(status)
        super().__init__(
            f"Ungeklärter Lauf {status.get('workflow')}/{status.get('run_id')} "
            f"({status.get('status')}, Phase {status.get('phase')}) blockiert den Start."
        )


def utc_now() -> str:
    """Return an RFC 3339 UTC timestamp with millisecond precision."""

    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or "T" not in value or not value.endswith("Z"):
        raise ValueError("UTC date-time string ending in Z required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def _retention_until(status: str, now: str) -> str:
    days = 90 if status in {"failed", "blocked"} else 30
    return (
        _timestamp(now) + timedelta(days=days)
    ).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _duration(created_at: str, ended_at: str) -> float:
    return round(
        max(0.0, (_timestamp(ended_at) - _timestamp(created_at)).total_seconds()),
        3,
    )


def _portable_run_id(value: str | None = None) -> str:
    candidate = value
    if candidate is None:
        external = os.environ.get("GITHUB_RUN_ID") or os.environ.get("CI_PIPELINE_ID")
        attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
        candidate = f"{external}-{attempt}" if external and attempt else external
    if candidate is None:
        candidate = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    candidate = str(candidate)
    if not _RUN_ID_RE.fullmatch(candidate):
        raise ValueError(
            "run_id darf nur portable Zeichen A-Z, a-z, 0-9, Punkt, "
            "Unterstrich und Bindestrich enthalten"
        )
    _redacted, contains_sensitive_value = redact_text(candidate, limit=128)
    if contains_sensitive_value:
        raise ValueError("run_id darf keine erkennbaren Zugangsdaten enthalten")
    return candidate


def _canonical_phase(value: Any, status: str = "running") -> str:
    if isinstance(value, str):
        value = _LEGACY_PHASES.get(value, value)
    if isinstance(value, str) and value in PHASES:
        return value
    if status in FINAL_STATUSES:
        return "complete"
    return "initialize"


def _canonical_status(value: Any) -> str:
    if value == "started":
        return "created"
    return value if isinstance(value, str) and value in STATUSES else "running"


def _git_sha(value: Any = None) -> str | None:
    candidate = value or os.environ.get("GITHUB_SHA")
    if not candidate:
        try:
            candidate = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    candidate = str(candidate).strip()
    return candidate if _SHA_RE.fullmatch(candidate) else None


def _integer(value: Any, *, minimum: int = 1) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= minimum else None


def _safe_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username:
        return None
    # Query strings and fragments frequently contain short-lived signatures.
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _safe_branch(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > 255 or any(ord(char) < 32 for char in value):
        return None
    redacted, _changed = redact_text(value, limit=255)
    return redacted


def default_context(
    *,
    repository: str | None = None,
    branch: str | None = None,
    commit_sha: str | None = None,
    pr_number: int | None = None,
    pr_url: str | None = None,
) -> dict[str, Any]:
    """Build a secret-free repository and GitHub Actions context."""

    repository_value = repository or os.environ.get(
        "GITHUB_REPOSITORY", "H234598/ADHS-Lernpfad"
    )
    _redacted_repository, repository_is_sensitive = redact_text(
        repository_value,
        limit=200,
    )
    if (
        not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository_value)
        or repository_is_sensitive
    ):
        repository_value = "H234598/ADHS-Lernpfad"
    branch_value = branch or os.environ.get("GITHUB_HEAD_REF") or os.environ.get(
        "GITHUB_REF_NAME"
    )
    run_id = _integer(os.environ.get("GITHUB_RUN_ID"))
    attempt = _integer(os.environ.get("GITHUB_RUN_ATTEMPT")) or 1
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    workflow_run = None
    if run_id is not None:
        run_url = f"{server}/{repository_value}/actions/runs/{run_id}"
        raw_job_id = os.environ.get("GITHUB_JOB") or None
        safe_job_id = (
            redact_text(raw_job_id, limit=200)[0]
            if raw_job_id is not None
            else None
        )
        workflow_run = {
            "id": run_id,
            "attempt": attempt,
            "job_id": safe_job_id,
            "url": run_url,
            "logs_url": run_url,
        }
    return {
        "repository": repository_value,
        "branch": _safe_branch(branch_value),
        "commit_sha": _git_sha(commit_sha),
        "pr_number": _integer(pr_number),
        "pr_url": _safe_url(pr_url),
        "workflow_run": workflow_run,
    }


def redact_text(value: Any, *, limit: int = 2000) -> tuple[str, bool]:
    """Redact credentials and personal addresses from diagnostic text."""

    raw_text = str(value or "")
    text = "".join(
        " " if ord(character) < 32 or ord(character) == 127 else character
        for character in raw_text
    )
    text = re.sub(r" +", " ", text).strip()
    changed = text != raw_text
    for pattern in _SECRET_PATTERNS:
        if pattern.groups == 1:
            replacement = r"\1[REDACTED]"
        elif pattern.groups >= 2:
            replacement = r"\1=[REDACTED]"
        else:
            replacement = "[REDACTED]"
        text, count = pattern.subn(replacement, text)
        changed = changed or count > 0
    if len(text) > limit:
        text = text[: max(0, limit - 15)] + "… [gekürzt]"
        changed = True
    return text or "Keine Detailmeldung verfügbar.", changed


def _sanitize_json_value(value: Any) -> Any:
    """Redact strings recursively before arbitrary metrics enter a status."""

    if isinstance(value, str):
        if not value:
            return value
        return redact_text(value)[0]
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            safe_key = redact_text(key, limit=120)[0]
            sanitized[safe_key] = _sanitize_json_value(item)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [_sanitize_json_value(item) for item in value]
    return value


def _safe_relative_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip().replace("\\", "/")
    path = PurePosixPath(candidate)
    if path.is_absolute() or ".." in path.parts or any(ord(char) < 32 for char in candidate):
        return None
    return candidate[:500]


def make_artifact(
    artifact_type: str,
    value: Any,
    *,
    path: str | None = None,
    url: str | None = None,
    sha256: str | None = None,
    reusable: bool = False,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError(f"Unbekannter Artefakttyp: {artifact_type}")
    safe_value, _changed = redact_text(value, limit=1000)
    safe_path = _safe_relative_path(path)
    safe_hash = sha256 if isinstance(sha256, str) and _SHA256_RE.fullmatch(sha256) else None
    return {
        "type": artifact_type,
        "value": safe_value,
        "path": safe_path,
        "url": _safe_url(url),
        "sha256": safe_hash,
        "reusable": bool(reusable),
        "recorded_at": recorded_at or utc_now(),
    }


def _legacy_artifact(value: str) -> dict[str, Any]:
    lowered = value.casefold()
    artifact_type = "other"
    if "graph" in lowered:
        artifact_type = "graph"
    elif "report" in lowered or "diagnostic" in lowered:
        artifact_type = "report"
    elif "site" in lowered:
        artifact_type = "site"
    elif "artifact" in lowered or "export" in lowered:
        artifact_type = "export"
    return make_artifact(
        artifact_type,
        value,
        path=value if _safe_relative_path(value) else None,
        reusable=artifact_type in {"graph", "report", "export", "site"},
    )


def _legacy_error_class(value: str | None) -> str:
    lowered = (value or "").casefold()
    mappings = (
        ("permission", "github_api_permission"),
        ("rate", "rate_limit"),
        ("timeout", "timeout"),
        ("conflict", "branch_conflict"),
        ("security", "security_policy"),
        ("scientific", "scientific_review"),
        ("configuration", "configuration"),
        ("external", "external_service"),
        ("repository", "repository_state"),
        ("github", "github_api_transient"),
        ("validation", "validation"),
        ("schema", "validation"),
        ("content", "validation"),
        ("graph", "validation"),
        ("export", "validation"),
    )
    return next(
        (mapped for needle, mapped in mappings if needle in lowered),
        "unknown",
    )


def make_error(
    error_class: str,
    message: Any,
    *,
    phase: str,
    code: str | None = None,
    retryable: bool = False,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    if error_class not in ERROR_CLASSES:
        error_class = _legacy_error_class(error_class)
    safe_message, redacted = redact_text(message)
    safe_code = code or error_class
    if not _CODE_RE.fullmatch(safe_code):
        safe_code = "unknown_error"
    return {
        "class": error_class,
        "code": safe_code,
        "message": safe_message,
        "phase": _canonical_phase(phase),
        "occurred_at": occurred_at or utc_now(),
        "retryable": bool(retryable),
        "redacted": redacted,
    }


def make_recovery(
    level: str,
    action: Any,
    *,
    resume_phase: str | None,
    block_next_run: bool = True,
    new_content_required: bool = False,
    acknowledged: bool = False,
) -> dict[str, Any]:
    if level not in RECOVERY_LEVELS:
        raise ValueError(f"Unbekanntes Recovery-Level: {level}")
    safe_action, _changed = redact_text(action, limit=1000)
    return {
        "level": level,
        "action": safe_action,
        "resume_phase": _canonical_phase(resume_phase) if resume_phase else None,
        "block_next_run": bool(block_next_run),
        "new_content_required": bool(new_content_required),
        "acknowledged": bool(acknowledged),
    }


def _exact_keys(
    value: Any,
    *,
    required: set[str],
    label: str,
) -> list[str]:
    if not isinstance(value, dict):
        return [f"{label} muss ein Objekt sein"]
    errors = []
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required)
    if missing:
        errors.append(f"{label}: Pflichtfelder fehlen: {', '.join(missing)}")
    if unknown:
        errors.append(f"{label}: unbekannte Felder: {', '.join(unknown)}")
    return errors


def validate_status(status: Mapping[str, Any]) -> list[str]:
    """Validate all invariants needed before an atomic write."""

    required = {
        "schema_version",
        "run_id",
        "workflow",
        "revision",
        "previous_status",
        "status",
        "phase",
        "completed_phases",
        "created_at",
        "updated_at",
        "ended_at",
        "duration_seconds",
        "retention_until",
        "context",
        "metrics",
        "artifacts",
        "error",
        "recovery",
    }
    errors = _exact_keys(status, required=required, label="Status")
    if status.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version muss {SCHEMA_VERSION} sein")
    if not isinstance(status.get("run_id"), str) or not _RUN_ID_RE.fullmatch(
        status.get("run_id", "")
    ):
        errors.append("run_id ist nicht portabel oder leer")
    elif redact_text(status["run_id"], limit=128)[1]:
        errors.append("run_id enthält möglicherweise Zugangsdaten")
    if status.get("workflow") not in WORKFLOWS:
        errors.append("workflow ist nicht unterstützt")
    revision = status.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        errors.append("revision muss eine positive Ganzzahl sein")
    previous = status.get("previous_status")
    if previous is not None and previous not in STATUSES:
        errors.append("previous_status ist ungültig")
    state = status.get("status")
    if state not in STATUSES:
        errors.append("status ist ungültig")
    phase = status.get("phase")
    if phase not in PHASES:
        errors.append("phase ist ungültig")
    completed = status.get("completed_phases")
    if (
        not isinstance(completed, list)
        or any(item not in PHASES for item in completed)
        or len(completed) != len(set(completed))
    ):
        errors.append("completed_phases muss eindeutige bekannte Phasen enthalten")

    parsed_times: dict[str, datetime] = {}
    for field in ("created_at", "updated_at", "retention_until"):
        try:
            parsed_times[field] = _timestamp(status.get(field))
        except (TypeError, ValueError):
            errors.append(f"{field} muss ein ISO-8601-UTC-Zeitstempel sein")
    ended_at = status.get("ended_at")
    duration = status.get("duration_seconds")
    if state in FINAL_STATUSES:
        try:
            parsed_times["ended_at"] = _timestamp(ended_at)
        except (TypeError, ValueError):
            errors.append("Finalstatus benötigt ended_at")
        if (
            not isinstance(duration, (int, float))
            or isinstance(duration, bool)
            or not math.isfinite(duration)
            or duration < 0
        ):
            errors.append("Finalstatus benötigt eine nichtnegative duration_seconds")
    elif ended_at is not None or duration is not None:
        errors.append("Nicht finaler Status darf keine Endzeit oder Laufzeit besitzen")
    created = parsed_times.get("created_at")
    updated = parsed_times.get("updated_at")
    ended = parsed_times.get("ended_at")
    retention = parsed_times.get("retention_until")
    if created and updated and updated < created:
        errors.append("updated_at darf nicht vor created_at liegen")
    if created and ended and ended < created:
        errors.append("ended_at darf nicht vor created_at liegen")
    if ended and updated and updated < ended:
        errors.append("updated_at darf nicht vor ended_at liegen")
    if updated and retention and retention <= updated:
        errors.append("retention_until muss nach updated_at liegen")

    context_required = {
        "repository",
        "branch",
        "commit_sha",
        "pr_number",
        "pr_url",
        "workflow_run",
    }
    context = status.get("context")
    errors.extend(_exact_keys(context, required=context_required, label="context"))
    if isinstance(context, dict):
        repository = context.get("repository")
        if not isinstance(repository, str) or not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository
        ):
            errors.append("context.repository muss owner/name enthalten")
        elif redact_text(repository, limit=200)[1]:
            errors.append("context.repository enthält möglicherweise Zugangsdaten")
        branch = context.get("branch")
        if branch is not None and _safe_branch(branch) != branch:
            errors.append("context.branch ist ungültig oder enthält sensible Daten")
        commit = context.get("commit_sha")
        if commit is not None and (
            not isinstance(commit, str) or not _SHA_RE.fullmatch(commit)
        ):
            errors.append("context.commit_sha ist ungültig")
        pr_number = context.get("pr_number")
        if pr_number is not None and (
            not isinstance(pr_number, int)
            or isinstance(pr_number, bool)
            or pr_number < 1
        ):
            errors.append("context.pr_number ist ungültig")
        for field in ("pr_url",):
            value = context.get(field)
            if value is not None and _safe_url(value) != value:
                errors.append(f"context.{field} ist keine persistierbare HTTPS-URL")
        workflow_run = context.get("workflow_run")
        if workflow_run is not None:
            run_required = {"id", "attempt", "job_id", "url", "logs_url"}
            errors.extend(
                _exact_keys(
                    workflow_run,
                    required=run_required,
                    label="context.workflow_run",
                )
            )
            if isinstance(workflow_run, dict):
                if _integer(workflow_run.get("id")) != workflow_run.get("id"):
                    errors.append("context.workflow_run.id ist ungültig")
                if _integer(workflow_run.get("attempt")) != workflow_run.get("attempt"):
                    errors.append("context.workflow_run.attempt ist ungültig")
                job_id = workflow_run.get("job_id")
                if job_id is not None and (
                    not isinstance(job_id, str)
                    or not job_id
                    or len(job_id) > 200
                    or redact_text(job_id, limit=200)[0] != job_id
                ):
                    errors.append("context.workflow_run.job_id ist ungültig")
                run_url = workflow_run.get("url")
                if run_url is None or _safe_url(run_url) != run_url:
                    errors.append(
                        "context.workflow_run.url ist keine persistierbare URL"
                    )
                logs_url = workflow_run.get("logs_url")
                if logs_url is not None and _safe_url(logs_url) != logs_url:
                    errors.append(
                        "context.workflow_run.logs_url ist keine persistierbare URL"
                    )

    metrics = status.get("metrics")
    if not isinstance(metrics, dict) or len(metrics) > 128:
        errors.append("metrics muss ein begrenztes Objekt sein")
    else:
        try:
            json.dumps(metrics, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError):
            errors.append("metrics enthält keine reinen JSON-Werte")
        if _sanitize_json_value(metrics) != metrics:
            errors.append("metrics enthält nicht redigierte sensible Zeichenketten")

    artifacts = status.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) > 256:
        errors.append("artifacts muss eine begrenzte Liste sein")
    else:
        identities: list[tuple[Any, Any]] = []
        artifact_required = {
            "type",
            "value",
            "path",
            "url",
            "sha256",
            "reusable",
            "recorded_at",
        }
        for index, artifact in enumerate(artifacts):
            label = f"artifacts[{index}]"
            errors.extend(
                _exact_keys(artifact, required=artifact_required, label=label)
            )
            if not isinstance(artifact, dict):
                continue
            if artifact.get("type") not in ARTIFACT_TYPES:
                errors.append(f"{label}.type ist ungültig")
            value = artifact.get("value")
            if not isinstance(value, str) or not value or len(value) > 1000:
                errors.append(f"{label}.value ist ungültig")
            elif redact_text(value, limit=1000)[0] != value:
                errors.append(f"{label}.value enthält nicht redigierte Daten")
            path = artifact.get("path")
            if path is not None and _safe_relative_path(path) != path:
                errors.append(f"{label}.path ist kein sicherer relativer Pfad")
            url = artifact.get("url")
            if url is not None and _safe_url(url) != url:
                errors.append(f"{label}.url enthält Query, Fragment oder Credentials")
            sha256 = artifact.get("sha256")
            if sha256 is not None and (
                not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256)
            ):
                errors.append(f"{label}.sha256 ist ungültig")
            if not isinstance(artifact.get("reusable"), bool):
                errors.append(f"{label}.reusable muss boolesch sein")
            try:
                _timestamp(artifact.get("recorded_at"))
            except (TypeError, ValueError):
                errors.append(f"{label}.recorded_at ist ungültig")
            identities.append((artifact.get("type"), value))
        if len(identities) != len(set(identities)):
            errors.append("artifacts enthält doppelte Typ/Wert-Kombinationen")

    error = status.get("error")
    recovery = status.get("recovery")
    error_required = {
        "class",
        "code",
        "message",
        "phase",
        "occurred_at",
        "retryable",
        "redacted",
    }
    if error is not None:
        errors.extend(_exact_keys(error, required=error_required, label="error"))
        if isinstance(error, dict):
            if error.get("class") not in ERROR_CLASSES:
                errors.append("error.class ist ungültig")
            if not isinstance(error.get("code"), str) or not _CODE_RE.fullmatch(
                error.get("code", "")
            ):
                errors.append("error.code ist ungültig")
            message = error.get("message")
            if not isinstance(message, str) or not message or len(message) > 2000:
                errors.append("error.message ist ungültig")
            elif redact_text(message)[0] != message:
                errors.append("error.message enthält nicht redigierte Daten")
            if error.get("phase") not in PHASES:
                errors.append("error.phase ist ungültig")
            try:
                _timestamp(error.get("occurred_at"))
            except (TypeError, ValueError):
                errors.append("error.occurred_at ist ungültig")
            if not isinstance(error.get("retryable"), bool):
                errors.append("error.retryable muss boolesch sein")
            if not isinstance(error.get("redacted"), bool):
                errors.append("error.redacted muss boolesch sein")

    recovery_required = {
        "level",
        "action",
        "resume_phase",
        "block_next_run",
        "new_content_required",
        "acknowledged",
    }
    if recovery is not None:
        errors.extend(
            _exact_keys(recovery, required=recovery_required, label="recovery")
        )
        if isinstance(recovery, dict):
            if recovery.get("level") not in RECOVERY_LEVELS:
                errors.append("recovery.level ist ungültig")
            action = recovery.get("action")
            if not isinstance(action, str) or not action or len(action) > 1000:
                errors.append("recovery.action ist ungültig")
            elif redact_text(action, limit=1000)[0] != action:
                errors.append("recovery.action enthält nicht redigierte Daten")
            resume = recovery.get("resume_phase")
            if resume is not None and resume not in PHASES:
                errors.append("recovery.resume_phase ist ungültig")
            for field in (
                "block_next_run",
                "new_content_required",
                "acknowledged",
            ):
                if not isinstance(recovery.get(field), bool):
                    errors.append(f"recovery.{field} muss boolesch sein")

    if state in {"failed", "blocked", "recovering", "recovered"}:
        if error is None:
            errors.append(f"{state} benötigt ein strukturiertes error-Objekt")
        if recovery is None:
            errors.append(f"{state} benötigt ein strukturiertes recovery-Objekt")
    if state == "success" and (error is not None or recovery is not None):
        errors.append("success darf keine Fehler- oder Recovery-Daten enthalten")
    return list(dict.fromkeys(errors))


@contextmanager
def file_lock(
    target: Path,
    *,
    timeout_seconds: float = 5.0,
    stale_after_seconds: float = 120.0,
) -> Iterator[Path]:
    """Acquire a portable O_EXCL process lock next to ``target``."""

    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = target.with_name(f".{target.name}.lock")
    deadline = time.monotonic() + timeout_seconds
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                age = time.time() - lock.stat().st_mtime
                if age > stale_after_seconds:
                    lock.unlink()
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise LockTimeout(f"Status-Lock ist belegt: {lock}")
            time.sleep(0.02)
    try:
        os.write(
            descriptor,
            f"pid={os.getpid()} created={utc_now()}\n".encode("utf-8"),
        )
        os.fsync(descriptor)
        yield lock
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def _atomic_dump(path: Path, payload: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
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
        try:
            directory = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory = None
        if directory is not None:
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def read_status(path: Path) -> dict[str, Any]:
    """Read and validate one status document."""

    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AutomationStatusError(f"Statusdatei fehlt: {path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AutomationStatusError(f"Statusdatei ist kein gültiges UTF-8-JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise AutomationStatusError(f"Statusdatei muss ein JSON-Objekt sein: {path}")
    errors = validate_status(payload)
    if errors:
        raise AutomationStatusError("Ungültiger Status: " + "; ".join(errors))
    return payload


def restore_status_file(path: Path, source: Path) -> dict[str, Any]:
    """Atomically restore one previously validated, not-yet-published revision."""

    path = Path(path)
    source = Path(source)
    if path.resolve() == source.resolve():
        raise AutomationStatusError("Statusquelle und Statusziel müssen verschieden sein")
    payload = read_status(source)
    with file_lock(path):
        _atomic_dump(path, payload)
    return payload


def _new_status(
    workflow: str,
    *,
    run_id: str | None = None,
    phase: str = "initialize",
    context: Mapping[str, Any] | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    if workflow not in WORKFLOWS:
        raise ValueError(f"Unbekannter Workflow: {workflow}")
    timestamp = now or utc_now()
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": _portable_run_id(run_id),
        "workflow": workflow,
        "revision": 1,
        "previous_status": None,
        "status": "created",
        "phase": _canonical_phase(phase),
        "completed_phases": [],
        "created_at": timestamp,
        "updated_at": timestamp,
        "ended_at": None,
        "duration_seconds": None,
        "retention_until": _retention_until("created", timestamp),
        "context": dict(context or default_context()),
        "metrics": {},
        "artifacts": [],
        "error": None,
        "recovery": None,
    }


def _latest_candidate_is_newer(
    candidate: Mapping[str, Any],
    current: Mapping[str, Any],
) -> bool:
    """Return whether ``candidate`` may advance the canonical latest mirror."""

    if candidate["workflow"] != current["workflow"]:
        raise AutomationStatusError(
            "latest.json darf keine Statusläufe verschiedener Workflows mischen"
        )
    if candidate["run_id"] == current["run_id"]:
        candidate_revision = int(candidate["revision"])
        current_revision = int(current["revision"])
        if candidate_revision != current_revision:
            return candidate_revision > current_revision
        return _timestamp(candidate["updated_at"]) >= _timestamp(current["updated_at"])
    candidate_created = _timestamp(candidate["created_at"])
    current_created = _timestamp(current["created_at"])
    if candidate_created != current_created:
        return candidate_created > current_created
    # Millisecond timestamps can collide. A stable run-id tie-break makes all
    # writers converge on the same mirror instead of depending on lock order.
    return str(candidate["run_id"]) > str(current["run_id"])


def _replace_latest_if_newer(
    latest_path: Path,
    payload: Mapping[str, Any],
) -> bool:
    """Serialize and monotonically advance a workflow's ``latest.json``."""

    latest_path = Path(latest_path)
    with file_lock(latest_path):
        if latest_path.exists():
            current = read_status(latest_path)
            if not _latest_candidate_is_newer(payload, current):
                return False
        _atomic_dump(latest_path, payload)
    return True


def create_status_file(
    path: Path,
    workflow: str,
    *,
    run_id: str | None = None,
    phase: str = "initialize",
    context: Mapping[str, Any] | None = None,
    force: bool = False,
    latest_path: Path | None = None,
    diagnostic_paths: Sequence[Path] | None = None,
) -> dict[str, Any]:
    """Create a revision-one status and monotonically advance ``latest.json``."""

    path = Path(path)
    resolved_latest = Path(latest_path) if latest_path is not None else None
    if resolved_latest is not None and resolved_latest.resolve() == path.resolve():
        raise ValueError("Laufdatei und latest.json müssen verschieden sein")
    payload = _new_status(
        workflow,
        run_id=run_id,
        phase=phase,
        context=context,
    )
    errors = validate_status(payload)
    if errors:
        raise AutomationStatusError("Neuer Status ist ungültig: " + "; ".join(errors))
    with file_lock(path):
        if path.exists() and not force:
            raise AutomationStatusError(f"Status existiert bereits: {path}")
        _atomic_dump(path, payload)
        latest_updated = (
            _replace_latest_if_newer(resolved_latest, payload)
            if resolved_latest is not None
            else False
        )
        for diagnostic_path in diagnostic_paths or ():
            diagnostic_path = Path(diagnostic_path)
            if (
                resolved_latest is not None
                and diagnostic_path == resolved_latest.with_suffix(".md")
                and not latest_updated
            ):
                continue
            write_diagnostic(diagnostic_path, payload)
    return payload


def _merge_artifacts(
    existing: Sequence[Mapping[str, Any]],
    additions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for artifact in [*existing, *additions]:
        item = dict(artifact)
        merged[(str(item.get("type")), str(item.get("value")))] = item
    return list(merged.values())


def transition_status_file(
    path: Path,
    *,
    status: str | None = None,
    phase: str | None = None,
    expected_revision: int | None = None,
    metrics: Mapping[str, Any] | None = None,
    artifacts: Sequence[Mapping[str, Any]] | None = None,
    context: Mapping[str, Any] | None = None,
    error: Mapping[str, Any] | None | object = _UNSET,
    recovery: Mapping[str, Any] | None | object = _UNSET,
    complete_previous_phase: bool = True,
    latest_path: Path | None = None,
    diagnostic_paths: Sequence[Path] | None = None,
) -> dict[str, Any]:
    """Lock, revision-check, transition, validate and atomically replace."""

    path = Path(path)
    resolved_latest = Path(latest_path) if latest_path is not None else None
    if resolved_latest is not None and resolved_latest.resolve() == path.resolve():
        raise ValueError("Laufdatei und latest.json müssen verschieden sein")
    with file_lock(path):
        current = read_status(path)
        if expected_revision is not None and current["revision"] != expected_revision:
            raise RevisionConflict(
                f"Erwartete Revision {expected_revision}, vorhanden "
                f"{current['revision']} für {current['run_id']}"
            )
        next_status = _canonical_status(status or current["status"])
        if next_status not in ALLOWED_TRANSITIONS[current["status"]]:
            raise InvalidTransition(
                f"Unzulässiger Übergang {current['status']} → {next_status}"
            )
        next_phase = (
            _canonical_phase(phase, next_status) if phase is not None else current["phase"]
        )
        now = utc_now()
        payload = dict(current)
        payload["revision"] = current["revision"] + 1
        payload["previous_status"] = current["status"]
        payload["status"] = next_status
        payload["phase"] = next_phase
        payload["updated_at"] = now
        completed = list(current["completed_phases"])
        if (
            complete_previous_phase
            and next_phase != current["phase"]
            and current["status"] in {"running", "recovering", "recovered"}
            and current["phase"] not in completed
        ):
            completed.append(current["phase"])
        if next_status == "success" and next_phase not in completed:
            completed.append(next_phase)
        payload["completed_phases"] = completed
        if metrics is not None:
            payload["metrics"] = {
                **current["metrics"],
                **_sanitize_json_value(dict(metrics)),
            }
        if artifacts is not None:
            payload["artifacts"] = _merge_artifacts(current["artifacts"], artifacts)
        if context is not None:
            merged_context = {**current["context"], **dict(context)}
            payload["context"] = default_context(
                repository=merged_context.get("repository"),
                branch=merged_context.get("branch"),
                commit_sha=merged_context.get("commit_sha"),
                pr_number=merged_context.get("pr_number"),
                pr_url=merged_context.get("pr_url"),
            )
            if "workflow_run" in merged_context:
                payload["context"]["workflow_run"] = merged_context["workflow_run"]
        if error is not _UNSET:
            payload["error"] = None if error is None else dict(error)
        if recovery is not _UNSET:
            payload["recovery"] = None if recovery is None else dict(recovery)
        if next_status == "success":
            payload["error"] = None
            payload["recovery"] = None
        if next_status in FINAL_STATUSES:
            payload["ended_at"] = now
            payload["duration_seconds"] = _duration(payload["created_at"], now)
        else:
            payload["ended_at"] = None
            payload["duration_seconds"] = None
        payload["retention_until"] = _retention_until(next_status, now)

        errors = validate_status(payload)
        if errors:
            raise AutomationStatusError("Statusupdate ist ungültig: " + "; ".join(errors))
        _atomic_dump(path, payload)
        latest_updated = (
            _replace_latest_if_newer(resolved_latest, payload)
            if resolved_latest is not None
            else False
        )
        for diagnostic_path in diagnostic_paths or ():
            diagnostic_path = Path(diagnostic_path)
            if (
                resolved_latest is not None
                and diagnostic_path == resolved_latest.with_suffix(".md")
                and not latest_updated
            ):
                continue
            write_diagnostic(diagnostic_path, payload)
        return payload


def recovery_from_artifacts(
    status: Mapping[str, Any],
) -> tuple[str, str, bool]:
    """Return recovery level, action and whether new content is required."""

    artifacts = [
        artifact
        for artifact in status.get("artifacts", [])
        if isinstance(artifact, dict) and artifact.get("reusable") is True
    ]
    priority = {"pull_request": 4, "commit": 3, "branch": 2, "graph": 1, "export": 1}
    candidate = max(
        artifacts,
        key=lambda artifact: priority.get(str(artifact.get("type")), 0),
        default=None,
    )
    phase = status.get("phase") or "initialize"
    if candidate is None:
        return (
            "retry_same_phase",
            f"Phase {phase} idempotent mit derselben run_id erneut ausführen.",
            False,
        )
    artifact_type = candidate["type"]
    value = candidate["value"]
    if artifact_type == "pull_request":
        action = f"Vorhandenen Pull Request {value} prüfen und weiterverwenden."
    elif artifact_type == "commit":
        action = f"Vorhandenen Commit {value} weiterverwenden; nur Push/PR fortsetzen."
    elif artifact_type == "branch":
        action = f"Vorhandenen Branch {value} auschecken und reparieren/fortsetzen."
    else:
        action = f"Vorhandenes Artefakt {value} weiterverwenden und Export fortsetzen."
    return "resume_from_artifact", action, False


def blocks_new_run(status: Mapping[str, Any]) -> bool:
    """Whether starting a second content-producing run is unsafe."""

    state = status.get("status")
    if state in {"created", "running", "recovering"}:
        return True
    recovery = status.get("recovery")
    return bool(
        state in {"failed", "blocked", "recovered"}
        and isinstance(recovery, dict)
        and recovery.get("block_next_run") is True
        and recovery.get("acknowledged") is not True
    )


class StatusStore:
    """Canonical ``automation/status`` store with a validated latest mirror."""

    def __init__(self, root: Path = DEFAULT_STATUS_ROOT) -> None:
        self.root = Path(root)

    def workflow_dir(self, workflow: str) -> Path:
        if workflow not in WORKFLOWS:
            raise ValueError(f"Unbekannter Workflow: {workflow}")
        return self.root / workflow

    def path_for(self, workflow: str, run_id: str) -> Path:
        return self.workflow_dir(workflow) / f"{_portable_run_id(run_id)}.json"

    def latest_path(self, workflow: str) -> Path:
        return self.workflow_dir(workflow) / "latest.json"

    def guard_path(self, workflow: str) -> Path:
        return self.workflow_dir(workflow) / ".workflow-guard"

    def resolve(
        self,
        *,
        workflow: str | None,
        run_id: str | None,
        latest: bool = False,
    ) -> Path:
        if latest:
            if workflow is None:
                raise ValueError("--latest benötigt --workflow")
            return self.latest_path(workflow)
        if run_id is None:
            raise ValueError("run_id fehlt")
        if workflow is not None:
            return self.path_for(workflow, run_id)
        matches = list(self.root.glob(f"*/{_portable_run_id(run_id)}.json"))
        if len(matches) != 1:
            raise AutomationStatusError(
                f"run_id {run_id} ist nicht eindeutig auffindbar ({len(matches)} Treffer)"
            )
        return matches[0]

    def start(
        self,
        workflow: str,
        *,
        run_id: str | None = None,
        phase: str = "initialize",
        context: Mapping[str, Any] | None = None,
        check_previous: bool = True,
    ) -> dict[str, Any]:
        resolved_run_id = _portable_run_id(run_id)
        with file_lock(self.guard_path(workflow)):
            latest = self.latest_path(workflow)
            if check_previous and latest.exists():
                previous = read_status(latest)
                if previous.get("run_id") != resolved_run_id and blocks_new_run(previous):
                    raise UnresolvedPreviousRun(previous)
            payload = create_status_file(
                self.path_for(workflow, resolved_run_id),
                workflow,
                run_id=resolved_run_id,
                phase=phase,
                context=context,
                latest_path=latest,
                diagnostic_paths=[
                    self.path_for(workflow, resolved_run_id).with_suffix(".md"),
                    latest.with_suffix(".md"),
                ],
            )
            return payload

    def update(
        self,
        workflow: str,
        run_id: str,
        **changes: Any,
    ) -> dict[str, Any]:
        run_path = self.path_for(workflow, run_id)
        latest_path = self.latest_path(workflow)
        with file_lock(self.guard_path(workflow)):
            mirror_latest = True
            if latest_path.exists():
                latest = read_status(latest_path)
                mirror_latest = latest["run_id"] == _portable_run_id(run_id)
            diagnostics = [run_path.with_suffix(".md")]
            if mirror_latest:
                diagnostics.append(latest_path.with_suffix(".md"))
            return transition_status_file(
                run_path,
                latest_path=latest_path if mirror_latest else None,
                diagnostic_paths=diagnostics,
                **changes,
            )

    def artifact(
        self,
        workflow: str,
        run_id: str,
        artifact: Mapping[str, Any],
        *,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        return self.update(
            workflow,
            run_id,
            artifacts=[artifact],
            expected_revision=expected_revision,
            complete_previous_phase=False,
        )

    def fail(
        self,
        workflow: str,
        run_id: str,
        *,
        error_class: str,
        message: Any,
        code: str | None = None,
        phase: str | None = None,
        recovery_level: str | None = None,
        recovery_action: str | None = None,
        retryable: bool = False,
        block_next_run: bool = True,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        current = read_status(self.path_for(workflow, run_id))
        failure_phase = _canonical_phase(phase or current["phase"])
        inferred_level, inferred_action, new_content = recovery_from_artifacts(current)
        level = recovery_level or inferred_level
        action = recovery_action or inferred_action
        error = make_error(
            error_class,
            message,
            phase=failure_phase,
            code=code,
            retryable=retryable,
        )
        recovery = make_recovery(
            level,
            action,
            resume_phase=failure_phase,
            block_next_run=block_next_run,
            new_content_required=new_content,
        )
        final_state = "blocked" if level in {"manual_intervention", "terminal_failure"} else "failed"
        return self.update(
            workflow,
            run_id,
            status=final_state,
            phase=failure_phase,
            error=error,
            recovery=recovery,
            expected_revision=expected_revision,
            complete_previous_phase=False,
        )

    def begin_recovery(
        self,
        workflow: str,
        run_id: str,
        *,
        phase: str | None = None,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        current = read_status(self.path_for(workflow, run_id))
        if not isinstance(current.get("recovery"), dict):
            raise InvalidTransition("Recovery benötigt einen vorherigen Fehlerstatus")
        recovery = dict(current["recovery"])
        recovery["acknowledged"] = True
        return self.update(
            workflow,
            run_id,
            status="recovering",
            phase=phase or recovery.get("resume_phase") or current["phase"],
            recovery=recovery,
            expected_revision=expected_revision,
            complete_previous_phase=False,
        )

    def mark_recovered(
        self,
        workflow: str,
        run_id: str,
        *,
        phase: str | None = None,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        current = read_status(self.path_for(workflow, run_id))
        if not isinstance(current.get("recovery"), dict):
            raise InvalidTransition("Recovered benötigt Recovery-Metadaten")
        recovery = dict(current["recovery"])
        recovery["block_next_run"] = False
        recovery["acknowledged"] = True
        return self.update(
            workflow,
            run_id,
            status="recovered",
            phase=phase or current["phase"],
            recovery=recovery,
            expected_revision=expected_revision,
        )

    def acknowledge(
        self,
        workflow: str,
        run_id: str,
        *,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        current = read_status(self.path_for(workflow, run_id))
        recovery = current.get("recovery")
        if not isinstance(recovery, dict):
            raise InvalidTransition("Status besitzt keinen quittierbaren Recovery-Blocker")
        updated = dict(recovery)
        updated["acknowledged"] = True
        updated["block_next_run"] = False
        return self.update(
            workflow,
            run_id,
            recovery=updated,
            expected_revision=expected_revision,
            complete_previous_phase=False,
        )


def render_diagnostic(status: Mapping[str, Any]) -> str:
    """Render the complete human recovery message required by the scheduler."""

    state = str(status.get("status") or "unknown")
    heading = (
        "ADHS-Automation erfolgreich"
        if state == "success"
        else "ADHS-Automation fehlgeschlagen"
        if state in {"failed", "blocked"}
        else "ADHS-Automation – Laufstatus"
    )
    completed = status.get("completed_phases")
    completed_label = (
        ", ".join(str(item) for item in completed)
        if isinstance(completed, list) and completed
        else "noch keine abgeschlossene Phase"
    )
    reusable = [
        f"{item.get('type')}: {item.get('value')}"
        for item in status.get("artifacts", [])
        if isinstance(item, dict) and item.get("reusable") is True
    ]
    context = status.get("context") if isinstance(status.get("context"), dict) else {}
    if context.get("branch"):
        reusable.insert(0, f"Branch: {context['branch']}")
    if context.get("commit_sha"):
        reusable.append(f"Commit: {context['commit_sha']}")
    if context.get("pr_number"):
        reusable.append(f"PR: #{context['pr_number']}")
    error = status.get("error") if isinstance(status.get("error"), dict) else {}
    recovery = (
        status.get("recovery") if isinstance(status.get("recovery"), dict) else {}
    )
    lines = [
        heading,
        f"Lauf: {status.get('workflow', 'unbekannt')}/{status.get('run_id', 'unbekannt')}",
        f"Status: {state}",
        f"Phase: {status.get('phase', 'unbekannt')}",
        f"Revision: {status.get('revision', 'unbekannt')}",
        f"Erfolgreich: {completed_label}",
        f"Vorhanden: {', '.join(reusable) if reusable else 'keine wiederverwendbaren Artefakte'}",
    ]
    if error:
        lines.extend(
            [
                f"Fehlerklasse: {error.get('class', 'unknown')}",
                f"Fehlercode: {error.get('code', 'unknown_error')}",
                f"Fehler: {error.get('message', 'Keine Detailmeldung verfügbar.')}",
            ]
        )
    if recovery:
        lines.extend(
            [
                f"Recovery-Level: {recovery.get('level', 'unbekannt')}",
                f"Recovery: {recovery.get('action', 'Diagnosebericht prüfen.')}",
                "Neuer Inhalt erforderlich: "
                + ("ja" if recovery.get("new_content_required") else "nein"),
                "Blockiert nächsten Generatorlauf: "
                + ("ja" if blocks_new_run(status) else "nein"),
            ]
        )
    return "\n".join(lines) + "\n"


def write_diagnostic(path: Path, status: Mapping[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = render_diagnostic(status)
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return path


def prune_statuses(
    root: Path,
    *,
    retention_days: int | None = None,
    max_per_workflow: int = 100,
    now: datetime | None = None,
) -> list[Path]:
    """Delete expired run snapshots, never ``latest.json``."""

    root = Path(root)
    current_time = now or datetime.now(timezone.utc)
    removed: list[Path] = []
    for workflow_dir in sorted(path for path in root.glob("*") if path.is_dir()):
        runs: list[tuple[datetime, Path]] = []
        for path in sorted(workflow_dir.glob("*.json")):
            if path.name == "latest.json":
                continue
            try:
                status = read_status(path)
                expiry = (
                    _timestamp(status["updated_at"]) + timedelta(days=retention_days)
                    if retention_days is not None
                    else _timestamp(status["retention_until"])
                )
                runs.append((_timestamp(status["created_at"]), path))
            except AutomationStatusError:
                # Corrupt files are retained for manual forensic inspection.
                continue
            if expiry <= current_time:
                path.unlink()
                diagnostic = path.with_suffix(".md")
                if diagnostic.exists():
                    diagnostic.unlink()
                removed.append(path)
        remaining = [
            item for item in runs
            if item[1].exists()
        ]
        for _created, path in sorted(remaining, reverse=True)[max_per_workflow:]:
            path.unlink()
            diagnostic = path.with_suffix(".md")
            if diagnostic.exists():
                diagnostic.unlink()
            removed.append(path)
    return removed


def status_exit_code(status: Mapping[str, Any]) -> int:
    if status.get("status") == "success":
        return EXIT_SUCCESS
    recovery = status.get("recovery")
    if isinstance(recovery, dict) and recovery.get("level") in {
        "manual_intervention",
        "terminal_failure",
    }:
        return EXIT_MANUAL
    if blocks_new_run(status) or status.get("status") in {"failed", "blocked"}:
        return EXIT_BLOCKED
    return EXIT_CONTINUE


# ---------------------------------------------------------------------------
# Compatibility interface for the existing graph/export runtime file.


def status_is_managed(env: Mapping[str, str] | None = None) -> bool:
    values = os.environ if env is None else env
    return values.get("RUNTIME_STATUS_MANAGED", "").strip().lower() in _TRUE_VALUES


def start_run(
    path: Path,
    workflow: str,
    *,
    phase: str = "initialize",
    git_sha: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    return create_status_file(
        Path(path),
        workflow,
        run_id=run_id,
        phase=_canonical_phase(phase),
        context=default_context(commit_sha=git_sha),
        force=True,
    )


def _read_status(path: Path) -> dict[str, Any]:
    try:
        return read_status(path)
    except AutomationStatusError:
        return {}


def update_status(
    path: Path,
    *,
    status: str | None = None,
    phase: str | None = None,
    workflow: str | None = None,
    run_id: str | None = None,
    git_sha: str | None = None,
    metrics: Mapping[str, Any] | None = None,
    artifacts: Sequence[str] | None = None,
    error_class: str | None | object = _UNSET,
    error_message: str | None | object = _UNSET,
    recovery_action: str | None | object = _UNSET,
) -> dict[str, Any]:
    target = Path(path)
    if not target.exists() or not _read_status(target):
        start_run(
            target,
            workflow or "knowledge-graph",
            phase=phase or "initialize",
            git_sha=git_sha,
            run_id=run_id,
        )
    current = read_status(target)
    changes: dict[str, Any] = {
        "status": _canonical_status(status or current["status"]),
        "phase": _canonical_phase(phase, _canonical_status(status or current["status"]))
        if phase is not None
        else None,
        "metrics": metrics,
        "artifacts": [_legacy_artifact(value) for value in artifacts or []] or None,
    }
    if git_sha is not None:
        changes["context"] = {"commit_sha": _git_sha(git_sha)}
    next_status = changes["status"]
    if next_status in {"failed", "blocked"} or any(
        value is not _UNSET
        for value in (error_class, error_message, recovery_action)
    ):
        failure_phase = changes["phase"] or current["phase"]
        legacy_class = None if error_class is _UNSET else str(error_class or "unknown")
        legacy_message = (
            "Automation fehlgeschlagen ohne Detailmeldung"
            if error_message is _UNSET
            else error_message
        )
        action = (
            "Protokoll prüfen und denselben Lauf fortsetzen."
            if recovery_action is _UNSET
            else recovery_action
        )
        level, inferred, new_content = recovery_from_artifacts(current)
        changes["error"] = make_error(
            _legacy_error_class(legacy_class),
            legacy_message,
            phase=failure_phase,
            code=re.sub(r"[^A-Za-z0-9_.-]+", "_", legacy_class or "unknown_error")[:120],
            retryable=level != "terminal_failure",
        )
        changes["recovery"] = make_recovery(
            level,
            action or inferred,
            resume_phase=failure_phase,
            new_content_required=new_content,
        )
    return transition_status_file(
        target,
        **{key: value for key, value in changes.items() if value is not None},
    )


def finish_run(
    path: Path,
    *,
    success: bool,
    phase: str | None = None,
    metrics: Mapping[str, Any] | None = None,
    artifacts: Sequence[str] | None = None,
    error_class: str | None = None,
    error_message: str | None = None,
    recovery_action: str | None = None,
) -> dict[str, Any]:
    target = Path(path)
    if not target.exists() or not _read_status(target):
        start_run(target, "manual")
    current = read_status(target)
    if current["status"] == "created":
        current = transition_status_file(
            target,
            status="running",
            phase=current["phase"],
            complete_previous_phase=False,
        )
    if success:
        return transition_status_file(
            target,
            status="success",
            phase=_canonical_phase(phase or "complete", "success"),
            metrics=metrics,
            artifacts=[_legacy_artifact(value) for value in artifacts or []] or None,
            error=None,
            recovery=None,
        )
    failure_phase = _canonical_phase(phase or current["phase"], "failed")
    level, inferred, new_content = recovery_from_artifacts(current)
    return transition_status_file(
        target,
        status="failed",
        phase=failure_phase,
        metrics=metrics,
        artifacts=[_legacy_artifact(value) for value in artifacts or []] or None,
        error=make_error(
            _legacy_error_class(error_class),
            error_message or "Automation fehlgeschlagen ohne Detailmeldung",
            phase=failure_phase,
            code=re.sub(
                r"[^A-Za-z0-9_.-]+",
                "_",
                error_class or "unknown_error",
            )[:120],
            retryable=True,
        ),
        recovery=make_recovery(
            level,
            recovery_action or inferred,
            resume_phase=failure_phase,
            new_content_required=new_content,
        ),
        complete_previous_phase=False,
    )


def write_status(path: Path, status: Mapping[str, Any]) -> dict[str, Any]:
    """Compatibility normalizer for callers that previously passed partial data."""

    workflow = status.get("workflow")
    if workflow not in WORKFLOWS:
        workflow = "knowledge-graph"
    created = start_run(
        path,
        str(workflow),
        phase=_canonical_phase(status.get("phase")),
        git_sha=status.get("git_sha"),
        run_id=status.get("run_id"),
    )
    requested = _canonical_status(status.get("status"))
    if requested == "created" and not status.get("metrics") and not status.get("artifacts"):
        return created
    if requested in {"failed", "blocked"}:
        return finish_run(
            path,
            success=False,
            phase=_canonical_phase(status.get("phase"), requested),
            metrics=status.get("metrics") if isinstance(status.get("metrics"), dict) else None,
            artifacts=[
                str(value) for value in status.get("artifacts", [])
            ] if isinstance(status.get("artifacts"), list) else None,
            error_class=str(status.get("error_class") or "unknown_error"),
            error_message=str(
                status.get("error_message")
                or "Automation fehlgeschlagen ohne Detailmeldung"
            ),
            recovery_action=str(
                status.get("recovery_action")
                or "Protokoll prüfen und denselben Lauf fortsetzen."
            ),
        )
    return transition_status_file(
        Path(path),
        status=requested,
        phase=_canonical_phase(status.get("phase"), requested),
        metrics=status.get("metrics") if isinstance(status.get("metrics"), dict) else None,
        artifacts=[
            _legacy_artifact(str(value)) for value in status.get("artifacts", [])
        ] if isinstance(status.get("artifacts"), list) else None,
    )


# ---------------------------------------------------------------------------
# New subcommand CLI.


def _add_locator(parser: argparse.ArgumentParser, *, latest: bool = False) -> None:
    parser.add_argument("--root", type=Path, default=cli_status_root())
    parser.add_argument("--workflow", choices=sorted(WORKFLOWS), required=True)
    if not latest:
        parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-revision", type=int, default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="neuen kanonischen Lauf starten")
    start.add_argument("--root", type=Path, default=cli_status_root())
    start.add_argument("--workflow", choices=sorted(WORKFLOWS), required=True)
    start.add_argument("--run-id", default=None)
    start.add_argument("--phase", choices=sorted(PHASES), default="initialize")
    start.add_argument("--repository", default=None)
    start.add_argument("--branch", default=None)
    start.add_argument("--commit", default=None)
    start.add_argument("--pr-number", type=int, default=None)
    start.add_argument("--pr-url", default=None)
    start.add_argument("--allow-unresolved", action="store_true")

    phase = subparsers.add_parser("phase", help="Phase desselben Laufs aktualisieren")
    _add_locator(phase)
    phase.add_argument("--phase", choices=sorted(PHASES), required=True)
    phase.add_argument("--metric", action="append", default=[])

    artifact = subparsers.add_parser("artifact", help="Artefakt registrieren")
    _add_locator(artifact)
    artifact.add_argument("--type", choices=sorted(ARTIFACT_TYPES), required=True)
    artifact.add_argument("--value", required=True)
    artifact.add_argument("--path", default=None)
    artifact.add_argument("--url", default=None)
    artifact.add_argument("--sha256", default=None)
    artifact.add_argument("--reusable", action=argparse.BooleanOptionalAction, default=False)

    fail = subparsers.add_parser("fail", help="Fehler und Recovery atomar erfassen")
    _add_locator(fail)
    fail.add_argument("--class", dest="error_class", choices=sorted(ERROR_CLASSES), required=True)
    fail.add_argument("--code", default=None)
    fail.add_argument("--message", required=True)
    fail.add_argument("--phase", choices=sorted(PHASES), default=None)
    fail.add_argument("--recovery", choices=sorted(RECOVERY_LEVELS), default=None)
    fail.add_argument("--action", default=None)
    fail.add_argument("--retryable", action=argparse.BooleanOptionalAction, default=False)
    fail.add_argument("--block-next-run", action=argparse.BooleanOptionalAction, default=True)

    recover = subparsers.add_parser("recover", help="Wiederaufnahme desselben Laufs beginnen")
    _add_locator(recover)
    recover.add_argument("--phase", choices=sorted(PHASES), default=None)
    recover.add_argument("--completed", action="store_true")

    finish = subparsers.add_parser("finish", help="Lauf erfolgreich abschließen")
    _add_locator(finish)
    finish.add_argument("--phase", choices=sorted(PHASES), default="complete")

    acknowledge = subparsers.add_parser(
        "acknowledge",
        help="manuellen/terminalen Blocker quittieren",
    )
    _add_locator(acknowledge)

    inspect = subparsers.add_parser("inspect", help="Status und Diagnose ausgeben")
    inspect.add_argument("--root", type=Path, default=cli_status_root())
    inspect.add_argument("--workflow", choices=sorted(WORKFLOWS), required=True)
    inspect_group = inspect.add_mutually_exclusive_group(required=True)
    inspect_group.add_argument("--run-id")
    inspect_group.add_argument("--latest", action="store_true")
    inspect.add_argument("--json", action="store_true")
    inspect.add_argument("--report", type=Path, default=None)

    guard = subparsers.add_parser("guard", help="ungeklärten Vorgängerlauf prüfen")
    guard.add_argument("--root", type=Path, default=cli_status_root())
    guard.add_argument("--workflow", choices=sorted(WORKFLOWS), required=True)

    prune = subparsers.add_parser("prune", help="Retention kontrolliert anwenden")
    prune.add_argument("--root", type=Path, default=cli_status_root())
    prune.add_argument("--retention-days", type=int, default=None)
    prune.add_argument("--max-per-workflow", type=int, default=100)
    return parser


def _parse_metrics(values: Sequence[str]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--metric erwartet KEY=JSON_VALUE")
        key, raw = value.split("=", 1)
        if not key:
            raise ValueError("Metrikschlüssel darf nicht leer sein")
        try:
            metrics[key] = json.loads(raw)
        except json.JSONDecodeError:
            metrics[key] = raw
    return metrics


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        store = StatusStore(args.root)
        if args.command == "start":
            payload = store.start(
                args.workflow,
                run_id=args.run_id,
                phase=args.phase,
                context=default_context(
                    repository=args.repository,
                    branch=args.branch,
                    commit_sha=args.commit,
                    pr_number=args.pr_number,
                    pr_url=args.pr_url,
                ),
                check_previous=not args.allow_unresolved,
            )
        elif args.command == "phase":
            payload = store.update(
                args.workflow,
                args.run_id,
                status="running",
                phase=args.phase,
                metrics=_parse_metrics(args.metric) or None,
                expected_revision=args.expected_revision,
            )
        elif args.command == "artifact":
            payload = store.artifact(
                args.workflow,
                args.run_id,
                make_artifact(
                    args.type,
                    args.value,
                    path=args.path,
                    url=args.url,
                    sha256=args.sha256,
                    reusable=args.reusable,
                ),
                expected_revision=args.expected_revision,
            )
        elif args.command == "fail":
            payload = store.fail(
                args.workflow,
                args.run_id,
                error_class=args.error_class,
                code=args.code,
                message=args.message,
                phase=args.phase,
                recovery_level=args.recovery,
                recovery_action=args.action,
                retryable=args.retryable,
                block_next_run=args.block_next_run,
                expected_revision=args.expected_revision,
            )
        elif args.command == "recover":
            if args.completed:
                payload = store.mark_recovered(
                    args.workflow,
                    args.run_id,
                    phase=args.phase,
                    expected_revision=args.expected_revision,
                )
            else:
                payload = store.begin_recovery(
                    args.workflow,
                    args.run_id,
                    phase=args.phase,
                    expected_revision=args.expected_revision,
                )
        elif args.command == "finish":
            payload = store.update(
                args.workflow,
                args.run_id,
                status="success",
                phase=args.phase,
                expected_revision=args.expected_revision,
            )
        elif args.command == "acknowledge":
            payload = store.acknowledge(
                args.workflow,
                args.run_id,
                expected_revision=args.expected_revision,
            )
        elif args.command == "inspect":
            path = store.resolve(
                workflow=args.workflow,
                run_id=args.run_id,
                latest=args.latest,
            )
            payload = read_status(path)
            if args.report:
                write_diagnostic(args.report, payload)
            if args.json:
                json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
                sys.stdout.write("\n")
            else:
                print(render_diagnostic(payload), end="")
            return status_exit_code(payload)
        elif args.command == "guard":
            latest = store.latest_path(args.workflow)
            if not latest.exists():
                print("Kein Vorgängerlauf vorhanden.")
                return EXIT_SUCCESS
            payload = read_status(latest)
            print(render_diagnostic(payload), end="")
            return EXIT_BLOCKED if blocks_new_run(payload) else EXIT_SUCCESS
        elif args.command == "prune":
            removed = prune_statuses(
                args.root,
                retention_days=args.retention_days,
                max_per_workflow=args.max_per_workflow,
            )
            for path in removed:
                print(path)
            print(f"Entfernte Statusläufe: {len(removed)}")
            return EXIT_SUCCESS
        else:  # pragma: no cover - argparse prevents this branch.
            raise AssertionError(args.command)
    except (AutomationStatusError, ValueError) as exc:
        print(f"Automation-Status: {exc}", file=sys.stderr)
        if isinstance(exc, UnresolvedPreviousRun):
            print(render_diagnostic(exc.status), file=sys.stderr, end="")
            return EXIT_BLOCKED
        if isinstance(exc, (InvalidTransition, RevisionConflict, LockTimeout)):
            return EXIT_BLOCKED
        return EXIT_MANUAL

    print(render_diagnostic(payload), end="")
    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
