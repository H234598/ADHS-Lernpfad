#!/usr/bin/env python3
"""Finalize graph data and orchestrate all relation builders."""

from __future__ import annotations

from collections import Counter
import os
from pathlib import Path
import subprocess
from typing import Any, Callable

from content_links import scan_wikilinks
from content_model import json_compatible
from graph_metadata import (
    add_link_occurrence, add_prerequisites, add_references, add_related, add_tags,
)
from graph_model import GraphBuilder, SCHEMA_VERSION


def _source_revision(root: Path) -> str | None:
    if os.getenv("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


PhaseCallback = Callable[[str, dict[str, Any]], None]


def graph_metrics(builder: GraphBuilder) -> dict[str, Any]:
    """Return status metrics without mutating or finalizing the builder."""

    return {
        "nodes": len(builder.nodes),
        "node_types": dict(sorted(Counter(
            str(node.get("type", "unknown")) for node in builder.nodes.values()
        ).items())),
        "edges": len(builder.edges),
        "relations": dict(sorted(Counter(
            str(edge.get("type", "unknown")) for edge in builder.edges.values()
        ).items())),
        "errors": sum(issue.get("severity") == "error" for issue in builder.issues),
        "warnings": sum(issue.get("severity") == "warning" for issue in builder.issues),
        "missing_pages": sum(
            node.get("type") == "placeholder" for node in builder.nodes.values()
        ),
        "planned_pages": sum(
            node.get("type") == "planned" for node in builder.nodes.values()
        ),
    }


def _emit_phase(
    callback: PhaseCallback | None, phase: str, builder: GraphBuilder,
) -> None:
    if callback is not None:
        callback(phase, graph_metrics(builder))


def finalize_graph(builder: GraphBuilder) -> dict[str, Any]:
    nodes = [builder.nodes[key] for key in sorted(builder.nodes)]
    edges = []
    for key in sorted(builder.edges):
        edge = builder.edges[key]
        edge["occurrences"] = sorted(
            edge["occurrences"], key=lambda item: (
                str(item.get("path", "")), int(item.get("line", 0) or 0),
                int(item.get("column", 0) or 0), str(item.get("field", "")),
                str(item.get("value", "")),
            ),
        )
        edge["count"] = len(edge["occurrences"]) or int(edge["count"])
        edges.append(edge)
    issues = sorted(builder.issues, key=lambda item: (
        str(item.get("severity", "")), str(item.get("code", "")),
        str(item.get("path", "")), int(item.get("line", 0) or 0),
        int(item.get("column", 0) or 0), str(item.get("message", "")),
    ))
    stats = {
        "node_count": len(nodes), "edge_count": len(edges),
        "issue_count": len(issues),
        "error_count": sum(item.get("severity") == "error" for item in issues),
        "warning_count": sum(item.get("severity") == "warning" for item in issues),
        "nodes_by_type": dict(sorted(Counter(str(n["type"]) for n in nodes).items())),
        "edges_by_type": dict(sorted(Counter(str(e["type"]) for e in edges).items())),
        "issues_by_code": dict(sorted(Counter(str(i["code"]) for i in issues).items())),
    }
    return json_compatible({
        "schema_version": SCHEMA_VERSION,
        "source_revision": _source_revision(builder.index.root),
        "scopes": sorted({str(n.get("scope")) for n in nodes if n.get("scope")}),
        "stats": stats, "nodes": nodes, "edges": edges, "issues": issues,
    })


def build_nodes(builder: GraphBuilder) -> None:
    """Create all nodes known before link and metadata resolution."""

    for document in sorted(builder.index.documents.values(), key=lambda item: item.id):
        builder.add_document(document)
    for planned in sorted(builder.index.planned_nodes.values(), key=lambda item: item.id):
        builder.add_planned(planned)
    builder.issues.extend(issue.as_dict() for issue in builder.index.model_issues)


def build_edges(builder: GraphBuilder) -> None:
    """Resolve relations; target resolution may add sections/placeholders."""

    for document in sorted(builder.index.documents.values(), key=lambda item: item.id):
        for occurrence in scan_wikilinks(document.raw_text, document.path):
            add_link_occurrence(builder, document, occurrence)
        add_prerequisites(builder, document)
        add_tags(builder, document)
        add_references(builder, document)
        add_related(builder, document)
    for earlier, later in zip(builder.index.chapter_ids, builder.index.chapter_ids[1:]):
        builder.add_edge(
            "sequence", earlier, later,
            occurrence={"path": "index.json", "from": earlier, "to": later},
        )
    roadmap = next((
        doc for doc in builder.index.documents.values()
        if doc.relative_path.as_posix() == "ROADMAP.md"
    ), None)
    if roadmap:
        for planned in sorted(builder.index.planned_nodes.values(), key=lambda item: item.id):
            builder.add_edge(
                "planned_in", roadmap.id, planned.id, status="planned",
                occurrence={
                    "path": "knowledge-graph/planned-nodes.yaml",
                    "roadmap": planned.roadmap,
                },
            )


def build_graph(
    builder: GraphBuilder, *, phase_callback: PhaseCallback | None = None,
) -> dict[str, Any]:
    """Build a deterministic graph while exposing real phase boundaries."""

    build_nodes(builder)
    _emit_phase(phase_callback, "build_nodes", builder)
    build_edges(builder)
    _emit_phase(phase_callback, "build_edges", builder)
    return finalize_graph(builder)
