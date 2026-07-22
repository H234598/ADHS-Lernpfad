---
title: Ausbauplan der Synchronisierung
tags: [Wartung, Sync, Architektur, Sicherheit]
last_reviewed: 2026-07-15
hide: [navigation]
---

[↩️](README.md "Zurück zur Sync-Übersicht")

# Ausbauplan der Synchronisierung

## Zielbild

Der Ordner `Sync/` stellt für die verbreiteten Desktop- und Mobilplattformen reproduzierbare, deinstallierbare und möglichst gleichartige Synchronisationspakete bereit. Lernende sollen zwischen sicheren Pull-Varianten und einem ausdrücklich getrennten bidirektionalen Gerätebranch wählen können, ohne dass ein Skript direkt in `main` schreibt.

## Leitprinzipien

1. **`main` bleibt veröffentlicht und geprüft.** Pull-Modi lesen ausschließlich aus einem konfigurierten Remote-Branch.
2. **Kein stilles Überschreiben.** `safe-pull` und `prompt-pull` erkennen lokale Abweichungen vor dem Abruf neuer Remote-Daten.
3. **Full Sync niemals direkt nach `main`.** Bidirektionale Änderungen werden in einen eigenen Branch wie `sync/laptop-bernhard` geschrieben und anschließend per Pull Request geprüft.
4. **Gerätedaten bleiben lokal.** `.obsidian/`, Syncthing-Metadaten, Papierkorb und Plattformdateien sind standardmäßig geschützt.
5. **Privater Checkout, sichtbarer Vault.** Wo möglich, liegt Git in einem privaten Anwendungsverzeichnis und der Obsidian-Vault enthält nur Lern- und Gerätedateien.
6. **Abbruch statt Raten.** Bei gleichzeitigen lokalen und entfernten Änderungen im Full-Sync-Branch wird nicht automatisch überschrieben oder zusammengeführt.
7. **Deinstallation löscht keine Lerninhalte.** Installer und Zeitplaner können entfernt werden, ohne den Vault oder einen privaten Checkout ungefragt zu vernichten.

## Gemeinsame Modi

| Modus | Quelle → Ziel | Lokale Abweichung | Löschen veralteter Dateien | Rückschreiben |
|---|---|---|---|---|
| `safe-pull` | Remote-Branch → Vault | Abbruch | ja, nach erfolgreicher Prüfung | nein |
| `prompt-pull` | Remote-Branch → Vault | interaktive Bestätigung; ohne Terminal Abbruch | ja | nein |
| `forced-pull` | Remote-Branch → Vault | wird verworfen | ja | nein |
| `additive-pull` | Remote-Branch → Vault | bleibt erhalten | nein | nein |
| `full-sync` | Gerätebranch ↔ Vault | konfliktbewusst | ja | nur Gerätebranch |

## Full-Sync-Konfliktmodell

Die private Arbeitskopie ist der letzte bekannte gemeinsame Stand. Vor jedem Lauf werden zwei Fragen getrennt beantwortet:

- Hat sich der sichtbare Vault gegenüber der privaten Arbeitskopie geändert?
- Hat sich der entfernte Gerätebranch gegenüber der privaten Arbeitskopie geändert?

| Vault geändert | Remote geändert | Verhalten |
|---|---|---|
| nein | nein | kein Inhaltswechsel; ausstehender Push wird erneut versucht |
| nein | ja | Remote fast-forwarden und in den Vault spiegeln |
| ja | nein | Vault importieren, committen und in den Gerätebranch pushen |
| ja | ja | kontrollierter Abbruch wegen Divergenz |

Dieses Modell vermeidet automatische Dreiwege-Merges in unbeaufsichtigten Jobs. Ein Konflikt bleibt sichtbar und kann anschließend bewusst aufgelöst werden.

## Plattformarchitektur

### Gemeinsame Bash-Engine

`Sync/Common/adhs-sync.sh` enthält die eigentliche Logik für Linux, Android/Termux, macOS, BSD und iSH. Plattformpakete liefern nur:

- Standardpfade,
- Konfigurationsdatei,
- Installer und Deinstaller,
- systemeigenen Zeitplaner,
- Diagnosebefehle.

### Windows

Windows erhält eine native PowerShell-Implementierung mit derselben Modus- und Konfliktsemantik. Die Aufgabenplanung wird als normale Benutzeraufgabe registriert; Administratorrechte sind nicht erforderlich.

### iPhone und iPad

Das Skriptpaket richtet sich an iSH und läuft bewusst manuell. iOS erlaubt keine verlässliche allgemeine Hintergrundausführung eines solchen Shelljobs und trennt App-Dateisysteme. Der Zielordner muss daher über iSH in einen von Obsidian erreichbaren Files-Ordner eingebunden werden.

## Verzeichnisstruktur

```text
Sync/
├── README.md
├── PLAN.md
├── MODES.md
├── CONFIGURATION.md
├── TROUBLESHOOTING.md
├── Common/
│   ├── README.md
│   └── adhs-sync.sh
├── Linux/
├── Android/
├── Windows/
├── macOS/
├── iOS/
├── BSD/
└── tests/
```

## Qualitätssicherung

Die CI prüft:

- Bash-Syntax aller Shellskripte,
- PowerShell-Parserfehler,
- XML-Syntax der LaunchAgent-Datei,
- reproduzierbare Dokumentationslinks,
- Pull-Modi in temporären lokalen Git-Repositorys,
- Schutz lokaler `.obsidian`-Dateien,
- Divergenzabbruch im Full Sync,
- vollständigen MkDocs- und Exportbau.

## Umsetzungsstatus

- [x] gemeinsame Architektur und Modussemantik
- [x] gemeinsame Bash-Engine
- [x] Linux mit systemd-Benutzertimer
- [x] Android mit Termux und optionalem Bootstart
- [x] Windows mit PowerShell und Aufgabenplanung
- [x] macOS mit LaunchAgent
- [x] BSD mit Benutzer-Crontab
- [x] iOS/iPadOS über iSH, manuell
- [x] Deinstaller und Diagnosewege
- [x] automatisierte Integrationstests
- [ ] grafische Installer
- [ ] signierte Binärpakete
- [ ] Konfliktassistent für Full Sync
- [ ] optionaler Pull-Request-Assistent für Gerätebranches
