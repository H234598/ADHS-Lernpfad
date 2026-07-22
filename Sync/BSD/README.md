---
title: BSD-Synchronisierung
tags: [Wartung, Sync, BSD, Cron, Obsidian]
last_reviewed: 2026-07-15
hide: [navigation]
---

[↩️](../README.md "Zurück zur Sync-Übersicht")

# BSD-Synchronisierung

Das BSD-Paket nutzt die gemeinsame Bash-Engine und richtet auf Wunsch einen Eintrag in der Benutzer-Crontab ein. Es setzt weder systemd noch Linux-spezifisches `flock` voraus.

## Dateien

- [Installer](install.sh){ .md-button .md-button--primary }
- [Sync-Wrapper](sync.sh){ .md-button }
- [Deinstaller](uninstall.sh){ .md-button }
- [gemeinsame Engine](../Common/adhs-sync.sh){ .md-button }

## Voraussetzungen

```text
Bash
Git
rsync
crontab   nur für automatische Läufe
```

Typische Paketbefehle:

```text
FreeBSD: sudo pkg install bash git rsync
OpenBSD: doas pkg_add bash git rsync
NetBSD:  sudo pkgin install bash git-base rsync
```

Paketnamen können je nach Release und Repository abweichen; der Installer installiert keine Systempakete mit Root-Rechten.

## Standardinstallation

```bash
git clone https://github.com/H234598/ADHS-Lernpfad.git
cd ADHS-Lernpfad
./Sync/BSD/install.sh
```

Standardziel:

```text
~/Obsidian/ADHS-Lernpfad
```

## Beispiele

### Reiner Lesespiegel

```bash
./Sync/BSD/install.sh --mode forced-pull
```

### Manuell mit Rückfrage

```bash
./Sync/BSD/install.sh --manual --mode prompt-pull
```

### Full Sync über Gerätebranch

```bash
./Sync/BSD/install.sh \
  --mode full-sync \
  --device-branch sync/mein-freebsd-rechner \
  --adopt-existing-target
```

## Betrieb

```bash
adhs-lernpfad-sync
crontab -l
tail -n 100 "$HOME/.local/state/adhs-lernpfad-sync.log"
```

Der Cronjob läuft nichtinteraktiv. `prompt-pull` bricht bei lokalen Änderungen deshalb ab.

## Deinstallation

```bash
./Sync/BSD/uninstall.sh
```

Optional:

```bash
./Sync/BSD/uninstall.sh --purge-config --remove-checkout
```

Der Vault wird niemals gelöscht.

## Portabilität

Die Sperre verwendet atomar angelegte Verzeichnisse statt `flock`. Zeitangaben, Git-Operationen und rsync-Aufrufe vermeiden GNU-spezifische Optionen, soweit dies für die gemeinsame Engine praktikabel ist. Die CI läuft auf Linux; echte Laufzeittests auf FreeBSD, OpenBSD und NetBSD bleiben zusätzlich sinnvoll.

Weitere Einzelheiten: [[Sync/MODES|Modi]], [[Sync/CONFIGURATION|Konfiguration]] und [[Sync/TROUBLESHOOTING|Fehlersuche]].
