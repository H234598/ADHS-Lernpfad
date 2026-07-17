#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "agent/wissensgraph-web-final-8"
BOOTSTRAP = ROOT / ".graph-web-final"
WORKFLOW = ROOT / ".github" / "workflows" / "apply-graph-web-final.yml"


def write(path: str, content: str) -> None:
    destination = ROOT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    destination = ROOT / path
    text = destination.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Erwartete Einfügestelle fehlt in {path}: {old!r}")
    destination.write_text(text.replace(old, new, 1), encoding="utf-8")


def run(*command: str, cwd: Path = ROOT) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


write(
    "scripts/graph_web.py",
    r'''
    #!/usr/bin/env python3
    """Webaufbereitung und barrierearme Fallbackansicht des Wissensgraphen."""

    from __future__ import annotations

    from collections import Counter, defaultdict
    from html import escape
    import json
    import os
    from pathlib import Path
    import re
    from urllib.parse import quote

    GRAPH_RELATIVE_CANDIDATES = (
        Path("build/knowledge-graph/knowledge-graph.json"),
        Path("build/knowledge-graph.json"),
    )
    WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]\n]+)\]\]")
    FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
    FALLBACK_START = "<!-- knowledge-graph-fallback:start -->"
    FALLBACK_END = "<!-- knowledge-graph-fallback:end -->"

    STATUS_LABELS = {
        "planned": "geplant",
        "missing": "Ziel fehlt",
        "missing-document": "Ziel fehlt",
        "missing-heading": "Abschnitt fehlt",
        "ambiguous": "mehrdeutig",
        "malformed": "ungültig",
        "excluded-target": "nicht in der Webfassung",
    }


    def graph_json_path(root: Path) -> Path | None:
        for relative in GRAPH_RELATIVE_CANDIDATES:
            candidate = root / relative
            if candidate.is_file():
                return candidate
        return None


    def load_graph(root: Path) -> dict[str, object]:
        path = graph_json_path(root)
        if path is None:
            return {"nodes": [], "edges": [], "issues": [], "stats": {}}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"nodes": [], "edges": [], "issues": []}


    def _as_list(value: object) -> list[dict[str, object]]:
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


    def _node_status(node: dict[str, object]) -> str:
        status = str(node.get("link_status") or node.get("status") or "ok")
        if node.get("planned") is True or node.get("exists") is False and str(node.get("type")) == "planned":
            return "planned"
        return status


    def _node_keys(node: dict[str, object]) -> set[str]:
        keys: set[str] = set()
        for field in ("id", "label", "title", "path", "reference_id"):
            value = node.get(field)
            if isinstance(value, str) and value.strip():
                normalized = value.strip().replace("\\", "/")
                keys.update({normalized.casefold(), Path(normalized).stem.casefold()})
                if normalized.endswith(".md"):
                    keys.add(normalized[:-3].casefold())
        aliases = node.get("aliases")
        if isinstance(aliases, list):
            keys.update(str(alias).strip().casefold() for alias in aliases if str(alias).strip())
        return keys


    def _split_wikilink(raw: str) -> tuple[str, str, str | None]:
        target_part, separator, alias = raw.partition("|")
        target, heading_separator, heading = target_part.strip().partition("#")
        label = alias.strip() if separator and alias.strip() else (heading.strip() if heading_separator else Path(target).stem)
        return target.strip(), label or target.strip(), heading.strip() if heading_separator else None


    def _special_targets(data: dict[str, object]) -> dict[str, tuple[str, str, str]]:
        result: dict[str, tuple[str, str, str]] = {}
        for node in _as_list(data.get("nodes")):
            status = _node_status(node)
            if status not in STATUS_LABELS:
                continue
            node_id = str(node.get("id") or "")
            label = str(node.get("label") or node.get("title") or node.get("path") or node_id)
            for key in _node_keys(node):
                result[key] = (status, node_id, label)

        for issue in _as_list(data.get("issues")):
            status = str(issue.get("status") or issue.get("code") or issue.get("type") or "missing")
            if status not in STATUS_LABELS:
                continue
            requested = str(
                issue.get("requested_target")
                or issue.get("target")
                or issue.get("raw_target")
                or issue.get("link")
                or ""
            ).strip()
            if requested:
                result[requested.casefold()] = (status, str(issue.get("target_id") or ""), requested)
        return result


    def _replace_outside_fences(text: str, replacer) -> str:
        output: list[str] = []
        fence: str | None = None
        for line in text.splitlines(keepends=True):
            match = FENCE_RE.match(line)
            if match:
                marker = match.group(1)[0]
                fence = marker if fence is None else (None if fence == marker else fence)
                output.append(line)
                continue
            output.append(line if fence else replacer(line))
        return "".join(output)


    def annotate_special_wikilinks(text: str, source: Path, root: Path) -> str:
        """Geplante oder defekte Wikilinks vor der normalen Konvertierung sichtbar ersetzen."""

        special = _special_targets(load_graph(root))
        if not special:
            return text

        def replace_line(line: str) -> str:
            def replace(match: re.Match[str]) -> str:
                target, label, heading = _split_wikilink(match.group(1))
                lookup = [target.casefold(), Path(target).stem.casefold()]
                if heading:
                    lookup.insert(0, f"{target}#{heading}".casefold())
                resolved = next((special[key] for key in lookup if key in special), None)
                if resolved is None:
                    return match.group(0)
                status, node_id, _ = resolved
                status_label = STATUS_LABELS[status]
                css_status = re.sub(r"[^a-z0-9-]+", "-", status.casefold()).strip("-")
                badge = (
                    f'<span class="kg-link__badge" aria-hidden="true">{escape(status_label)}</span>'
                    f'<span class="visually-hidden"> ({escape(status_label)})</span>'
                )
                if status == "planned":
                    href = "/knowledge-graph/?node=" + quote(node_id or target, safe="")
                    return (
                        f'<a class="kg-link kg-link--{css_status}" href="{href}" '
                        f'data-kg-status="{escape(status)}">{escape(label)}{badge}</a>'
                    )
                return (
                    f'<span class="kg-link kg-link--{css_status}" role="note" '
                    f'data-kg-status="{escape(status)}">{escape(label)}{badge}</span>'
                )

            return WIKILINK_RE.sub(replace, line)

        return _replace_outside_fences(text, replace_line)


    def _node_url(node: dict[str, object]) -> str | None:
        url = node.get("url")
        if isinstance(url, str) and url.strip():
            return url
        path = node.get("path")
        if not isinstance(path, str) or not path.endswith(".md"):
            return None
        without_suffix = path[:-3]
        if without_suffix.endswith("/README"):
            without_suffix = without_suffix[:-7]
        return "/" + without_suffix.strip("/") + "/"


    def render_fallback_markdown(data: dict[str, object]) -> str:
        nodes = sorted(
            _as_list(data.get("nodes")),
            key=lambda node: (str(node.get("type") or ""), str(node.get("label") or node.get("id") or "").casefold()),
        )
        edges = _as_list(data.get("edges"))
        issues = _as_list(data.get("issues"))
        node_types = Counter(str(node.get("type") or "unbekannt") for node in nodes)
        edge_types = Counter(str(edge.get("type") or "unbekannt") for edge in edges)
        statuses = Counter(_node_status(node) for node in nodes)
        statuses.update(str(issue.get("status") or issue.get("code") or "problem") for issue in issues)

        lines = [
            "## Semantische Graphansicht",
            "",
            "Diese Tabellen sind die vollständige textuelle Alternative zur interaktiven Darstellung und bleiben auch ohne JavaScript verfügbar.",
            "",
            f"**{len(nodes)} Knoten · {len(edges)} Beziehungen · {len(issues)} gemeldete Probleme**",
            "",
            "### Kennzahlen",
            "",
            "| Kategorie | Anzahl |",
            "|---|---:|",
        ]
        lines.extend(f"| Knoten: `{escape(kind)}` | {count} |" for kind, count in sorted(node_types.items()))
        lines.extend(f"| Beziehung: `{escape(kind)}` | {count} |" for kind, count in sorted(edge_types.items()))
        lines.extend(f"| Status: `{escape(kind)}` | {count} |" for kind, count in sorted(statuses.items()) if kind != "ok")

        lines.extend(["", "### Link- und Strukturprobleme", ""])
        if issues:
            lines.extend(["| Status | Ziel | Fundstelle | Hinweis |", "|---|---|---|---|"])
            for issue in issues:
                status = str(issue.get("status") or issue.get("code") or issue.get("type") or "Problem")
                target = str(issue.get("requested_target") or issue.get("target") or issue.get("target_id") or "—")
                path = str(issue.get("path") or issue.get("source_path") or "—")
                line = issue.get("line")
                location = f"`{escape(path)}:{line}`" if line else f"`{escape(path)}`"
                message = str(issue.get("message") or issue.get("detail") or "—").replace("|", "\\|")
                lines.append(f"| **{escape(STATUS_LABELS.get(status, status))}** | `{escape(target)}` | {location} | {escape(message)} |")
        else:
            lines.append("Keine ungeklärten internen Link- oder Strukturprobleme im aktuellen Build.")

        lines.extend(["", "### Knotenverzeichnis", "", "| Knoten | Typ | Status | Pfad oder ID |", "|---|---|---|---|"])
        for node in nodes:
            label = str(node.get("label") or node.get("title") or node.get("id") or "Unbenannt")
            node_type = str(node.get("type") or "document")
            status = _node_status(node)
            identifier = str(node.get("path") or node.get("id") or "—")
            url = _node_url(node)
            shown_label = f"[{label}]({url})" if url and status == "ok" else escape(label)
            lines.append(f"| {shown_label} | `{escape(node_type)}` | {escape(STATUS_LABELS.get(status, status))} | `{escape(identifier)}` |")
        return "\n".join(lines) + "\n"


    def inject_fallback(text: str, root: Path) -> str:
        if FALLBACK_START not in text or FALLBACK_END not in text:
            return text
        before, remainder = text.split(FALLBACK_START, 1)
        _, after = remainder.split(FALLBACK_END, 1)
        fallback = render_fallback_markdown(load_graph(root))
        return before + FALLBACK_START + "\n\n" + fallback + "\n" + FALLBACK_END + after


    def copy_graph_outputs(root: Path, docs: Path) -> list[str]:
        source_json = graph_json_path(root)
        if source_json is None:
            raise FileNotFoundError("Wissensgraph-JSON wurde vor dem Dokumentationsbuild nicht erzeugt")
        destination = docs / "knowledge-graph" / "data"
        destination.mkdir(parents=True, exist_ok=True)
        copied: list[str] = []
        candidates = {
            "knowledge-graph.json": source_json,
            "knowledge-graph.mmd": source_json.with_suffix(".mmd"),
            "knowledge-graph.graphml": source_json.with_suffix(".graphml"),
            "graph-report.md": source_json.parent / "graph-report.md",
            "graph-report.json": source_json.parent / "graph-report.json",
        }
        for name, source in candidates.items():
            if source.is_file():
                shutil_target = destination / name
                shutil_target.write_bytes(source.read_bytes())
                copied.append(name)
        return copied
    ''',
)

write(
    "assets/javascripts/knowledge-graph.js",
    r'''
    (() => {
      "use strict";

      const instances = new WeakMap();
      const statusLabels = {
        ok: "vorhanden",
        planned: "geplant",
        missing: "Ziel fehlt",
        "missing-document": "Ziel fehlt",
        "missing-heading": "Abschnitt fehlt",
        ambiguous: "mehrdeutig",
        malformed: "ungültig",
        "excluded-target": "nicht in der Webfassung",
      };

      function text(value) {
        return value == null ? "" : String(value);
      }

      function nodeStatus(node) {
        if (node.planned === true || (node.exists === false && node.type === "planned")) return "planned";
        return text(node.link_status || node.status || "ok");
      }

      function nodeLabel(node) {
        return text(node.label || node.title || node.path || node.id || "Unbenannt");
      }

      function normaliseGraph(raw) {
        const nodes = Array.isArray(raw.nodes) ? raw.nodes.filter(Boolean) : [];
        const edges = Array.isArray(raw.edges) ? raw.edges.filter(Boolean) : [];
        return {
          ...raw,
          nodes: nodes.map((node) => ({
            ...node,
            id: text(node.id),
            label: nodeLabel(node),
            type: text(node.type || "document"),
            scope: text(node.scope || "learning"),
            graphStatus: nodeStatus(node),
          })),
          edges: edges.map((edge, index) => ({
            ...edge,
            id: text(edge.id || `edge-${index}`),
            source: text(edge.source),
            target: text(edge.target),
            type: text(edge.type || "wikilink"),
            graphStatus: text(edge.status || "ok"),
          })),
          issues: Array.isArray(raw.issues) ? raw.issues : [],
        };
      }

      function optionValues(items, field) {
        return [...new Set(items.map((item) => text(item[field])).filter(Boolean))].sort((a, b) => a.localeCompare(b, "de"));
      }

      function fillSelect(select, values, allLabel) {
        select.replaceChildren(new Option(allLabel, ""));
        values.forEach((value) => select.add(new Option(value, value)));
      }

      function searchableNode(node) {
        return [node.id, node.label, node.path, node.type, node.scope, node.graphStatus]
          .concat(Array.isArray(node.aliases) ? node.aliases : [])
          .concat(Array.isArray(node.tags) ? node.tags : [])
          .join(" ")
          .toLocaleLowerCase("de");
      }

      function createElements(graph) {
        return [
          ...graph.nodes.map((node) => ({ group: "nodes", data: node })),
          ...graph.edges
            .filter((edge) => edge.source && edge.target)
            .map((edge) => ({ group: "edges", data: edge })),
        ];
      }

      function stylesheet() {
        return [
          {
            selector: "node",
            style: {
              label: "data(label)",
              "font-size": 10,
              "text-wrap": "wrap",
              "text-max-width": 110,
              "text-valign": "center",
              "text-halign": "center",
              width: 54,
              height: 54,
              "background-color": "#546e7a",
              color: "#111",
              "border-width": 2,
              "border-color": "#263238",
            },
          },
          { selector: 'node[type = "chapter"]', style: { shape: "round-rectangle", width: 110, height: 48, "background-color": "#90caf9" } },
          { selector: 'node[type = "concept"]', style: { shape: "ellipse", "background-color": "#a5d6a7" } },
          { selector: 'node[type = "reference"]', style: { shape: "diamond", "background-color": "#ce93d8" } },
          { selector: 'node[type = "section"]', style: { shape: "hexagon", "background-color": "#ffe082" } },
          { selector: 'node[graphStatus = "planned"]', style: { "background-opacity": 0.25, "border-style": "dashed", "border-width": 4 } },
          { selector: 'node[graphStatus = "missing"], node[graphStatus = "missing-document"], node[graphStatus = "missing-heading"]', style: { shape: "tag", "background-color": "#ef9a9a", "border-width": 4 } },
          { selector: 'node[graphStatus = "ambiguous"]', style: { shape: "barrel", "background-color": "#b39ddb", "border-style": "double", "border-width": 5 } },
          {
            selector: "edge",
            style: {
              width: 1.6,
              "line-color": "#78909c",
              "target-arrow-color": "#78909c",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              opacity: 0.7,
            },
          },
          { selector: 'edge[type = "prerequisite"]', style: { width: 3, "line-color": "#1565c0", "target-arrow-color": "#1565c0" } },
          { selector: 'edge[type = "cites"]', style: { "line-style": "dotted", "line-color": "#7b1fa2", "target-arrow-color": "#7b1fa2" } },
          { selector: 'edge[type = "tagged_with"]', style: { "line-style": "dashed", "line-color": "#2e7d32", "target-arrow-color": "#2e7d32" } },
          { selector: 'edge[graphStatus != "ok"]', style: { "line-style": "dashed", "line-color": "#c62828", "target-arrow-color": "#c62828", width: 3 } },
          { selector: ".kg-hidden", style: { display: "none" } },
          { selector: ".kg-neighbour", style: { "border-width": 5, "border-color": "#ff6f00" } },
          { selector: ":selected", style: { "border-width": 6, "border-color": "#d84315", "z-index": 999 } },
        ];
      }

      function layoutOptions(name, reducedMotion) {
        if (name === "breadthfirst") return { name, directed: true, padding: 30, animate: !reducedMotion, spacingFactor: 1.25 };
        if (name === "concentric") return { name, padding: 30, animate: !reducedMotion, minNodeSpacing: 35 };
        return { name: "cose", padding: 30, animate: !reducedMotion, randomize: false, nodeRepulsion: 500000, idealEdgeLength: 100 };
      }

      function renderDetails(panel, node, graph) {
        if (!node) {
          panel.innerHTML = "<h2>Details</h2><p>Wähle einen Knoten in der Grafik oder in der Tabelle.</p>";
          return;
        }
        const incoming = graph.edges.filter((edge) => edge.target === node.id);
        const outgoing = graph.edges.filter((edge) => edge.source === node.id);
        const relation = (edge) => `<li><code>${edge.type}</code> – ${edge.source === node.id ? edge.target : edge.source}</li>`;
        const url = text(node.url);
        const openLink = url && node.graphStatus === "ok" ? `<p><a class="md-button md-button--primary" href="${url}">Seite öffnen</a></p>` : "";
        panel.innerHTML = `
          <h2 tabindex="-1">${node.label}</h2>
          <p><span class="kg-badge kg-badge--${node.graphStatus}">${statusLabels[node.graphStatus] || node.graphStatus}</span>
          <span class="kg-badge">${node.type}</span></p>
          ${openLink}
          <dl>
            <dt>Stabile ID</dt><dd><code>${node.id}</code></dd>
            <dt>Pfad</dt><dd><code>${text(node.path || "—")}</code></dd>
            <dt>Scope</dt><dd>${node.scope}</dd>
          </dl>
          <h3>Ausgehende Beziehungen (${outgoing.length})</h3><ul>${outgoing.map(relation).join("") || "<li>keine</li>"}</ul>
          <h3>Eingehende Beziehungen (${incoming.length})</h3><ul>${incoming.map(relation).join("") || "<li>keine</li>"}</ul>`;
        const heading = panel.querySelector("h2");
        if (heading) heading.focus({ preventScroll: true });
      }

      function initialise(container) {
        const previous = instances.get(container);
        if (previous) previous.destroy();

        const graphHost = container.querySelector("[data-kg-canvas]");
        const status = container.querySelector("[data-kg-live]");
        const search = container.querySelector("[data-kg-search]");
        const typeSelect = container.querySelector("[data-kg-type]");
        const edgeSelect = container.querySelector("[data-kg-edge]");
        const statusSelect = container.querySelector("[data-kg-status]");
        const scopeSelect = container.querySelector("[data-kg-scope]");
        const layoutSelect = container.querySelector("[data-kg-layout]");
        const resetButton = container.querySelector("[data-kg-reset]");
        const fitButton = container.querySelector("[data-kg-fit]");
        const detailPanel = container.querySelector("[data-kg-details]");
        const fallbackRows = [...document.querySelectorAll("[data-kg-node-row]")];
        const dataUrl = container.dataset.graphUrl;
        const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
        const abortController = new AbortController();
        let cy = null;
        let graph = null;
        let selectedId = new URLSearchParams(location.search).get("node") || "";
        let selecting = false;

        async function load() {
          try {
            const response = await fetch(dataUrl, { signal: abortController.signal, credentials: "same-origin" });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            graph = normaliseGraph(await response.json());
            fillSelect(typeSelect, optionValues(graph.nodes, "type"), "Alle Knotentypen");
            fillSelect(edgeSelect, optionValues(graph.edges, "type"), "Alle Beziehungen");
            fillSelect(statusSelect, optionValues(graph.nodes, "graphStatus"), "Alle Status");
            fillSelect(scopeSelect, optionValues(graph.nodes, "scope"), "Alle Bereiche");

            if (typeof window.cytoscape !== "function") throw new Error("Cytoscape.js wurde nicht geladen");
            cy = window.cytoscape({
              container: graphHost,
              elements: createElements(graph),
              style: stylesheet(),
              layout: layoutOptions(layoutSelect.value, reducedMotion),
              minZoom: 0.15,
              maxZoom: 3,
              wheelSensitivity: 0.2,
            });

            cy.on("select", "node", (event) => {
              if (selecting) return;
              selecting = true;
              try {
                selectedId = event.target.id();
                cy.nodes().removeClass("kg-neighbour");
                event.target.closedNeighborhood().nodes().addClass("kg-neighbour");
                renderDetails(detailPanel, event.target.data(), graph);
                document.querySelectorAll("[data-kg-node-row]").forEach((row) => {
                  row.toggleAttribute("data-selected", row.dataset.nodeId === selectedId);
                });
                const url = new URL(location.href);
                url.searchParams.set("node", selectedId);
                history.replaceState(null, "", url);
              } finally {
                selecting = false;
              }
            });

            if (selectedId && cy.getElementById(selectedId).length) {
              const selected = cy.getElementById(selectedId);
              selected.select();
              cy.center(selected);
            }
            applyFilters();
          } catch (error) {
            if (error.name === "AbortError") return;
            graphHost.innerHTML = `<p class="admonition warning">Die interaktive Graphansicht konnte nicht geladen werden: ${error.message}. Die Tabellenansicht darunter bleibt vollständig nutzbar.</p>`;
            status.textContent = "Interaktive Ansicht nicht verfügbar; semantische Tabellenansicht aktiv.";
          }
        }

        function applyFilters() {
          if (!cy || !graph) return;
          const query = search.value.trim().toLocaleLowerCase("de");
          const wantedType = typeSelect.value;
          const wantedEdge = edgeSelect.value;
          const wantedStatus = statusSelect.value;
          const wantedScope = scopeSelect.value;
          let visibleNodes = 0;

          cy.batch(() => {
            cy.elements().removeClass("kg-hidden");
            cy.nodes().forEach((element) => {
              const node = element.data();
              const visible = (!query || searchableNode(node).includes(query))
                && (!wantedType || node.type === wantedType)
                && (!wantedStatus || node.graphStatus === wantedStatus)
                && (!wantedScope || node.scope === wantedScope);
              element.toggleClass("kg-hidden", !visible);
              if (visible) visibleNodes += 1;
            });
            cy.edges().forEach((element) => {
              const edge = element.data();
              const endpointsVisible = !element.source().hasClass("kg-hidden") && !element.target().hasClass("kg-hidden");
              element.toggleClass("kg-hidden", !endpointsVisible || Boolean(wantedEdge && edge.type !== wantedEdge));
            });
          });

          fallbackRows.forEach((row) => {
            const node = graph.nodes.find((candidate) => candidate.id === row.dataset.nodeId);
            if (!node) return;
            const visible = (!query || searchableNode(node).includes(query))
              && (!wantedType || node.type === wantedType)
              && (!wantedStatus || node.graphStatus === wantedStatus)
              && (!wantedScope || node.scope === wantedScope);
            row.hidden = !visible;
          });
          status.textContent = `${visibleNodes} von ${graph.nodes.length} Knoten sichtbar.`;
        }

        [search, typeSelect, edgeSelect, statusSelect, scopeSelect].forEach((control) => {
          control.addEventListener(control === search ? "input" : "change", applyFilters);
        });
        layoutSelect.addEventListener("change", () => cy && cy.layout(layoutOptions(layoutSelect.value, reducedMotion)).run());
        fitButton.addEventListener("click", () => cy && cy.fit(cy.elements(":visible"), 30));
        resetButton.addEventListener("click", () => {
          search.value = "";
          [typeSelect, edgeSelect, statusSelect, scopeSelect].forEach((select) => { select.value = ""; });
          selectedId = "";
          if (cy) {
            cy.elements().unselect();
            cy.nodes().removeClass("kg-neighbour");
          }
          renderDetails(detailPanel, null, graph || { edges: [] });
          const url = new URL(location.href);
          url.searchParams.delete("node");
          history.replaceState(null, "", url);
          applyFilters();
        });
        fallbackRows.forEach((row) => {
          row.addEventListener("click", () => {
            if (!cy) return;
            const node = cy.getElementById(row.dataset.nodeId);
            if (node.length) {
              node.select();
              cy.center(node);
            }
          });
        });

        load();
        const instance = { destroy() { abortController.abort(); if (cy) cy.destroy(); } };
        instances.set(container, instance);
        return instance;
      }

      function initialiseAll() {
        document.querySelectorAll("[data-knowledge-graph]").forEach(initialise);
      }

      if (typeof window.document$ !== "undefined" && window.document$.subscribe) {
        window.document$.subscribe(initialiseAll);
      } else if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialiseAll, { once: true });
      } else {
        initialiseAll();
      }
    })();
    ''',
)

write(
    "assets/stylesheets/knowledge-graph.css",
    r'''
    .knowledge-graph-shell {
      display: grid;
      gap: 1rem;
      margin-block: 1rem 2rem;
    }

    .knowledge-graph-controls {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
      gap: 0.75rem;
      padding: 1rem;
      border: 1px solid var(--md-default-fg-color--lightest);
      border-radius: 0.75rem;
      background: color-mix(in srgb, var(--md-primary-fg-color) 6%, var(--md-default-bg-color));
    }

    .knowledge-graph-controls label {
      display: grid;
      gap: 0.25rem;
      font-weight: 650;
    }

    .knowledge-graph-controls input,
    .knowledge-graph-controls select,
    .knowledge-graph-controls button {
      min-height: 2.65rem;
      padding: 0.55rem 0.7rem;
      border: 1px solid var(--md-default-fg-color--lightest);
      border-radius: 0.45rem;
      background: var(--md-default-bg-color);
      color: var(--md-default-fg-color);
      font: inherit;
    }

    .knowledge-graph-controls button {
      cursor: pointer;
      font-weight: 700;
    }

    .knowledge-graph-controls button:hover,
    .knowledge-graph-controls button:focus-visible {
      border-color: var(--md-accent-fg-color);
    }

    .knowledge-graph-stage {
      min-height: min(72vh, 52rem);
      border: 1px solid var(--md-default-fg-color--lightest);
      border-radius: 0.75rem;
      overflow: hidden;
      background: var(--md-default-bg-color);
      box-shadow: 0 0.35rem 1.15rem rgb(0 0 0 / 8%);
    }

    .knowledge-graph-canvas {
      width: 100%;
      min-height: min(72vh, 52rem);
    }

    .knowledge-graph-layout {
      display: grid;
      grid-template-columns: minmax(0, 3fr) minmax(16rem, 1fr);
      gap: 1rem;
    }

    .knowledge-graph-details {
      max-height: min(72vh, 52rem);
      padding: 1rem;
      overflow: auto;
      border: 1px solid var(--md-default-fg-color--lightest);
      border-radius: 0.75rem;
      background: var(--md-default-bg-color);
    }

    .knowledge-graph-details h2:focus {
      outline: 2px solid var(--md-accent-fg-color);
      outline-offset: 0.2rem;
    }

    .kg-badge,
    .kg-link__badge {
      display: inline-block;
      margin-inline-start: 0.35em;
      padding: 0.12rem 0.42rem;
      border: 1px solid currentColor;
      border-radius: 999px;
      font-size: 0.72em;
      font-weight: 750;
      line-height: 1.35;
      vertical-align: 0.08em;
    }

    .kg-link {
      border-radius: 0.2rem;
      text-decoration-style: dashed;
      text-decoration-thickness: 0.1em;
      text-underline-offset: 0.18em;
    }

    .kg-link--planned,
    .kg-badge--planned {
      color: #8a5600;
      background: color-mix(in srgb, #ffb300 16%, transparent);
    }

    .kg-link--missing,
    .kg-link--missing-document,
    .kg-link--missing-heading,
    .kg-link--malformed,
    .kg-badge--missing,
    .kg-badge--missing-document,
    .kg-badge--missing-heading,
    .kg-badge--malformed {
      color: #a21b1b;
      background: color-mix(in srgb, #d32f2f 12%, transparent);
    }

    .kg-link--ambiguous,
    .kg-badge--ambiguous {
      color: #5e2a84;
      background: color-mix(in srgb, #7e57c2 14%, transparent);
    }

    .kg-link[data-kg-status]:not(a) {
      cursor: help;
      border-bottom: 0.13em dotted currentColor;
    }

    .knowledge-graph-legend {
      display: flex;
      flex-wrap: wrap;
      gap: 0.6rem;
      padding: 0;
      list-style: none;
    }

    .knowledge-graph-legend li {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
    }

    .knowledge-graph-legend__symbol {
      width: 1.05rem;
      height: 1.05rem;
      border: 2px solid currentColor;
      border-radius: 0.2rem;
    }

    .knowledge-graph-legend__symbol--planned { border-style: dashed; }
    .knowledge-graph-legend__symbol--missing { border-width: 4px; }
    .knowledge-graph-legend__symbol--ambiguous { border-style: double; border-width: 4px; }

    .visually-hidden {
      position: absolute !important;
      width: 1px !important;
      height: 1px !important;
      padding: 0 !important;
      margin: -1px !important;
      overflow: hidden !important;
      clip: rect(0, 0, 0, 0) !important;
      white-space: nowrap !important;
      border: 0 !important;
    }

    [data-kg-node-row] { cursor: pointer; }
    [data-kg-node-row][data-selected] { outline: 3px solid var(--md-accent-fg-color); outline-offset: -3px; }

    @media (max-width: 59.99em) {
      .knowledge-graph-layout { grid-template-columns: 1fr; }
      .knowledge-graph-stage,
      .knowledge-graph-canvas { min-height: 62vh; }
      .knowledge-graph-details { max-height: none; }
    }

    @media print {
      .knowledge-graph-controls,
      .knowledge-graph-stage,
      .knowledge-graph-details { display: none !important; }
    }

    @media (prefers-reduced-motion: reduce) {
      .knowledge-graph-shell *,
      .kg-link { scroll-behavior: auto !important; transition: none !important; animation: none !important; }
    }
    ''',
)

write(
    "knowledge-graph/README.md",
    r'''
    ---
    title: Wissensgraph
    tags: [Wissensgraph, Obsidian, Navigation, Metadaten]
    ---

    # Wissensgraph

    Der Wissensgraph wird bei jedem Build aus den Markdown-Dateien, ihren YAML-Metadaten, Überschriften, Wikilinks, Einbettungen, Quellenangaben und der Lernpfadreihenfolge neu erzeugt. Er ist ein **Dokument- und Navigationsgraph** des Kompendiums, keine automatisch abgeleitete medizinische Ontologie.

    ## Interaktive Ansicht

    <div class="knowledge-graph-shell" data-knowledge-graph data-graph-url="data/knowledge-graph.json">
      <div class="knowledge-graph-controls" aria-label="Wissensgraph filtern">
        <label>Suche
          <input type="search" data-kg-search placeholder="Titel, Tag, Pfad oder ID" autocomplete="off">
        </label>
        <label>Knotentyp
          <select data-kg-type><option value="">Alle Knotentypen</option></select>
        </label>
        <label>Beziehung
          <select data-kg-edge><option value="">Alle Beziehungen</option></select>
        </label>
        <label>Status
          <select data-kg-status><option value="">Alle Status</option></select>
        </label>
        <label>Bereich
          <select data-kg-scope><option value="">Alle Bereiche</option></select>
        </label>
        <label>Layout
          <select data-kg-layout>
            <option value="cose">Netzwerk</option>
            <option value="breadthfirst">Lernpfad</option>
            <option value="concentric">Fokus</option>
          </select>
        </label>
        <button type="button" data-kg-fit>Alles einpassen</button>
        <button type="button" data-kg-reset>Filter zurücksetzen</button>
      </div>
      <p data-kg-live aria-live="polite">Graphdaten werden geladen.</p>
      <div class="knowledge-graph-layout">
        <div class="knowledge-graph-stage">
          <div class="knowledge-graph-canvas" data-kg-canvas role="img" aria-label="Interaktive visuelle Darstellung des Wissensgraphen"></div>
        </div>
        <aside class="knowledge-graph-details" data-kg-details aria-label="Details zum ausgewählten Graphknoten">
          <h2>Details</h2>
          <p>Wähle einen Knoten in der Grafik oder in der Tabelle.</p>
        </aside>
      </div>
    </div>

    ## Legende

    <ul class="knowledge-graph-legend">
      <li><span class="knowledge-graph-legend__symbol"></span> vorhandene Seite oder Begriff</li>
      <li><span class="knowledge-graph-legend__symbol knowledge-graph-legend__symbol--planned"></span> geplante, ausdrücklich registrierte Seite</li>
      <li><span class="knowledge-graph-legend__symbol knowledge-graph-legend__symbol--missing"></span> ungeplant fehlendes Ziel oder fehlender Abschnitt</li>
      <li><span class="knowledge-graph-legend__symbol knowledge-graph-legend__symbol--ambiguous"></span> mehrdeutiges Ziel</li>
    </ul>

    Status werden zusätzlich als Text, Form, Rahmen- oder Linienart dargestellt; Farbe ist nie das einzige Unterscheidungsmerkmal. Geplante Seiten führen nicht auf eine 404-Seite, sondern auf ihre Detailansicht im Graphen. Ungeplant fehlende oder mehrdeutige Ziele bleiben Validierungsfehler.

    <!-- knowledge-graph-fallback:start -->

    Die semantische Tabellenansicht wird beim Dokumentationsbuild eingesetzt.

    <!-- knowledge-graph-fallback:end -->

    ## Datenquellen und Aktualisierung

    Der kanonische Generator verarbeitet:

    - jede eingeschlossene Markdown-Datei als Dokumentknoten,
    - `prerequisites`, `tags`, `references` und optionale `related`-Metadaten,
    - Wikilinks und Obsidian-Einbettungen außerhalb von Codebereichen,
    - referenzierte Überschriften,
    - die Reihenfolge aus `index.json`,
    - ausdrücklich registrierte geplante Ziele aus `knowledge-graph/planned-nodes.yaml`.

    Die Webansicht verwendet dieselbe JSON-Ausgabe wie die Berichte und maschinenlesbaren Exporte. Der native Obsidian-Graph bleibt davon unabhängig und entsteht unmittelbar aus den Wikilinks im Vault.

    ## Ausgabeformate

    - `knowledge-graph.json` – kanonische Knoten, Kanten, Fundstellen, Status und Kennzahlen
    - `knowledge-graph.graphml` – Austauschformat für Gephi und Cytoscape Desktop
    - `knowledge-graph.mmd` – kompakte Mermaid-Diagnoseansicht
    - `graph-report.md` und `graph-report.json` – verständlicher Qualitätsbericht
    ''',
)

write(
    "package.json",
    r'''
    {
      "name": "adhs-lernpfad-web-assets",
      "private": true,
      "version": "1.0.0",
      "description": "Reproduzierbare Web-Assets für den ADHS-Lernpfad",
      "license": "MIT",
      "devDependencies": {
        "cytoscape": "3.34.0"
      },
      "scripts": {
        "check:graph-js": "node --check assets/javascripts/knowledge-graph.js",
        "test": "npm run check:graph-js"
      }
    }
    ''',
)

write(
    "tests/test_graph_web.py",
    r'''
    from __future__ import annotations

    import json
    from pathlib import Path
    import sys
    import tempfile
    import unittest

    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

    from graph_web import annotate_special_wikilinks, inject_fallback, render_fallback_markdown


    class GraphWebTests(unittest.TestCase):
        def graph(self) -> dict[str, object]:
            return {
                "nodes": [
                    {"id": "doc:vorhanden", "label": "Vorhanden", "type": "chapter", "status": "ok", "path": "Vorhanden.md"},
                    {"id": "planned:spaeter", "label": "Später", "type": "planned", "planned": True, "exists": False, "path": "Spaeter.md"},
                ],
                "edges": [{"id": "e1", "source": "doc:vorhanden", "target": "planned:spaeter", "type": "wikilink"}],
                "issues": [{"status": "missing-heading", "requested_target": "Vorhanden#Fehlt", "path": "Quelle.md", "line": 3}],
            }

        def write_graph(self, root: Path) -> None:
            destination = root / "build" / "knowledge-graph"
            destination.mkdir(parents=True)
            (destination / "knowledge-graph.json").write_text(json.dumps(self.graph()), encoding="utf-8")

        def test_planned_link_becomes_marked_graph_link(self) -> None:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.write_graph(root)
                source = root / "Kapitel.md"
                converted = annotate_special_wikilinks("Siehe [[Spaeter|spätere Einheit]].\n", source, root)
                self.assertIn('kg-link--planned', converted)
                self.assertIn('data-kg-status="planned"', converted)
                self.assertIn('node=planned%3Aspaeter', converted)

        def test_missing_heading_becomes_non_navigating_note(self) -> None:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.write_graph(root)
                converted = annotate_special_wikilinks("[[Vorhanden#Fehlt|Abschnitt]]", root / "Quelle.md", root)
                self.assertIn('role="note"', converted)
                self.assertIn("Abschnitt fehlt", converted)
                self.assertNotIn("href=", converted)

        def test_code_fence_is_not_rewritten(self) -> None:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.write_graph(root)
                text = "```markdown\n[[Spaeter]]\n```\n"
                self.assertEqual(text, annotate_special_wikilinks(text, root / "Quelle.md", root))

        def test_fallback_contains_nodes_and_issues(self) -> None:
            fallback = render_fallback_markdown(self.graph())
            self.assertIn("2 Knoten", fallback)
            self.assertIn("Später", fallback)
            self.assertIn("Abschnitt fehlt", fallback)

        def test_fallback_injection_preserves_markers(self) -> None:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.write_graph(root)
                source = "A\n<!-- knowledge-graph-fallback:start -->\nalt\n<!-- knowledge-graph-fallback:end -->\nB\n"
                rendered = inject_fallback(source, root)
                self.assertIn("Semantische Graphansicht", rendered)
                self.assertNotIn("\nalt\n", rendered)

        def test_assets_are_locally_referenced(self) -> None:
            mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
            self.assertIn("assets/vendor/cytoscape/cytoscape.min.js", mkdocs)
            self.assertNotIn("cdn.jsdelivr.net/npm/cytoscape", mkdocs)


    if __name__ == "__main__":
        unittest.main()
    ''',
)

# Integrate styles and scripts into MkDocs.
replace_once(
    "mkdocs.yml",
    "  - assets/stylesheets/evidence.css\n",
    "  - assets/stylesheets/evidence.css\n  - assets/stylesheets/knowledge-graph.css\n",
)
replace_once(
    "mkdocs.yml",
    "  - assets/javascripts/mathjax.js\n",
    "  - assets/javascripts/mathjax.js\n  - assets/vendor/cytoscape/cytoscape.min.js\n  - assets/javascripts/knowledge-graph.js\n",
)

# Integrate graph preparation into the documentation build using stable textual anchors.
build_docs = ROOT / "scripts" / "build_docs.py"
build_text = build_docs.read_text(encoding="utf-8")
if "from graph_web import" not in build_text:
    build_text = build_text.replace(
        "from content_links import convert_for_web, validate_all\n",
        "from content_links import convert_for_web, validate_all\n"
        "from graph_web import annotate_special_wikilinks, copy_graph_outputs, inject_fallback\n",
        1,
    )
if "annotate_special_wikilinks" not in build_text.split("for relative_path in files:", 1)[-1]:
    old = '    converted = convert_for_web(source.read_text(encoding="utf-8"), source, ROOT)\n'
    new = (
        '    source_text = source.read_text(encoding="utf-8")\n'
        '    if relative_path == "knowledge-graph/README.md":\n'
        '        source_text = inject_fallback(source_text, ROOT)\n'
        '    source_text = annotate_special_wikilinks(source_text, source, ROOT)\n'
        '    converted = convert_for_web(source_text, source, ROOT)\n'
    )
    if old not in build_text:
        raise RuntimeError("Konvertierungsstelle in scripts/build_docs.py nicht gefunden")
    build_text = build_text.replace(old, new, 1)
if "copy_graph_outputs(ROOT, DOCS)" not in build_text:
    anchor = 'shutil.copy2(ROOT / "CNAME", DOCS / "CNAME")\n'
    if anchor not in build_text:
        raise RuntimeError("CNAME-Kopierstelle in scripts/build_docs.py nicht gefunden")
    build_text = build_text.replace(
        anchor,
        'graph_outputs = copy_graph_outputs(ROOT, DOCS)\n\n' + anchor,
        1,
    )
    build_text = build_text.replace(
        '"optionale Downloads und CNAME"\n',
        'f"{len(graph_outputs)} Wissensgraphdateien, optionale Downloads und CNAME"\n',
        1,
    )
build_docs.write_text(build_text, encoding="utf-8")

# Update or add the explicit phase checklist in the versioned plan.
plan = ROOT / "knowledge-graph" / "IMPLEMENTIERUNGSPLAN.md"
if plan.is_file():
    plan_text = plan.read_text(encoding="utf-8")
else:
    plan_text = "# Implementierungsplan – Wissensgraph 2.0\n"
status_block = """
## Umsetzungsstatus

- [x] **Phase 1 – Kernmodell, Resolver und Generator:** kanonischer Inhaltsindex, typisierte Beziehungen, stabile IDs, Provenienz, JSON, Mermaid, GraphML, Berichte und Tests.
- [x] **Phase 2 – Weboberfläche und Linkkennzeichnung:** lokale Cytoscape-Auslieferung, interaktive Suche und Filter, Fokus- und Layoutmodi, Detailansicht, semantische No-JS-Alternative, mobile Darstellung, reduzierte Bewegung sowie sichtbare Status für geplante oder defekte Ziele.
- [ ] **Phase 3 – CI, Exporte, Migration und Betriebsdokumentation:** Qualitätsgates, Preview- und Berichtartefakte, Graphdownloads, kanonische Metadatenmigration und Aktualisierung der Automationsregeln.

### Phase-2-Abnahme

- [x] Graphdaten werden als statisches JSON in die MkDocs-Seite kopiert.
- [x] Suche, Typ-, Beziehungs-, Status- und Scopefilter sind implementiert.
- [x] Lernpfad-, Netzwerk- und Fokuslayout sind umschaltbar.
- [x] Vorhandene Seiten sind aus der Detailansicht erreichbar; geplante Ziele führen nicht auf 404-Seiten.
- [x] Geplante, fehlende, mehrdeutige und ungültige Ziele besitzen Textbadge, Form beziehungsweise Linienart und Farbe.
- [x] Eine vollständige semantische Tabellenansicht bleibt ohne JavaScript und im Druck verfügbar.
- [x] MkDocs Instant Navigation initialisiert die Graphinstanz kontrolliert neu.
- [x] Touch-/Mobilansicht und `prefers-reduced-motion` werden berücksichtigt.
- [x] Cytoscape.js wird lokal, versionsfest und mit Lizenz sowie Prüfsummen ausgeliefert.
""".strip() + "\n"
pattern = re.compile(r"\n## Umsetzungsstatus\n.*?(?=\n## (?!Umsetzungsstatus)|\Z)", re.S)
if pattern.search(plan_text):
    plan_text = pattern.sub("\n" + status_block + "\n", plan_text, count=1)
else:
    plan_text = plan_text.rstrip() + "\n\n" + status_block
plan.write_text(plan_text, encoding="utf-8")

# Vendor the exact Cytoscape release from npm and create a deterministic lockfile.
with tempfile.TemporaryDirectory(prefix="cytoscape-vendor-") as temp:
    temp_path = Path(temp)
    result = subprocess.run(
        ["npm", "pack", "cytoscape@3.34.0", "--silent"],
        cwd=temp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    archive_path = temp_path / result.stdout.strip().splitlines()[-1]
    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(temp_path, filter="data")
    package = temp_path / "package"
    metadata = json.loads((package / "package.json").read_text(encoding="utf-8"))
    if metadata.get("version") != "3.34.0":
        raise RuntimeError("Unerwartete Cytoscape-Version")
    vendor = ROOT / "assets" / "vendor" / "cytoscape"
    vendor.mkdir(parents=True, exist_ok=True)
    shutil.copy2(package / "dist" / "cytoscape.min.js", vendor / "cytoscape.min.js")
    shutil.copy2(package / "LICENSE", vendor / "LICENSE")
    (vendor / "VERSION.txt").write_text("3.34.0\n", encoding="utf-8")

run("npm", "install", "--package-lock-only", "--ignore-scripts")
checksum = subprocess.run(
    ["sha256sum", "cytoscape.min.js", "LICENSE", "VERSION.txt"],
    cwd=ROOT / "assets" / "vendor" / "cytoscape",
    check=True,
    capture_output=True,
    text=True,
).stdout
(ROOT / "assets" / "vendor" / "cytoscape" / "SHA256SUMS.txt").write_text(checksum, encoding="utf-8")

# Remove the transport before verification so it can never enter the final phase commit.
shutil.rmtree(BOOTSTRAP)
WORKFLOW.unlink(missing_ok=True)

run("python", "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements-docs.txt", "-r", "requirements-export.txt")
run("python", "-m", "pip", "check")
run("python", "-m", "compileall", "-q", "scripts", "tests")
run("python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py")
run("npm", "test")
run("git", "diff", "--check")
run("python", "scripts/build_literature.py")
run("git", "diff", "--exit-code", "--", "Literatur.md", "references.bib", "references.json")
run("python", "scripts/validate_links.py")
run("python", "scripts/build_graph.py")
run("python", "scripts/validate_compendium.py")
run("python", "scripts/build_combined.py")
run("python", "scripts/build_anki.py")
run("python", "scripts/build_docs.py")
run("mkdocs", "build", "--strict")

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", "-A")
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
    print("Keine Phase-2-Änderungen anzuwenden")
    raise SystemExit(0)
run("git", "commit", "-m", "Wissensgraph 2.0: interaktive Weboberfläche")
run("git", "push", "origin", f"HEAD:{BRANCH}")
print("Phase 2 vollständig angewendet, geprüft und veröffentlicht")
