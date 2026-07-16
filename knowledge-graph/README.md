# Wissensgraph

Der Wissensgraph wird aus den Markdown-Dokumenten, ihren YAML-Metadaten und den internen Obsidian-Wikilinks erzeugt. Der native Obsidian-Graph bleibt weiterhin direkt aus dem Vault ableitbar; zusätzlich erstellt `scripts/build_graph.py` einen kanonischen, typisierten Projektgraphen.

## Datenquellen

Der Generator erfasst:

- jedes relevante Markdown-Dokument als stabilen Knoten,
- Wikilinks und Einbettungen außerhalb von Frontmatter, Codeblöcken, Inline-Code und HTML-Kommentaren,
- `prerequisites` als gerichtete Voraussetzungskanten,
- `tags` als Beziehungen zu Glossarabschnitten oder Begriffsknoten,
- `references` als Zitationskanten zu Studienkarten,
- optionale `related`-Beziehungen,
- die Kapitelreihenfolge aus `index.json`,
- bewusst geplante Seiten aus `knowledge-graph/planned-nodes.yaml`.

Alle Linkauflösungen verwenden dasselbe Inhaltsmodell wie Web- und Gesamtdokumentexporte. Titel, Aliase, Pfade, Überschriften und `reference_id` werden auf stabile kanonische IDs abgebildet.

## Ausgaben

Ein Lauf von

```bash
python3 scripts/build_graph.py
```

erzeugt:

```text
build/knowledge-graph/knowledge-graph.json
build/knowledge-graph/knowledge-graph.mmd
build/knowledge-graph/knowledge-graph.graphml
build/knowledge-graph/graph-report.md
build/knowledge-graph/graph-report.json
```

Aus Kompatibilitätsgründen bleiben zusätzlich `build/knowledge-graph.json` und `build/knowledge-graph.mmd` erhalten.

Die JSON-Ausgabe enthält getrennte `nodes`, `edges`, `issues` und `stats`. Jede Kante besitzt ihren Typ, Status und die Fundstellen in den Quelldateien. Die GraphML-Datei ist für Gephi, Cytoscape Desktop und vergleichbare Werkzeuge vorgesehen. Mermaid dient als kompakte Diagnose- und Offlineansicht.

## Linkstatus

| Status | Bedeutung | Freigabe |
|---|---|---|
| `ok` | Ziel ist eindeutig vorhanden | erlaubt |
| `planned` | Ziel fehlt bewusst und ist registriert | Warnung, erlaubt |
| `missing-document` | Zielseite fehlt ungeplant | Fehler |
| `missing-heading` | Dokument existiert, Abschnitt fehlt | Fehler |
| `ambiguous` | mehrere Ziele sind möglich | Fehler |
| `malformed` | ungültiges oder unsicheres Ziel | Fehler |

Nur Einträge in `planned-nodes.yaml` gelten als bewusst geplant. Sobald eine registrierte Seite tatsächlich existiert, meldet die Validierung den überholten Registry-Eintrag.

## Webdarstellung

Die interaktive, filterbare Weboberfläche und die sichtbare Inline-Kennzeichnung problematischer Links werden in Phase 2 des [[knowledge-graph/IMPLEMENTIERUNGSPLAN|Implementierungsplans]] ergänzt. Bis dahin liefern JSON, Mermaid, GraphML und der Bericht bereits den vollständigen maschinenlesbaren Datenbestand.
