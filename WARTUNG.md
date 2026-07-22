---
title: Wartung und Automatisierung
tags: [Wartung, Automatisierung, CI]
last_reviewed: 2026-07-22
hide: [navigation]
---

[↩️](README.md "Zurück zur Startseite")

# Wartung und Automatisierung

Diese Seite bündelt den technischen Betrieb des Lernkompendiums. Sie gehört nicht zum eigentlichen Lernpfad und ist deshalb aus der normalen Navigation ausgeblendet.

## Automatisierter Tageslauf

```text
06:00  neue Einheit recherchieren und erstellen
          ↓
        lokale Pflichtprüfungen
          ↓
        Branch, Push und Draft-Pull-Request
          ↓
        mindestens zwei Stunden Prüfzeit
          ↓
ab 08:00 stündlicher Prüf-, Reparatur- und Merge-Wächter
          ↓
        erste CI grün → Ready for review
          ↓
        zweite CI grün → Squash-Merge nach main
```

CodeRabbit bekommt während der zweistündigen Draft-Phase Gelegenheit zur Prüfung. Eine fehlende Prüfung oder ein ausgeschöpftes Kontingent ist nach Ablauf der Frist kein harter Blocker. Nachvollziehbare kritische Hinweise werden dennoch berücksichtigt.

Fehlgeschlagene CI wird nicht einfach liegen gelassen: Der Wächter führt auf dem bestehenden Einheiten-Branch genau einen sicheren Reparaturzyklus aus und wartet anschließend auf die neu gestartete CI. Nicht sicher automatisch lösbare Fehler bleiben offen und werden gemeldet.

## Automationsprompts

- [[prompts/AUTOMATION-PROMPT|Tägliche Erzeugung einer neuen Einheit]]
- [[prompts/DEEP-RESEARCH-PROMPT|Verbindliche wissenschaftliche Recherche]]
- [[prompts/MERGE-AUTOMATION-PROMPT|Prüfung, Reparatur, Freigabe und Merge]]
- [[prompts/PR-REPAIR-PROMPT|Reparatur fehlgeschlagener Einheiten-PRs]]
- [[prompts/README|Überblick über die Promptpipeline]]

Die geplanten Aufgaben enthalten nur kurze Startanweisungen. Die ausführlichen Regeln werden bei jedem Lauf frisch aus diesen Dateien gelesen.

## CI und Wartung

Die CI verwendet aktuelle GitHub-Actions-Majors mit Node-24-Runtime, feste Ubuntu-24.04-Runner, minimale Berechtigungen, Dependency-Caches, Zeitlimits und Concurrency-Regeln.

Geprüft werden unter anderem:

- Python-Syntax und Whitespace,
- Quellen- und Kapitelstruktur,
- Mindest-, Warn- und Maximallänge,
- Obsidian-Wikilinks einschließlich Aliasen, Unterordnern und Überschriftenankern,
- fortlaufende Kapitelnummerierung,
- Übereinstimmung von Studienkarten, `Literatur.md`, `references.bib` und `references.json`,
- Wissensgraph, Gesamtdokument und Anki-Paket,
- Shellsyntax, PowerShell-Parser und echte Sync-Integrationstests,
- MkDocs-Build im Strict-Modus.

Dependabot kontrolliert wöchentlich GitHub Actions und Python-Abhängigkeiten. Einzelheiten stehen in [[.github/README|GitHub-Automation]].

## Wissensgraph

Die öffentlich sichtbare Seite [[knowledge-graph/README|Wissensgraph]] enthält ausschließlich die interaktive Graphoberfläche, die Knotendetails und eine aus den jeweils vorhandenen Knoten-, Beziehungs- und Statustypen erzeugte Legende. Die technische Beschreibung gehört vollständig in diese Wartungssektion.

Der Wissensgraph wird aus den Markdown-Dokumenten, ihren YAML-Metadaten und den internen Obsidian-Wikilinks erzeugt. Er bildet Dokumente und Navigation des Kompendiums ab; er ist keine automatisch abgeleitete medizinische Ontologie. Der native Obsidian-Graph bleibt direkt aus dem Vault ableitbar, zusätzlich erstellt `scripts/build_graph.py` einen kanonischen, typisierten Projektgraphen.

### Datenquellen

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

### Erzeugte Dateien

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

Aus Kompatibilitätsgründen bleiben zusätzlich `build/knowledge-graph.json` und `build/knowledge-graph.mmd` erhalten. Die JSON-Ausgabe enthält getrennte `nodes`, `edges`, `issues` und `stats`; jede Kante besitzt Typ, Status und Fundstellen. GraphML ist für Gephi, Cytoscape Desktop und vergleichbare Werkzeuge vorgesehen, Mermaid dient als kompakte Diagnose- und Offlineansicht.

### Linkstatus

| Status | Bedeutung | Freigabe |
|---|---|---|
| `ok` | Ziel ist eindeutig vorhanden | erlaubt |
| `planned` | Ziel fehlt bewusst und ist registriert | Warnung, erlaubt |
| `missing-document` | Zielseite fehlt ungeplant | Fehler |
| `missing-heading` | Dokument existiert, Abschnitt fehlt | Fehler |
| `ambiguous` | mehrere Ziele sind möglich | Fehler |
| `malformed` | ungültiges oder unsicheres Ziel | Fehler |

Nur Einträge in `planned-nodes.yaml` gelten als bewusst geplant. Sobald eine registrierte Seite tatsächlich existiert, meldet die Validierung den überholten Registry-Eintrag.

### Webdarstellung

Der Dokumentationslauf lädt die kanonische JSON-Ausgabe, ersetzt den einzelnen Marker in `knowledge-graph/README.md` durch die Graphoberfläche und kopiert die Daten nach `knowledge-graph/data/knowledge-graph.json`. Das Browser-Skript rendert daraus den aktuellen Graphen, Filter, Knotendetails und die datenabhängige Legende. Cytoscape.js ist auf Version `3.34.0` festgelegt; Farbe ist bei Statusdarstellungen nicht das einzige Unterscheidungsmerkmal.

Fehlt die Graph-JSON oder enthält sie nicht die erwartete Grundstruktur, bricht `scripts/build_docs.py` mit einer konkreten Fehlermeldung ab. Dadurch kann keine veraltete oder leere Wissensgraph-Seite veröffentlicht werden.

## Linkaufbereitung für Web und Exporte

Die Markdown-Quelldateien behalten ihre Obsidian-Wikilinks. Beim Web-Build werden sie in relative Standard-Markdown-Links umgewandelt; MkDocs erzeugt daraus korrekte HTML-Ziele. Für das Gesamtdokument werden stabile interne Anker erzeugt, damit Navigation auch in HTML, EPUB, LaTeX und PDF erhalten bleibt.

Nicht auflösbare oder mehrdeutige Ziele lassen die CI fehlschlagen. Quelltextblöcke werden von der Konvertierung ausgenommen.

## Literaturdaten

Die Studienkarten unter `references/` sind die gemeinsame Quelle für:

- das lesbare `Literatur.md`,
- `references.bib` für BibTeX und BibLaTeX,
- `references.json` im CSL-JSON-Format für CiteProc und Literaturverwaltungen.

Die im Studienkartentext sichtbare vollständige Zitation muss exakt aus den strukturierten `citation`-Metadaten reproduzierbar sein. Dadurch können die Ausgabeformate nicht unbemerkt auseinanderlaufen.

## Schutzregeln für automatische Merges

Normale neue Lerneinheiten dürfen nach zwei grünen CI-Phasen automatisch gemergt werden. Pull Requests mit Änderungen an folgenden Bereichen benötigen dagegen eine bewusste manuelle Prüfung:

- `.github/` und Workflows,
- `prompts/`,
- Validatoren,
- `CNAME`,
- Build-, Veröffentlichungs-, Sicherheits- oder Synchronisationsinfrastruktur.

Diese Trennung verhindert, dass ein PR seine eigenen Prüfregeln verändert und anschließend automatisch durch genau diese veränderten Regeln freigegeben wird.

## Betrieb und Synchronisierung

- [[Sync/README|Synchronisierung nach Betriebssystem]]
  - [[Sync/Linux/README|Linux und systemd]]
  - [[Sync/Android/README|Android und Termux]]
  - [[Sync/Windows/README|Windows und Aufgabenplanung]]
  - [[Sync/macOS/README|macOS und LaunchAgent]]
  - [[Sync/iOS/README|iPhone und iPad über iSH]]
  - [[Sync/BSD/README|BSD und Benutzer-Cron]]
- [[Sync/MODES|Pull-, Überschreib- und Full-Sync-Modi]]
- [[Sync/CONFIGURATION|Konfigurationsreferenz]]
- [[Sync/TROUBLESHOOTING|Fehlersuche und Rückgabecodes]]
- [[Sync/PLAN|Architektur- und Umsetzungsplan]]
- [[CONTRIBUTING|Beitrags-, Evidenz- und Branchregeln]]
- [[CHANGELOG|Änderungsverlauf]]

Alle sechs Plattformbereiche enthalten Installer beziehungsweise Installationspakete, Betriebsanleitungen und Deinstallationswege. Linux, Android, macOS, BSD und iSH verwenden dieselbe getestete Bash-Engine; Windows besitzt eine funktional gleichwertige PowerShell-Engine. Die öffentlichen ZIP-Pakete werden reproduzierbar gebaut und mit SHA-256-Prüfsummen veröffentlicht.

Ein bidirektionaler `full-sync` schreibt nie direkt nach `main`, sondern ausschließlich auf einen konfigurierten Gerätebranch. Checkout und Vault dürfen nicht überlappen; parallele Läufe und divergierende Gerätebranches werden kontrolliert abgefangen.

## Automatische Ausgaben

Bei Änderungen an `main` werden erzeugt beziehungsweise veröffentlicht:

- die MkDocs-Webseite mit MathJax-Unterstützung,
- ein Markdown-Gesamtdokument,
- HTML- und EPUB-3-Exporte,
- LaTeX-Quelltext und ein mit LuaLaTeX gebautes PDF,
- BibTeX- und CSL-JSON-Bibliografien,
- ein Anki-Deck im APKG-Format,
- ein lernorientierter Obsidian-Vault als ZIP,
- sechs plattformspezifische Sync-Pakete,
- SHA-256-Prüfsummen und ein JSON-Downloadmanifest,
- Validierungs- und Wissensgraph-Artefakte.

Die lesefreundliche Übersicht steht unter [[DOWNLOADS|Downloads]]. Die Dateien werden zusammen mit der Website unter stabilen `/artifacts/`-Adressen veröffentlicht; die klassischen GitHub-Actions-Artefakte bleiben als zeitlich begrenzte technische Kopie erhalten.

## Branch-Hygiene

Jeder Nicht-`main`-Branch muss einem aktiven oder nachvollziehbar abgeschlossenen Arbeitsvorgang zugeordnet sein. Nach Merge oder partieller Übernahme wird geprüft, ob noch einzigartige Änderungen gegenüber `main` verbleiben. Überholte Parallelstände dürfen nicht still liegen bleiben.
