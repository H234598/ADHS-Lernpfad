#!/usr/bin/env python3
"""Load and validate deliberately planned knowledge-graph nodes."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

from content_model import ModelIssue, PlannedNode, canonical_document_path


def _as_string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, Iterable) and not isinstance(value, (dict, bytes)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return (str(value).strip(),)


def load_planned_nodes(root: Path) -> tuple[dict[str, PlannedNode], list[ModelIssue]]:
    registry = root / "knowledge-graph" / "planned-nodes.yaml"
    if not registry.exists():
        return {}, []
    try:
        loaded = yaml.safe_load(registry.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return {}, [ModelIssue(
            "invalid-planned-node-registry", "error",
            f"Ungültige Planned-Node-Registry: {str(exc).splitlines()[0]}",
            "knowledge-graph/planned-nodes.yaml", 1,
        )]
    entries = loaded.get("nodes", []) if isinstance(loaded, dict) else []
    if not isinstance(entries, list):
        return {}, [ModelIssue(
            "invalid-planned-node-registry", "error",
            "knowledge-graph/planned-nodes.yaml: nodes muss eine Liste sein",
            "knowledge-graph/planned-nodes.yaml", 1,
        )]
    nodes: dict[str, PlannedNode] = {}
    issues: list[ModelIssue] = []
    for position, item in enumerate(entries, start=1):
        if not isinstance(item, dict) or not item.get("path") or not item.get("title"):
            issues.append(ModelIssue(
                "invalid-planned-node", "error",
                f"Planned-Node-Eintrag {position} benötigt path und title",
                "knowledge-graph/planned-nodes.yaml",
            ))
            continue
        path = canonical_document_path(Path(str(item["path"])))
        node_id = f"planned:{path}"
        if node_id in nodes:
            issues.append(ModelIssue(
                "duplicate-planned-node", "error",
                f"Doppelter geplanter Knoten: {path}",
                "knowledge-graph/planned-nodes.yaml",
            ))
            continue
        nodes[node_id] = PlannedNode(
            node_id, path, str(item["title"]), str(item.get("type", "planned")),
            str(item.get("scope", "learning")),
            str(item["level"]) if item.get("level") is not None else None,
            str(item["roadmap"]) if item.get("roadmap") is not None else None,
            str(item["reason"]) if item.get("reason") is not None else None,
            _as_string_tuple(item.get("aliases")),
            str(item.get("status", "planned")),
        )
        if nodes[node_id].lifecycle_status not in {"planned", "in_progress"}:
            issues.append(ModelIssue(
                "invalid-planned-node-status", "error",
                f"Unbekannter Planned-Node-Status für {path}: "
                f"{nodes[node_id].lifecycle_status}",
                "knowledge-graph/planned-nodes.yaml",
            ))
    return nodes, issues
