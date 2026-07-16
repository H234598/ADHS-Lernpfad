#!/usr/bin/env python3
"""Build the canonical, typed and deterministic project knowledge graph."""

from __future__ import annotations

import argparse
from pathlib import Path

from content_model import build_content_index
from graph_model import GraphBuilder
from graph_relations import build_graph
from graph_render import render_graphml, render_mermaid, render_report, write_outputs

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scope", choices=("learning", "all"), default="learning",
        help="Mermaid-Ausgabe auf Lerninhalte begrenzen oder alle Knoten ausgeben",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    graph = build_graph(GraphBuilder(build_content_index(ROOT)))
    write_outputs(graph, ROOT, scope=args.scope)
    stats = graph["stats"]
    print(
        "Wissensgraph: "
        f"{stats['node_count']} Knoten, {stats['edge_count']} Kanten, "
        f"{stats['error_count']} Fehler, {stats['warning_count']} Warnungen"
    )


if __name__ == "__main__":
    main()


__all__ = ["GraphBuilder", "render_graphml", "render_mermaid", "render_report"]
