---
title: Sync-Konfiguration
tags: [Wartung, Sync, Konfiguration]
last_reviewed: 2026-07-15
hide: [navigation]
---

[↩️](README.md "Zurück zur Sync-Übersicht")

# Konfiguration

Die Installer erzeugen eine Konfigurationsdatei mit sicheren Standardwerten. Linux, Android, macOS, BSD und iSH verwenden Shellvariablen; Windows verwendet JSON mit denselben Bedeutungen.

## Zentrale Einstellungen

| Shellvariable | Windows-JSON | Bedeutung |
|---|---|---|
| `ADHS_SYNC_REPO_URL` | `RepoUrl` | Git-Repository |
| `ADHS_SYNC_REMOTE` | `Remote` | Git-Remote, normalerweise `origin` |
| `ADHS_SYNC_BASE_BRANCH` | `BaseBranch` | veröffentlichter Pull-Branch, normalerweise `main` |
| `ADHS_SYNC_REPO_DIR` | `RepoDir` | privater Git-Checkout |
| `ADHS_SYNC_TARGET_DIR` | `TargetDir` | sichtbarer Obsidian-Vault |
| `ADHS_SYNC_MODE` | `Mode` | Synchronisationsmodus |
| `ADHS_SYNC_DEVICE_BRANCH` | `DeviceBranch` | eigener Branch für `full-sync` |
| `ADHS_SYNC_NONINTERACTIVE` | `NonInteractive` | Rückfragen verbieten und sicher abbrechen |
| `ADHS_SYNC_PROTECT_OBSIDIAN` | `ProtectObsidian` | `.obsidian/` lokal belassen |
| `ADHS_SYNC_ADOPT_EXISTING_TARGET` | `AdoptExistingTarget` | vorhandenen Vault beim ersten Full Sync bewusst übernehmen |

## Beispiel für Pull-only

```bash
ADHS_SYNC_REPO_URL='https://github.com/H234598/ADHS-Lernpfad.git'
ADHS_SYNC_REMOTE='origin'
ADHS_SYNC_BASE_BRANCH='main'
ADHS_SYNC_REPO_DIR="$HOME/.local/share/adhs-lernpfad-sync/repo"
ADHS_SYNC_TARGET_DIR="$HOME/Dokumente/Obsidian/ADHS-Lernpfad"
ADHS_SYNC_MODE='safe-pull'
ADHS_SYNC_NONINTERACTIVE='1'
ADHS_SYNC_PROTECT_OBSIDIAN='1'
```

## Beispiel für Full Sync

```bash
ADHS_SYNC_MODE='full-sync'
ADHS_SYNC_DEVICE_BRANCH='sync/mein-laptop'
ADHS_SYNC_NONINTERACTIVE='1'
ADHS_SYNC_GIT_AUTHOR_NAME='Bernhard'
ADHS_SYNC_GIT_AUTHOR_EMAIL='adresse@example.invalid'
```

Der Gerätebranch muss Schreibzugriff erlauben. Zugangsdaten gehören nicht in diese Datei. Verwende stattdessen SSH-Schlüssel, Git Credential Manager oder den systemeigenen sicheren Credential-Speicher.

## Zusätzliche Ausschlüsse

Mit `ADHS_SYNC_EXCLUDE_FILE` kann eine rsync-kompatible Ausschlussliste angegeben werden:

```text
private-notes/
*.local.md
```

Solche Ausschlüsse sind lokale Sonderregeln. Sie können dazu führen, dass ein Vault nicht vollständig dem Remote-Stand entspricht, und sollten deshalb bewusst dokumentiert werden.

## Automatisierte Läufe

Zeitplaner setzen `ADHS_SYNC_NONINTERACTIVE=1`. Ein konfiguriertes `prompt-pull` verhält sich dann absichtlich wie ein sicherer Abbruch. Für unbeaufsichtigte reine Lesespiegel ist `forced-pull` geeignet; für Arbeitsvaults ist `safe-pull` die konservative Wahl.
