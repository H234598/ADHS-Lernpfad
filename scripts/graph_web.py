#!/usr/bin/env python3
"""Prepare the lean, dynamically rendered knowledge-graph page for MkDocs."""

from __future__ import annotations

import html
import json
from pathlib import Path
import shutil
from typing import Any

MARKER = "<!-- knowledge-graph-app -->"
GRAPH_CANDIDATES = (
    Path("build/knowledge-graph/knowledge-graph.json"),
    Path("build/knowledge-graph.json"),
)


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _status(node: dict[str, Any]) -> str:
    if node.get("planned"):
        return "planned"
    if node.get("type") == "placeholder":
        return str(node.get("issue_code", "missing-document"))
    return str(node.get("status", "ok"))


def _option(value: str, label: str) -> str:
    return f'<option value="{_escape(value)}">{_escape(label)}</option>'


def graph_json_path(root: Path) -> Path:
    """Return the generated graph JSON path or raise a precise build error."""

    for relative in GRAPH_CANDIDATES:
        candidate = root / relative
        if candidate.is_file():
            return candidate
    checked = ", ".join(str(path) for path in GRAPH_CANDIDATES)
    raise FileNotFoundError(
        "Wissensgraph-JSON fehlt. Vor scripts/build_docs.py muss "
        f"scripts/build_graph.py laufen (geprüft: {checked})."
    )


def load_graph(root: Path) -> dict[str, Any]:
    """Load and minimally validate the generated graph object."""

    data = json.loads(graph_json_path(root).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("Wissensgraph-JSON muss ein Objekt sein")
    for key in ("nodes", "edges", "issues", "stats"):
        if key not in data:
            raise ValueError(f"Wissensgraph-JSON enthält kein Feld {key!r}")
    if not isinstance(data["nodes"], list) or not isinstance(data["edges"], list):
        raise TypeError("Wissensgraph-Knoten und -Kanten müssen Listen sein")
    return data


def copy_graph_data(root: Path, docs: Path) -> Path:
    """Copy the canonical JSON used by the client-side graph into MkDocs."""

    source = graph_json_path(root)
    destination = docs / "knowledge-graph" / "data" / "knowledge-graph.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def render_graph_shell(
    graph: dict[str, Any], graph_url: str = "data/knowledge-graph.json"
) -> str:
    """Render only the graph controls, canvas, details and data-driven legend."""

    nodes = [node for node in graph.get("nodes", []) if isinstance(node, dict)]
    edges = [edge for edge in graph.get("edges", []) if isinstance(edge, dict)]

    node_types = sorted({str(node.get("type", "document")) for node in nodes})
    edge_types = sorted({str(edge.get("type", "wikilink")) for edge in edges})
    scopes = sorted({str(node.get("scope", "support")) for node in nodes})
    statuses = sorted(
        {
            *(_status(node) for node in nodes),
            *(str(edge.get("status", "ok")) for edge in edges),
        }
    )

    node_options = _option("", "Alle Knotentypen") + "".join(
        _option(item, item) for item in node_types
    )
    edge_options = _option("", "Alle Beziehungen") + "".join(
        _option(item, item) for item in edge_types
    )
    scope_options = _option("", "Alle Bereiche") + "".join(
        _option(item, item) for item in scopes
    )
    status_options = _option("", "Alle Status") + "".join(
        _option(item, item) for item in statuses
    )

    return f"""
<div class="knowledge-graph-shell" data-knowledge-graph data-graph-url="{_escape(graph_url)}">
  <form class="knowledge-graph-controls" data-kg-controls aria-label="Wissensgraph filtern">
    <label class="knowledge-graph-control knowledge-graph-control--search">
      <span>Suche</span>
      <input type="search" data-kg-search autocomplete="off" placeholder="Titel, Pfad, Tag oder ID">
    </label>
    <label class="knowledge-graph-control">
      <span>Knotentyp</span>
      <select data-kg-type>{node_options}</select>
    </label>
    <label class="knowledge-graph-control">
      <span>Beziehung</span>
      <select data-kg-edge>{edge_options}</select>
    </label>
    <label class="knowledge-graph-control">
      <span>Bereich</span>
      <select data-kg-scope>{scope_options}</select>
    </label>
    <label class="knowledge-graph-control">
      <span>Status</span>
      <select data-kg-status>{status_options}</select>
    </label>
    <label class="knowledge-graph-control">
      <span>Layout</span>
      <select data-kg-layout>
        <option value="cose">Netzwerk</option>
        <option value="breadthfirst">Lernpfad</option>
        <option value="concentric">Fokus</option>
      </select>
    </label>
    <div class="knowledge-graph-actions" role="group" aria-label="Graphansicht">
      <button type="button" data-kg-fit>Alles einpassen</button>
      <button type="button" data-kg-reset>Zurücksetzen</button>
    </div>
  </form>

  <p class="knowledge-graph-live" data-kg-live aria-live="polite">Graphdaten werden geladen.</p>

  <div class="knowledge-graph-layout">
    <div class="knowledge-graph-stage">
      <div class="knowledge-graph-canvas" data-kg-canvas role="img" tabindex="0"
        aria-label="Interaktiver Wissensgraph"></div>
    </div>
    <aside class="knowledge-graph-details" data-kg-details tabindex="-1"
      aria-label="Details zum ausgewählten Graphobjekt">
      <h2>Details</h2>
      <p>Knoten oder Beziehung auswählen.</p>
    </aside>
  </div>

  <details class="knowledge-graph-legend" open>
    <summary>Legende</summary>
    <div data-kg-legend aria-live="polite">
      <p>Legende wird aus den aktuellen Graphdaten erzeugt.</p>
    </div>
  </details>

  <noscript><p class="knowledge-graph-error">Für den interaktiven Wissensgraphen ist JavaScript erforderlich.</p></noscript>
</div>
""".strip()


def inject_graph_page(
    markdown: str,
    graph: dict[str, Any],
    graph_url: str = "data/knowledge-graph.json",
) -> str:
    """Replace the single graph marker while rejecting ambiguous source pages."""

    marker_count = markdown.count(MARKER)
    if marker_count != 1:
        raise ValueError(
            "Graphseite muss den Marker genau einmal enthalten: "
            f"{MARKER} (gefunden: {marker_count})"
        )
    return markdown.replace(MARKER, render_graph_shell(graph, graph_url), 1)
