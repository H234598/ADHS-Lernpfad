from __future__ import annotations

from copy import deepcopy

from scripts.unit_pr_reconciliation import REQUIRED_CHECKS, evaluate_closed_unit_pr

HEAD = "a" * 40
MERGE = "b" * 40
READY_AT = "2026-09-08T04:08:24Z"


def _status(*, state: str = "running") -> dict:
    return {
        "run_id": "generator-1",
        "workflow": "generator",
        "revision": 14,
        "status": state,
        "phase": "ready_for_review" if state == "running" else "complete",
        "context": {
            "repository": "H234598/ADHS-Lernpfad",
            "branch": "agent/einheit-21-example",
            "commit_sha": HEAD,
            "pr_number": 66,
            "pr_url": "https://github.com/H234598/ADHS-Lernpfad/pull/66",
            "workflow_run": None,
        },
        "metrics": {
            "recovery_ready_for_review": True,
            "recovery_ready_for_review_at": READY_AT,
            "next_generator_blocked": True,
        },
        "artifacts": [],
        "error": None,
        "recovery": None,
    }


def _pull(*, merged: bool = True) -> dict:
    return {
        "number": 66,
        "state": "closed",
        "merged": merged,
        "merged_at": "2026-09-08T10:20:12Z" if merged else None,
        "merge_commit_sha": MERGE if merged else None,
        "body": "<!-- adhs-daily-unit -->\nRecovery",
        "base": {"ref": "main"},
        "head": {"ref": "agent/einheit-21-example", "sha": HEAD},
    }


def _checks(*, conclusion: str = "success", created_at: str = "2026-09-08T04:10:00Z") -> list[dict]:
    return [
        {
            "id": index,
            "name": name,
            "head_sha": HEAD,
            "status": "completed",
            "conclusion": conclusion,
            "created_at": created_at,
            "completed_at": "2026-09-08T04:12:30Z",
            "html_url": f"https://github.com/example/check/{index}",
        }
        for index, name in enumerate(REQUIRED_CHECKS, start=1)
    ]


def test_merged_matching_pr_with_green_second_gates_can_complete() -> None:
    decision = evaluate_closed_unit_pr(_status(), _pull(), _checks())

    assert decision.action == "complete_merged_run"
    assert decision.passed is True
    assert decision.code == "merged_after_green_second_gates"
    assert decision.merge_sha == MERGE
    assert set(decision.required_checks) == set(REQUIRED_CHECKS)


def test_merged_pr_with_failed_required_gate_stays_blocked() -> None:
    checks = _checks()
    checks[-1] = {**checks[-1], "conclusion": "failure"}

    decision = evaluate_closed_unit_pr(_status(), _pull(), checks)

    assert decision.action == "block_merged_outside_policy"
    assert decision.passed is False
    assert decision.code == "merged_without_green_second_gates"


def test_green_checks_from_before_ready_do_not_count_as_second_round() -> None:
    decision = evaluate_closed_unit_pr(
        _status(),
        _pull(),
        _checks(created_at="2026-09-08T04:05:00Z"),
    )

    assert decision.action == "block_merged_outside_policy"
    assert decision.passed is False
    assert decision.code == "merged_without_green_second_gates"


def test_closed_without_merge_is_user_intervention_blocker() -> None:
    decision = evaluate_closed_unit_pr(_status(), _pull(merged=False), _checks())

    assert decision.action == "block_closed_without_merge"
    assert decision.passed is False
    assert decision.code == "unit_pr_closed_without_merge"


def test_mismatching_pr_is_ignored_without_touching_other_run() -> None:
    pull = deepcopy(_pull())
    pull["head"]["sha"] = "c" * 40

    decision = evaluate_closed_unit_pr(_status(), pull, _checks())

    assert decision.action == "ignore"
    assert decision.passed is False
    assert decision.code == "pr_does_not_match_status"


def test_final_generator_status_is_ignored() -> None:
    decision = evaluate_closed_unit_pr(_status(state="success"), _pull(), _checks())

    assert decision.action == "ignore"
    assert decision.passed is True
    assert decision.code == "run_already_final"
