#!/usr/bin/env python3
"""Create a compact CI summary for knowledge graph validation."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    candidates = [ROOT / "knowledge-graph" / "knowledge-graph.json", ROOT / "build" / "knowledge-graph.json"]
    graph_file = next((path for path in candidates if path.exists()), None)
    summary = ["# Wissensgraph CI Summary", ""]
    if graph_file is None:
        summary.append("- Graph artifact: nicht gefunden")
    else:
        graph = json.loads(graph_file.read_text(encoding="utf-8"))
        summary.extend([
            f"- Quelle: `{graph_file.relative_to(ROOT)}`",
            f"- Nodes: {len(graph.get('nodes', []))}",
            f"- Edges: {len(graph.get('edges', []))}",
        ])
    output = ROOT / "build" / "graph-ci-summary.md"
    output.parent.mkdir(exist_ok=True)
    output.write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
