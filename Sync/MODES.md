---
title: Synchronisationsmodi
tags: [Wartung, Sync, Sicherheit]
last_reviewed: 2026-07-15
hide: [navigation]
---

[↩️](README.md "Zurück zur Sync-Übersicht")

# Synchronisationsmodi

Die Namen beschreiben, wie lokale Änderungen behandelt werden. Ein Installer oder Skript ersetzt einen unbekannten Modus niemals stillschweigend durch eine riskantere Variante.

| Modus | Verhalten | Überschreibt | Löscht | Remote-Schreibzugriff |
|---|---|---|---|---|
| `safe-pull` | vergleicht den Vault mit dem letzten privaten Checkout und bricht bei Abweichungen ab | nein | nur nach bestandener Prüfung | nein |
| `prompt-pull` | zeigt lokale Abweichungen und fragt vor dem Verwerfen; ohne Terminal Abbruch | nach Bestätigung | nach Bestätigung | nein |
| `forced-pull` | setzt den privaten Checkout auf den Remote-Branch und spiegelt ihn exakt | ja | ja | nein |
| `additive-pull` | kopiert ausschließlich noch nicht vorhandene Dateien | nein | nein | nein |
| `full-sync` | synchronisiert konfliktbewusst mit einem eigenen Gerätebranch | bewusst | bewusst | ja, nur Gerätebranch |

## `safe-pull`

Die konservative Wahl für einen Vault, in dem gelegentlich versehentlich oder bewusst gearbeitet wird. Schon eine geänderte normale Markdown-Datei führt zum Abbruch. Geschützte Gerätedateien werden beim Vergleich ignoriert.

## `prompt-pull`

Wie `safe-pull`, aber mit manueller Entscheidung. In systemd, launchd, Cron, Termux:Boot und Windows-Aufgabenplanung existiert kein interaktives Terminal; dort bricht der Modus deshalb sicher ab.

## `forced-pull`

Geeignet für einen ausdrücklich schreibgeschützten Lesespiegel. Nicht geschützte lokale Dateien werden auf den Remote-Stand zurückgesetzt oder gelöscht. Dieser Modus ist kein Backup.

## `additive-pull`

Ergänzt nur fehlende Dateien. Bereits vorhandene Dateien werden nicht aktualisiert, selbst wenn der Remote-Stand neuer ist. Dadurch können Kapitel dauerhaft veralten. Der Modus ist nützlich für einmalige Materialsammlungen, aber nicht für einen konsistenten Lernspiegel.

## `full-sync`

Full Sync arbeitet zwingend auf einem eigenen Gerätebranch:

```text
main
└── sync/mein-laptop
```

Das Skript prüft lokale und entfernte Änderungen getrennt. Wurden beide Seiten seit dem letzten gemeinsamen Stand verändert, erfolgt ein Konfliktabbruch. Es gibt keinen automatischen Gewinner und keinen unbeaufsichtigten Merge.

Fachliche Änderungen gelangen anschließend über einen normalen Pull Request vom Gerätebranch nach `main`. Dadurch bleiben Validator, Review und CI erhalten.

## Geschützte Gerätedateien

Standardmäßig bleiben erhalten:

- `.obsidian/`
- `.stfolder`
- `.stignore`
- `.nomedia`
- `.trash/`
- `.DS_Store`
- `Thumbs.db`
- `desktop.ini`

Mit `ADHS_SYNC_PROTECT_OBSIDIAN=0` beziehungsweise `ProtectObsidian: false` kann `.obsidian/` bewusst in die Synchronisierung einbezogen werden. Das ist bei unterschiedlichen Obsidian-Versionen und Plugins riskanter und daher nicht der Standard.

## Empfehlung

- **reiner Lesespiegel:** `forced-pull`
- **Arbeitsvault ohne Rückschreiben:** `safe-pull`
- **manuell kontrolliertes Überschreiben:** `prompt-pull`
- **nur fehlende Dateien:** `additive-pull`
- **eigene Inhalte über Git zurückschreiben:** `full-sync` mit eindeutigem Gerätebranch
