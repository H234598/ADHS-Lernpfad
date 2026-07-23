from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.automation_status import (
    StatusStore,
    make_artifact,
)
from scripts.persist_automation_status import (
    MAX_STATUS_BYTES,
    discover_status,
    merge_snapshot,
    prepare_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]


def _successful_status(path: Path, run_id: str = "persist-run") -> dict:
    store = StatusStore(path.parent / "canonical")
    status = store.start("generator", run_id=run_id)
    status = store.update(
        "generator",
        run_id,
        status="running",
        phase="create_branch",
    )
    status = store.artifact(
        "generator",
        run_id,
        make_artifact(
            "branch",
            "agent/einheit-15",
            reusable=True,
        ),
    )
    status = store.update(
        "generator",
        run_id,
        status="success",
        phase="complete",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return status


def test_prepare_snapshot_writes_only_status_and_redacted_diagnosis(
    tmp_path: Path,
) -> None:
    source = tmp_path / "incoming" / "runtime-status.json"
    expected = _successful_status(source)
    output = tmp_path / "snapshot"
    actual = prepare_snapshot(source, output)

    status_dir = output / "automation/status/generator"
    assert actual == expected
    assert json.loads(
        (status_dir / "persist-run.json").read_text(encoding="utf-8")
    ) == expected
    assert (status_dir / "latest.json").read_bytes() == (
        status_dir / "persist-run.json"
    ).read_bytes()
    diagnosis = (status_dir / "latest.md").read_text(encoding="utf-8")
    assert "Lauf: generator/persist-run" in diagnosis
    assert "agent/einheit-15" in diagnosis
    assert (output / "README.md").is_file()
    assert (output / ".nojekyll").is_file()
    assert not (output / "scripts").exists()


def test_discovery_requires_exactly_one_regular_status(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Genau eine"):
        discover_status(tmp_path)
    first = tmp_path / "one/runtime-status.json"
    _successful_status(first)
    assert discover_status(tmp_path) == first
    second = tmp_path / "two/runtime-status.json"
    second.parent.mkdir()
    second.write_bytes(first.read_bytes())
    with pytest.raises(ValueError, match="gefunden: 2"):
        discover_status(tmp_path)


def test_snapshot_rejects_invalid_and_oversized_status(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"status":"success"}', encoding="utf-8")
    with pytest.raises(ValueError, match="ungültig"):
        prepare_snapshot(invalid, tmp_path / "invalid-output")

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"{" + b" " * MAX_STATUS_BYTES + b"}")
    with pytest.raises(ValueError, match="überschreitet"):
        prepare_snapshot(oversized, tmp_path / "oversized-output")


def test_merge_snapshot_keeps_newer_latest_when_deliveries_arrive_out_of_order(
    tmp_path: Path,
) -> None:
    older_source = tmp_path / "older/incoming/runtime-status.json"
    newer_source = tmp_path / "newer/incoming/runtime-status.json"
    older = _successful_status(older_source, "older-run")
    newer = _successful_status(newer_source, "newer-run")
    older["created_at"] = "2026-07-22T08:00:00.000Z"
    older["updated_at"] = "2026-07-22T08:01:00.000Z"
    older["ended_at"] = "2026-07-22T08:01:00.000Z"
    older["retention_until"] = "2026-08-21T08:01:00.000Z"
    older["duration_seconds"] = 60.0
    newer["created_at"] = "2026-07-23T08:00:00.000Z"
    newer["updated_at"] = "2026-07-23T08:01:00.000Z"
    newer["ended_at"] = "2026-07-23T08:01:00.000Z"
    newer["retention_until"] = "2026-08-22T08:01:00.000Z"
    newer["duration_seconds"] = 60.0
    older_source.write_text(json.dumps(older), encoding="utf-8")
    newer_source.write_text(json.dumps(newer), encoding="utf-8")

    older_snapshot = tmp_path / "older/snapshot"
    newer_snapshot = tmp_path / "newer/snapshot"
    branch = tmp_path / "branch"
    prepare_snapshot(older_source, older_snapshot)
    prepare_snapshot(newer_source, newer_snapshot)
    merge_snapshot(newer_snapshot, branch)
    merge_snapshot(older_snapshot, branch)

    status_dir = branch / "automation/status/generator"
    assert json.loads(
        (status_dir / "latest.json").read_text(encoding="utf-8")
    )["run_id"] == "newer-run"
    assert (status_dir / "older-run.json").is_file()
    assert (status_dir / "newer-run.json").is_file()


def test_workflow_uses_trusted_main_and_has_fallback_diagnosis() -> None:
    workflow = (
        ROOT / ".github/workflows/persist-automation-status.yml"
    ).read_text(encoding="utf-8")
    assert "ref: main" in workflow
    assert "head_repository.full_name == github.repository" in workflow
    assert "without executing them" in workflow
    assert "jsonschema==4.26.0" in workflow
    assert "Statusbranch: **Schreibvorgang fehlgeschlagen**" in workflow
    assert "persisted-status-fallback-" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "--snapshot-root build/status-snapshot" in workflow
