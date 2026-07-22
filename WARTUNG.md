---
title: Wartung und Automatisierung
tags: [Wartung, Automatisierung, CI]
last_reviewed: 2026-07-22
hide: [navigation]
---

[↩️](README.md "Zurück zur Startseite")

# Wartung und Automatisierung

Diese Seite bündelt den technischen Betrieb des Lernkompendiums. Sie gehört nicht zum eigentlichen Lernpfad und ist deshalb aus der normalen Navigation ausgeblendet.

> Die technische Weiterentwicklung des Projekts ist in einer separaten Roadmap dokumentiert:
>
> [[TECHNISCHE_ROADMAP|Technische Roadmap]]

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

## Linkaufbereitung für Web und Exporte

Die Markdown-Quelldateien behalten ihre Obsidian-Wikilinks. Beim Web-Build werden sie in relative Standard-Markdown-Links umgewandelt; MkDocs erzeugt daraus korrekte HTML-Ziele. Für das Gesamtdokument werden stabile interne Anker erzeugt, damit Navigation auch in HTML, EPUB, LaTeX und PDF erhalten bleibt.

Nicht auflösbare oder mehrdeutige Ziele lassen die CI fehlschlagen. Quelltextblöcke werden von der Konvertierung ausgenommen.

## Literaturdaten

Die Studienkarten unter `references/` sind die gemeinsame Quelle für:

- das lesbare `Literatur.md`,
- `references.bib` für BibTeX und BibLaTeX,
- `references.json` im CSL-JSON-Format für CiteProc und Literaturverwaltungen.

Die im Studienkartentext sichtbare vollständige Zitation muss exakt aus den strukturierten `citation`-Metadaten reproduzierbar sein.

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
- [[Sync/MODES|Pull-, Überschreib- und Full-Sync-Modi]]
- [[Sync/CONFIGURATION|Konfigurationsreferenz]]
- [[Sync/TROUBLESHOOTING|Fehlersuche und Rückgabecodes]]
- [[CONTRIBUTING|Beitrags-, Evidenz- und Branchregeln]]
- [[CHANGELOG|Änderungsverlauf]]

## Automatische Ausgaben

Bei Änderungen an `main` werden erzeugt beziehungsweise veröffentlicht:

- die MkDocs-Webseite
- Markdown-Gesamtdokument
- HTML- und EPUB-Exporte
- LaTeX/PDF
- Bibliografien
- Anki-Deck
- Obsidian-Vault
- Sync-Pakete
- Prüfsummen und Manifest
- Validierungs- und Wissensgraph-Artefakte

## Branch-Hygiene

Jeder Nicht-`main`-Branch muss einem aktiven oder nachvollziehbar abgeschlossenen Arbeitsvorgang zugeordnet sein.
