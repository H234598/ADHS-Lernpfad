#!/usr/bin/env python3
"""Validate generated knowledge graph artifacts.

Phase 3 foundation: checks generated graph structure and reports quality issues.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "knowledge-graph" / "knowledge-graph.json"


def load_graph() -> dict:
    if not GRAPH.exists():
        raise FileNotFoundError(f"Missing graph artifact: {GRAPH}")
    return json.loads(GRAPH.read_text(encoding="utf-8"))


def validate(graph: dict) -> list[str]:
    errors: list[str] = []
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    ids = [node.get("id") for node in nodes]

    if len(ids) != len(set(ids)):
        errors.append("duplicate node ids")

    known = set(ids)
    for edge in edges:
        if edge.get("source") not in known:
            errors.append(f"unknown edge source: {edge.get('source')}")
        if edge.get("target") not in known:
            errors.append(f"unknown edge target: {edge.get('target')}")

    for node in nodes:
        if not node.get("id"):
            errors.append("node without id")
        if not node.get("title"):
            errors.append(f"node without title: {node.get('id')}")

    return errors


def main() -> int:
    errors = validate(load_graph())
    if errors:
        print("Knowledge graph validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("Knowledge graph validation OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
