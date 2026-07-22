(() => {
  "use strict";

  const instances = new WeakMap();
  const statusLabels = {
    ok: "vorhanden",
    planned: "geplant",
    missing: "Ziel fehlt",
    "missing-document": "Ziel fehlt",
    "missing-heading": "Abschnitt fehlt",
    "missing-reference": "Quelle fehlt",
    ambiguous: "mehrdeutig",
    malformed: "ungültig",
    "excluded-target": "nicht in der Webfassung",
  };
  const lifecycleLabels = {
    planned: "geplant",
    in_progress: "in Arbeit",
    published: "veröffentlicht",
    not_applicable: "nicht anwendbar",
  };
  const runStatusLabels = {
    started: "gestartet",
    running: "läuft",
    success: "OK",
    failed: "fehlgeschlagen",
    blocked: "blockiert",
    recovered: "wiederhergestellt",
    unknown: "unbekannt",
  };

  function text(value) {
    return value == null ? "" : String(value);
  }

  function escapeHtml(value) {
    return text(value).replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[character]));
  }

  function safeSiteUrl(value) {
    const candidate = text(value).trim();
    if (!candidate.startsWith("/") || candidate.startsWith("//") || /[\\\u0000-\u001f\u007f]/.test(candidate)) return "";
    const rawPath = candidate.split(/[?#]/, 1)[0];
    let decodedPath;
    try {
      decodedPath = decodeURIComponent(rawPath);
    } catch {
      return "";
    }
    if (/[\\\u0000-\u001f\u007f]/.test(decodedPath) || decodedPath.split("/").some((part) => part === "." || part === "..")) return "";
    try {
      const parsed = new URL(candidate, location.origin);
      return parsed.origin === location.origin ? candidate : "";
    } catch {
      return "";
    }
  }

  function nodeStatus(node) {
    if (node.planned === true || (node.exists === false && node.type === "planned")) return "planned";
    if (node.type === "placeholder") return text(node.issue_code || "missing-document");
    return text(node.graph_status || node.link_status || "ok");
  }

  function lifecycleStatus(node) {
    if (node.type === "placeholder") return "not_applicable";
    const value = text(node.lifecycle_status);
    if (lifecycleLabels[value]) return value;
    return node.planned === true ? "planned" : "published";
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
        lifecycleStatus: lifecycleStatus(node),
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
    return [node.id, node.label, node.path, node.type, node.scope, node.graphStatus, node.lifecycleStatus]
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
          "font-size": 12,
          "text-wrap": "wrap",
          "text-max-width": 110,
          "text-valign": "center",
          "text-halign": "center",
          width: 54,
          height: 54,
          "background-color": "#546e7a",
          color: "#fff",
          "border-width": 2,
          "border-color": "#263238",
        },
      },
      { selector: 'node[type = "chapter"]', style: { shape: "round-rectangle", width: 110, height: 48, "background-color": "#90caf9", color: "#111" } },
      { selector: 'node[type = "concept"]', style: { shape: "ellipse", "background-color": "#a5d6a7", color: "#111" } },
      { selector: 'node[type = "reference"]', style: { shape: "diamond", "background-color": "#ce93d8", color: "#111" } },
      { selector: 'node[type = "section"]', style: { shape: "hexagon", "background-color": "#ffe082", color: "#111" } },
      { selector: 'node[graphStatus = "planned"]', style: { "background-opacity": 0.25, "border-style": "dashed", "border-width": 4, color: "#111" } },
      { selector: 'node[lifecycleStatus = "in_progress"]', style: { "background-color": "#ffcc80", "border-style": "double", "border-width": 5, color: "#111" } },
      { selector: 'node[graphStatus = "missing"], node[graphStatus = "missing-document"], node[graphStatus = "missing-heading"], node[graphStatus = "missing-reference"]', style: { shape: "tag", "background-color": "#ef9a9a", "border-width": 4, color: "#111" } },
      { selector: 'node[graphStatus = "ambiguous"]', style: { shape: "barrel", "background-color": "#b39ddb", "border-style": "double", "border-width": 5, color: "#111" } },
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
    const relation = (edge) => `<li><code>${escapeHtml(edge.type)}</code> – ${escapeHtml(edge.source === node.id ? edge.target : edge.source)}</li>`;
    const safeUrl = escapeHtml(safeSiteUrl(node.url));
    const openLink = safeUrl && node.graphStatus === "ok" ? `<p><a class="md-button md-button--primary" href="${safeUrl}">Seite öffnen</a></p>` : "";
    panel.innerHTML = `
      <h2 tabindex="-1">${escapeHtml(node.label)}</h2>
      <p><span class="kg-badge kg-badge--${escapeHtml(node.graphStatus)}">${escapeHtml(statusLabels[node.graphStatus] || node.graphStatus)}</span>
      <span class="kg-badge">${escapeHtml(node.type)}</span>
      <span class="kg-badge kg-badge--${escapeHtml(node.lifecycleStatus)}">${escapeHtml(lifecycleLabels[node.lifecycleStatus] || node.lifecycleStatus)}</span></p>
      ${openLink}
      <dl>
        <dt>Stabile ID</dt><dd><code>${escapeHtml(node.id)}</code></dd>
        <dt>Pfad</dt><dd><code>${escapeHtml(node.path || "—")}</code></dd>
        <dt>Scope</dt><dd>${escapeHtml(node.scope)}</dd>
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
    const tagSelect = container.querySelector("[data-kg-tag]");
    const lifecycleSelect = container.querySelector("[data-kg-lifecycle]");
    const layoutSelect = container.querySelector("[data-kg-layout]");
    const resetButton = container.querySelector("[data-kg-reset]");
    const fitButton = container.querySelector("[data-kg-fit]");
    const detailPanel = container.querySelector("[data-kg-details]");
    const runtimeLive = container.querySelector("[data-kg-runtime-live]");
    const fallbackRows = [...document.querySelectorAll("[data-kg-node-row]")];
    fallbackRows.forEach((row) => row.querySelectorAll(".kg-node-select").forEach((button) => button.remove()));
    const dataUrl = container.dataset.graphUrl;
    const runtimeUrl = container.dataset.runtimeUrl;
    const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const abortController = new AbortController();
    let cy = null;
    let graph = null;
    let selectedId = new URLSearchParams(location.search).get("node") || "";
    let selecting = false;

    async function loadRuntimeStatus() {
      if (!runtimeLive || !runtimeUrl) return;
      try {
        const response = await fetch(runtimeUrl, { signal: abortController.signal, credentials: "same-origin" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const runtime = await response.json();
        const runState = text(runtime.status || "unknown");
        const timestamp = text(runtime.ended_at || runtime.updated_at || "Zeitpunkt unbekannt");
        const phase = text(runtime.phase || "unbekannt");
        const details = [`Generator: ${runStatusLabels[runState] || runState}`, `Phase: ${phase}`, timestamp];
        if (runState === "failed") {
          details.push(`Fehlerklasse: ${text(runtime.error_class || "unbekannt")}`);
          details.push(`Fehler: ${text(runtime.error_message || "Keine Detailmeldung vorhanden")}`);
          details.push(`Recovery: ${text(runtime.recovery_action || "Diagnosebericht prüfen")}`);
        }
        runtimeLive.textContent = details.join(" · ");
        runtimeLive.dataset.status = runState;
      } catch (error) {
        if (error.name === "AbortError") return;
        runtimeLive.textContent = "Laufstatus nicht verfügbar; die statische Status- und Tabellenansicht bleibt nutzbar.";
        runtimeLive.dataset.status = "unknown";
      }
    }

    async function load() {
      try {
        const response = await fetch(dataUrl, { signal: abortController.signal, credentials: "same-origin" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        graph = normaliseGraph(await response.json());
        fillSelect(typeSelect, optionValues(graph.nodes, "type"), "Alle Knotentypen");
        fillSelect(edgeSelect, optionValues(graph.edges, "type"), "Alle Beziehungen");
        fillSelect(statusSelect, optionValues(graph.nodes, "graphStatus"), "Alle Status");
        fillSelect(scopeSelect, optionValues(graph.nodes, "scope"), "Alle Bereiche");
        fillSelect(
          tagSelect,
          [...new Set(graph.nodes.flatMap((node) => Array.isArray(node.tags) ? node.tags.map(text) : []).filter(Boolean))]
            .sort((a, b) => a.localeCompare(b, "de")),
          "Alle Tags",
        );

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
        enhanceFallbackRows();

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
        graphHost.replaceChildren();
        const warning = document.createElement("p");
        warning.className = "admonition warning";
        warning.textContent = `Die interaktive Graphansicht konnte nicht geladen werden: ${text(error.message)}. Die Tabellenansicht darunter bleibt vollständig nutzbar.`;
        graphHost.append(warning);
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
      const wantedTag = tagSelect.value;
      const wantedLifecycle = lifecycleSelect.value;
      let visibleNodes = 0;

      cy.batch(() => {
        cy.elements().removeClass("kg-hidden");
        cy.nodes().forEach((element) => {
          const node = element.data();
          const visible = (!query || searchableNode(node).includes(query))
            && (!wantedType || node.type === wantedType)
            && (!wantedStatus || node.graphStatus === wantedStatus)
            && (!wantedScope || node.scope === wantedScope)
            && (!wantedTag || (Array.isArray(node.tags) && node.tags.map(text).includes(wantedTag)))
            && (!wantedLifecycle || node.lifecycleStatus === wantedLifecycle);
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
          && (!wantedScope || node.scope === wantedScope)
          && (!wantedTag || (Array.isArray(node.tags) && node.tags.map(text).includes(wantedTag)))
          && (!wantedLifecycle || node.lifecycleStatus === wantedLifecycle);
        row.hidden = !visible;
      });
      status.textContent = `${visibleNodes} von ${graph.nodes.length} Knoten sichtbar.`;
    }

    [search, typeSelect, edgeSelect, statusSelect, scopeSelect, tagSelect, lifecycleSelect].forEach((control) => {
      control.addEventListener(control === search ? "input" : "change", applyFilters);
    });
    layoutSelect.addEventListener("change", () => cy && cy.layout(layoutOptions(layoutSelect.value, reducedMotion)).run());
    fitButton.addEventListener("click", () => cy && cy.fit(cy.elements(":visible"), 30));
    resetButton.addEventListener("click", () => {
      search.value = "";
      [typeSelect, edgeSelect, statusSelect, scopeSelect, tagSelect, lifecycleSelect].forEach((select) => { select.value = ""; });
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
    function enhanceFallbackRows() {
      fallbackRows.forEach((row) => {
        const selectRow = () => {
          if (!cy) return;
          const node = cy.getElementById(row.dataset.nodeId);
          if (node.length) {
            node.select();
            cy.center(node);
          }
        };
        const button = document.createElement("button");
        button.type = "button";
        button.className = "kg-node-select";
        button.textContent = "Details anzeigen";
        const label = row.querySelector("td")?.textContent?.trim() || row.dataset.nodeId;
        button.setAttribute("aria-label", `Details zu ${label} anzeigen`);
        button.addEventListener("click", selectRow);
        const cell = row.querySelector("td");
        if (cell) cell.append(" ", button);
      });
    }

    loadRuntimeStatus();
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
