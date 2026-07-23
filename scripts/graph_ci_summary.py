#!/usr/bin/env python3
"""Create a resilient CI summary from graph and runtime-status artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any

try:  # Support direct script execution and package imports.
    from .automation_status import blocks_new_run, render_diagnostic
    from .validate_runtime_status import validate_file as validate_runtime_status_file
except ImportError:  # pragma: no cover - direct command-line use
    from automation_status import blocks_new_run, render_diagnostic
    from validate_runtime_status import validate_file as validate_runtime_status_file

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "build" / "knowledge-graph" / "knowledge-graph.json"
OUTPUT = ROOT / "build" / "graph-ci-summary.md"
STATUS = ROOT / "build" / "runtime-status.json"


def _load_json(path: Path, label: str) -> tuple[dict[str, Any], str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, f"{label} fehlt: `{path}`"
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, f"{label} ist nicht lesbar: {exc}"
    if not isinstance(payload, dict):
        return {}, f"{label} muss ein JSON-Objekt sein"
    return payload, None


def _nonnegative_int(value: Any, default: int = 0) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else default


def _graph_counts(graph: dict[str, Any]) -> dict[str, int]:
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    edges = graph.get("edges") if isinstance(graph.get("edges"), list) else []
    issues = graph.get("issues") if isinstance(graph.get("issues"), list) else []
    stats = graph.get("stats") if isinstance(graph.get("stats"), dict) else {}
    typed_nodes = [node for node in nodes if isinstance(node, dict)]
    typed_issues = [issue for issue in issues if isinstance(issue, dict)]
    return {
        "nodes": _nonnegative_int(stats.get("node_count"), len(nodes)),
        "edges": _nonnegative_int(stats.get("edge_count"), len(edges)),
        "errors": _nonnegative_int(
            stats.get("error_count"),
            sum(issue.get("severity") == "error" for issue in typed_issues),
        ),
        "warnings": _nonnegative_int(
            stats.get("warning_count"),
            sum(issue.get("severity") == "warning" for issue in typed_issues),
        ),
        "planned": sum(
            node.get("planned") is True or node.get("type") == "planned"
            for node in typed_nodes
        ),
        "missing": sum(node.get("type") == "placeholder" for node in typed_nodes),
    }


def _metric_int(runtime: dict[str, Any], *keys: str) -> int | None:
    metrics = runtime.get("metrics") if isinstance(runtime.get("metrics"), dict) else {}
    for key in keys:
        value = metrics.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
    return None


def _duration_seconds(runtime: dict[str, Any]) -> float | None:
    value = runtime.get("duration_seconds")
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
        return float(value)
    started = runtime.get("created_at") or runtime.get("started_at")
    completed = runtime.get("completed_at") or runtime.get("ended_at") or runtime.get("updated_at")
    if not isinstance(started, str) or not isinstance(completed, str):
        return None
    try:
        start_time = datetime.fromisoformat(started.replace("Z", "+00:00"))
        completed_time = datetime.fromisoformat(completed.replace("Z", "+00:00"))
        seconds = (completed_time - start_time).total_seconds()
    except ValueError:
        return None
    return seconds if seconds >= 0 else None


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "nicht verfügbar"
    if seconds < 60:
        return f"{seconds:.2f} s"
    minutes, remainder = divmod(int(round(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:d} h {minutes:02d} min {remainder:02d} s" if hours else f"{minutes:d} min {remainder:02d} s"


def build_summary(
    graph: dict[str, Any], runtime: dict[str, Any],
    *, input_problems: list[str] | None = None,
) -> str:
    counts = _graph_counts(graph)
    # Runtime metrics make a partial diagnostic useful even when graph export
    # failed before the canonical JSON was written.
    metric_aliases = {
        "nodes": ("nodes", "node_count"),
        "edges": ("edges", "edge_count"),
        "errors": ("errors", "error_count"),
        "warnings": ("warnings", "warning_count"),
        "planned": ("planned_pages", "planned"),
        "missing": ("missing_pages", "missing"),
    }
    if not graph:
        for target, aliases in metric_aliases.items():
            metric = _metric_int(runtime, *aliases)
            if metric is not None:
                counts[target] = metric

    status = str(runtime.get("status") or "unknown")
    phase = str(runtime.get("phase") or "unknown")
    context = runtime.get("context") if isinstance(runtime.get("context"), dict) else {}
    lines = [
        "# Wissensgraph CI-Zusammenfassung", "",
        "## Laufstatus", "",
        f"- Status: **{status}**",
        f"- Letzte Phase: **{phase}**",
        f"- Laufzeit: **{_format_duration(_duration_seconds(runtime))}**",
        f"- Run-ID: `{runtime.get('run_id') or 'nicht verfügbar'}`",
        f"- Workflow: `{runtime.get('workflow') or 'nicht verfügbar'}`",
        f"- Revision: **{runtime.get('revision') or 'nicht verfügbar'}**",
        f"- Git-Commit: `{context.get('commit_sha') or 'nicht verfügbar'}`",
        f"- Branch: `{context.get('branch') or 'nicht verfügbar'}`",
        f"- Pull Request: **{('#' + str(context['pr_number'])) if context.get('pr_number') else 'nicht verfügbar'}**",
        "", "## Graphqualität", "",
        f"- Knoten: **{counts['nodes']}**",
        f"- Kanten: **{counts['edges']}**",
        f"- Fehler: **{counts['errors']}**",
        f"- Warnungen: **{counts['warnings']}**",
        f"- Geplante Seiten: **{counts['planned']}**",
        f"- Fehlende Seiten/Abschnitte: **{counts['missing']}**",
    ]
    error = runtime.get("error") if isinstance(runtime.get("error"), dict) else {}
    recovery = (
        runtime.get("recovery")
        if isinstance(runtime.get("recovery"), dict)
        else {}
    )
    if error or recovery:
        lines.extend(["", "## Fehler und Recovery", ""])
        if error:
            lines.append(f"- Fehlerklasse: `{error.get('class', 'unknown')}`")
            lines.append(f"- Fehlercode: `{error.get('code', 'unknown_error')}`")
            lines.append(f"- Meldung: {error.get('message', 'Keine Detailmeldung.')}")
        if recovery:
            lines.append(f"- Recovery-Level: `{recovery.get('level', 'unbekannt')}`")
            lines.append(
                f"- Empfohlene Aktion: **{recovery.get('action', 'Diagnose prüfen.')}**"
            )
            lines.append(
                "- Neuer Inhalt erforderlich: "
                + ("**ja**" if recovery.get("new_content_required") else "**nein**")
            )
            lines.append(
                "- Blockiert den nächsten Generatorlauf: "
                + ("**ja**" if blocks_new_run(runtime) else "**nein**")
            )
        lines.extend(
            [
                "",
                "### Vollständiger Diagnoseblock",
                "",
                "```text",
                render_diagnostic(runtime).rstrip(),
                "```",
            ]
        )
    if input_problems:
        lines.extend(["", "## Unvollständige Diagnoseeingaben", ""])
        lines.extend(f"- {problem}" for problem in input_problems)
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=GRAPH)
    parser.add_argument("--status", type=Path, default=STATUS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--github-summary", type=Path, default=None,
        help="Optional zusätzlich an eine GitHub-Step-Summary-Datei anhängen",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    graph, graph_problem = _load_json(args.graph, "Graphausgabe")
    runtime, runtime_problem = _load_json(args.status, "Runtime-Status")
    problems = [problem for problem in (graph_problem, runtime_problem) if problem]
    if runtime_problem is None:
        problems.extend(
            f"Runtime-Status verletzt das Schema: {error}"
            for error in validate_runtime_status_file(args.status)
        )
    summary = build_summary(graph, runtime, input_problems=problems)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(summary, encoding="utf-8")

    github_summary = args.github_summary
    if github_summary is None and os.getenv("GITHUB_STEP_SUMMARY"):
        github_summary = Path(os.environ["GITHUB_STEP_SUMMARY"])
    if github_summary is not None and github_summary.resolve() != args.output.resolve():
        github_summary.parent.mkdir(parents=True, exist_ok=True)
        with github_summary.open("a", encoding="utf-8") as handle:
            handle.write(summary)
    print(args.output)
    # Summary generation is diagnostic and must remain available after an
    # earlier failure. The actual graph/status validators provide CI gates.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
