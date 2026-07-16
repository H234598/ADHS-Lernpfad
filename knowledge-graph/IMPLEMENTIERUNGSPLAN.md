---
title: Wissensgraph 2.0 – Implementierungsplan und Fortschritt
aliases: [Wissensgraph-Implementierungsplan, Plan Wissensgraph 2.0]
type: plan
status: in-progress
repository: H234598/ADHS-Lernpfad
created: 2026-07-16
last_updated: 2026-07-16
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

**Status: geplant.**

- [ ] Graphdaten in `build/docs/knowledge-graph/data/` übernehmen.
- [ ] Lokale, exakt gepinnte Graphbibliothek samt Lizenz einchecken.
- [ ] Interaktive Graphansicht mit Suche, Filtern, Fokus und Detailpanel implementieren.
- [ ] Filter für Knotentyp, Kantenart, Scope und Status ergänzen.
- [ ] Lernpfad-, Netzwerk- und Fokuslayout anbieten.
- [ ] Vorhandene Ziele aus dem Detailpanel öffnen.
- [ ] Geplante Ziele ohne 404 auf ihre Graphdetailansicht führen.
- [ ] Fehlende Dokumente, fehlende Überschriften und Mehrdeutigkeiten inline kennzeichnen.
- [ ] Status nie ausschließlich über Farbe vermitteln.
- [ ] Semantische No-JavaScript- und Druck-Fallbackansicht erzeugen.
- [ ] MkDocs-Instant-Navigation ohne doppelte Graphinstanzen unterstützen.
- [ ] Mobile und tastaturbedienbare Darstellung prüfen.
- [ ] Browser-Smoke- und Accessibility-Tests ergänzen.

## Phase 3 – CI, Exporte, Migration und Betriebsdokumentation

**Status: geplant.**

- [ ] Python-Tests und Graphschema in der CI verbindlich prüfen.
- [ ] Graph vor Link- und Kompendiumsvalidierung erzeugen.
- [ ] PR-Vorschau und Graphbericht auch bei blockierenden Linkproblemen als Artefakte bereitstellen.
- [ ] Produktionsbuild bei ungeplanten Defekten blockieren.
- [ ] `planned` als zulässige Warnung behandeln.
- [ ] Graphstatistik in den PR-Validierungsbericht aufnehmen.
- [ ] JSON, Mermaid, GraphML und Bericht in öffentliche Downloads übernehmen.
- [ ] Downloadmanifest und SHA-256-Prüfsummen erweitern.
- [ ] Bestehende Voraussetzungen schrittweise auf kanonische Pfade migrieren.
- [ ] Automations-, Reparatur- und Merge-Prompts an die neuen Regeln anpassen.
- [ ] `CONTRIBUTING.md`, `WARTUNG.md`, `DOWNLOADS.md`, README und Changelog aktualisieren.
- [ ] End-to-End-Build inklusive MkDocs Strict Mode und Exporte prüfen.

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

- [ ] alle drei Phasen gemergt;
- [ ] keine ungeplanten defekten internen Links auf `main`;
- [ ] alle Kantenendpunkte vorhanden;
- [ ] Graphausgabe bei identischem Inhalt byteidentisch;
- [ ] Webgraph und semantische Fallbackansicht veröffentlicht;
- [ ] Downloads, CI, Dokumentation und Automationsprompts verwenden dasselbe Graphmodell.
