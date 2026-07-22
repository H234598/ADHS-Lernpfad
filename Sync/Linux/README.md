---
title: Linux-Synchronisierung
tags: [Wartung, Sync, Linux, systemd, Obsidian]
last_reviewed: 2026-07-15
hide: [navigation]
---

[↩️](../README.md "Zurück zur Sync-Übersicht")

# Linux-Synchronisierung

Das Linux-Paket verwendet einen privaten Git-Checkout und spiegelt daraus in den sichtbaren Obsidian-Vault. Standardmäßig installiert es einen systemd-Benutzertimer im 30-Minuten-Takt. Administratorrechte sind nicht erforderlich.

## Dateien

- [Installer](install.sh){ .md-button .md-button--primary }
- [Sync-Wrapper](sync.sh){ .md-button }
- [Deinstaller](uninstall.sh){ .md-button }
- [systemd-Service](systemd/adhs-lernpfad-sync.service){ .md-button }
- [systemd-Timer-Beispiel](systemd/adhs-lernpfad-sync.timer){ .md-button }
- [gemeinsame Engine](../Common/adhs-sync.sh){ .md-button }

## Voraussetzungen

```text
bash
Git
rsync
systemd --user   nur für den automatischen Timer
```

## Standardinstallation

```bash
git clone https://github.com/H234598/ADHS-Lernpfad.git
cd ADHS-Lernpfad
./Sync/Linux/install.sh
```

Standardwerte:

```text
Ziel:     ~/Dokumente/Obsidian/ADHS-Lernpfad
Modus:    safe-pull
Intervall: 30 Minuten
```

## Beispiele

### Reiner Lesespiegel

```bash
./Sync/Linux/install.sh \
  --target "$HOME/Dokumente/Obsidian/ADHS-Lernpfad" \
  --mode forced-pull
```

### Bei lokalen Änderungen abbrechen

```bash
./Sync/Linux/install.sh --mode safe-pull
```

### Full Sync über Gerätebranch

```bash
./Sync/Linux/install.sh \
  --mode full-sync \
  --device-branch sync/mein-linux-laptop \
  --adopt-existing-target
```

Der Gerätebranch benötigt einen eingerichteten Git-Schreibzugang. Er wird nicht automatisch nach `main` gemergt.

### Nur manuell, ohne systemd

```bash
./Sync/Linux/install.sh --manual --mode prompt-pull
```

## Betrieb

```bash
adhs-lernpfad-sync
systemctl --user status adhs-lernpfad-sync.timer
systemctl --user start adhs-lernpfad-sync.service
journalctl --user -u adhs-lernpfad-sync.service -n 100 --no-pager
```

Konfiguration:

```text
~/.config/adhs-lernpfad-sync.env
```

Privater Checkout:

```text
~/.local/share/adhs-lernpfad-sync/repo
```

Der Service setzt `ADHS_SYNC_NONINTERACTIVE=1`. `prompt-pull` kann deshalb nur bei einem manuellen Start tatsächlich fragen; im Timerlauf bricht er bei lokalen Änderungen ab.

## Deinstallation

```bash
./Sync/Linux/uninstall.sh
```

Optional:

```bash
./Sync/Linux/uninstall.sh --purge-config --remove-checkout
```

Der Vault wird auch mit diesen Optionen nicht gelöscht.

## Sicherheitsdetails

Der systemd-Service läuft mit `NoNewPrivileges`, privatem temporärem Verzeichnis, restriktiver Dateimaske und niedriger I/O-Priorität. `.obsidian/` und Syncthing-Metadaten bleiben standardmäßig lokal.

Weitere Einzelheiten: [[Sync/MODES|Modi]], [[Sync/CONFIGURATION|Konfiguration]] und [[Sync/TROUBLESHOOTING|Fehlersuche]].
