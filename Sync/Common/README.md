---
title: Gemeinsame Sync-Engine
tags: [Wartung, Sync, Bash, Architektur]
last_reviewed: 2026-07-15
hide: [navigation]
---

[↩️](../README.md "Zurück zur Sync-Übersicht")

# Gemeinsame Bash-Engine

`adhs-sync.sh` enthält die gemeinsame Logik für Linux, Android/Termux, macOS, BSD und iSH auf iOS/iPadOS. Das Skript wird normalerweise nicht direkt aus dem Repository gestartet, sondern durch den jeweiligen Plattforminstaller zusammen mit einem kleinen Wrapper installiert.

## Voraussetzungen

- Bash
- Git
- rsync
- `cksum`, `find`, `sed` und übliche Unix-Basiswerkzeuge

## Direkter Testlauf

```bash
ADHS_SYNC_REPO_DIR="$HOME/.local/share/adhs-sync/repo" \
ADHS_SYNC_TARGET_DIR="$HOME/Obsidian/ADHS-Lernpfad" \
ADHS_SYNC_MODE=safe-pull \
./Sync/Common/adhs-sync.sh
```

## Sicherheitsmodell

- Git arbeitet in einem privaten Checkout außerhalb des sichtbaren Vaults.
- Vor `safe-pull` und `prompt-pull` wird der Vault gegen den letzten privaten Stand verglichen.
- Vergleichsfehler von `rsync` werden als Fehler behandelt, nicht als „keine Änderungen“.
- Full Sync verlangt einen eigenen Gerätebranch und bricht bei gleichzeitigen lokalen und entfernten Änderungen ab.
- Nicht gepushte Full-Sync-Commits werden bei normalen Pull-Läufen nicht still verworfen.

Alle Variablen stehen unter [[Sync/CONFIGURATION|Konfiguration]].
