"""Unit and integration tests for the automation recovery implementation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

import scripts.automation_status as automation_status
from scripts.automation_status import (
    ALLOWED_TRANSITIONS,
    DEFAULT_STATUS_PATH,
    EXIT_BLOCKED,
    EXIT_SUCCESS,
    PHASES,
    InvalidTransition,
    RevisionConflict,
    StatusStore,
    UnresolvedPreviousRun,
    blocks_new_run,
    create_status_file,
    finish_run,
    make_artifact,
    make_error,
    make_recovery,
    prune_statuses,
    read_status,
    recovery_from_artifacts,
    render_diagnostic,
    restore_status_file,
    start_run,
    status_is_managed,
    transition_status_file,
    update_status,
    validate_status,
    write_status,
)
from scripts.runtime_status_phase import runtime_phase
from scripts.validate_runtime_status import validate_file


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "automation_status.py"


def test_required_tools_and_canonical_paths_exist() -> None:
    assert DEFAULT_STATUS_PATH == Path("build/runtime-status.json")
    for relative in (
        "automation/run-status.schema.json",
        "scripts/automation_status.py",
        "scripts/automation_run_status.py",
        "scripts/runtime_status_cli.py",
        "scripts/runtime_status_phase.py",
        "scripts/validate_runtime_status.py",
    ):
        assert (ROOT / relative).is_file()


def test_build_workflows_restore_pre_final_status_before_recording_late_failure() -> None:
    for relative in (
        ".github/workflows/export.yml",
        ".github/workflows/pages.yml",
        ".github/workflows/validate.yml",
    ):
        workflow = (ROOT / relative).read_text(encoding="utf-8")
        assert "cp build/runtime-status.json build/runtime-status-pre-final.json" in workflow
        assert "--restore-from build/runtime-status-pre-final.json" in workflow


def test_all_workflow_failure_phases_are_schema_values() -> None:
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        workflow = path.read_text(encoding="utf-8")
        phases = set(re.findall(r"current_phase=([a-z_]+)", workflow))
        assert phases <= PHASES, f"{path}: {sorted(phases - PHASES)}"


def test_start_update_finish_preserves_identity_and_increments_revisions(
    tmp_path: Path,
) -> None:
    target = tmp_path / "runtime-status.json"
    started = start_run(
        target,
        "knowledge-graph",
        run_id="run-42",
        git_sha="0123456789abcdef",
    )
    running = update_status(
        target,
        status="running",
        phase="load_content",
        metrics={"documents": 4},
        artifacts=["build/source-index.json"],
    )
    exporting = update_status(
        target,
        status="running",
        phase="export",
        metrics={"nodes": 12},
        artifacts=["build/knowledge-graph/knowledge-graph.json"],
    )
    finished = finish_run(
        target,
        success=True,
        phase="complete",
    )

    assert started["revision"] == 1
    assert running["revision"] == 2
    assert exporting["revision"] == 3
    assert finished["revision"] == 4
    assert finished["run_id"] == started["run_id"]
    assert finished["created_at"] == started["created_at"]
    assert finished["status"] == "success"
    assert finished["phase"] == "complete"
    assert finished["previous_status"] == "running"
    assert finished["duration_seconds"] >= 0
    assert finished["metrics"] == {"documents": 4, "nodes": 12}
    assert finished["completed_phases"] == ["load_content", "export", "complete"]
    assert {artifact["path"] for artifact in finished["artifacts"]} == {
        "build/source-index.json",
        "build/knowledge-graph/knowledge-graph.json",
    }
    assert validate_status(finished) == []
    assert validate_file(target) == []


def test_failed_finish_replaces_corrupt_input_with_complete_safe_status(
    tmp_path: Path,
) -> None:
    target = tmp_path / "runtime-status.json"
    target.write_text("not-json", encoding="utf-8")
    failed = finish_run(
        target,
        success=False,
        phase="validate_graph",
        error_class="graph_validation_error",
        error_message="token=top-secret link target missing",
        recovery_action="repair existing graph",
    )

    assert failed["status"] == "failed"
    assert failed["phase"] == "validate_graph"
    assert failed["error"]["class"] == "validation"
    assert failed["error"]["code"] == "graph_validation_error"
    assert "top-secret" not in failed["error"]["message"]
    assert failed["recovery"]["action"] == "repair existing graph"
    assert blocks_new_run(failed)
    assert validate_status(failed) == []


def test_atomic_write_leaves_no_partial_or_lock_file(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "runtime-status.json"
    payload = write_status(target, {"workflow": "knowledge-graph"})
    assert json.loads(target.read_text(encoding="utf-8")) == payload
    assert list(target.parent.glob(f".{target.name}.*.tmp")) == []
    assert not target.with_name(f".{target.name}.lock").exists()


def test_pre_finalization_revision_can_be_restored_and_failed_atomically(
    tmp_path: Path,
) -> None:
    target = tmp_path / "runtime-status.json"
    backup = tmp_path / "runtime-status-pre-final.json"
    start_run(target, "manual", run_id="finalization-rollback")
    running = transition_status_file(
        target,
        status="running",
        phase="validate",
    )
    backup.write_bytes(target.read_bytes())
    transition_status_file(target, status="success", phase="complete")

    restored = restore_status_file(target, backup)
    failed = finish_run(
        target,
        success=False,
        phase="validate",
        error_class="validation",
        error_message="post-finalization gate failed",
    )

    assert restored == running
    assert failed["run_id"] == "finalization-rollback"
    assert failed["status"] == "failed"
    assert failed["previous_status"] == "running"
    assert validate_status(failed) == []


def test_explicit_state_matrix_and_forbidden_transition(tmp_path: Path) -> None:
    assert ALLOWED_TRANSITIONS == {
        "created": {"created", "running", "blocked", "failed"},
        "running": {"running", "success", "blocked", "failed"},
        "success": {"success"},
        "blocked": {"blocked", "recovering", "failed"},
        "failed": {"failed", "recovering"},
        "recovering": {"recovering", "recovered", "blocked", "failed"},
        "recovered": {"recovered", "running", "success", "blocked", "failed"},
    }
    target = tmp_path / "status.json"
    start_run(target, "manual", run_id="transition-test")
    transition_status_file(target, status="running")
    transition_status_file(target, status="success", phase="complete")
    with pytest.raises(InvalidTransition):
        transition_status_file(target, status="running")


def _status_at(path: Path, state: str) -> dict:
    current = start_run(path, "manual", run_id=path.stem)
    if state == "created":
        return current
    current = transition_status_file(path, status="running")
    if state == "running":
        return current
    if state == "success":
        return transition_status_file(path, status="success", phase="complete")
    error = make_error(
        "validation",
        "controlled transition test",
        phase="validate",
    )
    recovery = make_recovery(
        "retry_same_phase",
        "controlled retry",
        resume_phase="validate",
    )
    current = transition_status_file(
        path,
        status="blocked" if state == "blocked" else "failed",
        phase="validate",
        error=error,
        recovery=recovery,
    )
    if state in {"blocked", "failed"}:
        return current
    current = transition_status_file(
        path,
        status="recovering",
        phase="validate",
    )
    if state == "recovering":
        return current
    return transition_status_file(
        path,
        status="recovered",
        phase="validate",
    )


def test_every_allowed_and_forbidden_state_transition(tmp_path: Path) -> None:
    for origin in sorted(ALLOWED_TRANSITIONS):
        for target_state in sorted(ALLOWED_TRANSITIONS):
            target = tmp_path / f"{origin}-to-{target_state}.json"
            current = _status_at(target, origin)
            error = current["error"]
            recovery = current["recovery"]
            if target_state in {"blocked", "failed"} and error is None:
                error = make_error(
                    "validation",
                    "controlled transition test",
                    phase="validate",
                )
                recovery = make_recovery(
                    "retry_same_phase",
                    "controlled retry",
                    resume_phase="validate",
                )
            changes = {
                "status": target_state,
                "phase": "complete" if target_state == "success" else current["phase"],
                "error": error,
                "recovery": recovery,
            }
            if target_state in ALLOWED_TRANSITIONS[origin]:
                transitioned = transition_status_file(target, **changes)
                assert transitioned["status"] == target_state
            else:
                with pytest.raises(InvalidTransition):
                    transition_status_file(target, **changes)


def test_optimistic_revision_prevents_lost_update(tmp_path: Path) -> None:
    target = tmp_path / "status.json"
    start_run(target, "manual", run_id="revision-test")
    running = transition_status_file(target, status="running")
    transition_status_file(
        target,
        metrics={"first": True},
        expected_revision=running["revision"],
    )
    with pytest.raises(RevisionConflict):
        transition_status_file(
            target,
            metrics={"stale": True},
            expected_revision=running["revision"],
        )
    assert read_status(target)["metrics"] == {"first": True}


def test_parallel_writers_are_locked_and_one_stale_revision_is_rejected(
    tmp_path: Path,
) -> None:
    target = tmp_path / "status.json"
    start_run(target, "manual", run_id="parallel-test")
    running = transition_status_file(target, status="running")

    def update(key: str) -> str:
        try:
            transition_status_file(
                target,
                metrics={key: True},
                expected_revision=running["revision"],
            )
        except RevisionConflict:
            return "conflict"
        return "written"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = sorted(executor.map(update, ("alpha", "beta")))
    assert results == ["conflict", "written"]
    assert read_status(target)["revision"] == running["revision"] + 1


def test_redaction_removes_credentials_email_and_signed_url_query(
    tmp_path: Path,
) -> None:
    store = StatusStore(tmp_path / "status")
    store.start("generator", run_id="redaction-run")
    store.update(
        "generator",
        "redaction-run",
        status="running",
        phase="create_branch",
        metrics={
            "nested": {
                "contact": "metric-owner@example.org",
                "credential": "token=metric-secret",
            }
        },
    )
    store.artifact(
        "generator",
        "redaction-run",
        make_artifact(
            "branch",
            "agent/einheit-15",
            url="https://github.com/H234598/ADHS-Lernpfad/tree/branch?sig=secret",
            reusable=True,
        ),
    )
    failed = store.fail(
        "generator",
        "redaction-run",
        error_class="github_api_transient",
        code="create_pr_failed",
        message=(
            "Authorization: Bearer ghp_abcdefghijklmnopqrstuvwxyz "
            "user@example.org token=abc123"
        ),
        retryable=True,
    )
    serialized = json.dumps(failed)
    assert "abcdefghijklmnopqrstuvwxyz" not in serialized
    assert "user@example.org" not in serialized
    assert "abc123" not in serialized
    assert "metric-owner@example.org" not in serialized
    assert "metric-secret" not in serialized
    assert "?sig=" not in serialized
    assert failed["error"]["redacted"] is True


def test_run_id_rejects_secret_shaped_values(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status")
    with pytest.raises(ValueError, match="Zugangsdaten"):
        store.start(
            "manual",
            run_id="ghp_abcdefghijklmnopqrstuvwxyz",
        )


@pytest.mark.parametrize(
    ("artifact_type", "expected_level", "action_fragment"),
    [
        ("branch", "resume_from_artifact", "Branch"),
        ("commit", "resume_from_artifact", "Commit"),
        ("pull_request", "resume_from_artifact", "Pull Request"),
    ],
)
def test_recovery_detects_reusable_branch_commit_or_pr(
    tmp_path: Path,
    artifact_type: str,
    expected_level: str,
    action_fragment: str,
) -> None:
    target = tmp_path / f"{artifact_type}.json"
    start_run(target, "generator", run_id=f"{artifact_type}-run")
    transition_status_file(target, status="running", phase="create_pr")
    transition_status_file(
        target,
        artifacts=[
            make_artifact(
                artifact_type,
                {
                    "branch": "agent/einheit-15",
                    "commit": "a" * 40,
                    "pull_request": "#123",
                }[artifact_type],
                reusable=True,
            )
        ],
    )
    level, action, new_content = recovery_from_artifacts(read_status(target))
    assert level == expected_level
    assert action_fragment in action
    assert new_content is False


def test_generator_recovery_reuses_same_run_and_blocks_duplicate(
    tmp_path: Path,
) -> None:
    store = StatusStore(tmp_path / "automation" / "status")
    store.start("generator", run_id="generator-1")
    store.update(
        "generator",
        "generator-1",
        status="running",
        phase="create_branch",
    )
    store.artifact(
        "generator",
        "generator-1",
        make_artifact(
            "branch",
            "agent/einheit-15",
            reusable=True,
        ),
    )
    failed = store.fail(
        "generator",
        "generator-1",
        error_class="github_api_transient",
        code="push_timeout",
        message="Push timed out",
        retryable=True,
    )
    with pytest.raises(UnresolvedPreviousRun):
        store.start("generator", run_id="generator-2")

    recovering = store.begin_recovery(
        "generator",
        "generator-1",
        phase="push",
    )
    recovered = store.mark_recovered(
        "generator",
        "generator-1",
        phase="push",
    )
    resumed = store.update(
        "generator",
        "generator-1",
        status="running",
        phase="create_pr",
    )
    success = store.update(
        "generator",
        "generator-1",
        status="success",
        phase="complete",
    )

    assert failed["recovery"]["level"] == "resume_from_artifact"
    assert recovering["run_id"] == recovered["run_id"] == resumed["run_id"] == "generator-1"
    assert success["status"] == "success"
    assert len(list((tmp_path / "automation/status/generator").glob("generator-*.json"))) == 1
    assert read_status(store.latest_path("generator")) == success
    assert store.latest_path("generator").with_suffix(".md").is_file()


def test_older_run_update_cannot_regress_latest_mirror(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status")
    store.start("manual", run_id="older-run")
    store.update(
        "manual",
        "older-run",
        status="running",
        phase="validate",
    )
    store.update(
        "manual",
        "older-run",
        status="success",
        phase="complete",
    )
    newest = store.start("manual", run_id="newest-run")

    store.artifact(
        "manual",
        "older-run",
        make_artifact("report", "late-report", reusable=True),
    )

    assert read_status(store.latest_path("manual")) == newest
    assert read_status(store.path_for("manual", "older-run"))["revision"] == 4


def test_generic_latest_mirror_serializes_different_run_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        automation_status,
        "utc_now",
        lambda: "2026-07-23T12:00:00.000Z",
    )
    latest = tmp_path / "manual/latest.json"
    latest_diagnostic = latest.with_suffix(".md")

    def create(index: int) -> None:
        run_id = f"run-{index:02d}"
        create_status_file(
            tmp_path / f"manual/{run_id}.json",
            "manual",
            run_id=run_id,
            latest_path=latest,
            diagnostic_paths=[latest_diagnostic],
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(create, range(20)))

    newest = read_status(latest)
    assert newest["run_id"] == "run-19"
    assert "Lauf: manual/run-19" in latest_diagnostic.read_text(encoding="utf-8")

    transition_status_file(
        tmp_path / "manual/run-00.json",
        status="running",
        phase="validate",
        latest_path=latest,
        diagnostic_paths=[latest_diagnostic],
    )
    assert read_status(latest) == newest
    assert "Lauf: manual/run-19" in latest_diagnostic.read_text(encoding="utf-8")


def test_end_to_end_interruption_reuses_branch_commit_and_pr_until_merge(
    tmp_path: Path,
) -> None:
    store = StatusStore(tmp_path / "status")
    run_id = "e2e-recovery-run"
    store.start("generator", run_id=run_id)
    for phase in (
        "load_main",
        "check_previous_run",
        "check_existing_pr",
        "read_prompts",
        "research",
        "create_branch",
    ):
        store.update("generator", run_id, status="running", phase=phase)
    for artifact in (
        make_artifact("branch", "agent/einheit-15", reusable=True),
        make_artifact("commit", "b" * 40, reusable=True),
        make_artifact(
            "pull_request",
            "#123",
            url="https://github.com/H234598/ADHS-Lernpfad/pull/123",
            reusable=True,
        ),
    ):
        store.artifact("generator", run_id, artifact)
    store.update("generator", run_id, status="running", phase="wait_review")
    failed = store.fail(
        "generator",
        run_id,
        error_class="validation",
        code="ci_red",
        message="Validate and build failed",
        recovery_level="repair_existing_branch",
        recovery_action="PR #123 auf demselben Branch reparieren",
    )
    assert failed["recovery"]["new_content_required"] is False
    assert len(failed["artifacts"]) == 3

    store.begin_recovery("generator", run_id, phase="repair")
    store.artifact(
        "generator",
        run_id,
        make_artifact("commit", "c" * 40, reusable=True),
    )
    store.mark_recovered("generator", run_id, phase="repair")
    for phase in (
        "wait_review",
        "ready_for_review",
        "verify_second_ci",
        "merge",
        "cleanup",
    ):
        store.update("generator", run_id, status="running", phase=phase)
    store.artifact(
        "generator",
        run_id,
        make_artifact("commit", "d" * 40, reusable=True),
    )
    completed = store.update(
        "generator",
        run_id,
        status="success",
        phase="complete",
    )

    assert completed["run_id"] == run_id
    assert completed["status"] == "success"
    assert completed["completed_phases"][-4:] == [
        "verify_second_ci",
        "merge",
        "cleanup",
        "complete",
    ]
    assert {
        artifact["value"]
        for artifact in completed["artifacts"]
        if artifact["type"] == "pull_request"
    } == {"#123"}
    assert len(list((tmp_path / "status/generator").glob("*run.json"))) == 1


def test_manual_terminal_blocker_requires_acknowledgement(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status")
    store.start("generator", run_id="terminal-run")
    store.update(
        "generator",
        "terminal-run",
        status="running",
        phase="research",
    )
    blocked = store.fail(
        "generator",
        "terminal-run",
        error_class="scientific_review",
        code="evidence_ambiguous",
        message="Scientific assessment needs a human decision",
        recovery_level="manual_intervention",
        recovery_action="Quellenlage manuell prüfen",
    )
    assert blocked["status"] == "blocked"
    assert blocks_new_run(blocked)
    acknowledged = store.acknowledge("generator", "terminal-run")
    assert acknowledged["recovery"]["acknowledged"] is True
    assert not blocks_new_run(acknowledged)


def test_retention_removes_run_but_never_latest(tmp_path: Path) -> None:
    root = tmp_path / "status"
    store = StatusStore(root)
    store.start("manual", run_id="retention-run")
    store.update(
        "manual",
        "retention-run",
        status="running",
        phase="validate",
    )
    store.update(
        "manual",
        "retention-run",
        status="success",
        phase="complete",
    )
    removed = prune_statuses(
        root,
        retention_days=0,
        now=datetime.now(timezone.utc) + timedelta(seconds=1),
    )
    assert store.path_for("manual", "retention-run") in removed
    assert store.latest_path("manual").is_file()


def test_diagnostic_contains_phase_artifacts_error_and_recovery(
    tmp_path: Path,
) -> None:
    store = StatusStore(tmp_path / "status")
    store.start("generator", run_id="diagnostic-run")
    store.update(
        "generator",
        "diagnostic-run",
        status="running",
        phase="commit",
    )
    store.artifact(
        "generator",
        "diagnostic-run",
        make_artifact("commit", "a" * 40, reusable=True),
    )
    failed = store.fail(
        "generator",
        "diagnostic-run",
        error_class="github_api_transient",
        code="push_failed",
        message="GitHub temporarily unavailable",
        retryable=True,
    )
    rendered = render_diagnostic(failed)
    for expected in (
        "ADHS-Automation fehlgeschlagen",
        "Lauf: generator/diagnostic-run",
        "Phase: commit",
        "Commit:",
        "Fehlerklasse: github_api_transient",
        "Recovery-Level: resume_from_artifact",
        "Neuer Inhalt erforderlich: nein",
        "Blockiert nächsten Generatorlauf: ja",
    ):
        assert expected in rendered


def test_cli_end_to_end_and_exit_codes(tmp_path: Path) -> None:
    status_root = tmp_path / "status"
    environment = dict(os.environ, GITHUB_SHA="a" * 40)

    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *arguments],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )

    assert run(
        "start",
        "--root",
        str(status_root),
        "--workflow",
        "generator",
        "--run-id",
        "cli-run",
    ).returncode == EXIT_SUCCESS
    assert run(
        "phase",
        "--root",
        str(status_root),
        "--workflow",
        "generator",
        "--run-id",
        "cli-run",
        "--phase",
        "validate",
    ).returncode == EXIT_SUCCESS
    assert run(
        "artifact",
        "--root",
        str(status_root),
        "--workflow",
        "generator",
        "--run-id",
        "cli-run",
        "--type",
        "branch",
        "--value",
        "agent/einheit-15",
        "--reusable",
    ).returncode == EXIT_SUCCESS
    failed = run(
        "fail",
        "--root",
        str(status_root),
        "--workflow",
        "generator",
        "--run-id",
        "cli-run",
        "--class",
        "validation",
        "--message",
        "Link validation failed",
        "--recovery",
        "repair_existing_branch",
    )
    assert failed.returncode == EXIT_SUCCESS
    inspected = run(
        "inspect",
        "--root",
        str(status_root),
        "--workflow",
        "generator",
        "--latest",
    )
    assert inspected.returncode == EXIT_BLOCKED
    assert "repair_existing_branch" in inspected.stdout


def test_managed_phase_context_finishes_only_standalone_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RUNTIME_STATUS_MANAGED", raising=False)
    standalone = tmp_path / "standalone.json"
    with runtime_phase(standalone, "build_nodes") as metrics:
        metrics["nodes"] = 7
    standalone_payload = read_status(standalone)
    assert standalone_payload["status"] == "success"
    assert standalone_payload["metrics"]["nodes"] == 7

    managed = tmp_path / "managed.json"
    initial = start_run(managed, "knowledge-graph", run_id="outer-run")
    monkeypatch.setenv("RUNTIME_STATUS_MANAGED", "1")
    with runtime_phase(managed, "build_edges") as metrics:
        metrics["edges"] = 6
    managed_payload = read_status(managed)
    assert managed_payload["run_id"] == initial["run_id"]
    assert managed_payload["status"] == "running"
    assert managed_payload["phase"] == "build_edges"


def test_managed_flag_accepts_only_explicit_truthy_values() -> None:
    assert status_is_managed({"RUNTIME_STATUS_MANAGED": "true"})
    assert status_is_managed({"RUNTIME_STATUS_MANAGED": "1"})
    assert not status_is_managed({"RUNTIME_STATUS_MANAGED": "0"})
    assert not status_is_managed({})


def test_validator_reports_invalid_json_without_traceback(tmp_path: Path) -> None:
    target = tmp_path / "broken.json"
    report_json = tmp_path / "runtime-report.json"
    report_md = tmp_path / "runtime-report.md"
    target.write_text("{", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_runtime_status.py"),
            str(target),
            "--report-json",
            str(report_json),
            "--report-md",
            str(report_md),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "ungültig" in result.stdout
    assert "Traceback" not in result.stderr
    assert report_json.is_file() and report_md.is_file()
    assert json.loads(report_json.read_text(encoding="utf-8"))["valid"] is False


def test_validator_rejects_reversed_timestamps_and_nonfinite_metrics(
    tmp_path: Path,
) -> None:
    target = tmp_path / "status.json"
    create_status_file(target, "manual", run_id="semantic-test")
    payload = transition_status_file(target, status="running")
    payload["created_at"] = "2026-07-22T12:00:00Z"
    payload["updated_at"] = "2026-07-22T11:00:00Z"
    payload["metrics"]["non_finite"] = float("nan")
    target.write_text(json.dumps(payload, allow_nan=True), encoding="utf-8")
    errors = validate_file(target)
    assert any("updated_at darf nicht vor created_at" in error for error in errors)
    assert any("reinen JSON-Werte" in error for error in errors)
