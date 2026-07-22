---
title: Wissensgraph
tags: [Wissensgraph, Obsidian, Navigation, Metadaten]
---

# Wissensgraph

Der Wissensgraph wird bei jedem Build aus den Markdown-Dateien, ihren YAML-Metadaten, Überschriften, Wikilinks, Einbettungen, Quellenangaben und der Lernpfadreihenfolge neu erzeugt. Er ist ein **Dokument- und Navigationsgraph** des Kompendiums, keine automatisch abgeleitete medizinische Ontologie.

## Interaktive Ansicht

<!-- knowledge-graph-runtime:start -->

Der Laufstatus wird beim Dokumentationsbuild eingesetzt.

<!-- knowledge-graph-runtime:end -->

<div class="knowledge-graph-shell" data-knowledge-graph data-graph-url="data/knowledge-graph.json" data-runtime-url="data/runtime-status.json">
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
    <label>Tag
      <select data-kg-tag><option value="">Alle Tags</option></select>
    </label>
    <label>Lebenszyklus
      <select data-kg-lifecycle>
        <option value="">Alle Lebenszyklusstatus</option>
        <option value="planned">geplant</option>
        <option value="in_progress">in Arbeit</option>
        <option value="published">veröffentlicht</option>
      </select>
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
  <p class="knowledge-graph-runtime-live" data-kg-runtime-live aria-live="polite">Laufstatus wird geladen.</p>
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

Der Lebenszyklus ist davon getrennt: vorhandene Inhalte gelten als **veröffentlicht**, registrierte künftige Seiten als **geplant** oder **in Arbeit**. Der Laufstatus dokumentiert den letzten Generatorlauf einschließlich Phase, Commit, Fehlerklasse und vorbereitetem Recovery-Schritt.

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
- `runtime-status.json` – schema-validierter Laufstatus mit Phase, Dauer, Commit und Recovery-Hinweis

## Lokal bauen und prüfen

```bash
python scripts/build_graph.py
python scripts/validate_graph.py
python scripts/validate_runtime_status.py build/runtime-status.json
python scripts/build_docs.py
mkdocs build --strict
```

Die gleichen Prüfungen laufen im stabilen GitHub-Check `Validate and build`.
Bei einem blockierenden Linkfehler bleibt die Veröffentlichung gesperrt; die CI
erzeugt mit `KNOWLEDGE_GRAPH_DIAGNOSTIC=1` jedoch eine separate, nicht
veröffentlichte Vorschau, in der Fehlerstatus, fehlende Ziele und Recovery-Daten
sichtbar bleiben.
