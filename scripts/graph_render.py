#!/usr/bin/env python3
"""Render canonical graph data as JSON, Mermaid, GraphML and reports."""

from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import shutil
from typing import Any


def _stable_id(value: str, prefix: str, length: int = 16) -> str:
    return prefix + hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def _escape_mermaid(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', "'").replace("[", "(").replace("]", ")")


def _selected_node_ids(graph: dict[str, Any], scope: str) -> set[str]:
    if scope == "all":
        return {str(node["id"]) for node in graph["nodes"]}
    selected = {
        str(node["id"]) for node in graph["nodes"]
        if node.get("scope") in {"learning", "concept"}
        or node.get("type") in {"planned", "placeholder"}
    }
    for edge in graph["edges"]:
        if (
            edge["source"] in selected
            and edge["type"] in {"cites", "wikilink", "prerequisite", "related"}
        ):
            selected.add(str(edge["target"]))
    return selected


def render_mermaid(graph: dict[str, Any], scope: str = "learning") -> str:
    selected = _selected_node_ids(graph, scope)
    nodes = [node for node in graph["nodes"] if node["id"] in selected]
    edges = [
        edge for edge in graph["edges"]
        if edge["source"] in selected and edge["target"] in selected
    ]
    lines = ["flowchart LR"]
    for node in nodes:
        node_id = _stable_id(str(node["id"]), "N", 14)
        label = _escape_mermaid(str(node.get("label") or node["id"]))
        left, right = ("((", "))") if node["type"] == "concept" else ("[", "]")
        if node["type"] == "reference":
            left, right = "{", "}"
        lines.append(f'  {node_id}{left}"{label}"{right}')
        css = (
            "planned" if node.get("planned")
            else "missing" if node["type"] == "placeholder"
            else str(node["type"])
        )
        lines.append(f"  class {node_id} {css}")
    for edge in edges:
        arrow = "-.->" if edge.get("status") != "ok" or edge["type"] == "planned_in" else "-->"
        label = _escape_mermaid(str(edge["type"]))
        lines.append(
            f"  {_stable_id(edge['source'], 'N', 14)} {arrow}|{label}| "
            f"{_stable_id(edge['target'], 'N', 14)}"
        )
    lines.extend([
        "  classDef chapter fill:#e3f2fd,stroke:#1565c0,stroke-width:1.5px",
        "  classDef intro fill:#e8eaf6,stroke:#3949ab",
        "  classDef glossary fill:#e0f2f1,stroke:#00897b",
        "  classDef concept fill:#fff8e1,stroke:#f9a825",
        "  classDef section fill:#f1f8e9,stroke:#689f38",
        "  classDef reference fill:#f3e5f5,stroke:#7b1fa2",
        "  classDef document fill:#fafafa,stroke:#616161",
        "  classDef planned fill:#fff3e0,stroke:#ef6c00,stroke-dasharray:5 4",
        "  classDef missing fill:#ffebee,stroke:#c62828,stroke-width:2px,stroke-dasharray:3 3",
    ])
    return "\n".join(lines) + "\n"


def render_graphml(graph: dict[str, Any]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <key id="canonical_id" for="node" attr.name="canonical_id" attr.type="string"/>',
        '  <key id="label" for="node" attr.name="label" attr.type="string"/>',
        '  <key id="type" for="all" attr.name="type" attr.type="string"/>',
        '  <key id="status" for="edge" attr.name="status" attr.type="string"/>',
        '  <key id="url" for="node" attr.name="url" attr.type="string"/>',
        '  <graph id="ADHS_Lernpfad" edgedefault="directed">',
    ]
    for node in graph["nodes"]:
        canonical = str(node["id"])
        lines.append(f'    <node id="{_stable_id(canonical, "n", 20)}">')
        lines.append(f'      <data key="canonical_id">{html.escape(canonical)}</data>')
        lines.append(f'      <data key="label">{html.escape(str(node.get("label", canonical)))}</data>')
        lines.append(f'      <data key="type">{html.escape(str(node.get("type", "document")))}</data>')
        if node.get("url"):
            lines.append(f'      <data key="url">{html.escape(str(node["url"]))}</data>')
        lines.append("    </node>")
    for edge in graph["edges"]:
        lines.append(
            f'    <edge id="{_stable_id(str(edge["id"]), "e", 20)}" '
            f'source="{_stable_id(str(edge["source"]), "n", 20)}" '
            f'target="{_stable_id(str(edge["target"]), "n", 20)}">'
        )
        lines.append(f'      <data key="type">{html.escape(str(edge["type"]))}</data>')
        lines.append(f'      <data key="status">{html.escape(str(edge.get("status", "ok")))}</data>')
        lines.append("    </edge>")
    return "\n".join([*lines, "  </graph>", "</graphml>"]) + "\n"


def render_report(graph: dict[str, Any]) -> str:
    stats = graph["stats"]
    lines = [
        "# Wissensgraph-Bericht", "",
        f"- Schema: `{graph['schema_version']}`",
        f"- Quellrevision: `{graph.get('source_revision') or 'nicht verfügbar'}`",
        f"- Knoten: **{stats['node_count']}**",
        f"- Kanten: **{stats['edge_count']}**",
        f"- Fehler: **{stats['error_count']}**",
        f"- Warnungen: **{stats['warning_count']}**", "",
        "## Knoten nach Typ", "",
    ]
    lines.extend(f"- `{key}`: {value}" for key, value in stats["nodes_by_type"].items())
    lines.extend(["", "## Kanten nach Typ", ""])
    lines.extend(f"- `{key}`: {value}" for key, value in stats["edges_by_type"].items())
    lines.extend(["", "## Probleme", ""])
    if not graph["issues"]:
        lines.append("- keine")
    for issue in graph["issues"]:
        location = str(issue.get("path", "Repository"))
        if issue.get("line"):
            location += f":{issue['line']}"
        if issue.get("column"):
            location += f":{issue['column']}"
        lines.append(
            f"- **{issue.get('severity', 'error')} · `{issue.get('code', 'unknown')}`** — "
            f"{location}: {issue.get('message', '')}"
        )
    return "\n".join(lines) + "\n"


def write_outputs(
    graph: dict[str, Any], root: Path, *, scope: str = "learning",
) -> None:
    output = root / "build" / "knowledge-graph"
    output.mkdir(parents=True, exist_ok=True)
    files = {
        "knowledge-graph.json": json.dumps(graph, ensure_ascii=False, indent=2) + "\n",
        "knowledge-graph.mmd": render_mermaid(graph, scope),
        "knowledge-graph.graphml": render_graphml(graph),
        "graph-report.md": render_report(graph),
        "graph-report.json": json.dumps(
            {"stats": graph["stats"], "issues": graph["issues"]},
            ensure_ascii=False, indent=2,
        ) + "\n",
    }
    for name, content in files.items():
        (output / name).write_text(content, encoding="utf-8")
    legacy = root / "build"
    shutil.copy2(output / "knowledge-graph.json", legacy / "knowledge-graph.json")
    shutil.copy2(output / "knowledge-graph.mmd", legacy / "knowledge-graph.mmd")
