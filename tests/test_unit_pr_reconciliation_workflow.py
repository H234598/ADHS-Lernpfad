from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/reconcile-unit-pr.yml"
ADAPTER = ROOT / "scripts/unit_pr_reconciliation_cli.py"
RECONCILER = ROOT / "scripts/unit_pr_reconciliation.py"


def _on(workflow: dict) -> dict:
    return workflow[True] if True in workflow else workflow["on"]


def test_reconciliation_workflow_reacts_to_closed_pull_requests_and_manual_recovery() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    triggers = _on(workflow)

    assert triggers["pull_request_target"]["types"] == ["closed"]
    assert "workflow_dispatch" in triggers
    assert triggers["workflow_dispatch"]["inputs"]["pr_number"]["type"] == "number"


def test_reconciliation_workflow_is_same_repo_fail_closed_and_trusted_main_only() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    job = workflow["jobs"]["reconcile"]

    assert workflow["permissions"] == {
        "contents": "write",
        "pull-requests": "read",
        "checks": "read",
    }
    condition = str(job["if"])
    assert "head.repo.full_name == github.repository" in condition
    assert "base.ref == 'main'" in condition
    assert "startsWith(github.event.pull_request.head.ref, 'agent/einheit-')" in condition
    assert "adhs-daily-unit" in condition

    checkout = next(
        step
        for step in job["steps"]
        if step.get("name")
        == "Check out trusted reconciliation implementation from main"
    )
    assert checkout["with"]["ref"] == "main"
    assert "pull_request.head.sha" not in str(checkout)
    assert "github.event.pull_request.head.sha" not in str(checkout)


def test_reconciliation_workflow_serializes_status_writes_and_uses_existing_store() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)

    assert workflow["concurrency"]["group"] == "automation-status"
    assert workflow["concurrency"]["cancel-in-progress"] is False
    assert "git fetch --depth=1 origin automation-status" in text
    assert "git worktree add" in text
    assert "AUTOMATION_STATUS_ROOT" in text
    assert "python scripts/unit_pr_reconciliation.py" in text
    assert "scripts/validate_runtime_status.py" in text
    assert "latest.json" in text
    assert "push origin HEAD:refs/heads/automation-status" in text
    assert "--force" not in text
    assert "push --force" not in text


def test_remote_cleanup_happens_only_after_cleanup_phase_was_persisted() -> None:
    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    adapter_text = ADAPTER.read_text(encoding="utf-8")
    reconciler_text = RECONCILER.read_text(encoding="utf-8")

    first_persist = workflow_text.index("Persist reconciled pre-cleanup status")
    delete_branch = workflow_text.index("Delete reconciled unit branch")
    finalize = workflow_text.index("Finalize canonical run after cleanup attempt")
    second_persist = workflow_text.index("Persist completed reconciliation status")

    assert first_persist < delete_branch < finalize < second_persist
    assert "--prepare-decision" in workflow_text
    assert "--finalize-cleanup" in workflow_text
    assert "git push origin --delete" in workflow_text
    assert "branch_cleanup" not in adapter_text
    assert "prepare_reconciliation" in reconciler_text
    assert "finalize_reconciliation" in reconciler_text
    assert "complete_merged_run" in reconciler_text
    assert "block_closed_without_merge" in reconciler_text
    assert "block_merged_outside_policy" in reconciler_text
