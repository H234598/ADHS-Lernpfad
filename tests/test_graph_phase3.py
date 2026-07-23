from __future__ import annotations

import json
from pathlib import Path

from scripts.automation_run_status import write_status
from scripts.validate_graph import SCHEMA, validate_graph_file


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_status_writer_is_atomic(tmp_path: Path) -> None:
    target = tmp_path / "runtime-status.json"
    write_status(
        target,
        {
            "run_id": "test-run",
            "workflow": "manual",
            "status": "running",
            "phase": "validate",
        },
    )

    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["run_id"] == "test-run"
    assert data["status"] == "running"
    assert "updated_at" in data


def test_phase3_has_no_bootstrap_or_retry_self_modifying_files() -> None:
    forbidden = [
        ".graph-pipeline-final",
        ".graph-pipeline-retry",
        ".graph-web-bootstrap",
        ".graph-web-final",
        ".github/workflows/apply-graph-pipeline-final.yml",
        ".github/workflows/retry-graph-pipeline-final.yml",
        ".github/workflows/apply-graph-web-final.yml",
        ".github/workflows/apply-graph-web-phase.yml",
    ]
    assert all(not (ROOT / relative).exists() for relative in forbidden)


def test_phase3_acceptance_files_and_preview_first_gate_last_order_exist() -> None:
    required = [
        "scripts/validate_graph.py",
        "scripts/graph_ci_summary.py",
        "tests/web/knowledge-graph.spec.mjs",
        "knowledge-graph/knowledge-graph.schema.json",
        "knowledge-graph/planned-nodes.yaml",
    ]
    assert all((ROOT / relative).is_file() for relative in required)
    workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
    assert workflow.index("Build diagnostic web preview") < workflow.index(
        "Enforce validation result"
    )
    for artifact in (
        "knowledge-graph.json",
        "knowledge-graph.graphml",
        "knowledge-graph.mmd",
        "graph-report.json",
        "graph-report.md",
    ):
        assert artifact in (
            ROOT / "scripts/build_exports.py"
        ).read_text(encoding="utf-8")


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
