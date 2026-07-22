---
title: Sync-Fehlersuche
tags: [Wartung, Sync, Diagnose]
last_reviewed: 2026-07-15
hide: [navigation]
---

[↩️](README.md "Zurück zur Sync-Übersicht")

# Fehlersuche

## Diagnose in sinnvoller Reihenfolge

1. Prüfe, ob Git, rsync beziehungsweise PowerShell verfügbar sind.
2. Starte den Sync einmal manuell im Terminal.
3. Prüfe Modus, Zielpfad und privaten Checkout in der Konfiguration.
4. Lies den plattformspezifischen Zeitplanerstatus und das Log.
5. Führe erst danach einen erzwungenen Pull aus.

## Häufige Rückgabecodes

| Code | Bedeutung |
|---:|---|
| `0` | erfolgreich oder anderer Lauf bereits aktiv |
| `4` | lokale Abweichung oder fehlende interaktive Bestätigung |
| `6` | vorhandener Vault beim ersten Full Sync nicht ausdrücklich übernommen |
| `7` | Full-Sync-Divergenz oder Git-Konfliktzustand |
| `8` | Push des Gerätebranches fehlgeschlagen; lokaler Commit bleibt erhalten |
| `9` | nicht gepushte Commits blockieren den Wechsel in einen Pull-Modus |
| `64` | ungültige Konfiguration oder nicht unterstützter Modus |
| `65` | privater Checkoutpfad ist kein Git-Repository |
| `66` | konfigurierte Ausschlussdatei fehlt |
| `127` | erforderliches Programm fehlt |

## `safe-pull` bricht ab

Das ist kein Fehler des Sicherheitsmechanismus, sondern sein Zweck. Der Vault weicht vom letzten privaten Checkout ab. Starte manuell und prüfe die angezeigten rsync-Zeilen. Danach stehen drei bewusste Entscheidungen offen:

- Änderungen anderweitig sichern und `forced-pull` verwenden,
- bei einem Arbeitsvault auf einen Gerätebranch mit `full-sync` wechseln,
- lokale Änderungen zurücknehmen und erneut `safe-pull` ausführen.

## `prompt-pull` fragt im Zeitplaner nicht

Zeitplaner laufen ohne interaktives Terminal. Deshalb bricht `prompt-pull` dort ab. Die Rückfrage ist nur bei einer manuellen Ausführung möglich.

## Full Sync meldet Divergenz

Vault und Remote-Gerätebranch wurden beide seit dem letzten gemeinsamen Stand verändert. Das Skript nimmt absichtlich keine automatische Gewinnerseite an.

```bash
cd /pfad/zum/privaten/checkout
git status
git log --oneline --graph --decorate --all -n 30
```

Sichere den Vault, löse die Unterschiede bewusst im privaten Checkout, committe und pushe den Gerätebranch. Danach kann der normale Lauf fortgesetzt werden.

## Push schlägt fehl

Der lokale Commit bleibt im privaten Checkout erhalten. Prüfe:

- Schreibrecht auf das Repository,
- SSH-Schlüssel oder Credential Manager,
- Branchschutz für den Gerätebranch,
- Netzwerkverbindung,
- `git status` und `git log` im privaten Checkout.

## Vault ist für Obsidian nicht sichtbar

Auf Android und iOS muss der Zielpfad im für andere Apps freigegebenen Speicher liegen. Der private Git-Checkout darf dagegen im App-internen Speicher verbleiben.

## Geschützte Dateien fehlen

Standardmäßig geschützt sind `.obsidian/`, `.stfolder`, `.stignore`, `.nomedia`, `.trash/`, `.DS_Store`, `Thumbs.db` und `desktop.ini`. Setze `ADHS_SYNC_PROTECT_OBSIDIAN=0` nur bewusst, wenn Obsidian-Einstellungen tatsächlich über den Gerätebranch synchronisiert werden sollen.

## Neuinstallation

Deinstalliere zunächst nur Zeitplaner und Programmdateien. Vault und privater Checkout bleiben standardmäßig erhalten. Dadurch kann nach einer Neuinstallation der bisherige Zustand geprüft und weiterverwendet werden.
