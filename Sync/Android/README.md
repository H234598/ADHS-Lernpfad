---
title: Android-Synchronisierung
tags: [Wartung, Sync, Android, Termux, Obsidian]
last_reviewed: 2026-07-14
hide: [navigation]
---

[↩️](../README.md "Zurück zur Sync-Übersicht")

# Android-Synchronisierung mit Termux

Das Android-Paket verwendet einen privaten Git-Checkout innerhalb von Termux und spiegelt daraus in den frei zugänglichen Obsidian-Vault. Dadurch liegt kein `.git`-Verzeichnis im gemeinsamen Android-Speicher. Das entspricht dem bereits erprobten schreibgeschützten Spiegel: `origin/main` wird im privaten Checkout erzwungen und anschließend per `rsync` in den Vault übertragen.

## Dateien

- [Termux-Installer herunterladen](install-termux.sh){ .md-button .md-button--primary }
- [Sync-Skript herunterladen](sync-termux.sh){ .md-button }

## Installation

```bash
termux-setup-storage
pkg update
pkg install git rsync

git clone https://github.com/H234598/ADHS-Lernpfad.git
cd ADHS-Lernpfad
./Sync/Android/install-termux.sh \
  "$HOME/storage/shared/Documents/Obsidian" \
  forced-pull
```

Der erzeugte Vault liegt standardmäßig unter:

```text
/storage/emulated/0/Documents/Obsidian/ADHS-Lernpfad
```

Der private Checkout liegt unter:

```text
$HOME/.local/share/adhs-lernpfad/repo
```

## Manuell synchronisieren

```bash
adhs-lernpfad-sync
```

## Modus wählen

```bash
./Sync/Android/install-termux.sh "/Vault-Stamm" safe-pull
./Sync/Android/install-termux.sh "/Vault-Stamm" prompt-pull
./Sync/Android/install-termux.sh "/Vault-Stamm" forced-pull
./Sync/Android/install-termux.sh "/Vault-Stamm" additive-pull
```

- `safe-pull` vergleicht den Vault mit dem zuletzt ausgecheckten Stand und bricht bei lokalen Abweichungen ab.
- `prompt-pull` fragt vor dem Verwerfen lokaler Abweichungen nach.
- `forced-pull` erzeugt einen exakten Lesespiegel und ist der erprobte Standard für Android.
- `additive-pull` ergänzt nur neue Dateien; bestehende Dateien werden weder überschrieben noch gelöscht und können deshalb veralten.

Die vollständige Definition steht unter [[Sync/MODES|Synchronisationsmodi]].

## Geschützte Dateien

Beim Spiegeln bleiben `.obsidian/`, `.stfolder`, `.stignore`, `.nomedia` und `.trash/` erhalten. Das schützt Geräte- und Syncthing-Konfigurationen, nicht aber lokale Änderungen an normalen Lerninhalten.

## Optional beim Gerätestart

```bash
./Sync/Android/install-termux.sh \
  "$HOME/storage/shared/Documents/Obsidian" \
  forced-pull \
  boot
```

Dadurch wird ein kleines Termux:Boot-Skript angelegt. Ohne die entsprechende Boot-Erweiterung bleibt die manuelle Ausführung unverändert nutzbar.

> [!warning]
> `forced-pull` ist für einen reinen Lesespiegel gedacht. Eigene Markdown-Notizen gehören in einen getrennten Vault oder in ausdrücklich geschützte Dateien.
