#!/usr/bin/env python3
"""Canonical knowledge-graph node and edge collection primitives."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

from content_links import LinkOccurrence, placeholder_id
from content_model import (
    ContentIndex, Document, Heading, PlannedNode, json_compatible, slugify,
)

SCHEMA_VERSION = "1.0.0"
NODE_METADATA_FIELDS = (
    "level", "difficulty", "estimated_time", "evidence", "status",
    "last_reviewed", "minimum_reading_minutes", "maximum_reading_minutes",
    "evidence_type", "evidence_grade", "doi", "pmid", "reference_id",
)


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable) and not isinstance(value, (dict, bytes)):
        return [str(item) for item in value]
    return [str(value)]


def edge_id(edge_type: str, source: str, target: str) -> str:
    digest = hashlib.sha256(
        f"{edge_type}\0{source}\0{target}".encode("utf-8")
    ).hexdigest()[:16]
    return f"edge:{edge_type}:{digest}"


class GraphBuilder:
    """Collect canonical nodes, aggregated typed edges and explicit issues."""

    def __init__(self, index: ContentIndex) -> None:
        self.index = index
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[tuple[str, str, str], dict[str, Any]] = {}
        self.issues: list[dict[str, Any]] = []

    def add_node(self, node: dict[str, Any]) -> str:
        node_id = str(node["id"])
        normalized = json_compatible(node)
        existing = self.nodes.get(node_id)
        if existing is not None and existing != normalized:
            self.add_issue(
                code="conflicting-node-definition", severity="error",
                message=f"Widersprüchliche Definitionen für Knoten {node_id}",
                node_id=node_id,
            )
            return node_id
        self.nodes[node_id] = normalized
        return node_id

    def add_issue(
        self, *, code: str, severity: str, message: str, **context: Any,
    ) -> None:
        issue = {"code": code, "severity": severity, "message": message}
        issue.update({
            key: json_compatible(value)
            for key, value in context.items() if value is not None
        })
        self.issues.append(issue)

    def add_edge(
        self, edge_type: str, source: str, target: str, *, status: str = "ok",
        occurrence: dict[str, Any] | None = None,
    ) -> str:
        key = (edge_type, source, target)
        edge = self.edges.setdefault(key, {
            "id": edge_id(edge_type, source, target),
            "type": edge_type,
            "source": source,
            "target": target,
            "status": status,
            "count": 0,
            "occurrences": [],
        })
        if edge["status"] == "ok" and status != "ok":
            edge["status"] = status
        edge["count"] += 1
        if occurrence is not None:
            normalized = json_compatible(occurrence)
            if normalized not in edge["occurrences"]:
                edge["occurrences"].append(normalized)
        return str(edge["id"])

    def add_document(self, document: Document) -> str:
        node: dict[str, Any] = {
            "id": document.id,
            "type": document.type,
            "label": document.title,
            "path": document.relative_path.as_posix(),
            "url": document.url,
            "scope": document.scope,
            "exists": True,
            "planned": False,
            "aliases": list(document.aliases),
            "tags": as_list(document.metadata.get("tags")),
        }
        for field in NODE_METADATA_FIELDS:
            if field in document.metadata:
                node[field] = document.metadata[field]
        return self.add_node(node)

    def add_planned(self, planned: PlannedNode) -> str:
        return self.add_node({
            "id": planned.id,
            "type": "planned",
            "planned_type": planned.type,
            "label": planned.title,
            "path": planned.path,
            "scope": planned.scope,
            "exists": False,
            "planned": True,
            "aliases": list(planned.aliases),
            "level": planned.level,
            "roadmap": planned.roadmap,
            "reason": planned.reason,
        })

    def add_section(self, document: Document, heading: Heading) -> str:
        node_id = f"section:{document.id}#{heading.anchor}"
        self.add_node({
            "id": node_id,
            "type": "section",
            "label": heading.title,
            "path": document.relative_path.as_posix(),
            "url": f"{document.url}#{heading.anchor}",
            "scope": document.scope,
            "exists": True,
            "planned": False,
            "document_id": document.id,
            "heading": heading.title,
            "anchor": heading.anchor,
            "line": heading.line,
        })
        self.add_edge(
            "contains", document.id, node_id,
            occurrence={"path": document.relative_path.as_posix(), "line": heading.line},
        )
        return node_id

    def add_asset(self, path: Path) -> str:
        relative = path.resolve().relative_to(self.index.root).as_posix()
        return self.add_node({
            "id": f"asset:{relative}", "type": "asset", "label": path.name,
            "path": relative, "url": f"/{relative}", "scope": "asset",
            "exists": True, "planned": False,
        })

    def add_placeholder(
        self, status: str, requested: str, candidates: Iterable[str] = (),
    ) -> str:
        node_id = placeholder_id(status, requested)
        return self.add_node({
            "id": node_id, "type": "placeholder",
            "label": requested or "Leeres Ziel", "scope": "issue",
            "exists": False, "planned": False, "issue_code": status,
            "requested_target": requested,
            "candidates": sorted(set(candidates)),
        })

    def build(self) -> dict[str, Any]:
        from graph_relations import build_graph
        return build_graph(self)

    def target_for_resolution(self, occurrence: LinkOccurrence, resolution: Any) -> str:
        if resolution.status == "ok":
            if resolution.document is not None and resolution.heading:
                wanted = slugify(resolution.heading)
                matches = [
                    heading for heading in resolution.document.headings
                    if heading.anchor == wanted
                ]
                if len(matches) == 1:
                    return self.add_section(resolution.document, matches[0])
            if resolution.document is not None:
                return resolution.document.id
            if resolution.path is not None:
                return self.add_asset(resolution.path)
        if resolution.status == "planned" and resolution.planned is not None:
            return self.add_planned(resolution.planned)
        return self.add_placeholder(
            resolution.status, occurrence.target, resolution.candidates,
        )
