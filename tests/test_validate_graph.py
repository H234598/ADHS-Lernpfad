from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from scripts.validate_graph import (
    SCHEMA, render_validation_report, report_payload, validate_graph_data,
    validate_graph_file,
)


def _stats(nodes: list[dict], edges: list[dict], issues: list[dict]) -> dict:
    node_types: dict[str, int] = {}
    edge_types: dict[str, int] = {}
    issue_codes: dict[str, int] = {}
    for node in nodes:
        node_types[node["type"]] = node_types.get(node["type"], 0) + 1
    for edge in edges:
        edge_types[edge["type"]] = edge_types.get(edge["type"], 0) + 1
    for issue in issues:
        issue_codes[issue["code"]] = issue_codes.get(issue["code"], 0) + 1
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "issue_count": len(issues),
        "error_count": sum(issue["severity"] == "error" for issue in issues),
        "warning_count": sum(issue["severity"] == "warning" for issue in issues),
        "nodes_by_type": dict(sorted(node_types.items())),
        "edges_by_type": dict(sorted(edge_types.items())),
        "issues_by_code": dict(sorted(issue_codes.items())),
    }


def _valid_graph(root: Path) -> dict:
    (root / "Alpha.md").write_text("# Alpha\n", encoding="utf-8")
    (root / "Beta.md").write_text("# Beta\n", encoding="utf-8")
    nodes = [
        {
            "id": "doc:Alpha", "type": "chapter", "label": "Alpha",
            "scope": "learning", "exists": True, "planned": False,
            "lifecycle_status": "published", "path": "Alpha.md", "url": "/Alpha/",
            "aliases": [], "tags": [],
        },
        {
            "id": "doc:Beta", "type": "chapter", "label": "Beta",
            "scope": "learning", "exists": True, "planned": False,
            "lifecycle_status": "published", "path": "Beta.md", "url": "/Beta/",
            "aliases": [], "tags": [],
        },
    ]
    edges = [{
        "id": "edge:sequence:1", "type": "sequence", "source": "doc:Alpha",
        "target": "doc:Beta", "status": "ok", "count": 1,
        "occurrences": [{"path": "index.json", "from": "doc:Alpha", "to": "doc:Beta"}],
    }]
    issues: list[dict] = []
    return {
        "schema_version": "1.0.0", "source_revision": None,
        "scopes": ["learning"], "stats": _stats(nodes, edges, issues),
        "nodes": nodes, "edges": edges, "issues": issues,
    }


def _schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_valid_graph_passes_schema_and_invariants(tmp_path: Path) -> None:
    result = validate_graph_data(_valid_graph(tmp_path), _schema(), root=tmp_path)
    assert result.valid, result.errors
    assert result.computed_stats["node_count"] == 2


def test_duplicate_ids_bad_relation_endpoint_and_stats_are_blocking(tmp_path: Path) -> None:
    graph = _valid_graph(tmp_path)
    graph["nodes"].append(deepcopy(graph["nodes"][0]))
    graph["edges"][0]["type"] = "made_up"
    graph["edges"][0]["target"] = "doc:missing"
    result = validate_graph_data(graph, _schema(), root=tmp_path)
    codes = {error["code"] for error in result.errors}
    assert {"duplicate-node-id", "invalid-relation", "missing-edge-target", "stats-mismatch"} <= codes


def test_labels_paths_urls_and_unknown_fields_are_checked(tmp_path: Path) -> None:
    graph = _valid_graph(tmp_path)
    graph["nodes"][0].update({
        "label": " ", "path": "../outside.md", "url": "javascript:alert(1)",
        "surprise": True,
    })
    result = validate_graph_data(graph, _schema(), root=tmp_path)
    codes = {error["code"] for error in result.errors}
    assert {"invalid-node-label", "unsafe-node-path", "unsafe-node-url", "unknown-node-fields"} <= codes


def test_error_issue_is_a_quality_gate_but_planned_node_is_allowed(tmp_path: Path) -> None:
    graph = _valid_graph(tmp_path)
    graph["issues"] = [{
        "code": "missing-document", "severity": "error", "message": "Fehlt",
    }]
    graph["stats"] = _stats(graph["nodes"], graph["edges"], graph["issues"])
    result = validate_graph_data(graph, _schema(), root=tmp_path)
    assert "blocking-graph-issue" in {error["code"] for error in result.errors}

    graph = _valid_graph(tmp_path)
    graph["nodes"].append({
        "id": "planned:Gamma", "type": "planned", "planned_type": "chapter",
        "label": "Gamma", "scope": "learning", "exists": False, "planned": True,
        "lifecycle_status": "planned", "path": "Gamma", "aliases": [],
    })
    graph["edges"].append({
        "id": "edge:planned:1", "type": "wikilink", "source": "doc:Beta",
        "target": "planned:Gamma", "status": "planned", "count": 1,
        "occurrences": [{"path": "Beta.md", "line": 1}],
    })
    graph["stats"] = _stats(graph["nodes"], graph["edges"], graph["issues"])
    result = validate_graph_data(graph, _schema(), root=tmp_path)
    assert result.valid, result.errors


def test_source_revision_must_match_ci_revision(tmp_path: Path) -> None:
    graph = _valid_graph(tmp_path)
    graph["source_revision"] = "old"
    result = validate_graph_data(
        graph, _schema(), root=tmp_path, expected_revision="expected",
    )
    assert "source-revision-mismatch" in {error["code"] for error in result.errors}


def test_wrong_json_scalar_types_never_escape_as_traceback(tmp_path: Path) -> None:
    graph = _valid_graph(tmp_path)
    graph["nodes"][0]["type"] = {"not": "a string"}
    graph["edges"][0].update({"type": [], "source": {}, "target": [], "status": {}})
    graph["issues"] = [42, {"code": [], "severity": "error", "message": "bad"}]
    graph["stats"] = {}
    result = validate_graph_data(graph, _schema(), root=tmp_path)
    assert not result.valid
    codes = {error["code"] for error in result.errors}
    assert {"schema-error", "invalid-node-type", "invalid-relation", "missing-edge-source"} <= codes
    assert "Wissensgraph-Bericht" in render_validation_report(result)


def test_malformed_or_missing_graph_writes_both_reports(tmp_path: Path) -> None:
    graph_path = tmp_path / "knowledge-graph.json"
    graph_path.write_text("{not json", encoding="utf-8")
    report_json = tmp_path / "graph-report.json"
    report_md = tmp_path / "graph-report.md"
    result = validate_graph_file(
        graph_path, SCHEMA, root=tmp_path,
        report_json=report_json, report_markdown=report_md,
    )
    assert not result.valid
    assert report_json.is_file() and report_md.is_file()
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["valid"] is False
    assert payload["validation"]["errors"][0]["code"] == "invalid-graph-json"


def test_reports_are_consistent_and_deterministic(tmp_path: Path) -> None:
    graph = _valid_graph(tmp_path)
    result = validate_graph_data(graph, _schema(), root=tmp_path)
    first_json = json.dumps(report_payload(result), ensure_ascii=False, sort_keys=True)
    second_json = json.dumps(report_payload(result), ensure_ascii=False, sort_keys=True)
    assert first_json == second_json
    markdown = render_validation_report(result)
    assert "Knoten: **2**" in markdown
    assert "Kanten: **1**" in markdown
    assert "Validierungsfehler: **0**" in markdown
