(() => {
  "use strict";

  const instances = new WeakMap();
  const activeInstances = new Set();

  const statusLabels = {
    ok: "vorhanden",
    planned: "geplant",
    missing: "Ziel fehlt",
    "missing-document": "Dokument fehlt",
    "missing-heading": "Abschnitt fehlt",
    ambiguous: "mehrdeutig",
    malformed: "ungültig",
    "excluded-target": "nicht in der Webfassung",
  };

  const nodeTypeLabels = {
    chapter: "Lerneinheit",
    document: "Dokument",
    concept: "Begriff",
    reference: "Quelle",
    section: "Abschnitt",
    planned: "geplantes Dokument",
    placeholder: "Problemziel",
  };

  const edgeTypeLabels = {
    wikilink: "Wikilink",
    embeds: "Einbettung",
    prerequisite: "Voraussetzung",
    related: "verwandt",
    cites: "zitiert",
    tagged_with: "verschlagwortet mit",
    sequence: "Lernpfadreihenfolge",
    roadmap: "Roadmap",
  };

  function text(value) {
    return value == null ? "" : String(value);
  }

  function statusOfNode(node) {
    if (node.planned === true || (node.exists === false && node.type === "planned")) {
      return "planned";
    }
    if (node.type === "placeholder") {
      return text(node.issue_code || node.status || "missing-document");
    }
    return "ok";
  }

  function labelOfNode(node) {
    return text(node.label || node.title || node.path || node.id || "Unbenannt");
  }

  function normaliseGraph(raw) {
    const nodes = Array.isArray(raw.nodes) ? raw.nodes.filter(Boolean) : [];
    const nodeIds = new Set(nodes.map((node) => text(node.id)).filter(Boolean));
    const edges = Array.isArray(raw.edges) ? raw.edges.filter(Boolean) : [];

    return {
      ...raw,
      nodes: nodes
        .map((node) => ({
          ...node,
          id: text(node.id),
          label: labelOfNode(node),
          type: text(node.type || "document"),
          scope: text(node.scope || "support"),
          graphStatus: statusOfNode(node),
        }))
        .filter((node) => node.id),
      edges: edges
        .map((edge, index) => ({
          ...edge,
          id: text(edge.id || `edge-${index}`),
          source: text(edge.source),
          target: text(edge.target),
          type: text(edge.type || "wikilink"),
          graphStatus: text(edge.status || "ok"),
        }))
        .filter((edge) => edge.source && edge.target && nodeIds.has(edge.source) && nodeIds.has(edge.target)),
      issues: Array.isArray(raw.issues) ? raw.issues : [],
    };
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
      ...graph.edges.map((edge) => ({ group: "edges", data: edge })),
    ];
  }

  function stylesheet() {
    return [
      {
        selector: "node",
        style: {
          label: "data(label)",
          "font-size": 10,
          "font-weight": 600,
          "text-wrap": "wrap",
          "text-max-width": 112,
          "text-valign": "center",
          "text-halign": "center",
          width: 58,
          height: 58,
          shape: "round-rectangle",
          "background-color": "#78909c",
          color: "#111111",
          "border-width": 2,
          "border-color": "#263238",
        },
      },
      {
        selector: 'node[type = "chapter"]',
        style: { width: 112, height: 50, shape: "round-rectangle", "background-color": "#90caf9" },
      },
      {
        selector: 'node[type = "concept"]',
        style: { shape: "ellipse", "background-color": "#a5d6a7" },
      },
      {
        selector: 'node[type = "reference"]',
        style: { shape: "diamond", "background-color": "#ce93d8" },
      },
      {
        selector: 'node[type = "section"]',
        style: { shape: "hexagon", "background-color": "#ffe082" },
      },
      {
        selector: 'node[type = "planned"], node[graphStatus = "planned"]',
        style: { "background-opacity": 0.28, "border-style": "dashed", "border-width": 4 },
      },
      {
        selector: 'node[type = "placeholder"], node[graphStatus = "missing"], node[graphStatus = "missing-document"], node[graphStatus = "missing-heading"]',
        style: { shape: "tag", "background-color": "#ef9a9a", "border-width": 4 },
      },
      {
        selector: 'node[graphStatus = "ambiguous"]',
        style: { shape: "barrel", "background-color": "#b39ddb", "border-style": "double", "border-width": 5 },
      },
      {
        selector: 'node[graphStatus = "malformed"]',
        style: { shape: "vee", "background-color": "#ffab91", "border-width": 5 },
      },
      {
        selector: "edge",
        style: {
          width: 1.6,
          "line-color": "#78909c",
          "target-arrow-color": "#78909c",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          opacity: 0.72,
        },
      },
      {
        selector: 'edge[type = "prerequisite"], edge[type = "sequence"]',
        style: { width: 3, "line-color": "#1565c0", "target-arrow-color": "#1565c0" },
      },
      {
        selector: 'edge[type = "cites"]',
        style: { "line-style": "dotted", "line-color": "#7b1fa2", "target-arrow-color": "#7b1fa2" },
      },
      {
        selector: 'edge[type = "tagged_with"]',
        style: { "line-style": "dashed", "line-color": "#2e7d32", "target-arrow-color": "#2e7d32" },
      },
      {
        selector: 'edge[type = "related"]',
        style: { "line-style": "dotted", "target-arrow-shape": "none" },
      },
      {
        selector: 'edge[graphStatus != "ok"]',
        style: { "line-style": "dashed", "line-color": "#c62828", "target-arrow-color": "#c62828", width: 3 },
      },
      { selector: ".kg-hidden", style: { display: "none" } },
      { selector: ".kg-neighbour", style: { "border-width": 5, "border-color": "#ff6f00" } },
      { selector: ":selected", style: { "border-width": 6, "border-color": "#d84315", "z-index": 999 } },
    ];
  }

  function layoutOptions(name, reducedMotion) {
    if (name === "breadthfirst") {
      return { name, directed: true, padding: 34, animate: !reducedMotion, spacingFactor: 1.25 };
    }
    if (name === "concentric") {
      return { name, padding: 34, animate: !reducedMotion, minNodeSpacing: 38 };
    }
    return {
      name: "cose",
      padding: 34,
      animate: !reducedMotion,
      randomize: false,
      nodeRepulsion: 500000,
      idealEdgeLength: 105,
    };
  }

  function displayLabel(value, labels) {
    return labels[value] || value;
  }

  function appendDefinition(list, term, value) {
    const dt = document.createElement("dt");
    dt.textContent = term;
    const dd = document.createElement("dd");
    dd.textContent = value || "—";
    list.append(dt, dd);
  }

  function renderDetails(panel, item, graph) {
    panel.replaceChildren();

    const heading = document.createElement("h2");
    heading.tabIndex = -1;
    panel.append(heading);

    if (!item) {
      heading.textContent = "Details";
      const paragraph = document.createElement("p");
      paragraph.textContent = "Knoten oder Beziehung auswählen.";
      panel.append(paragraph);
      return;
    }

    const group = item.group();
    const data = item.data();
    heading.textContent = group === "nodes" ? data.label : displayLabel(data.type, edgeTypeLabels);

    const badges = document.createElement("p");
    const typeBadge = document.createElement("span");
    typeBadge.className = "kg-badge";
    typeBadge.textContent = group === "nodes"
      ? displayLabel(data.type, nodeTypeLabels)
      : displayLabel(data.type, edgeTypeLabels);
    badges.append(typeBadge);

    const statusBadge = document.createElement("span");
    statusBadge.className = `kg-badge kg-badge--${data.graphStatus}`;
    statusBadge.textContent = displayLabel(data.graphStatus, statusLabels);
    badges.append(statusBadge);
    panel.append(badges);

    const definitions = document.createElement("dl");
    appendDefinition(definitions, "Stabile ID", data.id);

    if (group === "nodes") {
      appendDefinition(definitions, "Pfad", text(data.path));
      appendDefinition(definitions, "Bereich", text(data.scope));
      const incoming = graph.edges.filter((edge) => edge.target === data.id).length;
      const outgoing = graph.edges.filter((edge) => edge.source === data.id).length;
      appendDefinition(definitions, "Beziehungen", `${outgoing} ausgehend · ${incoming} eingehend`);
    } else {
      const source = graph.nodes.find((node) => node.id === data.source);
      const target = graph.nodes.find((node) => node.id === data.target);
      appendDefinition(definitions, "Von", source ? source.label : data.source);
      appendDefinition(definitions, "Nach", target ? target.label : data.target);
      appendDefinition(definitions, "Fundstellen", text(data.count || 1));
    }
    panel.append(definitions);

    if (group === "nodes" && data.url && data.graphStatus === "ok") {
      const paragraph = document.createElement("p");
      const link = document.createElement("a");
      link.className = "md-button md-button--primary";
      link.href = text(data.url);
      link.textContent = "Seite öffnen";
      paragraph.append(link);
      panel.append(paragraph);
    }

    heading.focus({ preventScroll: true });
  }

  function uniqueValues(items, field) {
    return [...new Set(items.map((item) => text(item[field])).filter(Boolean))]
      .sort((left, right) => left.localeCompare(right, "de"));
  }

  function createLegendItem(kind, value, label) {
    const item = document.createElement("li");
    const symbol = document.createElement("span");
    symbol.className = `knowledge-graph-legend__symbol knowledge-graph-legend__symbol--${kind} knowledge-graph-legend__symbol--${value}`;
    symbol.setAttribute("aria-hidden", "true");
    const caption = document.createElement("span");
    caption.textContent = label;
    item.append(symbol, caption);
    return item;
  }

  function renderLegend(host, graph) {
    host.replaceChildren();

    const sections = [
      ["Knoten", "node", uniqueValues(graph.nodes, "type"), nodeTypeLabels],
      ["Beziehungen", "edge", uniqueValues(graph.edges, "type"), edgeTypeLabels],
      [
        "Status",
        "status",
        [...new Set([
          ...graph.nodes.map((node) => node.graphStatus),
          ...graph.edges.map((edge) => edge.graphStatus),
        ].filter(Boolean))].sort((left, right) => left.localeCompare(right, "de")),
        statusLabels,
      ],
    ];

    sections.forEach(([title, kind, values, labels]) => {
      if (!values.length) return;
      const section = document.createElement("section");
      const heading = document.createElement("h3");
      heading.textContent = title;
      const list = document.createElement("ul");
      list.className = "knowledge-graph-legend__list";
      values.forEach((value) => {
        list.append(createLegendItem(kind, value, displayLabel(value, labels)));
      });
      section.append(heading, list);
      host.append(section);
    });
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
    const fitButton = container.querySelector("[data-kg-fit]");
    const resetButton = container.querySelector("[data-kg-reset]");
    const detailPanel = container.querySelector("[data-kg-details]");
    const legend = container.querySelector("[data-kg-legend]");
    const controls = container.querySelector("[data-kg-controls]");
    const dataUrl = container.dataset.graphUrl;

    if (!graphHost || !status || !search || !typeSelect || !edgeSelect || !statusSelect
      || !scopeSelect || !layoutSelect || !fitButton || !resetButton || !detailPanel
      || !legend || !controls || !dataUrl) {
      return { destroy() {} };
    }

    const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const abortController = new AbortController();
    let cy = null;
    let graph = null;
    let resizeObserver = null;
    let selectedId = new URLSearchParams(location.search).get("node") || "";

    function applyFilters() {
      if (!cy || !graph) return;

      const query = search.value.trim().toLocaleLowerCase("de");
      const wantedType = typeSelect.value;
      const wantedEdge = edgeSelect.value;
      const wantedStatus = statusSelect.value;
      const wantedScope = scopeSelect.value;
      let visibleNodes = 0;
      let visibleEdges = 0;

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
          const endpointsVisible = !element.source().hasClass("kg-hidden")
            && !element.target().hasClass("kg-hidden");
          const visible = endpointsVisible
            && (!wantedEdge || edge.type === wantedEdge)
            && (!wantedStatus || edge.graphStatus === wantedStatus);
          element.toggleClass("kg-hidden", !visible);
          if (visible) visibleEdges += 1;
        });
      });

      status.textContent = `${visibleNodes} von ${graph.nodes.length} Knoten und ${visibleEdges} von ${graph.edges.length} Beziehungen sichtbar.`;
    }

    async function load() {
      try {
        const response = await fetch(dataUrl, {
          signal: abortController.signal,
          credentials: "same-origin",
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        graph = normaliseGraph(await response.json());
        renderLegend(legend, graph);

        if (typeof window.cytoscape !== "function") {
          throw new Error("Cytoscape.js wurde nicht geladen");
        }

        cy = window.cytoscape({
          container: graphHost,
          elements: createElements(graph),
          style: stylesheet(),
          layout: layoutOptions(layoutSelect.value, reducedMotion),
          minZoom: 0.12,
          maxZoom: 3.5,
          wheelSensitivity: 0.2,
          selectionType: "single",
        });

        cy.on("select", "node, edge", (event) => {
          const item = event.target;
          selectedId = item.id();
          cy.elements().removeClass("kg-neighbour");
          if (item.isNode()) item.closedNeighborhood().addClass("kg-neighbour");
          renderDetails(detailPanel, item, graph);

          const url = new URL(location.href);
          url.searchParams.set("node", selectedId);
          history.replaceState(null, "", url);
        });

        cy.on("unselect", "node, edge", () => {
          if (cy.$(":selected").length === 0) {
            selectedId = "";
            cy.elements().removeClass("kg-neighbour");
            renderDetails(detailPanel, null, graph);
          }
        });

        if (selectedId && cy.getElementById(selectedId).length) {
          const selected = cy.getElementById(selectedId);
          selected.select();
          cy.center(selected);
        }

        resizeObserver = new ResizeObserver(() => cy && cy.resize());
        resizeObserver.observe(graphHost);
        applyFilters();
      } catch (error) {
        if (error.name === "AbortError") return;
        graphHost.replaceChildren();
        const message = document.createElement("p");
        message.className = "knowledge-graph-error";
        message.textContent = `Der Wissensgraph konnte nicht geladen werden: ${error.message}.`;
        graphHost.append(message);
        status.textContent = "Interaktive Ansicht nicht verfügbar.";
      }
    }

    controls.addEventListener("submit", (event) => event.preventDefault());
    [search, typeSelect, edgeSelect, statusSelect, scopeSelect].forEach((control) => {
      control.addEventListener(control === search ? "input" : "change", applyFilters);
    });

    layoutSelect.addEventListener("change", () => {
      if (cy) cy.layout(layoutOptions(layoutSelect.value, reducedMotion)).run();
    });

    fitButton.addEventListener("click", () => {
      if (cy) cy.fit(cy.elements(":visible"), 32);
    });

    resetButton.addEventListener("click", () => {
      search.value = "";
      [typeSelect, edgeSelect, statusSelect, scopeSelect].forEach((select) => {
        select.value = "";
      });
      selectedId = "";
      if (cy) {
        cy.elements().unselect();
        cy.elements().removeClass("kg-neighbour");
      }
      renderDetails(detailPanel, null, graph || { edges: [] });
      const url = new URL(location.href);
      url.searchParams.delete("node");
      history.replaceState(null, "", url);
      applyFilters();
    });

    load();

    const instance = {
      destroy() {
        abortController.abort();
        if (resizeObserver) resizeObserver.disconnect();
        if (cy) cy.destroy();
        activeInstances.delete(instance);
      },
    };
    instances.set(container, instance);
    activeInstances.add(instance);
    return instance;
  }

  function initialiseAll() {
    [...activeInstances].forEach((instance) => instance.destroy());
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
