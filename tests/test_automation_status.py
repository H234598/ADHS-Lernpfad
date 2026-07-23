"""Acceptance scenarios from issue #34 for interrupted generator runs."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.automation_status import StatusStore, make_artifact


@pytest.mark.parametrize(
    ("phase", "artifacts", "expected_level", "action_fragment"),
    [
        ("research", (), "retry_same_phase", "research"),
        (
            "create_branch",
            (("branch", "agent/einheit-15"),),
            "resume_from_artifact",
            "Branch",
        ),
        (
            "commit",
            (
                ("branch", "agent/einheit-15"),
                ("commit", "a" * 40),
            ),
            "resume_from_artifact",
            "Commit",
        ),
        (
            "create_pr",
            (
                ("branch", "agent/einheit-15"),
                ("commit", "b" * 40),
            ),
            "resume_from_artifact",
            "Push/PR",
        ),
        (
            "wait_review",
            (
                ("branch", "agent/einheit-15"),
                ("commit", "c" * 40),
                ("pull_request", "#123"),
            ),
            "resume_from_artifact",
            "Pull Request",
        ),
    ],
)
def test_interruption_reuses_most_advanced_artifact(
    tmp_path: Path,
    phase: str,
    artifacts: tuple[tuple[str, str], ...],
    expected_level: str,
    action_fragment: str,
) -> None:
    store = StatusStore(tmp_path / "status")
    run_id = f"interrupted-{phase}"
    store.start("generator", run_id=run_id)
    store.update("generator", run_id, status="running", phase=phase)
    for artifact_type, value in artifacts:
        store.artifact(
            "generator",
            run_id,
            make_artifact(artifact_type, value, reusable=True),
        )

    failed = store.fail(
        "generator",
        run_id,
        error_class="timeout",
        code=f"{phase}_interrupted",
        message=f"{phase} interrupted",
        retryable=True,
    )

    assert failed["run_id"] == run_id
    assert failed["recovery"]["level"] == expected_level
    assert action_fragment.casefold() in failed["recovery"]["action"].casefold()
    assert failed["recovery"]["new_content_required"] is False
    assert failed["recovery"]["block_next_run"] is True
