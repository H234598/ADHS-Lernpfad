# Generatorstatus – Einheit 20 – Revision 15

## Zustand

- Run-ID: `e55d7dcb-2e86-4b6a-822e-b67262473bcb`
- Status: `success`
- Phase: `complete`
- PR: `#50`
- Branch: `agent/einheit-20-substanzgebrauch-abhaengigkeit`
- finaler PR-Head: `daad16b1ee45c1ed2523dab48548c3a2f386506e`
- Squash-Merge-Commit: `999cc6e2b75e69831eff3e5aeddb67f0358edd06`
- aktueller `main`: `999cc6e2b75e69831eff3e5aeddb67f0358edd06`
- neue Einheit erforderlich: `nein`
- nächster Generatorlauf blockiert: `nein`

## Abschluss

Einheit 20 wurde nach der Synchronisation mit dem aktuellen `main` durch zwei
vollständige reguläre CI-/CodeRabbit-Zyklen geführt und anschließend per
Squash-Merge integriert.

### Erster Zyklus

- Validate compendium: `success` – Run `33713568051`
- Build all download formats: `success`
- Remark lint: `success` – Run `33713568060`
- Codacy Security Scan: `success` – Run `33713568054`
- CodeRabbit: `success`
- qlty: `success`
- CodeRabbit review gate (blocking): `success` – Run `33713565290`, Attempt 2
- ungelöste CodeRabbit-Threads: `0`
- CodeRabbit-Dissens: `nein`

Danach wurde PR #50 von Draft auf Ready for review gesetzt.

### Zweiter Zyklus

- Validate compendium: `success` – Run `33750957382`
- Validate and build: `success`
- Build all download formats: `success`
- Remark lint: `success` – Run `33750957286`
- CodeRabbit review gate (blocking): `success` – Run `33750957824`, Attempt 2
- CodeRabbit direkter Status auf unverändertem Head: `success`
- qlty direkter Status auf unverändertem Head: `success`
- ungelöste CodeRabbit-Threads: `0`
- CodeRabbit-Dissens: `nein`

Codacy wird durch `ready_for_review` nicht erneut ausgelöst; der erfolgreiche
erste Codacy-Zyklus gehört zum selben unveränderten Head.

## Merge

- Methode: `squash`
- erwarteter Head: `daad16b1ee45c1ed2523dab48548c3a2f386506e`
- Merge-Commit: `999cc6e2b75e69831eff3e5aeddb67f0358edd06`
- Mergezeitpunkt: `2026-09-03T11:46:14Z`
- PR geschlossen und gemergt: `ja`
- `main` zeigt auf den Merge-Commit: `ja`

## Endzustand

Der Generatorlauf ist abgeschlossen. `error` und `recovery` sind `null`.
Einheit 21 ist durch diesen Lauf nicht mehr blockiert.
