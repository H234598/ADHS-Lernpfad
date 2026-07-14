---
title: Linux-Synchronisierung
tags: [Wartung, Sync, Linux, systemd, Obsidian]
last_reviewed: 2026-07-14
hide: [navigation]
---

[↩️](../README.md "Zurück zur Sync-Übersicht")

# Linux-Synchronisierung

Das Linux-Paket installiert einen systemd-Benutzertimer. Er synchronisiert den veröffentlichten `main`-Stand alle 30 Minuten in einen Obsidian-Vault. Der Standardmodus ist `safe-pull`: lokale Änderungen werden niemals still überschrieben.

## Dateien

- [Installer herunterladen](install.sh){ .md-button .md-button--primary }
- [Sync-Skript herunterladen](sync.sh){ .md-button }
- [systemd-Service](systemd/adhs-lernpfad-sync.service){ .md-button }
- [systemd-Timer](systemd/adhs-lernpfad-sync.timer){ .md-button }

## Installation

```bash

git clone https://github.com/H234598/ADHS-Lernpfad.git
cd ADHS-Lernpfad
./Sync/Linux/install.sh "/vollstaendiger/Pfad/zum/Obsidian-Vault" safe-pull
```

Ohne Argument wird `$HOME/Dokumente/Obsidian/ADHS-Lernpfad` verwendet.

## Modus wählen

```bash
./Sync/Linux/install.sh "/Pfad/zum/Vault" safe-pull
./Sync/Linux/install.sh "/Pfad/zum/Vault" prompt-pull
./Sync/Linux/install.sh "/Pfad/zum/Vault" forced-pull
```

Die genaue Bedeutung steht unter [[Sync/MODES|Synchronisationsmodi]]. `full-sync` ist absichtlich noch nicht implementiert.

## Betrieb

```bash
systemctl --user status adhs-lernpfad-sync.timer
systemctl --user start adhs-lernpfad-sync.service
journalctl --user -u adhs-lernpfad-sync.service -n 100 --no-pager
```

Die Konfiguration liegt unter:

```text
~/.config/adhs-lernpfad-sync.env
```

Dort kann `ADHS_LERNPFAD_SYNC_MODE` nachträglich geändert werden. Danach genügt der nächste Timerlauf; ein `daemon-reload` ist für reine Umgebungsänderungen nicht erforderlich.

## Verhalten bei lokalen Änderungen

- `safe-pull`: kontrollierter Abbruch mit Statusausgabe.
- `prompt-pull`: interaktive Rückfrage; in einem nichtinteraktiven Timerlauf sicherer Abbruch.
- `forced-pull`: Reset auf `origin/main`; `.obsidian`, `.stfolder`, `.stignore`, `.nomedia` und `.trash` bleiben erhalten.

> [!warning]
> Der Zielordner ist bei `forced-pull` ein Spiegel und kein Arbeitsrepository. Normale lokale Markdown- und Bildänderungen werden verworfen.
