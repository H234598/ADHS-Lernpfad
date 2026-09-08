#!/usr/bin/env python3
"""Pure reconciliation decisions for externally closed automated unit PRs.

The module deliberately contains no GitHub or filesystem writes.  It reduces a
canonical generator status, a closed pull-request snapshot and the current
head's check-runs to an explicit action.  Persistence is handled separately so
that CAS semantics remain testable and fail-closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Iterable, Mapping


REQUIRED_CHECKS = (
    "Validate and build",
    "Build all download formats",
    "Remark lint (blocking)",
    "CodeRabbit review gate (blocking)",
    "Learning card policy (blocking)",
)
FINAL_STATES = {"success", "blocked", "failed", "recovered"}
UNIT_MARKER = "<!-- adhs-daily-unit -->"
UNIT_BRANCH_RE = re.compile(r"^agent/einheit-[A-Za-z0-9._/-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class ReconciliationDecision:
    """Side-effect-free decision for a closed unit pull request."""

    action: str
    passed: bool
    code: str
    merge_sha: str | None
    required_checks: dict[str, dict[str, str]]
    reasons: tuple[str, ...]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _creation_key(run: Mapping[str, Any]) -> tuple[str, int]:
    return str(run.get("created_at") or ""), int(run.get("id") or 0)


def select_latest_required_checks(
    check_runs: Iterable[Mapping[str, Any]],
    *,
    head_sha: str,
) -> dict[str, Mapping[str, Any]]:
    """Select the latest exact required check for the evaluated PR head."""

    latest: dict[str, Mapping[str, Any]] = {}
    for run in check_runs:
        name = str(run.get("name") or "")
        if name not in REQUIRED_CHECKS:
            continue
        if str(run.get("head_sha") or "") != head_sha:
            continue
        current = latest.get(name)
        if current is None or _creation_key(run) >= _creation_key(current):
            latest[name] = run
    return latest


def _check_summary(run: Mapping[str, Any] | None) -> dict[str, str]:
    if run is None:
        return {
            "state": "missing",
            "created_at": "",
            "completed_at": "",
            "url": "",
        }
    completed = str(run.get("status") or "").casefold() == "completed"
    conclusion = str(run.get("conclusion") or "").casefold()
    state = "success" if completed and conclusion == "success" else (
        "pending" if not completed else "failure"
    )
    return {
        "state": state,
        "created_at": str(run.get("created_at") or ""),
        "completed_at": str(run.get("completed_at") or ""),
        "url": str(run.get("html_url") or ""),
    }


def _ignore(code: str, *, passed: bool = False, reason: str) -> ReconciliationDecision:
    return ReconciliationDecision(
        action="ignore",
        passed=passed,
        code=code,
        merge_sha=None,
        required_checks={},
        reasons=(reason,),
    )


def _matches_status(status: Mapping[str, Any], pull: Mapping[str, Any]) -> bool:
    context = _mapping(status.get("context"))
    head = _mapping(pull.get("head"))
    base = _mapping(pull.get("base"))
    branch = str(context.get("branch") or "")
    return (
        status.get("workflow") == "generator"
        and int(context.get("pr_number") or 0) == int(pull.get("number") or -1)
        and str(context.get("commit_sha") or "") == str(head.get("sha") or "")
        and branch == str(head.get("ref") or "")
        and bool(UNIT_BRANCH_RE.fullmatch(branch))
        and str(base.get("ref") or "") == "main"
        and UNIT_MARKER in str(pull.get("body") or "")
    )


def evaluate_closed_unit_pr(
    status: Mapping[str, Any],
    pull_request: Mapping[str, Any],
    check_runs: Iterable[Mapping[str, Any]],
) -> ReconciliationDecision:
    """Decide how a closed automated unit PR affects its canonical run.

    A merge is eligible for automatic completion only when the same stored PR
    head has a complete second gate round created after the recorded
    ``recovery_ready_for_review_at`` timestamp.  Any uncertainty is fail-closed.
    """

    if str(status.get("status") or "") in FINAL_STATES:
        return _ignore(
            "run_already_final",
            passed=str(status.get("status")) == "success",
            reason="Der kanonische Generatorlauf ist bereits final.",
        )

    if not _matches_status(status, pull_request):
        return _ignore(
            "pr_does_not_match_status",
            reason="PR-Nummer, Head, Branch, Base oder Provenienzmarker passen nicht zum Lauf.",
        )

    if str(pull_request.get("state") or "").casefold() != "closed":
        return _ignore(
            "pr_not_closed",
            reason="Reconciliation gilt ausschließlich für geschlossene Unit-PRs.",
        )

    merged = bool(pull_request.get("merged")) or bool(pull_request.get("merged_at"))
    if not merged:
        return ReconciliationDecision(
            action="block_closed_without_merge",
            passed=False,
            code="unit_pr_closed_without_merge",
            merge_sha=None,
            required_checks={},
            reasons=(
                "Der zum laufenden Generatorstatus gehörende Unit-PR wurde ohne Merge geschlossen.",
            ),
        )

    merge_sha = str(pull_request.get("merge_commit_sha") or "")
    if not SHA_RE.fullmatch(merge_sha):
        return ReconciliationDecision(
            action="block_merged_outside_policy",
            passed=False,
            code="merged_without_green_second_gates",
            merge_sha=None,
            required_checks={},
            reasons=("Der Merge-Commit konnte nicht belastbar bestimmt werden.",),
        )

    context = _mapping(status.get("context"))
    head_sha = str(context.get("commit_sha") or "")
    metrics = _mapping(status.get("metrics"))
    ready_at = _timestamp(metrics.get("recovery_ready_for_review_at"))
    selected = select_latest_required_checks(check_runs, head_sha=head_sha)
    summaries = {
        name: _check_summary(selected.get(name))
        for name in REQUIRED_CHECKS
    }

    reasons: list[str] = []
    if ready_at is None:
        reasons.append("Zeitpunkt von Ready for review fehlt oder ist ungültig.")

    for name in REQUIRED_CHECKS:
        summary = summaries[name]
        if summary["state"] != "success":
            reasons.append(f"Required Check {name} ist {summary['state']}.")
            continue
        created_at = _timestamp(summary["created_at"])
        if ready_at is None or created_at is None or created_at <= ready_at:
            reasons.append(
                f"Required Check {name} ist nicht eindeutig Teil der zweiten Runde nach Ready for review."
            )

    if reasons:
        return ReconciliationDecision(
            action="block_merged_outside_policy",
            passed=False,
            code="merged_without_green_second_gates",
            merge_sha=merge_sha,
            required_checks=summaries,
            reasons=tuple(reasons),
        )

    return ReconciliationDecision(
        action="complete_merged_run",
        passed=True,
        code="merged_after_green_second_gates",
        merge_sha=merge_sha,
        required_checks=summaries,
        reasons=(
            "PR wurde mit unverändertem Lauf-Head nach vollständig grüner zweiter Gate-Runde gemergt.",
        ),
    )
