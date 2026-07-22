#!/usr/bin/env python3
"""Create a concise CI summary from the generated knowledge graph."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "build" / "knowledge-graph" / "knowledge-graph.json"
OUTPUT = ROOT / "build" / "graph-ci-summary.md"
STATUS = ROOT / "automation" / "runtime-status.json"


def main() -> None:
    data = json.loads(GRAPH.read_text(encoding="utf-8"))
    stats = data.get("stats", {})
    lines = [
        "# Wissensgraph CI Zusammenfassung",
        "",
        f"- Knoten: **{stats.get('node_count', 0)}**",
        f"- Kanten: **{stats.get('edge_count', 0)}**",
        f"- Fehler: **{stats.get('error_count', 0)}**",
        f"- Warnungen: **{stats.get('warning_count', 0)}**",
        "",
    ]
    if STATUS.exists():
        runtime = json.loads(STATUS.read_text(encoding="utf-8"))
        lines.extend(
            [
                "## Laufstatus",
                "",
                f"- Status: **{runtime.get('status', 'unknown')}**",
                f"- Phase: **{runtime.get('phase', 'unknown')}**",
                "",
            ]
        )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
