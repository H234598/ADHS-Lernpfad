---
title: Wartung und Automatisierung
tags: [Wartung, Automatisierung, CI]
last_reviewed: 2026-07-14
hide: [navigation]
---

<div class="maintenance-back" align="right">
<a href="README.md" title="Zurück zur Startseite" aria-label="Zurück zur Startseite">↩️</a>
</div>

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
- Wikilinks und fortlaufende Nummerierung,
- Übereinstimmung des generierten Literaturverzeichnisses,
- Wissensgraph, Gesamtdokument und Anki-Paket,
- MkDocs-Build im Strict-Modus.

Dependabot kontrolliert wöchentlich GitHub Actions und Python-Abhängigkeiten. Einzelheiten stehen in [[.github/README|GitHub-Automation]].

## Schutzregeln für automatische Merges

Normale neue Lerneinheiten dürfen nach zwei grünen CI-Phasen automatisch gemergt werden. Pull Requests mit Änderungen an folgenden Bereichen benötigen dagegen eine bewusste manuelle Prüfung:

- `.github/` und Workflows,
- `prompts/`,
- Validatoren,
- `CNAME`,
- Build-, Veröffentlichungs-, Sicherheits- oder Synchronisationsinfrastruktur.

Diese Trennung verhindert, dass ein PR seine eigenen Prüfregeln verändert und anschließend automatisch durch genau diese veränderten Regeln freigegeben wird.

## Betrieb und Synchronisierung

- [[SYNC-OBSIDIAN|Desktop-Synchronisierung nach Obsidian]]
- [[CONTRIBUTING|Beitrags-, Evidenz- und Branchregeln]]
- [[CHANGELOG|Änderungsverlauf]]

Der Android-Vault wird als schreibgeschützter Spiegel aus `main` erzeugt. Lokale inhaltliche Änderungen im Spiegel werden beim nächsten erzwungenen Abgleich überschrieben; gerätespezifische Obsidian- und Syncthing-Dateien bleiben erhalten.

## Automatische Ausgaben

Bei Änderungen an `main` werden erzeugt beziehungsweise veröffentlicht:

- die MkDocs-Webseite,
- ein Markdown-Gesamtdokument,
- HTML- und EPUB-Exporte,
- ein Anki-Deck im APKG-Format,
- Validierungs- und Wissensgraph-Artefakte.

## Branch-Hygiene

Jeder Nicht-`main`-Branch muss einem aktiven oder nachvollziehbar abgeschlossenen Arbeitsvorgang zugeordnet sein. Nach Merge oder partieller Übernahme wird geprüft, ob noch einzigartige Änderungen gegenüber `main` verbleiben. Überholte Parallelstände dürfen nicht still liegen bleiben.
