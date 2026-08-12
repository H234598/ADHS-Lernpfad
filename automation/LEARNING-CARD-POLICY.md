---
title: "Lernkarten-Policy: Anwendbarkeit, Semantik und Ruleset-Vertrag"
aliases:
  - "Learning Card Policy"
  - "Lernkarten-Gate-Router"
tags:
  - adhs-lernpfad
  - learning-card-policy
  - scientific-gates
  - github-ruleset
type: policy
status: in-review
updates:
  - "2026-08-12: Deterministischen Anwendbarkeitsrouter, semantische CodeRabbit-Prüfung und Buildaggregation implementiert."
  - "2026-08-12: Workflow- und Gatecode als orthogonale manuelle Sicherheitsklasse festgelegt."
date: 2026-08-12
created: 2026-08-12T20:22:24+02:00
---

# Lernkarten-Policy: Anwendbarkeit, Semantik und Ruleset-Vertrag

## Zweck

Die Policy trennt drei Aufgaben, die zuvor im Ruleset vermischt waren:

1. **Anwendbarkeit:** Ist eine Lernkarte oder ihre wissenschaftliche Grundlage betroffen?
2. **Semantik:** Bleiben Lernziel, Evidenzreichweite und Sicherheitsgrenzen erhalten?
3. **Reproduzierbarkeit:** Sind Validierung, Exporte und Review für denselben Head grün?

Der deterministische Router beantwortet ausschließlich die erste Frage. Er darf keine wissenschaftliche Richtigkeit behaupten.

```text
Learning card policy (blocking)
├── learning-card-applicability   deterministisch
├── content-scope                 semantisch
├── claim-source-entailment       semantisch
└── complete-build                deterministisch
```

## Deterministische Anwendbarkeit

### Direkte Lernkarten

Jede hinzugefügte, geänderte, umbenannte oder entfernte Markdown-Datei unter

```text
01-Grundlagen/
02-Vertiefung/
```

aktiviert die semantische Prüfung. Bei Renames werden `filename` und `previous_filename` geprüft; ein Verschieben aus dem Lernbaum umgeht die Policy nicht.

### Wissenschaftliche Begleitdaten

Auch diese Dateien aktivieren die Semantik:

```text
references/*.md
Glossar.md
Literatur.md
references.bib
references.json
cards/cards.yaml
```

`references/README.md` ist reine Repositorydokumentation und ausgenommen.

### Provenienz

```text
Branch: agent/einheit-*
Marker: <!-- adhs-daily-unit -->
```

sind dokumentierte Provenienzsignale, aber niemals die Schutzgrenze. Eine Lernkartenänderung ohne Marker bleibt geschützt; ein Marker ohne fachliche Änderung aktiviert keine Semantik.

## Semantische Subgates

### `content-scope`

Der CodeRabbit-Custom-Check vergleicht Basis, Head und Lernkontext. Er blockiert insbesondere:

- entfernte oder verdrängte Lernziele;
- abgeschwächte Differentialabgrenzungen, Unsicherheiten oder Sicherheitsgrenzen;
- Assoziation-zu-Kausalität-Drift;
- Gruppenbefund-zu-Individualaussage-Drift;
- Überdehnung von Leitlinie, Konsens, Beobachtungsstudie oder RCT;
- unsichere Diagnose-, Dosis-, Wechsel-, Absetz-, Entzugs- oder Selbstbehandlungsanweisungen;
- fachlich korrekte, aber kartenfremde Schwerpunktverschiebung.

Fehlender Kontext ist kein Erfolg, sondern ein blockierender unklarer Befund.

### `claim-source-entailment`

Der zweite Custom-Check prüft jede geänderte wissenschaftliche Behauptung gegen die tatsächlich zitierte strukturierte Quellenkarte, insbesondere:

- Population und Setting;
- Design und Evidenzart;
- Exposition, Intervention und Vergleich;
- Outcome und Effektmaß;
- Unsicherheit und Heterogenität;
- Kausalitätsrichtung;
- Publikations- und Aktualitätsstatus;
- Reichweite der Formulierung.

Eine Literaturangabe oder thematische Ähnlichkeit genügt nicht. Nicht zugängliche oder unzureichende Quelleninformation darf nicht als bestanden gelten.

### Technische Durchsetzung

`.coderabbit.yaml` aktiviert `request_changes_workflow` und zwei `mode: error`-Checks. Der Workflow `CodeRabbit hard gate` prüft zusätzlich den formellen Reviewzustand: Ein aktives `CHANGES_REQUESTED` blockiert auch bei einem separaten grünen Statussignal.

## Build-Subgate

`complete-build` ist nur erfolgreich, wenn auf demselben PR-Head beide echten Jobs erfolgreich abgeschlossen wurden:

```text
Validate and build
Build all download formats
```

Fehlend, ausstehend, neutral, übersprungen, abgebrochen, veraltet oder zeitüberschritten ist innerhalb einer anwendbaren Lernkartenpolicy kein Erfolg.

## PR-Klassen

### UI-, Navigation- oder Tests-only

```yaml
classification: not_applicable
requires_semantic_review: false
passed: true
```

Die allgemeinen Required Checks bleiben global aktiv.

### Lernkarte oder wissenschaftliche Begleitdatei

```yaml
requires_semantic_review: true
subgates:
  content_scope: success
  claim_source_entailment: success
  complete_build: success
```

### Workflow- oder Gatecode ohne Lernkarte

```yaml
classification: automation_only
requires_semantic_review: false
manual_merge_required: true
```

Als sensitiv gelten insbesondere `.github/`, `automation/`, `prompts/`, `scripts/`, `.coderabbit.yaml`, `.codacy.yml`, Paket- und Requirementsdateien. Fehlt `<!-- manual-merge-required -->`, blockiert die Policy. Mit Marker kann der Check grün werden; die bestehende Mergepolicy verbietet dennoch den automatischen Merge.

### Lernkarte plus sensible Automation

Alle wissenschaftlichen Subgates müssen bestehen; der Merge bleibt zusätzlich manuell.

## Vertrauensmodell des Workflows

`.github/workflows/learning-card-policy.yml`:

- läuft ohne `paths:`-Filter für jeden relevanten PR-Zustand;
- nutzt `pull_request_target`, Review-, Kommentar-, `workflow_run`- und Dispatch-Ereignisse;
- checkt ausschließlich die Implementierung von `main` aus;
- verwendet `persist-credentials: false`;
- besitzt nur lesende Berechtigungen;
- führt keinen PR-kontrollierten Code aus;
- liefert `Learning card policy (blocking)`;
- speichert JSON- und Markdownberichte als Artefakt.

## Ruleset-Zielvertrag

Nach Merge und bestandenem Shadow-Rollout verlangt `Main - Required Gates`:

```text
Validate and build
Build all download formats
Remark lint (blocking)
CodeRabbit review gate (blocking)
Learning card policy (blocking)
```

Ersetzt werden ausschließlich:

```text
content-scope
claim-source-entailment
complete-build
```

Die semantischen Funktionen bleiben innerhalb des Aggregators erhalten.

## Driftgeschützte Migration und Rollback

Versionierte Snapshots:

```text
automation/rulesets/main-required-gates.before.json
automation/rulesets/main-required-gates.target.json
```

`scripts/ruleset_migration.py` liest das Live-Ruleset, vergleicht kanonische SHA-256-Digests, erhält Bypass-Akteure, Branchbedingungen und alle anderen Regeln und erlaubt nur den Austausch der drei Rohkontexte gegen den Aggregator. `--apply` benötigt ein Administration-Write-Token; nach PUT wird der Vertrag frisch zurückgelesen. `--rollback --apply` verwendet denselben Drift- und Digestschutz.

```bash
python scripts/ruleset_migration.py --repository H234598/ADHS-Lernpfad

GITHUB_TOKEN='<Administration:write>' \
python scripts/ruleset_migration.py \
  --repository H234598/ADHS-Lernpfad \
  --ruleset-id 20499620 \
  --apply
```

Rollback:

```bash
GITHUB_TOKEN='<Administration:write>' \
python scripts/ruleset_migration.py \
  --repository H234598/ADHS-Lernpfad \
  --ruleset-id 20499620 \
  --rollback --apply
```

## Shadow-Abnahme

Vor der Rulesetumschaltung werden mindestens geprüft:

1. UI/Test-only → nicht anwendbar, grün;
2. geänderte oder neue Lernkarte → Semantik anwendbar;
3. Quellenkarte ohne Kapiteländerung → Semantik anwendbar;
4. Rename oder Löschung → Semantik anwendbar;
5. Marker ohne Karte → nicht anwendbar;
6. Karte ohne Marker → anwendbar, fail-closed;
7. Workflow-only → manuell;
8. Karte plus Workflow → semantisch und manuell;
9. absichtlich roter Build → `complete_build` blockiert.

## Nicht verhandelbare Grenzen

- Der Router bewertet keine wissenschaftliche Wahrheit.
- Unklarheit erzeugt keinen Erfolg.
- Kein Required Workflow fällt durch Pfadfilter aus.
- Nur der aktuelle Head kann freigeben.
- Neutral oder skipped zählt für anwendbare Subgates nicht als Erfolg.
- Ein aktives CodeRabbit-`CHANGES_REQUESTED` bleibt blockierend.
- Workflow- und Gateänderungen bleiben manuell.
- Die Rulesetmigration erfolgt erst nach Merge und Shadow-Abnahme.

## Verknüpfungen

- [[MERGE-REPAIR-POLICY]]
- [[AUTOMATION-PROMPT]]
- [[PR-REPAIR-PROMPT]]
- `CodeRabbit hard gate`
- `Main - Required Gates`
