---
title: Windows-Synchronisierung
tags: [Wartung, Sync, Windows, PowerShell, Obsidian]
last_reviewed: 2026-07-15
hide: [navigation]
---

[↩️](../README.md "Zurück zur Sync-Übersicht")

# Windows-Synchronisierung

Windows verwendet eine native PowerShell-Engine, Git für Windows und Robocopy. Der private Checkout liegt unter `%LOCALAPPDATA%`; im sichtbaren Obsidian-Vault befinden sich nur Lern- und geschützte Gerätedateien.

## Dateien

- [PowerShell-Engine](Sync-ADHSLernpfad.ps1){ .md-button }
- [Installer](Install-ADHSLernpfadSync.ps1){ .md-button .md-button--primary }
- [Deinstaller](Uninstall-ADHSLernpfadSync.ps1){ .md-button }

## Voraussetzungen

- Windows PowerShell 5.1 oder PowerShell 7
- Git für Windows im `PATH`
- Robocopy, Bestandteil unterstützter Windows-Versionen

## Installation

Öffne PowerShell im geklonten Repository:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\Sync\Windows\Install-ADHSLernpfadSync.ps1
```

Standardwerte:

```text
Ziel:      %USERPROFILE%\Documents\Obsidian\ADHS-Lernpfad
Modus:     safe-pull
Intervall: 30 Minuten
```

## Beispiele

### Reiner Lesespiegel

```powershell
.\Sync\Windows\Install-ADHSLernpfadSync.ps1 `
  -Mode forced-pull `
  -Target "$HOME\Documents\Obsidian\ADHS-Lernpfad"
```

### Manuell und mit Rückfrage

```powershell
.\Sync\Windows\Install-ADHSLernpfadSync.ps1 -Mode prompt-pull -Manual
```

### Full Sync über Gerätebranch

```powershell
.\Sync\Windows\Install-ADHSLernpfadSync.ps1 `
  -Mode full-sync `
  -DeviceBranch 'sync/mein-windows-pc' `
  -AdoptExistingTarget
```

Git Credential Manager oder SSH muss den Push erlauben. Der Gerätebranch wird nicht automatisch nach `main` gemergt.

## Manuell ausführen

```powershell
& "$env:LOCALAPPDATA\ADHS-Lernpfad-Sync\Sync-ADHSLernpfad.ps1" `
  -Config "$env:LOCALAPPDATA\ADHS-Lernpfad-Sync\config.json"
```

## Aufgabenplanung

Der Installer registriert die Benutzeraufgabe **ADHS-Lernpfad Sync**. Sie startet bei der Anmeldung und danach im gewählten Intervall. Mehrfachstarts werden unterdrückt; zusätzlich verhindert ein benutzerspezifischer Mutex parallele Läufe.

Prüfen:

```powershell
Get-ScheduledTask -TaskName 'ADHS-Lernpfad Sync'
Get-ScheduledTaskInfo -TaskName 'ADHS-Lernpfad Sync'
```

## Deinstallation

```powershell
.\Sync\Windows\Uninstall-ADHSLernpfadSync.ps1
```

Optional:

```powershell
.\Sync\Windows\Uninstall-ADHSLernpfadSync.ps1 -PurgeConfig -RemoveCheckout
```

Der Vault wird niemals gelöscht.

## Technische Hinweise

Die PowerShell-Engine vergleicht Dateibäume über SHA-256-Hashes und verwendet Robocopy nur für die eigentliche Übertragung. Robocopy-Rückgabecodes ab 8 gelten als Fehler. `.obsidian`, Syncthing-Dateien und typische Windows-Metadaten bleiben standardmäßig lokal.

Weitere Einzelheiten: [[Sync/MODES|Modi]], [[Sync/CONFIGURATION|Konfiguration]] und [[Sync/TROUBLESHOOTING|Fehlersuche]].
