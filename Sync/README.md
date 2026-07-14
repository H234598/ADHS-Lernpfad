---
title: Synchronisierung
tags: [Wartung, Sync, Obsidian]
last_reviewed: 2026-07-14
hide: [navigation]
---

[↩️](../WARTUNG.md "Zurück zur Wartung")

# Synchronisierung

Dieser Bereich bündelt alle Wege, den ADHS-Lernpfad auf Geräte und in Obsidian-Vaults zu spiegeln. Die Lerninhalte bleiben dadurch von betriebssystemspezifischen Installationsdateien getrennt.

## Betriebssysteme

| System | Stand | Anleitung |
|---|---|---|
| Linux | produktiv: systemd-Benutzertimer und manuelle Ausführung | [[Sync/Linux/README|Linux]] |
| Android | produktiv: Termux, privater Git-Checkout und Vault-Spiegel | [[Sync/Android/README|Android]] |
| Windows | Struktur vorbereitet; Implementierung folgt in einem eigenen Plan | [[Sync/Windows/README|Windows]] |
| macOS | Struktur vorbereitet; Implementierung folgt in einem eigenen Plan | [[Sync/macOS/README|macOS]] |
| iPhone und iPad | Struktur vorbereitet; Implementierung folgt in einem eigenen Plan | [[Sync/iOS/README|iOS]] |
| BSD | Struktur vorbereitet; Implementierung folgt in einem eigenen Plan | [[Sync/BSD/README|BSD]] |

## Synchronisationsarten

Die gemeinsame Bedeutung der Modi steht unter [[Sync/MODES|Synchronisationsmodi]]. Nicht jeder Modus ist auf jedem System bereits implementiert.

> [!warning] Vor dem Wechsel des Modus sichern
> `forced-pull` verwirft lokale Änderungen an den gespiegelten Lerninhalten. Gerätespezifische Obsidian- und Syncthing-Dateien werden von den vorhandenen Linux- und Android-Skripten ausdrücklich ausgenommen.

## Grundprinzip

`main` ist der veröffentlichte, geprüfte Stand. Ein Pull-Skript darf deshalb keine unbeabsichtigten lokalen Änderungen zurück nach GitHub übertragen. Ein echter bidirektionaler Full Sync benötigt einen getrennten, später auszuarbeitenden Konflikt-, Authentifizierungs- und Review-Prozess.
