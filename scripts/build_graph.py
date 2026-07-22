#!/usr/bin/env python3
"""Build, validate and export the canonical project knowledge graph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from automation_run_status import (
    DEFAULT_STATUS_PATH, finish_run, start_run, status_is_managed, update_status,
)
from content_model import build_content_index
from graph_model import GraphBuilder
from graph_relations import (
    build_edges, build_graph, build_nodes, finalize_graph, graph_metrics,
)
from graph_render import render_graphml, render_mermaid, render_report, write_outputs
from validate_graph import (
    SCHEMA as GRAPH_SCHEMA,
    validate_graph_data,
    write_reports as write_validation_reports,
)

ROOT = Path(__file__).resolve().parents[1]
GRAPH_ARTIFACTS = (
    "knowledge-graph.json", "knowledge-graph.graphml", "knowledge-graph.mmd",
    "graph-report.json", "graph-report.md",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scope", choices=("learning", "all"), default="learning",
        help="Mermaid-Ausgabe auf Lerninhalte begrenzen oder alle Knoten ausgeben",
    )
    parser.add_argument(
        "--status-file", type=Path, default=ROOT / DEFAULT_STATUS_PATH,
        help="Atomare Runtime-Statusdatei",
    )
    parser.add_argument("--workflow", default="knowledge-graph")
    return parser.parse_args(argv)


def _content_metrics(index: Any) -> dict[str, int]:
    documents = list(index.documents.values())
    return {
        "documents": len(documents),
        "sources": sum(document.type == "reference" for document in documents),
        "chapters": sum(document.type == "chapter" for document in documents),
    }


def _graph_status_metrics(graph: dict[str, Any], validation_errors: int = 0) -> dict[str, Any]:
    stats = graph.get("stats", {})
    nodes = graph.get("nodes", [])
    return {
        "nodes": int(stats.get("node_count", 0)),
        "node_types": stats.get("nodes_by_type", {}),
        "edges": int(stats.get("edge_count", 0)),
        "relations": stats.get("edges_by_type", {}),
        "errors": int(stats.get("error_count", 0)) + validation_errors,
        "warnings": int(stats.get("warning_count", 0)),
        "missing_pages": sum(
            isinstance(node, dict) and node.get("type") == "placeholder"
            for node in nodes
        ),
        "planned_pages": sum(
            isinstance(node, dict) and node.get("type") == "planned"
            for node in nodes
        ),
    }


def _additional_validation_error_count(errors: list[dict[str, Any]]) -> int:
    """Count validator-only errors, excluding graph issues already in stats."""

    return sum(error.get("code") != "blocking-graph-issue" for error in errors)


def _artifacts(root: Path = ROOT) -> list[str]:
    output = root / "build" / "knowledge-graph"
    return [
        (output / name).relative_to(root).as_posix()
        for name in GRAPH_ARTIFACTS
        if (output / name).is_file()
    ]


def _safe_error_message(exc: BaseException) -> str:
    message = str(exc) or type(exc).__name__
    return message.replace(str(ROOT), ".")[:2000]


def _failure_contract(phase: str, exc: BaseException) -> tuple[str, str]:
    if phase == "load_content":
        return "content_error", "fix_content_and_retry"
    if phase in {"build_nodes", "build_edges"}:
        return "graph_build_error", "inspect_graph_builder_and_retry"
    if phase == "validate_graph":
        error_class = "schema_error" if isinstance(exc, (json.JSONDecodeError, OSError)) else "graph_validation_error"
        return error_class, "fix_graph_and_retry_validation"
    if phase == "export":
        return "export_error", "reuse_valid_graph_and_retry_export"
    return "internal_error", "inspect_logs_and_retry"


def run_build(
    *,
    root: Path = ROOT,
    scope: str = "learning",
    status_file: Path | None = None,
    workflow: str = "knowledge-graph",
) -> tuple[dict[str, Any] | None, int]:
    """Run all real phases and return ``(graph, process_exit_code)``."""

    target = status_file or root / DEFAULT_STATUS_PATH
    managed = status_is_managed()
    if not managed:
        start_run(target, workflow)

    phase = "load_content"
    graph: dict[str, Any] | None = None
    try:
        update_status(
            target, status="running", phase=phase,
            workflow=None if managed else workflow,
        )
        index = build_content_index(root)
        update_status(target, metrics=_content_metrics(index))

        phase = "build_nodes"
        update_status(target, status="running", phase=phase)
        builder = GraphBuilder(index)
        build_nodes(builder)
        update_status(target, metrics=graph_metrics(builder))

        phase = "build_edges"
        update_status(target, status="running", phase=phase)
        build_edges(builder)
        update_status(target, metrics=graph_metrics(builder))
        graph = finalize_graph(builder)

        phase = "validate_graph"
        update_status(target, status="running", phase=phase, metrics=_graph_status_metrics(graph))
        schema = json.loads(GRAPH_SCHEMA.read_text(encoding="utf-8"))
        validation = validate_graph_data(graph, schema, root=root)

        metrics = _graph_status_metrics(
            graph,
            _additional_validation_error_count(validation.errors),
        )
        if not validation.valid:
            # Even an invalid graph gets deterministic diagnostics for CI and
            # recovery. It is never reported as a successful export phase.
            write_outputs(graph, root, scope=scope)
            write_validation_reports(
                validation,
                root / "build" / "knowledge-graph" / "graph-report.json",
                root / "build" / "knowledge-graph" / "graph-report.md",
            )
            update_status(target, metrics=metrics, artifacts=_artifacts(root))
            first = validation.errors[0]
            schema_failure = any(
                error.get("code") in {"schema-error", "missing-schema", "invalid-schema-file"}
                for error in validation.errors
            )
            message = (
                f"{len(validation.errors)} Graphvalidierungsfehler; "
                f"erster Befund {first['code']}: {first['message']}"
            )
            finish_run(
                target, success=False, phase=phase, metrics=metrics,
                artifacts=_artifacts(root),
                error_class="schema_error" if schema_failure else "graph_validation_error",
                error_message=message,
                recovery_action=(
                    "fix_schema_and_retry_validation" if schema_failure
                    else "fix_graph_and_retry_validation"
                ),
            )
            print(message, file=sys.stderr)
            return graph, 1

        phase = "export"
        update_status(target, status="running", phase=phase, metrics=metrics)
        write_outputs(graph, root, scope=scope)
        write_validation_reports(
            validation,
            root / "build" / "knowledge-graph" / "graph-report.json",
            root / "build" / "knowledge-graph" / "graph-report.md",
        )
        update_status(
            target, status="running", phase=phase, metrics=metrics,
            artifacts=_artifacts(root),
        )
        if not managed:
            finish_run(
                target, success=True, phase="success", metrics=metrics,
                artifacts=_artifacts(root),
            )
        return graph, 0
    except Exception as exc:
        error_class, recovery_action = _failure_contract(phase, exc)
        try:
            finish_run(
                target, success=False, phase=phase,
                metrics=_graph_status_metrics(graph) if graph else None,
                artifacts=_artifacts(root), error_class=error_class,
                error_message=_safe_error_message(exc),
                recovery_action=recovery_action,
            )
        except Exception as status_exc:  # Do not hide the original failure.
            print(f"Runtime-Status konnte nicht finalisiert werden: {status_exc}", file=sys.stderr)
        print(f"Wissensgraph fehlgeschlagen ({phase}): {_safe_error_message(exc)}", file=sys.stderr)
        return graph, 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    graph, exit_code = run_build(
        root=ROOT, scope=args.scope, status_file=args.status_file,
        workflow=args.workflow,
    )
    if graph is not None:
        stats = graph["stats"]
        print(
            "Wissensgraph: "
            f"{stats['node_count']} Knoten, {stats['edge_count']} Kanten, "
            f"{stats['error_count']} Fehler, {stats['warning_count']} Warnungen"
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "GraphBuilder", "build_graph", "render_graphml", "render_mermaid",
    "render_report", "run_build",
]
