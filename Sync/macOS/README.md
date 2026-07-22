---
title: macOS-Synchronisierung
tags: [Wartung, Sync, macOS, launchd, Obsidian]
last_reviewed: 2026-07-15
hide: [navigation]
---

[↩️](../README.md "Zurück zur Sync-Übersicht")

# macOS-Synchronisierung

Das macOS-Paket installiert die gemeinsame Bash-Engine in `~/Library/Application Support` und kann einen benutzerspezifischen LaunchAgent einrichten. Der sichtbare Obsidian-Vault bleibt frei von Git-Metadaten.

## Dateien

- [Installer](install.sh){ .md-button .md-button--primary }
- [Sync-Wrapper](sync.sh){ .md-button }
- [Deinstaller](uninstall.sh){ .md-button }
- [gemeinsame Engine](../Common/adhs-sync.sh){ .md-button }

## Voraussetzungen

- Bash
- Git, gegebenenfalls über die Apple Command Line Tools
- rsync
- launchctl und plutil für automatische Läufe

Fehlt Git:

```bash
xcode-select --install
```

## Standardinstallation

```bash
git clone https://github.com/H234598/ADHS-Lernpfad.git
cd ADHS-Lernpfad
./Sync/macOS/install.sh
```

Standardziel:

```text
~/Documents/Obsidian/ADHS-Lernpfad
```

Der LaunchAgent startet bei der Anmeldung und danach alle 30 Minuten.

## Beispiele

### Reiner Lesespiegel

```bash
./Sync/macOS/install.sh --mode forced-pull
```

### Manuell mit Rückfrage

```bash
./Sync/macOS/install.sh --manual --mode prompt-pull
```

### Full Sync über Gerätebranch

```bash
./Sync/macOS/install.sh \
  --mode full-sync \
  --device-branch sync/mein-macbook \
  --adopt-existing-target
```

## Betrieb

```bash
"$HOME/Library/Application Support/ADHS-Lernpfad-Sync/bin/adhs-lernpfad-sync"
launchctl print "gui/$UID/org.telacore.adhs-lernpfad-sync"
tail -n 100 "$HOME/Library/Logs/ADHS-Lernpfad-Sync.log"
```

Konfiguration:

```text
~/Library/Application Support/ADHS-Lernpfad-Sync/config.env
```

Privater Checkout:

```text
~/Library/Application Support/ADHS-Lernpfad-Sync/repo
```

## Deinstallation

```bash
./Sync/macOS/uninstall.sh
```

Optional:

```bash
./Sync/macOS/uninstall.sh --purge-config --remove-checkout
```

Der Vault bleibt immer erhalten.

## LaunchAgent-Verhalten

Der Agent verwendet `StartInterval`, `RunAtLoad`, niedrige I/O-Priorität und eine gemeinsame Logdatei. Er läuft nichtinteraktiv; `prompt-pull` führt bei lokalen Änderungen deshalb zum sicheren Abbruch.

Weitere Einzelheiten: [[Sync/MODES|Modi]], [[Sync/CONFIGURATION|Konfiguration]] und [[Sync/TROUBLESHOOTING|Fehlersuche]].
