from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from automation_run_status import start_run  # noqa: E402
from build_combined import run_build as run_combined  # noqa: E402
from build_graph import run_build as run_graph  # noqa: E402


def _graph_fixture(root: Path, *, broken_link: bool = False) -> None:
    (root / "01-Grundlagen").mkdir(parents=True)
    (root / "knowledge-graph").mkdir()
    (root / "README.md").write_text("# Projekt\n", encoding="utf-8")
    (root / "ROADMAP.md").write_text("# Roadmap\n", encoding="utf-8")
    (root / "Glossar.md").write_text("---\ntitle: Glossar\n---\n# Glossar\n", encoding="utf-8")
    link = "\n[[Nicht vorhanden]]\n" if broken_link else "\n"
    (root / "01-Grundlagen" / "01-Alpha.md").write_text(
        "---\ntitle: Alpha\nlevel: Grundlagen\ntags: []\n---\n# Alpha\n" + link,
        encoding="utf-8",
    )
    (root / "index.json").write_text(
        json.dumps({"chapters": [{"number": 1, "path": "01-Grundlagen/01-Alpha.md"}]}),
        encoding="utf-8",
    )
    (root / "knowledge-graph" / "planned-nodes.yaml").write_text(
        "nodes: []\n", encoding="utf-8",
    )


def test_standalone_graph_build_tracks_every_result_and_artifact(tmp_path: Path, monkeypatch) -> None:
    _graph_fixture(tmp_path)
    monkeypatch.delenv("RUNTIME_STATUS_MANAGED", raising=False)
    monkeypatch.setenv("GITHUB_SHA", "b" * 40)
    status_file = tmp_path / "build" / "runtime-status.json"
    graph, exit_code = run_graph(root=tmp_path, status_file=status_file, scope="all")
    assert exit_code == 0 and graph is not None
    status = json.loads(status_file.read_text(encoding="utf-8"))
    assert status["status"] == status["phase"] == "success"
    assert status["git_sha"] == "b" * 40
    assert status["metrics"]["documents"] == 4
    assert status["metrics"]["chapters"] == 1
    assert status["metrics"]["nodes"] == graph["stats"]["node_count"]
    assert status["metrics"]["edges"] == graph["stats"]["edge_count"]
    assert set(status["artifacts"]) == {
        "build/knowledge-graph/knowledge-graph.json",
        "build/knowledge-graph/knowledge-graph.graphml",
        "build/knowledge-graph/knowledge-graph.mmd",
        "build/knowledge-graph/graph-report.json",
        "build/knowledge-graph/graph-report.md",
    }


def test_managed_graph_build_preserves_outer_run_identity(tmp_path: Path, monkeypatch) -> None:
    _graph_fixture(tmp_path)
    status_file = tmp_path / "build" / "runtime-status.json"
    outer = start_run(status_file, "outer", run_id="outer-run", git_sha="a" * 40)
    monkeypatch.setenv("RUNTIME_STATUS_MANAGED", "1")
    graph, exit_code = run_graph(root=tmp_path, status_file=status_file)
    assert exit_code == 0 and graph is not None
    status = json.loads(status_file.read_text(encoding="utf-8"))
    assert status["run_id"] == outer["run_id"] == "outer-run"
    assert status["started_at"] == outer["started_at"]
    assert status["workflow"] == "outer"
    assert status["status"] == "running"
    assert status["phase"] == "export"


def test_graph_validation_failure_records_recovery_and_reports(tmp_path: Path, monkeypatch) -> None:
    _graph_fixture(tmp_path, broken_link=True)
    monkeypatch.delenv("RUNTIME_STATUS_MANAGED", raising=False)
    status_file = tmp_path / "build" / "runtime-status.json"
    graph, exit_code = run_graph(root=tmp_path, status_file=status_file)
    assert exit_code == 1 and graph is not None
    status = json.loads(status_file.read_text(encoding="utf-8"))
    assert status["status"] == "failed"
    assert status["phase"] == "validate_graph"
    assert status["error_class"] == "graph_validation_error"
    assert status["recovery_action"] == "fix_graph_and_retry_validation"
    assert status["metrics"]["errors"] == graph["stats"]["error_count"] == 1
    report = json.loads(
        (tmp_path / "build" / "knowledge-graph" / "graph-report.json").read_text(encoding="utf-8")
    )
    assert report["valid"] is False
    assert report["validation"]["error_count"] > 0


def test_combined_builder_tracks_load_export_and_success(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "01-Grundlagen").mkdir()
    (tmp_path / "references").mkdir()
    (tmp_path / "00-Einfuehrung.md").write_text("# Einführung\n", encoding="utf-8")
    (tmp_path / "01-Grundlagen" / "01-Alpha.md").write_text("# Alpha\n", encoding="utf-8")
    (tmp_path / "Glossar.md").write_text("# Glossar\n", encoding="utf-8")
    (tmp_path / "Literatur.md").write_text("# Literatur\n", encoding="utf-8")
    (tmp_path / "references" / "Ref.md").write_text("# Quelle\n", encoding="utf-8")
    (tmp_path / "index.json").write_text(
        json.dumps({"chapters": [{"path": "01-Grundlagen/01-Alpha.md"}]}),
        encoding="utf-8",
    )
    monkeypatch.delenv("RUNTIME_STATUS_MANAGED", raising=False)
    status_file = tmp_path / "build" / "runtime-status.json"
    assert run_combined(root=tmp_path, status_file=status_file) == 0
    status = json.loads(status_file.read_text(encoding="utf-8"))
    assert status["status"] == status["phase"] == "success"
    assert status["metrics"] == {"documents": 4, "chapters": 1, "sources": 1}
    assert status["artifacts"] == ["build/ADHS-Lernpfad-Gesamtdokument.md"]
