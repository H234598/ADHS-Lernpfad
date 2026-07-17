#!/usr/bin/env python3
"""Render the progressively enhanced, accessible knowledge-graph web page."""

from __future__ import annotations

from collections import Counter
import html
from typing import Any

MARKER = "<!-- knowledge-graph-app -->"


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _status(node: dict[str, Any]) -> str:
    if node.get("planned"):
        return "planned"
    if node.get("type") == "placeholder":
        return str(node.get("issue_code", "missing-document"))
    return "ok"


def _option(value: str, label: str) -> str:
    return f'<option value="{_escape(value)}">{_escape(label)}</option>'


def _stats_html(graph: dict[str, Any]) -> str:
    stats = graph["stats"]
    cards = [
        ("Knoten", stats["node_count"]),
        ("Beziehungen", stats["edge_count"]),
        ("Geplante Seiten", stats["nodes_by_type"].get("planned", 0)),
        ("Offene Probleme", stats["error_count"]),
    ]
    return "".join(
        '<div class="kgraph-stat">'
        f'<strong>{_escape(value)}</strong><span>{_escape(label)}</span>'
        "</div>"
        for label, value in cards
    )


def _node_table(graph: dict[str, Any]) -> str:
    degrees: Counter[str] = Counter()
    for edge in graph["edges"]:
        degrees[str(edge["source"])] += 1
        degrees[str(edge["target"])] += 1
    rows: list[str] = []
    for node in sorted(
        graph["nodes"],
        key=lambda item: (str(item.get("label", "")).casefold(), str(item["id"])),
    ):
        status = _status(node)
        label = _escape(node.get("label", node["id"]))
        path = _escape(node.get("path", "—"))
        select_button = (
            f'<button type="button" class="kgraph-table-select" '
            f'data-kgraph-select-node="{_escape(node["id"])}">{label}</button>'
        )
        if node.get("exists") and node.get("url"):
            title = select_button + f' <a href="{_escape(node["url"])}">Seite öffnen</a>'
        else:
            title = select_button
        rows.append(
            f'<tr data-node-id="{_escape(node["id"])}" '
            f'data-node-type="{_escape(node.get("type", "document"))}" '
            f'data-node-status="{_escape(status)}">'
            f'<td>{title}</td><td>{_escape(node.get("type", "document"))}</td>'
            f'<td><span class="kgraph-badge kgraph-badge--{_escape(status)}">'
            f'{_escape(status)}</span></td>'
            f'<td><code>{path}</code></td><td>{degrees[str(node["id"])]}</td></tr>'
        )
    return (
        '<div class="kgraph-table-wrap"><table class="kgraph-node-table">'
        '<thead><tr><th scope="col">Knoten</th><th scope="col">Typ</th>'
        '<th scope="col">Status</th><th scope="col">Pfad</th>'
        '<th scope="col">Beziehungen</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _issues_table(graph: dict[str, Any]) -> str:
    issues = graph.get("issues", [])
    if not issues:
        return '<p class="kgraph-empty">Keine ungeklärten Linkprobleme.</p>'
    rows: list[str] = []
    for issue in issues:
        location = str(issue.get("path", "Repository"))
        if issue.get("line"):
            location += f':{issue["line"]}'
        if issue.get("column"):
            location += f':{issue["column"]}'
        rows.append(
            "<tr>"
            f'<td><span class="kgraph-badge kgraph-badge--'
            f'{_escape(issue.get("code", "error"))}">'
            f'{_escape(issue.get("code", "error"))}</span></td>'
            f'<td>{_escape(issue.get("message", ""))}</td>'
            f'<td><code>{_escape(location)}</code></td>'
            "</tr>"
        )
    return (
        '<div class="kgraph-table-wrap"><table class="kgraph-issue-table">'
        '<thead><tr><th scope="col">Status</th>'
        '<th scope="col">Beschreibung</th><th scope="col">Fundstelle</th>'
        '</tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></div>"
    )


def render_graph_shell(
    graph: dict[str, Any], graph_url: str = "data/knowledge-graph.json",
) -> str:
    node_types = sorted({str(node.get("type", "document")) for node in graph["nodes"]})
    edge_types = sorted({str(edge.get("type", "wikilink")) for edge in graph["edges"]})
    scopes = sorted({str(node.get("scope", "support")) for node in graph["nodes"]})
    statuses = sorted({
        *(_status(node) for node in graph["nodes"]),
        *(str(edge.get("status", "ok")) for edge in graph["edges"]),
    })
    node_options = _option("", "Alle Knotentypen") + "".join(
        _option(item, item) for item in node_types
    )
    edge_options = _option("", "Alle Beziehungsarten") + "".join(
        _option(item, item) for item in edge_types
    )
    scope_options = _option("", "Alle Bereiche") + "".join(
        _option(item, item) for item in scopes
    )
    status_options = _option("", "Alle Status") + "".join(
        _option(item, item) for item in statuses
    )

    return f"""
<div class="knowledge-graph-app" data-knowledge-graph-app data-graph-url="{_escape(graph_url)}">
  <section class="kgraph-summary" aria-label="Graphstatistik">
    {_stats_html(graph)}
  </section>

  <form class="kgraph-controls" data-kgraph-controls aria-label="Wissensgraph filtern" onsubmit="return false">
    <label class="kgraph-control kgraph-control--search">
      <span>Suchen</span>
      <input type="search" data-kgraph-search autocomplete="off" placeholder="Titel, Pfad, Tag oder Quellen-ID">
    </label>
    <label class="kgraph-control"><span>Knotentyp</span><select data-kgraph-node-type>{node_options}</select></label>
    <label class="kgraph-control"><span>Beziehung</span><select data-kgraph-edge-type>{edge_options}</select></label>
    <label class="kgraph-control"><span>Bereich</span><select data-kgraph-scope>{scope_options}</select></label>
    <label class="kgraph-control"><span>Status</span><select data-kgraph-status>{status_options}</select></label>
    <label class="kgraph-check"><input type="checkbox" data-kgraph-technical> Technische Dokumente anzeigen</label>
    <div class="kgraph-actions" role="group" aria-label="Graphlayout">
      <button type="button" data-kgraph-layout="breadthfirst">Lernpfad</button>
      <button type="button" data-kgraph-layout="cose">Netzwerk</button>
      <button type="button" data-kgraph-layout="concentric">Fokus</button>
      <button type="button" data-kgraph-fit>Alles einpassen</button>
      <button type="button" data-kgraph-reset>Zurücksetzen</button>
    </div>
    <p class="kgraph-live" data-kgraph-live aria-live="polite">Interaktive Ansicht wird geladen.</p>
  </form>

  <div class="kgraph-workspace">
    <div class="kgraph-canvas" data-kgraph-canvas role="img" tabindex="0"
      aria-label="Interaktiver Wissensgraph. Die vollständige zugängliche Knotenliste folgt unterhalb."
      aria-describedby="knowledge-graph-help"></div>
    <aside class="kgraph-detail" data-kgraph-detail tabindex="-1" aria-label="Details zum ausgewählten Graphobjekt">
      <h3>Details</h3>
      <p>Knoten oder Beziehung auswählen. Alternativ ist die vollständige Tabelle unterhalb per Tastatur bedienbar.</p>
    </aside>
  </div>

  <p id="knowledge-graph-help" class="kgraph-help">
    Knoten können ausgewählt, verschoben und über die Filter eingegrenzt werden. Geplante Seiten sind gestrichelt,
    ungeplant fehlende Ziele werden als Problemknoten gekennzeichnet. Die Visualisierung ergänzt die semantische Liste.
  </p>

  <noscript><p class="kgraph-noscript">JavaScript ist deaktiviert. Die vollständige Tabellenansicht bleibt verfügbar.</p></noscript>

  <details class="kgraph-fallback" open>
    <summary>Vollständige zugängliche Knotenliste</summary>
    {_node_table(graph)}
  </details>

  <details class="kgraph-fallback">
    <summary>Linkprobleme und geplante Ziele</summary>
    {_issues_table(graph)}
  </details>
</div>
""".strip()


def inject_graph_page(
    markdown: str,
    graph: dict[str, Any],
    graph_url: str = "data/knowledge-graph.json",
) -> str:
    if MARKER not in markdown:
        raise ValueError(f"Graphseite enthält den erforderlichen Marker nicht: {MARKER}")
    return markdown.replace(MARKER, render_graph_shell(graph, graph_url), 1)
