# Automatisierungsprompt: fehlgeschlagenen Einheiten-PR sicher reparieren

Dieser Prompt wird ausschließlich vom Merge-Wächter aufgerufen, wenn das Reparaturfenster erreicht ist und die CI eines automatischen Einheiten-Pull-Requests fehlgeschlagen ist oder CodeRabbit eine fachlich beziehungsweise technisch notwendige Korrektur verlangt. Standardmäßig beginnt das Reparaturfenster frühestens um **20:00 Uhr Europe/Berlin am Tag der PR-Erstellung**, niemals vor Ablauf der zweistündigen Reviewfrist.

**CodeRabbit ist ein verpflichtendes hartes Gate.** Eine Reparatur ist erst abgeschlossen, wenn die berechtigten Hinweise behoben, alle Threads nachvollziehbar abgeschlossen, die inkrementelle Prüfung des aktuellen Heads erfolgreich und Remark-lint grün ist.

Arbeite im Repository `H234598/ADHS-Lernpfad` und ausschließlich auf dem bereits bestehenden Head-Branch des betroffenen Pull Requests.

## 1. Ausgangslage und Reparaturberechtigung sichern

1. Ermittle PR-Nummer, Erstellungszeit, Head-Branch und aktuellen Head-Commit erneut.
2. Prüfe, dass der PR gegen `main` zielt, der Branch `agent/einheit-*` entspricht und `<!-- adhs-daily-unit -->` vorhanden ist.
3. Berechne `repair_eligible_at = max(created_at + 2 Stunden, 20:00 Europe/Berlin am Erstellungstag)`.
4. Vor dieser Frist nimmst du keine inhaltliche Änderung vor und meldest `wait_until_repair_window`.
5. Arbeite niemals direkt auf `main`, führe keinen Force-Push aus und erstelle keinen zweiten Einheitenbranch.
6. Prüfe unmittelbar vor Änderungen, dass der Head seit Beginn des Laufs unverändert ist.
7. Vergleiche den Fehlerfingerabdruck mit früheren Reparaturen. Erzeuge keinen identischen Wiederholungs- oder No-op-Commit.

## 2. Vollständige Diagnose

1. Lies vollständige Logs aller fehlgeschlagenen Checks und Workflow-Jobs des aktuellen Heads.
2. Bestimme die konkrete Grundursache, nicht bloß das letzte Folge-Gate.
3. Prüfe alle CodeRabbit-Signale:
   - Statuschecks und Check-Runs;
   - formelle Reviews;
   - PR-Kommentare;
   - Inline-Kommentare und Review-Threads.
4. Erfasse **jeden** CodeRabbit-Thread in einer Reparaturmatrix mit:
   - Thread-ID und Datei;
   - Schweregrad und Behauptung;
   - Gültigkeit am aktuellen Head;
   - geplanter Änderung oder überprüfbarer Obsoleszenzbegründung;
   - Prüfnachweis;
   - Auflösungsstatus.
5. Auch veraltete Threads bleiben blockierend, bis sie nachvollziehbar abgeschlossen sind.
6. Lies den Remark-lint-Bericht beziehungsweise führe den reproduzierbaren lokalen Check aus. Ein grüner Codacy-SARIF-Upload ersetzt Remark-lint nicht.

## 3. Wissenschaftliche Evidenz aktualisieren

Bei jedem Hinweis zu Aktualität, Evidenz, Risiko, Kausalität, Leitlinien oder `last_reviewed` gilt zusätzlich:

1. Lies `prompts/DEEP-RESEARCH-PROMPT.md` vollständig und führe die einschlägige Recherche erneut bis zum aktuellen Datum aus.
2. Suche mindestens nach neueren Leitlinien, Konsenspapiere, systematischen Reviews, Meta-Analysen und relevanten großen Primärstudien seit der zuletzt verwendeten Kernquelle.
3. Trenne unterschiedliche Endpunkte ausdrücklich, beispielsweise Demenz aller Ursachen, einzelne Demenzformen und Parkinson-Inzidenz.
4. Trenne relative Gruppenmaße, absolute Risiken, Kausalität und individuelle Prognose.
5. Aktualisiere den Text, Frontmatter-Referenzen und strukturierte Studienkarten gemeinsam.
6. Setze `last_reviewed` nur dann auf das aktuelle Datum, wenn die Evidenz tatsächlich neu geprüft wurde.
7. Erfinde keine bibliografischen Angaben. Unvollständige Daten werden als solche gekennzeichnet.
8. Erzeuge danach `Literatur.md`, `references.bib` und `references.json` ausschließlich mit `scripts/build_literature.py` neu.

## 4. Threads bearbeiten und Dissens behandeln

Für jeden CodeRabbit-Thread gilt genau eine der folgenden Kategorien:

### A. Gültiger Hinweis

- Behebe die Ursache minimal, vollständig und ohne Validierung abzuschwächen.
- Führe passende Tests aus.
- Antworte mit Ursache, Änderung und Prüfnachweis.
- Löse den Thread erst nach der verifizierten Änderung auf.

### B. Durch aktuellen Diff gegenstandsloser Hinweis

- Prüfe, dass die betroffene Datei oder Logik wirklich nicht mehr im aktuellen PR-Diff vorkommt.
- Dokumentiere diese Prüfung mit aktuellem Head und konkreter Dateiliste.
- Löse den Thread mit dieser überprüfbaren Begründung auf.

### C. Fachlicher oder technischer Dissens

- Löse den Thread **nicht** einseitig auf.
- Schreibe einen strukturierten PR-Kommentar:

  ```html
  <!-- coderabbit-disagreement head=<CURRENT_HEAD_SHA> -->
  ```

- Nenne CodeRabbit-Behauptung, eigene Gegenposition, Quellen oder Codebelege, verbleibende Unsicherheit und benötigte menschliche Entscheidung.
- Setze Recovery auf `manual_intervention` und beende den Reparaturzyklus als harten Blocker.
- Erst nach CodeRabbit-Akzeptanz oder menschlicher Entscheidung darf der Konflikt mit `<!-- coderabbit-disagreement-resolved head=<CURRENT_HEAD_SHA> -->` abgeschlossen werden.

## 5. Sichere Reparatur

1. Behebe alle eindeutig zusammenhängenden Fehler in einem konsistenten Zyklus.
2. Verändere Prompts, Workflows, Requirements, Validatoren oder Sicherheitsinfrastruktur nur, wenn die Ursache nachweislich dort liegt und keine engere Lösung existiert. Füge dann `<!-- manual-merge-required -->` hinzu.
3. Repariere Obsidian-Wikilinks in den Quelldateien; erzeuge keine parallelen manuellen HTML-Linkvarianten.
4. Vermeide destruktive Vollersetzungen: Lade vollständige Dateien und pflege Ergänzungen additiv ein.
5. Verwende für temporäre Logs und Artefakte ausschließlich `$RUNNER_TEMP`, `tempfile` oder ein nicht getracktes Verzeichnis außerhalb des Worktrees.
6. Verwende kein blindes `git add -A`. Prüfe `git status --short`, stage eine explizite Allowlist beabsichtigter Dateien und kontrolliere `git diff --cached`.
7. Falls ein Git-Befehl einen Commit erzeugen kann, konfiguriere `user.name` und `user.email` **vor** diesem Befehl.
8. Entferne einmalige Reparaturworkflows und Reparaturskripte vor dem endgültigen Commit, sofern sie nicht als allgemein getestete Infrastruktur nach `main` gehören.

## 6. Verbindliche lokale Prüfung

Führe nach der Reparatur vollständig aus:

```bash
python -m pip install --disable-pip-version-check \
  -r requirements-docs.txt -r requirements-export.txt
python -m pip check
npm ci

REMARK_BASE_SHA="origin/main" REMARK_HEAD_SHA="HEAD" \
  npm run lint:markdown:changed

python -m compileall -q scripts tests
python scripts/validate_prompt_baselines.py
python -m pytest -q
npm test

python scripts/build_literature.py
git diff --exit-code -- Literatur.md references.bib references.json
python scripts/validate_links.py
python scripts/build_graph.py
python scripts/validate_graph.py
python scripts/validate_compendium.py
python scripts/build_combined.py
python scripts/build_anki.py
python scripts/build_docs.py
mkdocs build --strict
npm run test:web
```

Alle Prüfungen müssen erfolgreich sein. Kontrolliere zusätzlich:

- keine fremden oder temporären Dateien im Diff;
- keine versehentlichen Löschungen bestehender Karten, Glossarbegriffe oder Indexeinträge;
- keine unbekannten Änderungen außerhalb der Reparatur- allowlist;
- `Remark lint (blocking)` ist reproduzierbar grün.

## 7. Commit, Push und erneute Review

1. Committe ausschließlich die Reparatur auf dem bestehenden PR-Branch.
2. Verwende eine sachliche Nachricht wie `fix: repariere Review und CI für Einheit NN`.
3. Pushe normal zu `origin`; kein Force-Push.
4. Ergänze im PR:
   - Grundursache;
   - geänderte Dateien;
   - Evidenzrecherche und neue Quellen;
   - Thread-Matrix und Auflösungsbegründungen;
   - Remark-lint-Ergebnis;
   - vollständige lokale Prüfungen;
   - neuen Head-Commit.
5. Warte auf die inkrementelle CodeRabbit-Prüfung des neuen Heads.
6. Markiere den PR in diesem Lauf nicht Ready for review und merge nicht.
7. Der nächste Merge-Wächter-Lauf verlangt gleichzeitig:
   - aktuelle CI grün;
   - `Remark lint (blocking)` grün;
   - CodeRabbit-Signal grün;
   - keine ungelösten CodeRabbit-Threads;
   - kein ungeklärter Dissens.

## 8. Wiederholte Reparaturen

1. Es gibt keine starre Grenze von zwei roten CI-Läufen.
2. Pro Wächterlauf ist genau ein sicherer Reparaturzyklus zulässig.
3. Neue oder veränderte Fehlerfingerabdrücke dürfen in späteren Läufen erneut repariert werden.
4. Ein identischer Fehler ohne neue Diagnose darf keinen wiederholten identischen Commit erzeugen.
5. Transiente externe Fehler verwenden `retry_same_phase`; vorhandene Branches, Commits oder PRs werden mit `resume_from_artifact` weiterverwendet.
6. Nicht eindeutige wissenschaftliche oder sicherheitsrelevante Konflikte verwenden `manual_intervention`.

## 9. Nicht automatisch reparierbare Fälle

Nimm keine spekulativen Änderungen vor, wenn:

- Ursache nicht sicher bestimmbar ist;
- Zugangsdaten, externe Dienste oder Repository-Einstellungen fehlen;
- die Reparatur eine wissenschaftlich unsichere Behauptung erzwingen würde;
- Branch oder PR parallel verändert wurden;
- Agent und CodeRabbit nicht zu einer belastbaren Einigung kommen;
- eine Sicherheitsentscheidung menschliche Freigabe benötigt.

Lasse den PR offen und melde PR, Head, fehlgeschlagenen Check, Thread-IDs, relevante Logstellen, Dissens und konkreten nächsten Schritt.

## 10. Recovery-Status

1. Verwende den zu diesem PR gehörenden Generatorlauf auf `automation-status`; lege keinen unabhängigen fachlichen Lauf an.
2. Prüfe Branch, Head, PR, Run-/Job-IDs, Recovery-Level und `revision`.
3. Lies vor jeder schreibenden Statusoperation `REVISION` frisch ein und verwende sie genau einmal als `--expected-revision`. Exitcode `20` beendet den Versuch ohne Überschreiben.
4. Beginne mit:

   ```bash
   python scripts/automation_status.py recover \
     --workflow generator --run-id "$RUN_ID" --phase repair \
     --expected-revision "$REVISION"
   ```

5. Registriere Logs, Remark-Bericht, Review-Gate-Bericht und Reparaturcommit als strukturierte Artefakte.
6. Nach erfolgreicher Reparatur geht der Lauf zurück auf `running`, Phase `wait_review`; Gesamterfolg entsteht erst nach Merge und Cleanup.
7. Kann der Statusbranch nicht aktualisiert werden, gib den vollständigen Diagnoseblock aus `prompts/AUTOMATION-PROMPT.md` im PR und in der Benutzerbenachrichtigung aus. Der Statusfehler darf die eigentliche Ursache nicht verdecken.
