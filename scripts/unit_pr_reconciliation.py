"""Reconcile externally closed automated unit pull requests.

The decision layer is deliberately side-effect free. Persistence uses the
existing :mod:`automation_status` store so the same generator run advances via
its normal CAS/revision contract instead of creating a parallel state machine.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

try:  # Package import in tests; direct script import in trusted workflows.
    from .automation_status import (
        RevisionConflict as _RevisionConflict,
        StatusStore,
        make_artifact,
        make_error,
        make_recovery,
        read_status,
    )
except ImportError:  # pragma: no cover - direct command-line execution
    from automation_status import (  # type: ignore
        RevisionConflict as _RevisionConflict,
        StatusStore,
        make_artifact,
        make_error,
        make_recovery,
        read_status,
    )


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
    state = (
        "success"
        if completed and conclusion == "success"
        else ("pending" if not completed else "failure")
    )
    return {
        "state": state,
        "created_at": str(run.get("created_at") or ""),
        "completed_at": str(run.get("completed_at") or ""),
        "url": str(run.get("html_url") or ""),
    }


def _ignore(
    code: str,
    *,
    passed: bool = False,
    reason: str,
) -> ReconciliationDecision:
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


def _closed_pr_precondition(
    status: Mapping[str, Any],
    pull_request: Mapping[str, Any],
) -> ReconciliationDecision | None:
    """Return an early reconciliation decision when the snapshot is ineligible."""

    state = str(status.get("status") or "")
    if state in FINAL_STATES:
        return _ignore(
            "run_already_final",
            passed=state == "success",
            reason="Der kanonische Generatorlauf ist bereits final.",
        )
    if not _matches_status(status, pull_request):
        return _ignore(
            "pr_does_not_match_status",
            reason=(
                "PR-Nummer, Head, Branch, Base oder Provenienzmarker passen "
                "nicht zum Lauf."
            ),
        )
    if str(pull_request.get("state") or "").casefold() != "closed":
        return _ignore(
            "pr_not_closed",
            reason="Reconciliation gilt ausschließlich für geschlossene Unit-PRs.",
        )
    if not (
        bool(pull_request.get("merged"))
        or bool(pull_request.get("merged_at"))
    ):
        return ReconciliationDecision(
            action="block_closed_without_merge",
            passed=False,
            code="unit_pr_closed_without_merge",
            merge_sha=None,
            required_checks={},
            reasons=(
                "Der zum laufenden Generatorstatus gehörende Unit-PR wurde "
                "ohne Merge geschlossen.",
            ),
        )
    return None


def _second_round_reasons(
    summaries: Mapping[str, Mapping[str, str]],
    *,
    ready_at: datetime | None,
) -> list[str]:
    """Explain every missing or stale second-round gate."""

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
                f"Required Check {name} ist nicht eindeutig Teil der zweiten "
                "Runde nach Ready for review."
            )
    return reasons


def evaluate_closed_unit_pr(
    status: Mapping[str, Any],
    pull_request: Mapping[str, Any],
    check_runs: Iterable[Mapping[str, Any]],
) -> ReconciliationDecision:
    """Decide how a closed automated unit PR affects its canonical run.

    A merge is eligible for automatic completion only when the same stored PR
    head has a complete second gate round created after the recorded
    ``recovery_ready_for_review_at`` timestamp. Any uncertainty is fail-closed.
    """

    early = _closed_pr_precondition(status, pull_request)
    if early is not None:
        return early

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
    reasons = _second_round_reasons(summaries, ready_at=ready_at)

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
            "PR wurde mit unverändertem Lauf-Head nach vollständig grüner "
            "zweiter Gate-Runde gemergt.",
        ),
    )


def _assert_owned_revision(
    store: StatusStore,
    workflow: str,
    run_id: str,
    last_written_revision: int,
) -> int:
    """Refuse to continue if another writer interleaved between our phases."""

    current = read_status(store.path_for(workflow, run_id))
    current_revision = int(current["revision"])
    if current_revision != int(last_written_revision):
        raise _RevisionConflict(
            f"Reconciliation erwartete eigene Revision {last_written_revision}, "
            f"vorhanden {current_revision}"
        )
    return current_revision


def _check_artifacts(decision: ReconciliationDecision) -> list[dict[str, Any]]:
    """Convert verified gate summaries into structured, idempotent artifacts."""

    artifacts: list[dict[str, Any]] = []
    for name in REQUIRED_CHECKS:
        summary = decision.required_checks.get(name, {})
        if summary.get("state") != "success":
            continue
        artifacts.append(
            make_artifact(
                "ci_job",
                f"{name}: success",
                url=summary.get("url") or None,
                reusable=True,
            )
        )
    return artifacts


def _blocked_reconciliation(
    store: StatusStore,
    *,
    workflow: str,
    run_id: str,
    decision: ReconciliationDecision,
    expected_revision: int,
    repository: str,
    main_sha: str | None,
    branch_exists: bool,
) -> dict[str, Any]:
    """Persist a closed-PR state that requires manual intervention."""

    phase = (
        "merge"
        if decision.action == "block_merged_outside_policy"
        else "cleanup"
    )
    message = "; ".join(decision.reasons) or (
        "Geschlossener Unit-PR erfordert manuelle Klärung."
    )
    error = make_error(
        "repository_state",
        message,
        phase=phase,
        code=decision.code,
        retryable=False,
    )
    recovery = make_recovery(
        "manual_intervention",
        "Geschlossenen Unit-PR und kanonischen Generatorstatus prüfen; "
        "keinen neuen Inhalt erzeugen.",
        resume_phase=phase,
        block_next_run=True,
        new_content_required=False,
    )
    artifacts: list[dict[str, Any]] = []
    if decision.merge_sha and SHA_RE.fullmatch(decision.merge_sha):
        artifacts.append(
            make_artifact(
                "commit",
                decision.merge_sha,
                url=(
                    f"https://github.com/{repository}/commit/"
                    f"{decision.merge_sha}"
                ),
                reusable=True,
            )
        )
    metrics: dict[str, Any] = {
        "automatic_unit_pull_request_open": False,
        "next_generator_blocked": True,
        "branch_still_exists": bool(branch_exists),
    }
    if isinstance(main_sha, str) and SHA_RE.fullmatch(main_sha):
        metrics["current_main_commit"] = main_sha
    return store.update(
        workflow,
        run_id,
        status="blocked",
        phase=phase,
        expected_revision=expected_revision,
        complete_previous_phase=False,
        metrics=metrics,
        artifacts=artifacts,
        error=error,
        recovery=recovery,
    )


def _validate_success_inputs(
    decision: ReconciliationDecision,
    *,
    main_sha: str | None,
    main_contains_merge: bool | None,
) -> tuple[str, str]:
    """Validate success evidence before the first CAS mutation."""

    if decision.action != "complete_merged_run" or not decision.passed:
        raise ValueError(
            "Unbekannte oder inkonsistente Reconciliation-Aktion: "
            f"{decision.action}"
        )
    if not decision.merge_sha or not SHA_RE.fullmatch(decision.merge_sha):
        raise ValueError(
            "Erfolgreiche Reconciliation benötigt einen Merge-Commit"
        )
    if not isinstance(main_sha, str) or not SHA_RE.fullmatch(main_sha):
        raise ValueError(
            "Erfolgreiche Reconciliation benötigt einen aktuellen main-Commit"
        )
    if main_contains_merge is False:
        raise ValueError(
            "Merge-Commit ist nicht als Bestandteil von main nachgewiesen"
        )
    if main_contains_merge is None and main_sha != decision.merge_sha:
        raise ValueError(
            "Merge-Commit ist ohne expliziten Ancestor-Nachweis nicht auf main "
            "verifiziert"
        )
    return decision.merge_sha, main_sha


def prepare_reconciliation(
    store: StatusStore,
    *,
    workflow: str,
    run_id: str,
    decision: ReconciliationDecision,
    expected_revision: int,
    repository: str,
    pr_number: int,
    main_sha: str | None,
    branch_exists: bool,
    main_contains_merge: bool | None = None,
) -> dict[str, Any]:
    """Persist reconciliation through ``cleanup`` without remote branch deletion.

    Successful external side effects are deliberately deferred until this
    pre-cleanup state has itself been pushed to the remote automation-status
    branch by the trusted workflow.
    """

    current = read_status(store.path_for(workflow, run_id))
    context = _mapping(current.get("context"))
    if str(context.get("repository") or "") != repository:
        raise ValueError("Repository passt nicht zum kanonischen Lauf")
    if int(context.get("pr_number") or 0) != int(pr_number):
        raise ValueError("Pull Request passt nicht zum kanonischen Lauf")
    if decision.action == "ignore":
        return current
    if decision.action in {
        "block_merged_outside_policy",
        "block_closed_without_merge",
    }:
        return _blocked_reconciliation(
            store,
            workflow=workflow,
            run_id=run_id,
            decision=decision,
            expected_revision=expected_revision,
            repository=repository,
            main_sha=main_sha,
            branch_exists=branch_exists,
        )

    merge_sha, verified_main_sha = _validate_success_inputs(
        decision,
        main_sha=main_sha,
        main_contains_merge=main_contains_merge,
    )
    verified = store.update(
        workflow,
        run_id,
        status="running",
        phase="verify_second_ci",
        expected_revision=expected_revision,
        metrics={
            "recovery_second_ci_state": "success",
            "recovery_second_gate_round_complete": True,
            "next_generator_blocked": True,
        },
        artifacts=_check_artifacts(decision),
    )

    merge_artifacts = [
        make_artifact(
            "commit",
            merge_sha,
            url=f"https://github.com/{repository}/commit/{merge_sha}",
            reusable=True,
        ),
        make_artifact(
            "report",
            f"main:{verified_main_sha}",
            url=f"https://github.com/{repository}/tree/main",
            reusable=True,
        ),
    ]
    if verified_main_sha != merge_sha:
        merge_artifacts.append(
            make_artifact(
                "report",
                f"main-contains:{merge_sha}@{verified_main_sha}",
                url=(
                    f"https://github.com/{repository}/compare/"
                    f"{merge_sha}...main"
                ),
                reusable=True,
            )
        )

    merged = store.update(
        workflow,
        run_id,
        status="running",
        phase="merge",
        expected_revision=_assert_owned_revision(
            store,
            workflow,
            run_id,
            int(verified["revision"]),
        ),
        metrics={
            "recovery_merge_commit": merge_sha,
            "current_main_commit": verified_main_sha,
            "next_generator_blocked": True,
        },
        artifacts=merge_artifacts,
    )
    return store.update(
        workflow,
        run_id,
        status="running",
        phase="cleanup",
        expected_revision=_assert_owned_revision(
            store,
            workflow,
            run_id,
            int(merged["revision"]),
        ),
        metrics={
            "automatic_unit_pull_request_open": False,
            "branch_still_exists": bool(branch_exists),
            "recovery_cleanup_started": True,
            "recovery_cleanup_complete": False,
            "next_generator_blocked": True,
        },
    )


def finalize_reconciliation(
    store: StatusStore,
    *,
    workflow: str,
    run_id: str,
    expected_revision: int,
    branch_exists: bool,
) -> dict[str, Any]:
    """Finalize a remotely persisted cleanup phase after the cleanup attempt."""

    current = read_status(store.path_for(workflow, run_id))
    if current.get("status") != "running" or current.get("phase") != "cleanup":
        raise ValueError(
            "Cleanup-Finalisierung benötigt einen laufenden Status in Phase cleanup"
        )
    metrics = _mapping(current.get("metrics"))
    main_sha = str(metrics.get("current_main_commit") or "")
    if not SHA_RE.fullmatch(main_sha):
        raise ValueError("Cleanup-Finalisierung benötigt einen main-Nachweis")
    return store.update(
        workflow,
        run_id,
        status="success",
        phase="complete",
        expected_revision=expected_revision,
        metrics={
            "recovery_second_ci_state": "success",
            "automatic_unit_pull_request_open": False,
            "branch_still_exists": bool(branch_exists),
            "recovery_cleanup_complete": True,
            "next_generator_blocked": False,
            "new_content_required": False,
        },
        error=None,
        recovery=None,
    )


def apply_reconciliation(
    store: StatusStore,
    *,
    workflow: str,
    run_id: str,
    decision: ReconciliationDecision,
    expected_revision: int,
    repository: str,
    pr_number: int,
    main_sha: str | None,
    branch_exists: bool,
    main_contains_merge: bool | None = None,
    branch_cleanup: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Convenience wrapper for in-process/test reconciliation.

    Production workflow execution uses :func:`prepare_reconciliation`, pushes
    the cleanup phase remotely, performs branch cleanup, and only then invokes
    :func:`finalize_reconciliation`.
    """

    prepared = prepare_reconciliation(
        store,
        workflow=workflow,
        run_id=run_id,
        decision=decision,
        expected_revision=expected_revision,
        repository=repository,
        pr_number=pr_number,
        main_sha=main_sha,
        branch_exists=branch_exists,
        main_contains_merge=main_contains_merge,
    )
    if prepared.get("status") != "running" or prepared.get("phase") != "cleanup":
        return prepared

    effective_branch_exists = bool(branch_exists)
    if branch_cleanup is not None and effective_branch_exists:
        try:
            effective_branch_exists = bool(branch_cleanup())
        except (OSError, RuntimeError, ValueError):
            effective_branch_exists = True
    return finalize_reconciliation(
        store,
        workflow=workflow,
        run_id=run_id,
        expected_revision=int(prepared["revision"]),
        branch_exists=effective_branch_exists,
    )


if __name__ == "__main__":  # pragma: no cover - trusted Actions workflow
    from unit_pr_reconciliation_cli import main

    raise SystemExit(main())
