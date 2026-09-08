from __future__ import annotations

from pathlib import Path

import pytest

from scripts.automation_status import RevisionConflict, StatusStore, default_context, read_status
from scripts.unit_pr_reconciliation import ReconciliationDecision, apply_reconciliation

HEAD = "a" * 40
MERGE = "b" * 40
RUN_ID = "generator-reconcile-1"


def _running_store(tmp_path: Path) -> tuple[StatusStore, dict]:
    store = StatusStore(tmp_path / "status")
    created = store.start(
        "generator",
        run_id=RUN_ID,
        context=default_context(
            repository="H234598/ADHS-Lernpfad",
            branch="agent/einheit-21-example",
            commit_sha=HEAD,
            pr_number=66,
            pr_url="https://github.com/H234598/ADHS-Lernpfad/pull/66",
        ),
    )
    running = store.update(
        "generator",
        RUN_ID,
        status="running",
        phase="ready_for_review",
        expected_revision=created["revision"],
        metrics={
            "recovery_ready_for_review": True,
            "recovery_ready_for_review_at": "2026-09-08T04:08:24Z",
            "recovery_second_ci_state": "pending",
            "automatic_unit_pull_request_open": True,
            "next_generator_blocked": True,
            "branch_still_exists": True,
        },
    )
    return store, running


def _green_decision() -> ReconciliationDecision:
    return ReconciliationDecision(
        action="complete_merged_run",
        passed=True,
        code="merged_after_green_second_gates",
        merge_sha=MERGE,
        required_checks={
            "Validate and build": {"state": "success", "url": "https://example.invalid/1"},
            "Build all download formats": {"state": "success", "url": "https://example.invalid/2"},
            "Remark lint (blocking)": {"state": "success", "url": "https://example.invalid/3"},
            "CodeRabbit review gate (blocking)": {"state": "success", "url": "https://example.invalid/4"},
            "Learning card policy (blocking)": {"state": "success", "url": "https://example.invalid/5"},
        },
        reasons=("second gate round green",),
    )


def test_green_external_merge_completes_same_run_and_unblocks_next_generator(tmp_path: Path) -> None:
    store, running = _running_store(tmp_path)

    completed = apply_reconciliation(
        store,
        workflow="generator",
        run_id=RUN_ID,
        decision=_green_decision(),
        expected_revision=running["revision"],
        repository="H234598/ADHS-Lernpfad",
        pr_number=66,
        main_sha=MERGE,
        branch_exists=False,
    )

    assert completed["status"] == "success"
    assert completed["phase"] == "complete"
    assert completed["metrics"]["recovery_second_ci_state"] == "success"
    assert completed["metrics"]["automatic_unit_pull_request_open"] is False
    assert completed["metrics"]["next_generator_blocked"] is False
    assert completed["metrics"]["current_main_commit"] == MERGE
    assert completed["metrics"]["branch_still_exists"] is False
    assert {"verify_second_ci", "merge", "cleanup", "complete"}.issubset(
        set(completed["completed_phases"])
    )
    artifacts = {(item["type"], item["value"]) for item in completed["artifacts"]}
    assert ("commit", MERGE) in artifacts
    assert ("report", f"main:{MERGE}") in artifacts
    assert completed["error"] is None
    assert completed["recovery"] is None


def test_stale_expected_revision_aborts_before_any_reconciliation_write(tmp_path: Path) -> None:
    store, running = _running_store(tmp_path)
    before = read_status(store.path_for("generator", RUN_ID))

    with pytest.raises(RevisionConflict):
        apply_reconciliation(
            store,
            workflow="generator",
            run_id=RUN_ID,
            decision=_green_decision(),
            expected_revision=running["revision"] - 1,
            repository="H234598/ADHS-Lernpfad",
            pr_number=66,
            main_sha=MERGE,
            branch_exists=False,
        )

    after = read_status(store.path_for("generator", RUN_ID))
    assert after == before


def test_merged_without_green_second_gates_becomes_manual_blocker(tmp_path: Path) -> None:
    store, running = _running_store(tmp_path)
    decision = ReconciliationDecision(
        action="block_merged_outside_policy",
        passed=False,
        code="merged_without_green_second_gates",
        merge_sha=MERGE,
        required_checks={"CodeRabbit review gate (blocking)": {"state": "failure", "url": ""}},
        reasons=("required gate failed",),
    )

    blocked = apply_reconciliation(
        store,
        workflow="generator",
        run_id=RUN_ID,
        decision=decision,
        expected_revision=running["revision"],
        repository="H234598/ADHS-Lernpfad",
        pr_number=66,
        main_sha=MERGE,
        branch_exists=True,
    )

    assert blocked["status"] == "blocked"
    assert blocked["error"]["code"] == "merged_without_green_second_gates"
    assert blocked["recovery"]["level"] == "manual_intervention"
    assert blocked["recovery"]["block_next_run"] is True
    assert blocked["metrics"]["next_generator_blocked"] is True


def test_closed_without_merge_becomes_manual_blocker(tmp_path: Path) -> None:
    store, running = _running_store(tmp_path)
    decision = ReconciliationDecision(
        action="block_closed_without_merge",
        passed=False,
        code="unit_pr_closed_without_merge",
        merge_sha=None,
        required_checks={},
        reasons=("unit PR closed by user",),
    )

    blocked = apply_reconciliation(
        store,
        workflow="generator",
        run_id=RUN_ID,
        decision=decision,
        expected_revision=running["revision"],
        repository="H234598/ADHS-Lernpfad",
        pr_number=66,
        main_sha=None,
        branch_exists=True,
    )

    assert blocked["status"] == "blocked"
    assert blocked["error"]["code"] == "unit_pr_closed_without_merge"
    assert blocked["recovery"]["level"] == "manual_intervention"
    assert blocked["metrics"]["automatic_unit_pull_request_open"] is False
    assert blocked["metrics"]["next_generator_blocked"] is True
