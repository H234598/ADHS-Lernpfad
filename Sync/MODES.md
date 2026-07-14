---
title: Synchronisationsmodi
tags: [Wartung, Sync, Sicherheit]
last_reviewed: 2026-07-14
hide: [navigation]
---

[↩️](README.md "Zurück zur Sync-Übersicht")

# Synchronisationsmodi

Die Namen beschreiben, wie lokale Änderungen behandelt werden. Ein Installer oder Skript darf einen nicht unterstützten Modus nicht stillschweigend durch einen riskanteren ersetzen.

| Modus | Verhalten | Risiko | Stand |
|---|---|---|---|
| `safe-pull` | Aktualisiert nur, wenn keine lokalen Änderungen am Spiegel vorliegen; andernfalls Abbruch. | niedrig | Linux und Android |
| `prompt-pull` | Erkennt lokale Abweichungen und fragt interaktiv, bevor sie verworfen werden. Ohne Terminal erfolgt ein sicherer Abbruch. | mittel | Linux und Android |
| `forced-pull` | Setzt die Lerninhalte auf `origin/main` zurück und entfernt nicht geschützte lokale Dateien. | hoch | Linux und Android |
| `additive-pull` | Kopiert nur noch nicht vorhandene Dateien; überschreibt und löscht nichts. Bestehende Dateien können dadurch veralten. | niedrig, aber kein vollständiger Spiegel | Android |
| `full-sync` | Geplanter bidirektionaler Ablauf mit Konfliktbehandlung, Authentifizierung, Commit und Review. | hoch | noch nicht implementiert |

## Geschützte Gerätedateien

Die produktiven Skripte bewahren diese lokalen Steuerdateien, soweit sie im Ziel vorhanden sind:

- `.obsidian/`
- `.stfolder`
- `.stignore`
- `.nomedia`
- `.trash/`

Diese Ausnahmen schützen Einstellungen und Synchronisationsmetadaten. Sie machen `forced-pull` nicht zu einem Backup: Änderungen an normalen Markdown-, Bild- oder Literaturdateien werden weiterhin verworfen.

## Empfehlung

- **Nur lesen:** `forced-pull`, wenn der Zielordner bewusst ein schreibgeschützter Spiegel ist.
- **Gelegentliche lokale Notizen:** `safe-pull`; lokale Änderungen werden sichtbar und blockieren die Aktualisierung.
- **Bewusste manuelle Entscheidung:** `prompt-pull`.
- **Nur neue Dateien ergänzen:** `additive-pull`, mit dem Wissen, dass vorhandene Dateien nicht aktualisiert werden.
- **In beide Richtungen arbeiten:** derzeit nicht automatisieren; dafür wird später ein eigener Full-Sync-Plan erstellt.
