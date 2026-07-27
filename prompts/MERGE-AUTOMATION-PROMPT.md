# Automatisierungsprompt: Draft-Prüfung, verzögerte Reparatur und Merge

Dieser Prompt wird durch einen getrennten, wiederkehrenden Merge-Wächter ausgeführt. Der Wächter prüft einen automatisch erzeugten Einheiten-PR frühestens zwei Stunden nach seiner Erstellung und danach regelmäßig weiter. **CodeRabbit ist ein verpflichtendes hartes Gate.** Ein fehlendes, ausstehendes oder fehlgeschlagenes CodeRabbit-Signal, ein ungelöster CodeRabbit-Thread oder ein ungeklärter Dissens zwischen Agent und CodeRabbit verhindert Ready for review und Merge.

Der Reparaturzyklus beginnt nicht sofort nach einer roten CI. Er darf frühestens um **20:00 Uhr Europe/Berlin am Kalendertag der PR-Erstellung** starten; bei einer PR-Erstellung nach 18:00 Uhr gilt zusätzlich die vollständige zweistündige Reviewfrist. Bis zu diesem Zeitpunkt bleibt der Merge-Wächter aktiv, sammelt Diagnosen und prüft bei jedem Lauf erneut. Es gibt keinen Abbruch nach dem zweiten roten CI-Lauf.

Arbeite im Repository `H234598/ADHS-Lernpfad`.

## 1. Geeigneten Pull Request bestimmen

1. Suche offene Pull Requests gegen `main`, deren Head-Branch dem Muster `agent/einheit-*` entspricht und deren Beschreibung den Marker `<!-- adhs-daily-unit -->` enthält.
2. Falls kein geeigneter PR vorhanden ist, beende den Lauf ohne Benachrichtigung.
3. Falls mehrere geeignete PRs vorhanden sind, verändere keinen davon und melde den Mehrdeutigkeitsfehler als harten Blocker.
4. Arbeite ausschließlich mit dem eindeutig bestimmten PR und seinem aktuellen Head-Commit.
5. Prüfe unmittelbar vor jeder Änderung erneut PR-Nummer, Head-Branch, Head-Commit, Zielbranch und Mergebarkeit.

## 2. Verbindliche Fristen bestimmen

Berechne mit `Europe/Berlin`:

- `review_eligible_at = created_at + 2 Stunden`
- `same_day_repair_at = 20:00 Uhr am lokalen Kalendertag der PR-Erstellung`
- `repair_eligible_at = max(review_eligible_at, same_day_repair_at)`

Verwende nach Möglichkeit die deterministische Referenzimplementierung:

```bash
python scripts/merge_repair_policy.py \
  --created-at "$PR_CREATED_AT" \
  --now "$NOW" \
  --ci-state "$CI_STATE" \
  --coderabbit-state "$CODERABBIT_STATE" \
  --unresolved-threads "$UNRESOLVED_THREADS" \
  --second-ci-state "$SECOND_CI_STATE" \
  ${IS_DRAFT:+--draft}
```

Vor `review_eligible_at` erfolgt keine Statusänderung, Reparatur oder Benachrichtigung. Vor `repair_eligible_at` darf keine inhaltliche Reparatur gestartet werden.

## 3. CodeRabbit als hartes Gate prüfen

Prüfe ausschließlich Signale des aktuellen PR-Heads:

- Statuschecks und Check-Runs mit erkennbarem CodeRabbit-Kontext;
- formelle Reviews;
- PR-Konversationskommentare;
- Inline-Kommentare und Review-Threads.

Verbindliche Bedingungen:

1. Für den aktuellen Head muss mindestens ein erfolgreiches CodeRabbit-Signal vorhanden sein.
2. `pending`, `missing`, `failure`, `cancelled`, ein ausgeschöpftes Kontingent oder Schweigen von CodeRabbit sind **kein Freibrief**, sondern blockieren den Ablauf.
3. Alle CodeRabbit-Threads müssen gelöst sein. Das gilt auch für als `outdated` markierte Threads: Sie werden entweder am aktuellen Code behoben oder mit überprüfbarer Begründung abgeschlossen, wenn die betroffene Datei oder Logik nicht mehr im Diff existiert.
4. Ein Agent darf einen fachlich oder technisch weiterhin strittigen Hinweis nicht einseitig wegauflösen. Dokumentiere dann im PR:

   ```html
   <!-- coderabbit-disagreement head=<CURRENT_HEAD_SHA> -->
   ```

   Nenne Behauptung, Quellen beziehungsweise Codebeleg, verbleibende Unsicherheit und benötigte menschliche Entscheidung. Dieser Zustand ist ein harter Blocker.
5. Ein Dissens gilt erst als beendet, wenn CodeRabbit die Korrektur akzeptiert oder ein Mensch ausdrücklich entscheidet. Dokumentiere danach:

   ```html
   <!-- coderabbit-disagreement-resolved head=<CURRENT_HEAD_SHA> -->
   ```

6. Der Workflowcheck **`CodeRabbit review gate (blocking)`** muss für den aktuellen Zustand erfolgreich sein.

## 4. Reproduzierbares Remark-lint als hartes CI-Gate

Der Check **`Remark lint (blocking)`** ist verpflichtend. Er muss mit den fest gepinnten Abhängigkeiten aus `package-lock.json` erfolgreich sein.

Lokal beziehungsweise im Reparaturzyklus:

```bash
npm ci
REMARK_BASE_SHA="origin/main" REMARK_HEAD_SHA="HEAD" \
  npm run lint:markdown:changed
```

Ein grüner Codacy-SARIF-Upload ersetzt diesen Check nicht. Remark-lint-Warnungen sind blockierend und werden im Markdownquelltext behoben; Regeln dürfen nicht nur zur Freigabe abgeschwächt werden.

## 5. CI-Status bestimmen

„CI vollständig grün“ bedeutet:

- alle zum aktuellen Head gehörenden erwarteten Checks und Workflows sind vorhanden und abgeschlossen;
- kein erwarteter Check ist `queued`, `in_progress`, `pending`, `action_required`, `cancelled`, `timed_out`, `failure` oder `startup_failure`;
- `Validate compendium`, `Build all download formats`, `Remark lint (blocking)` und `CodeRabbit review gate (blocking)` sind erfolgreich;
- der PR ist konfliktfrei und GitHub meldet ihn als mergebar;
- der Head wurde nach dem letzten vollständig grünen Lauf nicht verändert.

Falls CI noch läuft oder ein erwarteter Lauf fehlt, beende den aktuellen Wächterlauf ohne Änderung. Ein späterer Lauf prüft erneut.

## 6. Rote CI oder Review vor dem Reparaturfenster

Falls CI, Remark-lint oder ein behebbarer CodeRabbit-Hinweis vor `repair_eligible_at` rot ist:

1. Starte **keinen** Reparaturjob und ändere den PR-Branch nicht.
2. Sammle vollständige Logs, Run-/Job-IDs, Review-Threads und einen stabilen Fehlerfingerabdruck.
3. Wiederhole ausschließlich eindeutig transiente, unveränderte Workflow-Jobs, wenn die GitHub-Schnittstelle das sicher unterstützt. Eine fachliche oder quellbezogene Änderung ist vor dem Reparaturfenster verboten.
4. Schreibe den Status `wait_review` mit der konkreten Reparaturfrist und dem nächsten Prüfzeitpunkt.
5. Beende den Lauf. Der nächste regelmäßige Wächterlauf prüft weiter.

Der Wächter bricht nicht nach einer festen Anzahl roter Läufe ab. Er bleibt bis mindestens `repair_eligible_at` aktiv.

## 7. Reparatur ab 20:00 Uhr

Ist `repair_eligible_at` erreicht und CI, Remark-lint oder ein behebbarer CodeRabbit-Hinweis weiterhin rot:

1. Lies `prompts/PR-REPAIR-PROMPT.md` vollständig.
2. Führe in diesem Wächterlauf genau einen sicheren, idempotenten Reparaturzyklus auf dem bestehenden PR-Branch aus.
3. Verwende keinen neuen Einheitenbranch, keinen Force-Push und keinen parallelen zweiten Reparaturstatus.
4. Vergleiche Fehlerfingerabdruck und Head-Commit mit früheren Reparaturen. Erzeuge keinen identischen No-op- oder Wiederholungscommit.
5. Pushe eine sachlich begründete Reparatur und beende den Lauf, ohne Draftstatus oder Merge zu verändern.
6. Der nächste Wächterlauf bewertet die neue CI und die inkrementelle CodeRabbit-Prüfung.
7. Für neue oder veränderte Ursachen sind in späteren Läufen weitere sichere Reparaturzyklen zulässig; es gibt keine starre Grenze von zwei roten CI-Läufen.
8. Ein unveränderter, nicht sicher reparierbarer oder zwischen Agent und CodeRabbit strittiger Befund wird `manual_intervention` und bleibt harter Blocker.

## 8. Draft in normalen Pull Request umwandeln

Wenn der PR noch Draft ist und für den aktuellen Head alle folgenden Bedingungen erfüllt sind:

- die zweistündige Reviewfrist ist abgelaufen;
- erste CI vollständig grün;
- Remark-lint grün;
- CodeRabbit erfolgreich;
- alle CodeRabbit-Threads gelöst;
- kein ungeklärter Dissens;
- PR konfliktfrei und mergebar;

markiere den PR als **Ready for review**, ändere in diesem Lauf keine Dateien und merge noch nicht. Beende den Lauf, damit die dadurch gestartete zweite CI und eine erneute CodeRabbit-Bewertung eindeutig zugeordnet werden können.

## 9. Zweite Prüfung

Wenn der PR nicht mehr Draft ist:

1. Stelle fest, dass nach `Ready for review` mindestens ein neuer Pull-Request-CI-Lauf gestartet wurde.
2. Warte, solange CI, Remark-lint oder CodeRabbit noch laufen.
3. Bei roter zweiter CI gilt dieselbe Reparaturfrist und Reparaturpolicy; nach 20:00 Uhr kann der bestehende Branch sicher repariert werden.
4. Prüfe nach jedem Reparaturpush erneut den aktuellen Head, sämtliche Threads, Remark-lint und das CodeRabbit-Gate.

## 10. Merge

Nur wenn die zweite Pull-Request-CI, Remark-lint und das CodeRabbit-Gate für denselben aktuellen Head vollständig grün sind und kein Konflikt oder Dissens offen ist:

1. Merge per **Squash-Merge** nach `main`.
2. Verwende einen sachlichen Commit-Titel mit Einheitsnummer und Thema.
3. Lösche den Head-Branch nach dem Merge, sofern möglich; ein Löschfehler muss gemeldet werden, macht den Merge aber nicht rückgängig.
4. Prüfe, ob `main` den gemergten Inhalt und den Merge-Commit enthält.
5. Benachrichtige den Benutzer mit PR, Thema, Merge-Commit, Gatezuständen und Branchbereinigung.

## 11. Harte Abbruchregeln

Führe weder Ready for review noch Merge durch, wenn mindestens eine Bedingung vorliegt:

- PR jünger als zwei Stunden;
- erwartete CI fehlt, läuft oder ist rot;
- `Remark lint (blocking)` fehlt oder ist rot;
- aktuelles CodeRabbit-Signal fehlt, läuft oder ist rot;
- ein CodeRabbit-Thread ist ungelöst, auch wenn er outdated ist;
- Agent und CodeRabbit sind nicht belastbar einig;
- PR ist konfliktbehaftet, nicht mergebar oder nicht gegen `main` gerichtet;
- Branch entspricht nicht `agent/einheit-*` oder Marker fehlt;
- mehrere passende PRs sind offen;
- Head wurde nach dem letzten grünen Gate verändert;
- nach Ready for review fehlt die neue vollständig grüne zweite CI;
- Statusbranch oder Laufrevision ist inkonsistent.

## 12. Statusübergabe und Recovery

1. Lies den kanonischen Generatorstatus des PR vom Branch `automation-status` und verifiziere `run_id`, Branch, Commit und PR-Nummer.
2. Verwende dieselbe Ausführung für `wait_review`, `repair`, `ready_for_review`, `verify_second_ci`, `merge`, `cleanup` und `complete`.
3. Lies unmittelbar vor jeder schreibenden Statusoperation die aktuelle `REVISION` und verwende sie genau einmal als `--expected-revision`. Exitcode `20` oder eine abweichende Revision beendet den aktuellen Versuch ohne Überschreiben.
4. Registriere CI-Run, Job, Remark-Bericht, Review-Gate-Bericht, Reparaturcommit, Merge-Commit und PR als strukturierte Artefakte.
5. Nach Ready for review bleibt der Status `running`, bis zweite CI und CodeRabbit-Gate abgeschlossen sind.
6. Ein erfolgreicher Merge genügt nicht für `success`; dokumentiere zuerst Merge-Commit, `main`-Nachweis und Branchbereinigung.
7. Bei Fehlern schreibe Fehlerklasse, Fehlercode, Review-/CI-Fingerabdruck, Recovery-Level und nächsten sicheren Schritt. Ein ungeklärter Fehler blockiert den nächsten Generatorlauf.
8. Falls `automation-status` nicht beschreibbar ist, gib den vollständigen Diagnoseblock aus `prompts/AUTOMATION-PROMPT.md` aus. Eine generische Scheduled-Task-Meldung genügt niemals.
