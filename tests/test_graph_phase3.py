from __future__ import annotations

import json
from pathlib import Path

from scripts.automation_run_status import write_status
from scripts.validate_graph import SCHEMA, validate_graph_file


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
    graph = tmp_path / "knowledge-graph.json"
    report_json = tmp_path / "graph-report.json"
    report_md = tmp_path / "graph-report.md"
    result = validate_graph_file(
        graph,
        SCHEMA,
        root=tmp_path,
        report_json=report_json,
        report_markdown=report_md,
    )
    assert not result.valid
    assert result.errors[0]["code"] == "missing-graph"
    assert report_json.is_file()
    assert report_md.is_file()
