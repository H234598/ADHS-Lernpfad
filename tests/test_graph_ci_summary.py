from __future__ import annotations

import json
from pathlib import Path

from scripts.graph_ci_summary import build_summary, main


def test_summary_contains_status_duration_phase_and_all_counts() -> None:
    graph = {
        "stats": {"node_count": 4, "edge_count": 3, "error_count": 1, "warning_count": 2},
        "nodes": [
            {"type": "chapter"}, {"type": "planned", "planned": True},
            {"type": "placeholder"}, {"type": "concept"},
        ],
        "edges": [{}, {}, {}],
        "issues": [],
    }
    runtime = {
        "run_id": "run-1", "workflow": "knowledge-graph", "revision": 4,
        "context": {
            "commit_sha": "abc1234", "branch": "agent/test", "pr_number": 42,
        },
        "status": "failed", "phase": "validate_graph", "duration_seconds": 4.25,
        "completed_phases": ["load_content", "build_nodes", "build_edges"],
        "artifacts": [],
        "error": {
            "class": "validation", "code": "graph_validation_error",
            "message": "Defekter Link",
        },
        "recovery": {
            "level": "retry_same_phase", "action": "fix_graph_and_retry",
            "new_content_required": False, "block_next_run": True,
            "acknowledged": False,
        },
    }
    summary = build_summary(graph, runtime)
    for expected in (
        "Status: **failed**", "Letzte Phase: **validate_graph**", "Laufzeit: **4.25 s**",
        "Knoten: **4**", "Kanten: **3**", "Fehler: **1**", "Warnungen: **2**",
        "Geplante Seiten: **1**", "Fehlende Seiten/Abschnitte: **1**",
        "graph_validation_error", "fix_graph_and_retry",
        "Blockiert den nächsten Generatorlauf: **ja**",
    ):
        assert expected in summary


def test_partial_runtime_metrics_are_used_without_graph() -> None:
    runtime = {
        "status": "failed", "phase": "build_edges",
        "metrics": {"nodes": 8, "edges": 4, "errors": 2, "missing_pages": 2},
    }
    summary = build_summary({}, runtime, input_problems=["Graph fehlt"])
    assert "Knoten: **8**" in summary
    assert "Kanten: **4**" in summary
    assert "Fehler: **2**" in summary
    assert "Fehlende Seiten/Abschnitte: **2**" in summary
    assert "Graph fehlt" in summary


def test_cli_survives_missing_and_malformed_inputs(tmp_path: Path) -> None:
    graph = tmp_path / "graph.json"
    graph.write_text("not json", encoding="utf-8")
    output = tmp_path / "summary.md"
    github_summary = tmp_path / "step-summary.md"
    assert main([
        "--graph", str(graph), "--status", str(tmp_path / "missing-status.json"),
        "--output", str(output), "--github-summary", str(github_summary),
    ]) == 0
    text = output.read_text(encoding="utf-8")
    assert "Unvollständige Diagnoseeingaben" in text
    assert "nicht lesbar" in text and "fehlt" in text
    assert github_summary.read_text(encoding="utf-8") == text


def test_cli_reads_valid_partial_files(tmp_path: Path) -> None:
    graph = tmp_path / "graph.json"
    status = tmp_path / "status.json"
    output = tmp_path / "summary.md"
    graph.write_text(json.dumps({"nodes": [], "edges": [], "issues": []}), encoding="utf-8")
    status.write_text(json.dumps({"status": "running", "phase": "export"}), encoding="utf-8")
    assert main([
        "--graph", str(graph), "--status", str(status), "--output", str(output),
    ]) == 0
    rendered = output.read_text(encoding="utf-8")
    assert "Status: **running**" in rendered
    assert "Runtime-Status verletzt das Schema" in rendered
