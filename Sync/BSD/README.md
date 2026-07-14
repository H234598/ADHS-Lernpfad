---
title: BSD-Synchronisierung
tags: [Wartung, Sync, BSD]
last_reviewed: 2026-07-14
hide: [navigation]
---

[↩️](../README.md "Zurück zur Sync-Übersicht")

# BSD-Synchronisierung

Die Ordnerstruktur ist vorbereitet. Ein produktives Paket für die BSD-Familie wird später als eigener Teil des plattformübergreifenden Sync-Plans entwickelt.

## Vorgesehene Punkte

- portable POSIX- beziehungsweise Shell-Basis
- regelmäßige Ausführung über den jeweiligen Systemdienst oder Zeitplaner
- klare Auswahl zwischen `safe-pull`, `prompt-pull`, `forced-pull` und einem späteren `full-sync`
- dokumentierte Abweichungen zwischen den unterstützten BSD-Systemen
- Installations-, Diagnose- und Deinstallationsweg

Die gemeinsame Modusdefinition steht unter [[Sync/MODES|Synchronisationsmodi]].

> [!info]
> Noch keine ausführbaren Dateien: Die spätere Umsetzung soll portabel getestet werden und keine Linux-spezifischen Annahmen verstecken.
