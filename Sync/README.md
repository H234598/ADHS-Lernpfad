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
| Linux | produktiv: systemd-Benutzertimer und manuelle Ausführung | [Linux](Linux/README.md) |
| Android | produktiv: Termux, privater Git-Checkout und Vault-Spiegel | [Android](Android/README.md) |
| Windows | Struktur vorbereitet; Implementierung folgt in einem eigenen Plan | [Windows](Windows/README.md) |
| macOS | Struktur vorbereitet; Implementierung folgt in einem eigenen Plan | [macOS](macOS/README.md) |
| iPhone und iPad | Struktur vorbereitet; Implementierung folgt in einem eigenen Plan | [iOS](iOS/README.md) |
| BSD | Struktur vorbereitet; Implementierung folgt in einem eigenen Plan | [BSD](BSD/README.md) |

## Synchronisationsarten

Die gemeinsame Bedeutung der Modi steht unter [[Sync/MODES|Synchronisationsmodi]]. Nicht jeder Modus ist auf jedem System bereits implementiert.

> [!warning] Vor dem Wechsel des Modus sichern
> `forced-pull` verwirft lokale Änderungen an den gespiegelten Lerninhalten. Gerätespezifische Obsidian- und Syncthing-Dateien werden von den vorhandenen Linux- und Android-Skripten ausdrücklich ausgenommen.

## Grundprinzip

`main` ist der veröffentlichte, geprüfte Stand. Ein Pull-Skript darf deshalb keine unbeabsichtigten lokalen Änderungen zurück nach GitHub übertragen. Ein echter bidirektionaler Full Sync benötigt einen getrennten, später auszuarbeitenden Konflikt-, Authentifizierungs- und Review-Prozess.
