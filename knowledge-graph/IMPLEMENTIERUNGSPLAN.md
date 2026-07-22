---
title: Wissensgraph 2.0 – Implementierungsplan und Fortschritt
aliases: [Wissensgraph-Implementierungsplan, Plan Wissensgraph 2.0]
type: plan
status: completed
repository: H234598/ADHS-Lernpfad
created: 2026-07-16
last_updated: 2026-07-22
tags: [Wissensgraph, MkDocs, Obsidian, Python, JavaScript, CI]
---

# Wissensgraph 2.0 – Implementierungsplan und Fortschritt

> [!summary] Ziel
> Der Wissensgraph wird aus allen relevanten Markdown-Dokumenten, relationalen YAML-Metadaten und internen Links deterministisch erzeugt. Die Webfassung erhält eine interaktive, filterbare und barrierearm ergänzte Darstellung. Bewusst geplante Seiten und unbeabsichtigt defekte Ziele werden klar unterschieden.

## Definition von vollständig

Der Graph ist vollständig relativ zu den definierten Projektquellen, wenn:

- jede eingeschlossene Markdown-Datei genau einen kanonischen Dokumentknoten besitzt;
- alle Wikilinks und Einbettungen außerhalb ausgeschlossener Syntaxbereiche erfasst sind;
- `prerequisites`, `tags`, `references` und optional `related` als typisierte Kanten vorliegen;
- Kapitelreihenfolge und geplante Roadmap-Ziele abgebildet sind;
- jede Beziehung Fundstelle und Status besitzt;
- jeder Kantenendpunkt als realer, geplanter oder Problemknoten existiert.

## Phase 1 – Kernmodell, Resolver und Generator

**Status: abgeschlossen in der Implementierung; Repository-CI und Merge werden im zugehörigen PR dokumentiert.**

- [x] Gemeinsamen Inhaltsindex für Markdown, YAML, Überschriften, Aliase und Referenz-IDs entwerfen.
- [x] Stabile kanonische IDs für Dokumente, Abschnitte, Quellen, Begriffe, Assets, geplante und fehlende Ziele definieren.
- [x] Scanner für Wikilinks und Einbettungen implementieren.
- [x] Frontmatter, Codeblöcke, Inline-Code und HTML-Kommentare beim Linkscan ausschließen.
- [x] Einen gemeinsamen Resolver für Graph, Webkonverter, Gesamtdokument und Validatoren implementieren.
- [x] Status `ok`, `planned`, `missing-document`, `missing-heading`, `ambiguous` und `malformed` modellieren.
- [x] `knowledge-graph/planned-nodes.yaml` als explizite Registry geplanter Seiten einführen.
- [x] YAML-Beziehungen `prerequisite`, `tagged_with`, `cites` und `related` erzeugen.
- [x] Kapitelreihenfolge aus `index.json` und Roadmap-Beziehungen ergänzen.
- [x] Aggregierte Kanten mit allen Fundstellen erzeugen.
- [x] Versionierte JSON-Ausgabe mit `nodes`, `edges`, `issues` und `stats` definieren.
- [x] Deterministische Mermaid-Ausgabe mit genau einer internen ID je Knoten erzeugen.
- [x] GraphML- und menschenlesbare Berichtsausgabe ergänzen.
- [x] JSON Schema für Version `1.0.0` hinzufügen.
- [x] Kompatible APIs für bestehende Web- und Gesamtdokument-Builds erhalten.
- [x] Unit-Tests für Inhaltsindex, Resolver, Statusfälle und Graphdeterminismus ergänzen.
- [x] Lokale Phase-1-Tests ausführen: 13 Tests erfolgreich.

### Phase-1-Ausgaben

```text
build/knowledge-graph/knowledge-graph.json
build/knowledge-graph/knowledge-graph.mmd
build/knowledge-graph/knowledge-graph.graphml
build/knowledge-graph/graph-report.md
build/knowledge-graph/graph-report.json
```

Die bisherigen Kompatibilitätspfade `build/knowledge-graph.json` und `build/knowledge-graph.mmd` bleiben zunächst erhalten.

## Phase 2 – Weboberfläche und sichtbare Linkstatus

**Status: abgeschlossen.**

- [x] Graphdaten in `build/docs/knowledge-graph/data/` übernehmen.
- [x] Lokale, exakt gepinnte Graphbibliothek samt Lizenz einchecken.
- [x] Interaktive Graphansicht mit Suche, Filtern, Fokus und Detailpanel implementieren.
- [x] Filter für Knotentyp, Kantenart, Scope und Status ergänzen.
- [x] Lernpfad-, Netzwerk- und Fokuslayout anbieten.
- [x] Vorhandene Ziele aus dem Detailpanel öffnen.
- [x] Geplante Ziele ohne 404 auf ihre Graphdetailansicht führen.
- [x] Fehlende Dokumente, fehlende Überschriften und Mehrdeutigkeiten inline kennzeichnen.
- [x] Status nie ausschließlich über Farbe vermitteln.
- [x] Semantische No-JavaScript- und Druck-Fallbackansicht erzeugen.
- [x] MkDocs-Instant-Navigation ohne doppelte Graphinstanzen unterstützen.
- [x] Mobile und tastaturbedienbare Darstellung prüfen.
- [x] Browser-Smoke- und Accessibility-Tests ergänzen.

## Phase 3 – CI, Exporte, Migration und Betriebsdokumentation

**Status: abgeschlossen.**

- [x] Python-Tests und Graphschema in der CI verbindlich prüfen.
- [x] Graph vor Link- und Kompendiumsvalidierung erzeugen.
- [x] PR-Vorschau und Graphbericht auch bei blockierenden Linkproblemen als Artefakte bereitstellen.
- [x] Produktionsbuild bei ungeplanten Defekten blockieren.
- [x] `planned` als zulässige Warnung behandeln.
- [x] Graphstatistik in den PR-Validierungsbericht aufnehmen.
- [x] JSON, Mermaid, GraphML und Bericht in öffentliche Downloads übernehmen.
- [x] Downloadmanifest und SHA-256-Prüfsummen erweitern.
- [x] Bestehende Voraussetzungen schrittweise auf kanonische Pfade migrieren.
- [x] Automations-, Reparatur- und Merge-Prompts an die neuen Regeln anpassen.
- [x] `CONTRIBUTING.md`, `WARTUNG.md`, `DOWNLOADS.md`, README und Changelog aktualisieren.
- [x] End-to-End-Build inklusive MkDocs Strict Mode und Exporte prüfen.

## Status- und Freigabepolicy

| Status | Bedeutung | Web | Freigabe |
|---|---|---|---|
| `ok` | Ziel eindeutig vorhanden | normaler Link | erlaubt |
| `planned` | bewusst registrierte, noch fehlende Seite | Badge „geplant“ | Warnung, erlaubt |
| `missing-document` | Zielseite fehlt ungeplant | Badge „Ziel fehlt“ | Fehler |
| `missing-heading` | Dokument vorhanden, Abschnitt fehlt | Badge „Abschnitt fehlt“ | Fehler |
| `ambiguous` | mehrere Ziele möglich | Badge „mehrdeutig“ | Fehler |
| `malformed` | ungültiges oder unsicheres Ziel | Badge „ungültig“ | Fehler |

## Nicht-Ziele der ersten Version

- keine KI-basierte Extraktion ungeschriebener medizinischer Beziehungen;
- keine automatische Kausalitätsbehauptung aus Tags oder bloßen Erwähnungen;
- keine Server-, Datenbank- oder Benutzerkontenpflicht;
- keine Veränderung wissenschaftlicher Texte zur künstlichen Erhöhung der Graphdichte.

## Abschlusskriterien

- [x] alle drei Phasen implementiert und über einen gemeinsamen PR freigegeben;
- [x] keine ungeplanten defekten internen Links;
- [x] alle Kantenendpunkte vorhanden;
- [x] Graphausgabe bei identischem Inhalt byteidentisch;
- [x] Webgraph und semantische Fallbackansicht veröffentlicht;
- [x] Downloads, CI, Dokumentation und Automationsprompts verwenden dasselbe Graphmodell.

## Umsetzungsstatus

- [x] **Phase 1 – Kernmodell, Resolver und Generator:** kanonischer Inhaltsindex, typisierte Beziehungen, stabile IDs, Provenienz, JSON, Mermaid, GraphML, Berichte und Tests.
- [x] **Phase 2 – Weboberfläche und Linkkennzeichnung:** lokale Cytoscape-Auslieferung, interaktive Suche und Filter, Fokus- und Layoutmodi, Detailansicht, semantische No-JS-Alternative, mobile Darstellung, reduzierte Bewegung sowie sichtbare Status für geplante oder defekte Ziele.
- [x] **Phase 3 – CI, Exporte, Migration und Betriebsdokumentation:** Qualitätsgates, Preview- und Berichtartefakte, Graphdownloads, kanonische Metadatenmigration und Aktualisierung der Automationsregeln.

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
