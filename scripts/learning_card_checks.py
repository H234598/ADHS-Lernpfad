"""Fail-closed Aggregation der Lernkarten-Subgates."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

from learning_card_scope import ScopeDecision

REQUIRED_POLICY_CHECKS = (
    "Validate and build",
    "Build all download formats",
    "CodeRabbit review gate (blocking)",
)
FAILURES = {
    "action_required",
    "cancelled",
    "failure",
    "stale",
    "startup_failure",
    "timed_out",
}
PENDING = {"", "neutral", "skipped"}


@dataclass(frozen=True)
class PolicyDecision:
    """Ergebnis von Semantik-, Build- und Manual-Merge-Vertrag."""

    head_sha: str
    passed: bool
    subgates: dict[str, str]
    required_checks: dict[str, dict[str, str]]
    manual_merge_required: bool
    reasons: tuple[str, ...]


def _creation_key(run: dict[str, Any]) -> tuple[str, int]:
    """GitHubs monotone Erzeugungsreihenfolge eines Check-Runs abbilden."""

    return (
        str(run.get("created_at") or ""),
        int(run.get("id") or 0),
    )


def select_latest_check_runs(
    check_runs: Iterable[dict[str, Any]],
    *,
    head_sha: str,
    names: set[str],
) -> dict[str, dict[str, Any]]:
    """Nur den neuesten Lauf je exaktem Namen und aktuellem Head wählen."""

    latest: dict[str, dict[str, Any]] = {}
    for run in check_runs:
        if not isinstance(run, dict):
            continue
        name = str(run.get("name") or "")
        if name not in names or str(run.get("head_sha") or "") != head_sha:
            continue
        current = latest.get(name)
        if current is None or _creation_key(run) >= _creation_key(current):
            latest[name] = run
    return latest


def _state(run: dict[str, Any] | None) -> str:
    if run is None:
        return "missing"
    if str(run.get("status") or "").casefold() != "completed":
        return "pending"
    conclusion = str(run.get("conclusion") or "").casefold()
    if conclusion == "success":
        return "success"
    if conclusion in PENDING:
        return "pending"
    if conclusion in FAILURES:
        return "failure"
    return "failure"


def _build_state(first: str, second: str) -> str:
    states = {first, second}
    for candidate in ("failure", "missing", "pending"):
        if candidate in states:
            return candidate
    return "success"


def _summary(run: dict[str, Any] | None) -> dict[str, str]:
    return {
        "state": _state(run),
        "url": "" if run is None else str(run.get("html_url") or ""),
        "completed_at": (
            "" if run is None else str(run.get("completed_at") or "")
        ),
    }


def evaluate_policy(
    *,
    scope: ScopeDecision,
    check_runs: list[dict[str, Any]],
    head_sha: str,
) -> PolicyDecision:
    """Anwendbare Subgates aggregieren, ohne Scheinstatus zu erzeugen."""

    if not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        raise ValueError("head_sha muss ein vollständiger Git-SHA sein")
    marker_missing = (
        scope.manual_merge_required and not scope.manual_merge_marker
    )
    reasons = list(scope.reasons)
    if marker_missing:
        reasons.append(
            "Automations- oder sicherheitssensitive Dateien sind betroffen, "
            "aber der Marker manual-merge-required fehlt."
        )

    if not scope.requires_semantic_review:
        return PolicyDecision(
            head_sha=head_sha,
            passed=not marker_missing,
            subgates={
                "content_scope": "not_applicable",
                "claim_source_entailment": "not_applicable",
                "complete_build": "not_applicable",
            },
            required_checks={},
            manual_merge_required=scope.manual_merge_required,
            reasons=tuple(reasons),
        )

    selected = select_latest_check_runs(
        check_runs,
        head_sha=head_sha,
        names=set(REQUIRED_POLICY_CHECKS),
    )
    review = _state(selected.get("CodeRabbit review gate (blocking)"))
    complete = _build_state(
        _state(selected.get("Validate and build")),
        _state(selected.get("Build all download formats")),
    )
    subgates = {
        "content_scope": review,
        "claim_source_entailment": review,
        "complete_build": complete,
    }
    reasons.extend(
        f"Subgate {name} ist {state}."
        for name, state in subgates.items()
        if state != "success"
    )
    return PolicyDecision(
        head_sha=head_sha,
        passed=(
            all(state == "success" for state in subgates.values())
            and not marker_missing
        ),
        subgates=subgates,
        required_checks={
            name: _summary(selected.get(name))
            for name in REQUIRED_POLICY_CHECKS
        },
        manual_merge_required=scope.manual_merge_required,
        reasons=tuple(reasons),
    )
