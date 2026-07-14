---
title: Synchronisierung
tags: [Wartung, Sync, Obsidian]
last_reviewed: 2026-07-15
hide: [navigation]
---

[↩️](../WARTUNG.md "Zurück zur Wartung")

# Synchronisierung

Dieser Bereich bündelt alle Wege, den ADHS-Lernpfad auf Geräte und in Obsidian-Vaults zu spiegeln. Die technische Infrastruktur bleibt außerhalb der normalen Lernnavigation; alle Installer und Skripte sind von den jeweiligen Plattformseiten direkt herunterladbar.

## Betriebssysteme

| System | Paket | Zeitplaner | Anleitung |
|---|---|---|---|
| Linux | Bash, Git und rsync | systemd-Benutzertimer oder manuell | [Linux](Linux/README.md) |
| Android | Termux, privater Checkout und rsync | manuell oder Termux:Boot | [Android](Android/README.md) |
| Windows | native PowerShell-Engine | Windows-Aufgabenplanung oder manuell | [Windows](Windows/README.md) |
| macOS | Bash, Git und rsync | LaunchAgent oder manuell | [macOS](macOS/README.md) |
| iPhone und iPad | iSH mit eingebundenem Files-Ordner | bewusst nur manuell | [iOS/iPadOS](iOS/README.md) |
| BSD | Bash, Git und rsync | Benutzer-Crontab oder manuell | [BSD](BSD/README.md) |

## Dokumentation

- [[Sync/PLAN|Architektur- und Ausbauplan]]
- [[Sync/MODES|Synchronisationsmodi]]
- [[Sync/CONFIGURATION|Konfiguration]]
- [[Sync/TROUBLESHOOTING|Fehlersuche]]
- [[Sync/Common/README|Gemeinsame Bash-Engine]]

## Die fünf Modi

| Modus | Typischer Einsatz |
|---|---|
| `safe-pull` | Arbeitsvault schützen; bei lokalen Änderungen abbrechen |
| `prompt-pull` | vor einem Überschreiben manuell entscheiden |
| `forced-pull` | reiner Lesespiegel von `main` |
| `additive-pull` | nur fehlende Dateien ergänzen; bestehende Dateien nicht aktualisieren |
| `full-sync` | lokale Änderungen über einen eigenen Gerätebranch zurückschreiben |

> [!warning] Full Sync schreibt nicht nach `main`
> Der bidirektionale Modus verwendet zwingend einen Gerätebranch wie `sync/mein-laptop`. Fachliche Änderungen gelangen erst über einen normalen Pull Request in den veröffentlichten Lernpfad.

## Gemeinsames Sicherheitsmodell

- Git liegt in einem privaten Checkout außerhalb des sichtbaren Vaults.
- Gerätespezifische `.obsidian`- und Syncthing-Dateien bleiben standardmäßig erhalten.
- Zeitplaner laufen nichtinteraktiv und brechen bei notwendigen Rückfragen ab.
- Gleichzeitige lokale und entfernte Full-Sync-Änderungen führen zu einem Konfliktabbruch statt zu einem automatischen Überschreiben.
- Deinstaller löschen den Vault niemals und entfernen den privaten Checkout nur nach ausdrücklicher Option.

Die automatisierten Integrationstests erzeugen temporäre lokale Git-Remotes und prüfen Pull, Überschreiben, additive Kopie, geschützte Obsidian-Dateien, Gerätebranch-Push und Divergenzabbruch.
