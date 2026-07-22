"""Regression tests for runtime status helper interfaces.

These tests intentionally verify the contract of the runtime status layer without
requiring a full GitHub Actions environment.
"""

from pathlib import Path
import json
import os
import subprocess
import sys

from scripts.automation_run_status import (
    DEFAULT_STATUS_PATH,
    finish_run,
    start_run,
    status_is_managed,
    update_status,
    validate_status,
    write_status,
)
from scripts.validate_runtime_status import validate_file
from scripts.runtime_status_phase import runtime_phase


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_status_schema_exists():
    schema = ROOT / "automation" / "schema" / "run-status.schema.json"
    assert schema.exists()
    data = json.loads(schema.read_text(encoding="utf-8"))
    assert data["type"] == "object"


def test_default_status_is_an_ignored_build_artifact():
    assert DEFAULT_STATUS_PATH == Path("build/runtime-status.json")


def test_runtime_status_tools_exist():
    expected = [
        ROOT / "scripts" / "automation_run_status.py",
        ROOT / "scripts" / "runtime_status_cli.py",
        ROOT / "scripts" / "runtime_status_phase.py",
        ROOT / "scripts" / "validate_runtime_status.py",
    ]
    assert all(path.exists() for path in expected)


def test_runtime_status_cli_help():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "runtime_status_cli.py"), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "status" in result.stdout.lower()


def test_start_update_finish_preserves_identity_and_merges_data(tmp_path):
    target = tmp_path / "runtime-status.json"
    started = start_run(
        target,
        "graph-test",
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
    finished = finish_run(
        target,
        success=True,
        metrics={"nodes": 12},
        artifacts=["build/knowledge-graph.json"],
    )

    assert running["run_id"] == started["run_id"] == finished["run_id"]
    assert running["started_at"] == started["started_at"] == finished["started_at"]
    assert finished["status"] == finished["phase"] == "success"
    assert finished["duration_seconds"] >= 0
    assert finished["metrics"] == {"documents": 4, "nodes": 12}
    assert finished["artifacts"] == [
        "build/source-index.json",
        "build/knowledge-graph.json",
    ]
    assert validate_status(finished) == []


def test_failed_finish_supplies_recovery_fields_for_partial_input(tmp_path):
    target = tmp_path / "runtime-status.json"
    # A missing/corrupt predecessor must not result in a partial status file.
    target.write_text("not-json", encoding="utf-8")
    failed = finish_run(target, success=False, phase="validate_graph")

    assert failed["status"] == "failed"
    assert failed["phase"] == "validate_graph"
    assert failed["error_class"] == "unknown_error"
    assert failed["error_message"]
    assert failed["recovery_action"] == "inspect_logs"
    assert validate_status(failed) == []


def test_write_status_is_atomic_and_leaves_no_temporary_file(tmp_path):
    target = tmp_path / "nested" / "runtime-status.json"
    payload = write_status(target, {"workflow": "partial-input"})

    assert json.loads(target.read_text(encoding="utf-8")) == payload
    assert list(target.parent.glob(f".{target.name}.*.tmp")) == []


def test_partial_input_with_wrong_scalar_types_is_normalised(tmp_path):
    target = tmp_path / "wrong-types.json"
    payload = write_status(
        target,
        {
            "run_id": None,
            "workflow": None,
            "git_sha": 42,
            "status": ["running"],
            "phase": {"unexpected": True},
            "metrics": None,
            "artifacts": None,
        },
    )
    assert payload["run_id"]
    assert payload["workflow"] == "knowledge-graph"
    assert payload["git_sha"] == "unknown"
    assert payload["status"] == "running"
    assert payload["phase"] == "initialization"
    assert validate_status(payload) == []


def test_managed_flag_accepts_only_explicit_truthy_values():
    assert status_is_managed({"RUNTIME_STATUS_MANAGED": "true"})
    assert status_is_managed({"RUNTIME_STATUS_MANAGED": "1"})
    assert not status_is_managed({"RUNTIME_STATUS_MANAGED": "0"})
    assert not status_is_managed({})


def test_phase_context_finishes_standalone_but_not_managed_run(tmp_path):
    standalone = tmp_path / "standalone.json"
    with runtime_phase(standalone, "build_nodes") as metrics:
        metrics["nodes"] = 7
    standalone_payload = json.loads(standalone.read_text(encoding="utf-8"))
    assert standalone_payload["status"] == "success"
    assert standalone_payload["metrics"]["nodes"] == 7

    managed = tmp_path / "managed.json"
    initial = start_run(managed, "outer-workflow", run_id="outer-run")
    previous = os.environ.get("RUNTIME_STATUS_MANAGED")
    os.environ["RUNTIME_STATUS_MANAGED"] = "1"
    try:
        with runtime_phase(managed, "build_edges") as metrics:
            metrics["edges"] = 6
    finally:
        if previous is None:
            os.environ.pop("RUNTIME_STATUS_MANAGED", None)
        else:
            os.environ["RUNTIME_STATUS_MANAGED"] = previous
    managed_payload = json.loads(managed.read_text(encoding="utf-8"))
    assert managed_payload["run_id"] == initial["run_id"] == "outer-run"
    assert managed_payload["started_at"] == initial["started_at"]
    assert managed_payload["status"] == "running"
    assert managed_payload["phase"] == "build_edges"
    assert managed_payload["metrics"]["edges"] == 6


def test_cli_records_metrics_artifacts_and_failure(tmp_path):
    target = tmp_path / "cli-status.json"
    environment = dict(os.environ, GITHUB_SHA="a" * 40)
    start = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "runtime_status_cli.py"),
            str(target),
            "--new-run",
            "--workflow",
            "cli-test",
            "--run-id",
            "cli-run",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    finish = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "runtime_status_cli.py"),
            str(target),
            "--finish",
            "failed",
            "--phase",
            "build_edges",
            "--metric",
            "edges=8",
            "--artifact",
            "build/partial.json",
            "--error-class",
            "ValueError",
            "--error-message",
            "edge target missing",
            "--recovery-action",
            "retry_validation",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert start.returncode == 0, start.stderr
    assert finish.returncode == 0, finish.stderr
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["run_id"] == "cli-run"
    assert payload["phase"] == "build_edges"
    assert payload["metrics"]["edges"] == 8
    assert payload["error_class"] == "ValueError"
    assert validate_file(target) == []


def test_validator_reports_invalid_json_without_traceback(tmp_path):
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
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["valid"] is False
    assert payload["error_count"] > 0
    original_report = report_md.read_text(encoding="utf-8")
    assert "gültiges UTF-8-JSON" in original_report

    # A workflow ERR trap may replace the invalid status with a normalized
    # failed status, but the validator's original diagnosis remains intact.
    finish_run(target, success=False, phase="validate_graph")
    assert report_md.read_text(encoding="utf-8") == original_report


def test_validator_rejects_a_parseable_but_broken_schema(tmp_path):
    target = tmp_path / "status.json"
    schema = tmp_path / "schema.json"
    start_run(target, "schema-check")
    schema.write_text('{"type": "object"}', encoding="utf-8")
    errors = validate_file(target, schema)
    assert any("schema" in error.lower() for error in errors)


def test_validator_always_runs_semantic_checks_with_jsonschema_installed(tmp_path):
    target = tmp_path / "status.json"
    payload = finish_run(
        tmp_path / "seed.json",
        success=True,
    )
    payload["metrics"]["non_finite"] = float("nan")
    target.write_text(json.dumps(payload, allow_nan=True), encoding="utf-8")

    errors = validate_file(target)
    assert any("JSON-compatible" in error for error in errors)


def test_validator_rejects_reversed_timestamps_and_stale_success_errors(tmp_path):
    target = tmp_path / "status.json"
    payload = finish_run(tmp_path / "seed.json", success=True)
    payload.update({
        "started_at": "2026-07-22T12:00:00Z",
        "ended_at": "2026-07-22T10:00:00Z",
        "updated_at": "2026-07-22T11:00:00Z",
        "error_class": "stale_error",
        "error_message": "stale message",
        "recovery_action": "stale_action",
    })
    target.write_text(json.dumps(payload), encoding="utf-8")

    errors = validate_file(target)
    assert any("ended_at must not be before started_at" in error for error in errors)
    assert any("updated_at must not be before started_at" in error for error in errors)
    assert any("must be null for a successful status" in error for error in errors)
