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
  - "2026-09-03: Aggregator veröffentlicht seinen Check explizit auf dem ausgewerteten PR-Head; Checks-Write ist auf diese Publikation begrenzt."
  - "2026-09-03: Rulesetmigration mit lokalem Exklusivlock und zweitem Live-Snapshot unmittelbar vor PUT gehärtet."
  - "2026-09-03: manual-merge-required als Deklaration von vertrauenswürdiger Human-Freigabe getrennt; sensible PRs bleiben bis zum expliziten workflow_dispatch fail-closed."
date: 2026-09-03
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

Der CodeRabbit-Custom-Check vergleicht ausschließlich den aktuellen PR-Diff mit der aktuellen Base. Historische Branch-Commits, Merge-Parents und gegenüber der Base unveränderte wissenschaftliche Dateien sind nicht Teil der Bewertung. Ist im aktuellen Diff keine Lernkarte und keine wissenschaftliche Begleitdatei betroffen, ist der Check explizit nicht anwendbar.

Bei anwendbarem Scope blockiert er insbesondere:

- entfernte oder verdrängte Lernziele;
- abgeschwächte Differentialabgrenzungen, Unsicherheiten oder Sicherheitsgrenzen;
- Assoziation-zu-Kausalität-Drift;
- Gruppenbefund-zu-Individualaussage-Drift;
- Überdehnung von Leitlinie, Konsens, Beobachtungsstudie oder RCT;
- unsichere Diagnose-, Dosis-, Wechsel-, Absetz-, Entzugs- oder Selbstbehandlungsanweisungen;
- fachlich korrekte, aber kartenfremde Schwerpunktverschiebung.

Fehlender Kontext ist kein Erfolg, sondern ein blockierender unklarer Befund.

### `claim-source-entailment`

Der zweite Custom-Check prüft ausschließlich wissenschaftliche Behauptungen, die im aktuellen PR-Diff tatsächlich verändert wurden, gegen die zitierte strukturierte Quellenkarte. Geprüft werden insbesondere:

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

Als sensitiv gelten insbesondere `.github/`, `automation/`, `prompts/`, `scripts/`, `.coderabbit.yaml`, `.codacy.yml`, Paket- und Requirementsdateien.

`<!-- manual-merge-required -->` ist **nur eine Deklaration**, dass sensible Infrastruktur betroffen ist. Der Marker ist PR-Inhalt und daher keine vertrauenswürdige Freigabe. Auf automatischen PR-, Review-, Kommentar- und `workflow_run`-Ereignissen bleibt `Learning card policy (blocking)` für sensible PRs fail-closed rot – auch wenn der Marker vorhanden ist.

Eine vertrauenswürdige Human-Freigabe kann ausschließlich über den auf `main` liegenden `workflow_dispatch` des Policy-Workflows erfolgen:

```text
pr_number: <PR>
manual_merge_authorized: true
```

Der Dispatch wird von einer Person mit Workflow-Schreibrecht ausgelöst und bewertet erneut den **aktuellen PR-Head**. Erst wenn Marker, Human-Freigabe und alle sonst anwendbaren Gates zusammenpassen, darf der aggregierte Check für diesen Head grün werden. Eine spätere PR-Änderung erzeugt einen neuen Head beziehungsweise neue Ereignisse und blockiert erneut, bis bewusst neu freigegeben wird.

Die bestehende Repositorypolicy verlangt anschließend weiterhin einen tatsächlichen menschlichen Merge; der Dispatch ist keine Auto-Merge-Erlaubnis.

### Lernkarte plus sensible Automation

Alle wissenschaftlichen Subgates müssen bestehen; zusätzlich gelten Deklarationsmarker und vertrauenswürdige Human-Freigabe. Der Merge bleibt manuell.

## Vertrauensmodell des Workflows

`.github/workflows/learning-card-policy.yml`:

- läuft ohne `paths:`-Filter für jeden relevanten PR-Zustand;
- nutzt `pull_request_target`, Review-, Kommentar-, `workflow_run`- und Dispatch-Ereignisse;
- checkt ausschließlich die Implementierung von `main` aus;
- verwendet `persist-credentials: false`;
- pinnt Drittanbieter-Actions kryptografisch auf vollständige Commit-SHAs;
- besitzt lesende Berechtigungen für Repository-/PR-/Issue-Daten;
- besitzt ausschließlich zusätzlich `checks: write`, um das aggregierte Ergebnis als GitHub-Check auf dem **ausgewerteten PR-Head** zu veröffentlichen;
- setzt `statuses: none` und besitzt keine Contents-/PR-/Issue-Schreibrechte;
- führt keinen PR-kontrollierten Code aus;
- veröffentlicht `Learning card policy (blocking)` explizit auf `pull_request.head.sha`, statt sich auf den Basis-SHA des `pull_request_target`-Workflowruns zu verlassen;
- behandelt `manual_merge_authorized` ausschließlich als vertrauenswürdigen booleschen `workflow_dispatch`-Input und übergibt ihn über eine Shell-Umgebungsvariable;
- speichert JSON- und Markdownberichte als Artefakt.

Der publizierte Check wird erst nach erneuter Prüfung von Head, Body, vollständigem Dateiscope und – bei semantischem Scope – nochmals frisch geladenen Check-Runs erzeugt. Bei einem Snapshotwechsel wird fail-closed ein blockierendes Ergebnis auf dem nun aktuellen Head veröffentlicht; ein veralteter Erfolg wird nicht übernommen.

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

`scripts/ruleset_migration.py` liest das Live-Ruleset, vergleicht kanonische SHA-256-Digests, erhält Bypass-Akteure, Branchbedingungen, alle nicht kontextbezogenen `required_status_checks`-Parameter und alle anderen Regeln. Die Reihenfolge von `bypass_actors` ist dabei semantisch irrelevant; verglichen wird ein reihenfolgeunabhängiges Multiset, während die Rohsnapshots unverändert protokolliert bleiben. Erlaubt ist nur der Austausch der drei Rohkontexte gegen den Aggregator.

Da GitHubs Ruleset-Update-API keinen dokumentierten serverseitigen `If-Match`-/Versions-Precondition-Write anbietet, erfolgt `--apply` bewusst nur in einem **exklusiven administrativen Änderungsfenster**. Zusätzlich serialisiert ein lokaler Interprozess-Lock konkurrierende Migrationen dieses Tools, und unmittelbar vor dem `PUT` wird ein zweiter Live-Snapshot gelesen und gegen den validierten Ausgangszustand verglichen. Jede erkannte Drift bricht fail-closed vor dem Schreibzugriff ab. Nach dem `PUT` wird der Vertrag erneut frisch gelesen und verifiziert.

`--apply` benötigt ein Administration-Write-Token. `--rollback --apply` verwendet denselben Lock-, Drift- und Digestschutz.

## Shadow-Abnahme

Vor der Rulesetumschaltung werden mindestens geprüft:

1. UI/Test-only → nicht anwendbar, grün;
2. geänderte oder neue Lernkarte → Semantik anwendbar;
3. Quellenkarte ohne Kapiteländerung → Semantik anwendbar;
4. Rename oder Löschung → Semantik anwendbar;
5. Marker ohne Karte → nicht anwendbar;
6. Karte ohne Marker → anwendbar, fail-closed;
7. Workflow-only ohne Human-Freigabe → manuell und rot;
8. Workflow-only mit Marker plus vertrauenswürdigem Dispatch → Policy kann auf exakt diesem Head grün werden, Merge bleibt manuell;
9. Karte plus Workflow → semantisch und manuell;
10. absichtlich roter Build → `complete_build` blockiert;
11. publizierter Aggregator-Check erscheint auf dem tatsächlichen PR-Head und nicht nur auf dem Basis-SHA des `pull_request_target`-Runs.

## Nicht verhandelbare Grenzen

- Der Router bewertet keine wissenschaftliche Wahrheit.
- Unklarheit erzeugt keinen Erfolg.
- Kein Required Workflow fällt durch Pfadfilter aus.
- Nur der aktuelle Head kann freigeben.
- Neutral oder skipped zählt für anwendbare Subgates nicht als Erfolg.
- Ein aktives CodeRabbit-`CHANGES_REQUESTED` bleibt blockierend.
- Der PR-Marker ist keine Human-Freigabe.
- Workflow- und Gateänderungen bleiben bis zum expliziten vertrauenswürdigen Dispatch blockiert und werden anschließend trotzdem manuell gemergt.
- Die Rulesetmigration erfolgt erst nach Merge und Shadow-Abnahme.
- Das Live-Ruleset wird nur in einem exklusiven administrativen Änderungsfenster geschrieben.

## Verknüpfungen

- [[MERGE-REPAIR-POLICY]]
- [[AUTOMATION-PROMPT]]
- [[PR-REPAIR-PROMPT]]
- `CodeRabbit hard gate`
- `Main - Required Gates`
