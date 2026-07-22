---
title: Android-Synchronisierung
tags: [Wartung, Sync, Android, Termux, Obsidian]
last_reviewed: 2026-07-15
hide: [navigation]
---

[↩️](../README.md "Zurück zur Sync-Übersicht")

# Android-Synchronisierung mit Termux

Das Android-Paket hält Git in einem privaten Termux-Verzeichnis und spiegelt nur die Lerninhalte in den frei zugänglichen Obsidian-Vault. Dadurch landen weder `.git` noch Zugangsdaten im gemeinsamen Android-Speicher.

## Dateien

- [Termux-Installer](install-termux.sh){ .md-button .md-button--primary }
- [Sync-Wrapper](sync-termux.sh){ .md-button }
- [Deinstaller](uninstall-termux.sh){ .md-button }
- [gemeinsame Engine](../Common/adhs-sync.sh){ .md-button }

## Voraussetzungen

Installiere eine aktuelle Termux-Version und erlaube den Speicherzugriff:

```bash
termux-setup-storage
```

Der Installer installiert `git` und `rsync` über `pkg`.

## Standardinstallation als Lesespiegel

```bash
git clone https://github.com/H234598/ADHS-Lernpfad.git
cd ADHS-Lernpfad
./Sync/Android/install-termux.sh --mode forced-pull
```

Standardziel:

```text
/storage/emulated/0/Documents/Obsidian/ADHS-Lernpfad
```

Privater Checkout:

```text
$HOME/.local/share/adhs-lernpfad-sync/repo
```

## Beispiele

### Lokale Änderungen schützen

```bash
./Sync/Android/install-termux.sh --mode safe-pull
```

### Vor Überschreiben fragen

```bash
./Sync/Android/install-termux.sh --mode prompt-pull
```

Die Rückfrage funktioniert nur bei manueller Ausführung. Ein Bootlauf bricht bei lokalen Änderungen ab.

### Nur fehlende Dateien ergänzen

```bash
./Sync/Android/install-termux.sh --mode additive-pull
```

Dieser Modus hält vorhandene Dateien bewusst unverändert; sie können deshalb veralten.

### Full Sync über Gerätebranch

```bash
./Sync/Android/install-termux.sh \
  --mode full-sync \
  --device-branch sync/mein-android-tablet \
  --adopt-existing-target
```

Für den Push muss Git in Termux bereits per SSH oder sicherem Credential-Mechanismus authentifiziert sein. Der Gerätebranch wird nicht automatisch nach `main` gemergt.

## Optionaler Start mit Termux:Boot

```bash
./Sync/Android/install-termux.sh --mode forced-pull --boot
```

Das erzeugte Bootskript wartet 60 Sekunden und startet anschließend nichtinteraktiv. Android kann Hintergrundausführung trotzdem verzögern oder durch Energiesparregeln verhindern; der manuelle Befehl bleibt daher wichtig.

## Manuell ausführen

```bash
adhs-lernpfad-sync
```

## Deinstallation

```bash
./Sync/Android/uninstall-termux.sh
```

Optional:

```bash
./Sync/Android/uninstall-termux.sh --purge-config --remove-checkout
```

Der sichtbare Vault wird niemals entfernt.

## Geschützte Gerätedateien

Standardmäßig erhalten bleiben `.obsidian/`, `.stfolder`, `.stignore`, `.nomedia`, `.trash/` und typische Plattformmetadaten. Normale Markdown-, Bild- und Literaturdateien sind bei `forced-pull` nicht geschützt.

Weitere Einzelheiten: [[Sync/MODES|Modi]], [[Sync/CONFIGURATION|Konfiguration]] und [[Sync/TROUBLESHOOTING|Fehlersuche]].
