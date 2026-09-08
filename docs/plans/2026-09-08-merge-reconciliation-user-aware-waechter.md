---
title: "ADHS-Lernpfad – Merge-Reconciliation und user-aware Wächter – Implementierungsplan"
aliases:
  - "ADHS Merge Reconciliation Plan"
  - "User-aware Merge-Wächter"
tags:
  - adhs-lernpfad
  - automation
  - github-actions
  - merge-watcher
  - reconciliation
  - coderabbit
  - learning-card-policy
  - tdd
type: plan
status: in-progress
updates:
  - "2026-09-08: Plan nach sichtbar gewordenem Out-of-band-Merge-Drift erstellt."
date: 2026-09-08
created: 2026-09-08T12:49:26+02:00
---

# ADHS-Lernpfad Merge-Reconciliation Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die Automationskette erkennt Nutzer-/Out-of-band-Eingriffe an Einheiten-PRs, reconciliert geschlossene oder gemergte PRs CAS-sicher in denselben Generatorlauf und verhindert, dass technische Gate-Races fachliche Fehler vortäuschen oder Einheit 22 unnötig blockieren.

**Architecture:** Eine vertrauenswürdige Reconciliation-Schicht wird zwischen GitHub-PR-Zustand und persistentem `automation-status` ergänzt. Ein `pull_request_target: closed`-Workflow lädt ausschließlich Code aus `main`, verifiziert PR/Head/Base/Marker/Gates und schreibt anschließend denselben Generatorlauf über den vorhandenen CAS-Statusmechanismus fort. CodeRabbit publiziert seinen aggregierten Required Check explizit auf dem ausgewerteten PR-Head; die Gate-Workflows werden pro PR serialisiert statt laufende gültige Checks gegenseitig abzubrechen.

**Tech Stack:** Python 3.12/stdlib, GitHub REST API, GitHub Actions YAML, bestehende `scripts/automation_status.py`-State-Machine, pytest, bestehende Learning-Card-/CodeRabbit-Gates.

## Global Constraints

- Keine direkte Änderung auf `main`; eigener Arbeitsbranch und Pull Request.
- Änderungen an `.github/`, `automation/`, `prompts/` und `scripts/` sind sensible Infrastruktur und erhalten `<!-- manual-merge-required -->`.
- Kein PR-Code wird in `pull_request_target` ausgeführt; Implementierung wird aus `main` geladen.
- Derselbe vorhandene Generator-`run_id` wird reconciliert; nie ein paralleler Ersatzstatus.
- Jede Statusmutation liest die aktuelle Revision und benutzt CAS/`expected_revision`; fremde neuere Revisionen werden nie überschrieben.
- Ein bereits gemergter PR mit nicht nachweislich grünen Gates wird nicht als Erfolg umetikettiert, sondern bleibt fail-closed/blockiert.
- Ein geschlossener, nicht gemergter automatischer Unit-PR wird als Nutzereingriff erkannt und blockiert neue Inhalte, bis der Zustand bewusst behandelt wurde.
- Ein sauber reconciliertes `success / complete` entsperrt den nächsten normalen Generatorlauf automatisch; keine manuelle „E22-Freigabe“.
- TDD: Verhaltensänderungen erhalten zuerst einen reproduzierbar roten Test, danach die minimale Implementierung.
- `CNAME` und Lerninhalte bleiben unberührt.

---

## Umsetzungsmilestones

1. Reine Reconciliation-Entscheidung für geschlossene/gemergte Unit-PRs mit Tests.
2. CAS-sichere Fortschreibung desselben Generatorlaufs bis `complete/success` oder fail-closed `blocked`.
3. Vertrauenswürdiger `pull_request_target: closed`-Workflow mit separatem `automation-status`-Worktree.
4. CodeRabbit-Gate explizit auf `pull_request.head.sha` publizieren; `cancel-in-progress`-Race beseitigen.
5. Learning-Card-Diagnose trennt formales Review-Gate von fachlichen Subgates.
6. Merge-/Generator-Prompts und technische Policy um Out-of-band-Reconciliation erweitern; Baselines aktualisieren.
7. Vollständige relevante Test-/CI-Runde, CodeRabbit und manuelle sensible Infrastrukturfreigabe.

## Verhaltensvertrag

### Gemergter PR, Gates grün

`running/ready_for_review -> verify_second_ci -> merge -> cleanup -> success/complete`; Merge-Commit und Main-Nachweis werden als Artefakte registriert, `next_generator_blocked=false`.

### Gemergter PR, Gates nicht nachweislich grün

Kein nachträgliches Schönfärben: Status wird `blocked/manual_intervention`, der nächste Generatorlauf bleibt gesperrt.

### Geschlossener PR ohne Merge

Nutzereingriff wird explizit erkannt und als `blocked/manual_intervention` dokumentiert; keine neue Einheit entsteht stillschweigend.

### Fremder/anderer PR oder finaler Lauf

Keine Mutation.

## Gate-Orchestrierung

- Required Checks: `Validate and build`, `Build all download formats`, `Remark lint (blocking)`, `CodeRabbit review gate (blocking)`, `Learning card policy (blocking)`.
- Für Reconciliation nach Ready müssen die relevanten zweiten Läufe zeitlich nach `recovery_ready_for_review_at` liegen.
- `CodeRabbit review gate (blocking)` wird explizit auf dem ausgewerteten PR-Head publiziert.
- Gate-Workflows werden pro PR serialisiert (`cancel-in-progress: false`) und prüfen vor Publikation erneut den aktuellen Head.
- Learning-Card-Policy bleibt fail-closed, bezeichnet einen abgebrochenen Reviewtransport aber nicht mehr als eigenständigen wissenschaftlichen Content-/Entailment-Fehler.

## Validierung

Mindestens:

```bash
python -m pytest -q \
  tests/test_unit_pr_reconciliation.py \
  tests/test_unit_pr_reconciliation_workflow.py \
  tests/test_review_gate.py \
  tests/test_review_policy_files.py \
  tests/test_learning_card_policy.py \
  tests/test_learning_card_policy_files.py \
  tests/test_automation_status.py \
  tests/test_runtime_status_cli.py
```

Anschließend vollständige Repository-CI.

## Sicherheitsabschluss

Der PR ist sensible Infrastruktur und bleibt bis zur expliziten vertrauenswürdigen Human-Freigabe fail-closed. Chat-Zustimmung ersetzt nicht den dafür vorgesehenen GitHub-Workflow-Dispatch.
