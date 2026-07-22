# Wissensgraph Phase 3 – Vollständiger Umsetzungsplan

Status: in progress

## Ziel

Aus dem bisherigen Graphgenerator wird eine überwachte, reproduzierbare Infrastruktur:

- validierter Wissensgraph
- Runtime Status für alle Generatorläufe
- CI-Gates
- reproduzierbare Artefakte
- Webstatus und Fehlerdiagnose

## Bereits vorhanden

- Graphgenerator
- JSON/Mermaid/GraphML Exporte
- Runtime Status Schema
- atomarer Status Writer
- CLI
- Validierung
- erste Tests

## Offene Umsetzung

### Runtime Integration

Buildphasen:

1. started
2. load_content
3. build_nodes
4. build_edges
5. validate_graph
6. export
7. success/failed

Jeder Fehler muss enthalten:

- phase
- error_class
- recovery_action

## Graph Validator

`scripts/validate_graph.py`

Prüft:

- Schema
- eindeutige Node IDs
- gültige Edges
- fehlende Seiten
- Obsidian/Web Links

## CI Integration

Workflow:

Checkout
→ Runtime Status
→ Graph Build
→ Validation
→ Export
→ Status Success

Fehler erzeugen:

- Statusdatei
- Bericht
- Artefakt

## Artefakte

Bereitzustellen:

- knowledge-graph.json
- knowledge-graph.graphml
- knowledge-graph.mmd
- graph-report.md
- graph-report.json
- runtime-status.json

## Downloadsystem

Erweitern:

- downloads.json
- SHA256SUMS.txt

## Web

Anzeigen:

- letzter Lauf
- Fehler
- fehlende Seiten
- geplante Nodes

## Tests

- Validator Tests
- Runtime Tests
- Export Tests
- Playwright Smoke Tests

## Merge Voraussetzungen

- CI grün
- Exporte grün
- Tests grün
- CodeRabbit geprüft
- keine offenen Threads
- Infrastrukturprüfung abgeschlossen
