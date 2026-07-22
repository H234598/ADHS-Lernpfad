---
title: iPhone- und iPad-Synchronisierung
tags: [Wartung, Sync, iOS, iPhone, iPad, iSH]
last_reviewed: 2026-07-15
hide: [navigation]
---

[↩️](../README.md "Zurück zur Sync-Übersicht")

# iPhone- und iPad-Synchronisierung über iSH

iOS und iPadOS trennen App-Dateisysteme und erlauben keinen allgemeinen dauerhaften Shell-Hintergrunddienst. Das Paket unterstützt deshalb einen **manuellen** Ablauf über iSH. Der Obsidian-Vault muss in einen iOS-Files-Ordner gelegt und in iSH eingebunden werden.

## Dateien

- [iSH-Installer](install-ish.sh){ .md-button .md-button--primary }
- [Sync-Wrapper](sync-ish.sh){ .md-button }
- [Deinstaller](uninstall-ish.sh){ .md-button }
- [gemeinsame Engine](../Common/adhs-sync.sh){ .md-button }

## Files-Ordner in iSH einbinden

Erstelle zunächst einen Ordner in der Dateien-App, den Obsidian als Vault öffnen kann. In iSH kann ein Files-Ordner interaktiv eingebunden werden:

```sh
mkdir -p /mnt/obsidian
mount -t ios . /mnt/obsidian
```

Der Dateiauswahldialog bestimmt, welcher iOS-Ordner unter `/mnt/obsidian` erscheint. Diese Einbindung kann nach einem Neustart erneut nötig sein.

## Installation

```bash
apk add bash git rsync coreutils

git clone https://github.com/H234598/ADHS-Lernpfad.git
cd ADHS-Lernpfad
./Sync/iOS/install-ish.sh \
  --target /mnt/obsidian/ADHS-Lernpfad \
  --mode safe-pull
```

## Reiner Lesespiegel

```bash
./Sync/iOS/install-ish.sh \
  --target /mnt/obsidian/ADHS-Lernpfad \
  --mode forced-pull
```

## Full Sync über Gerätebranch

```bash
./Sync/iOS/install-ish.sh \
  --target /mnt/obsidian/ADHS-Lernpfad \
  --mode full-sync \
  --device-branch sync/mein-ipad \
  --adopt-existing-target
```

Ein Push benötigt in iSH eingerichtete Git-Zugangsdaten. Der Gerätebranch wird nicht automatisch nach `main` gemergt.

## Manuell synchronisieren

Vor jedem Lauf muss der Files-Ordner erreichbar sein:

```bash
mount | grep /mnt/obsidian
adhs-lernpfad-sync
```

## Deinstallation

```bash
./Sync/iOS/uninstall-ish.sh
```

Optional:

```bash
./Sync/iOS/uninstall-ish.sh --purge-config --remove-checkout
```

Der eingebundene Vault wird niemals gelöscht.

## Grenzen

- keine verlässliche automatische Hintergrundausführung
- Files-Mount kann nach App- oder Gerätestart erneut nötig sein
- iSH ist eine zusätzliche Linux-Umgebung und nicht Teil von Obsidian
- große Vaults und Hashvergleiche können auf Mobilgeräten langsamer sein

Für vollautomatische Mehrgeräte-Synchronisierung sind Obsidian Sync oder ein vorhandener Dateisynchronisationsdienst in der Praxis komfortabler. Das iSH-Paket ist für kontrollierte Git-basierte Pulls und Gerätebranches gedacht.

Weitere Einzelheiten: [[Sync/MODES|Modi]], [[Sync/CONFIGURATION|Konfiguration]] und [[Sync/TROUBLESHOOTING|Fehlersuche]].
