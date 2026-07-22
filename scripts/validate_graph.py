#!/usr/bin/env python3
"""Validate generated knowledge graph output against schema and invariants."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "build" / "knowledge-graph" / "knowledge-graph.json"


def main() -> int:
    if not GRAPH.exists():
        print(f"missing graph output: {GRAPH}")
        return 1

    data = json.loads(GRAPH.read_text(encoding="utf-8"))
    nodes = {str(node["id"]) for node in data.get("nodes", [])}
    errors: list[str] = []

    if len(nodes) != len(data.get("nodes", [])):
        errors.append("duplicate node ids")

    for edge in data.get("edges", []):
        if edge.get("source") not in nodes:
            errors.append(f"missing source: {edge.get('source')}")
        if edge.get("target") not in nodes:
            errors.append(f"missing target: {edge.get('target')}")

    for issue in data.get("issues", []):
        if issue.get("severity") == "error":
            errors.append(issue.get("message", "unknown graph error"))

    if errors:
        print("Knowledge graph validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "Knowledge graph valid: "
        f"{len(nodes)} nodes, {len(data.get('edges', []))} edges"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
