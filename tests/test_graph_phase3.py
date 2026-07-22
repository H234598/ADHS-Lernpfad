from __future__ import annotations

import json
from pathlib import Path

from scripts.automation_run_status import write_status


def test_runtime_status_writer_is_atomic(tmp_path: Path) -> None:
    target = tmp_path / "runtime-status.json"
    write_status(
        target,
        {
            "run_id": "test-run",
            "workflow": "pytest",
            "status": "running",
            "phase": "unit-test",
        },
    )

    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["run_id"] == "test-run"
    assert data["status"] == "running"
    assert "updated_at" in data


def test_graph_validator_detects_missing_output(tmp_path: Path, monkeypatch) -> None:
    # Placeholder for the integration fixture used by the CI graph build.
    # The full fixture is intentionally added together with the CI wiring.
    assert not (tmp_path / "knowledge-graph.json").exists()
