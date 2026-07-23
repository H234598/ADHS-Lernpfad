# Automatisierungsprompt: Draft-Prüfung, Reparatur und Merge

Dieser Prompt wird durch einen getrennten Merge-Wächter **frühestens zwei Stunden nach Erstellung des Draft-Pull-Requests** ausgeführt. Die Frist gibt CodeRabbit Gelegenheit zur Prüfung und verhindert einen vorschnellen Merge. CodeRabbit ist dennoch kein Pflicht-Gate: Eine fehlende Prüfung oder ein ausgeschöpftes Review-Limit blockiert den Ablauf nach Ablauf der Frist nicht.

Arbeite im Repository `H234598/ADHS-Lernpfad`.

## 1. Geeigneten Pull Request bestimmen

1. Suche offene Pull Requests gegen `main`, deren Head-Branch dem Muster `agent/einheit-*` entspricht und deren Beschreibung den Marker `<!-- adhs-daily-unit -->` enthält.
2. Falls kein geeigneter PR vorhanden ist, beende den Lauf ohne Benachrichtigung.
3. Falls mehrere geeignete PRs vorhanden sind, verändere keinen davon und benachrichtige den Benutzer über den Mehrdeutigkeitsfehler.
4. Berücksichtige den eindeutig bestimmten PR erst, wenn seit seiner Erstellung mindestens **zwei volle Stunden** vergangen sind. Vorher beende den Lauf ohne Änderung und ohne Benachrichtigung.
5. Arbeite ausschließlich mit diesem PR und seinem aktuellen Head-Commit.

## 2. CodeRabbit-Signale über GitHub prüfen

Prüfe über die auf GitHub sichtbaren Daten:

- formelle Pull-Request-Reviews;
- PR-Konversationskommentare;
- Inline-Review-Kommentare und Review-Threads;
- Check-Runs oder Statuschecks, deren Name oder Absender CodeRabbit erkennen lässt.

Bewerte nur Einträge, die zum aktuellen PR und möglichst zum aktuellen Head-Commit gehören.

- Ist eine CodeRabbit-Prüfung vorhanden, berücksichtige nachvollziehbare, relevante Hinweise vor einer Statusänderung oder einem Merge.
- Ist keine Prüfung vorhanden, CodeRabbit still geblieben oder das Review-Limit vermutlich ausgeschöpft, fahre nach Ablauf der Zwei-Stunden-Frist allein anhand von CI, Mergebarkeit und Projektregeln fort.
- GitHub-Signale dürfen nicht als zuverlässige Auskunft über das verbleibende CodeRabbit-Kontingent oder dessen Erholungszeit interpretiert werden.

## 3. CI-Status bestimmen

„CI vollständig grün“ bedeutet:

- alle zum aktuellen Head-Commit gehörenden erwarteten Checks und Workflow-Läufe sind vorhanden und abgeschlossen;
- kein Check ist `queued`, `in_progress`, `pending`, `action_required`, `cancelled`, `timed_out`, `failure` oder `startup_failure`;
- alle erforderlichen Checks enden mit `success`, `neutral` oder einem ausdrücklich zulässigen `skipped`;
- insbesondere `Validate compendium` einschließlich Literatur-, Graph-, Validator-, Gesamt-, Anki-, Dokumentations- und MkDocs-Schritten ist erfolgreich;
- der PR ist konfliktfrei und GitHub meldet ihn als mergebar.

### CI läuft noch

Falls CI noch läuft oder ein erwarteter Prüflauf noch nicht sichtbar ist, beende den Lauf ohne Änderung und ohne Benachrichtigung. Ein späterer stündlicher Lauf prüft erneut.

### CI ist fehlgeschlagen

Falls ein Check fehlgeschlagen ist:

1. Lies `prompts/PR-REPAIR-PROMPT.md` vollständig.
2. Führe in diesem Lauf **genau einen sicheren Reparaturzyklus** auf dem bestehenden PR-Branch aus.
3. Berücksichtige dabei vorhandene, nachvollziehbare CodeRabbit-Hinweise, ohne deren Vorhandensein vorauszusetzen.
4. Pushe die Reparatur und beende den Lauf, ohne den Draft-Status zu ändern und ohne zu mergen.
5. Die neue CI wird in einem späteren Merge-Wächter-Lauf erneut bewertet.
6. Ist keine sichere automatische Reparatur möglich, lasse den PR offen und benachrichtige den Benutzer präzise über den Blocker.

Der Pull Request darf bei reparierbaren CI-Fehlern also nicht bloß unbeachtet liegen bleiben.

## 4. Draft in normalen Pull Request umwandeln

Wenn der PR noch ein Draft ist, mindestens zwei Stunden alt ist und die CI für den aktuellen Head-Commit vollständig erfolgreich ist:

1. Stelle sicher, dass keine vorhandene, nachvollziehbare CodeRabbit-Feststellung einen konkreten kritischen Fehler des aktuellen Head-Commits beschreibt. Das Fehlen eines CodeRabbit-Reviews ist kein Blocker.
2. Markiere den PR als **Ready for review**.
3. Verändere in diesem Lauf keine Dateien und pushe keinen neuen Commit.
4. Merge den PR in diesem Lauf noch nicht.
5. Beende den Lauf, damit die durch `ready_for_review` ausgelösten Prüfungen erneut laufen können.

## 5. Zweite Prüfung nach der Umwandlung

Wenn der PR kein Draft mehr ist:

1. Stelle fest, dass nach der Umwandlung zu „Ready for review“ mindestens ein neuer Pull-Request-CI-Lauf gestartet wurde.
2. Falls dieser Lauf noch läuft, beende den aktuellen Wächterlauf ohne Änderung.
3. Falls dieser Lauf fehlschlägt, führe nach `prompts/PR-REPAIR-PROMPT.md` genau einen Reparaturzyklus durch und warte anschließend auf die nächste CI.
4. Falls er vollständig grün ist, prüfe erneut Konflikte, Mergebarkeit und vorhandene relevante Review-Hinweise.

## 6. Merge

Nur wenn die zweite Pull-Request-CI vollständig grün ist und keine konkrete kritische Feststellung oder Konfliktsituation offen ist:

1. Merge den PR per **Squash-Merge** nach `main`.
2. Verwende einen sachlichen Commit-Titel mit Einheitsnummer und Thema.
3. Lösche den Head-Branch nach dem Merge, sofern die verfügbare GitHub-Schnittstelle dies unterstützt. Ein Fehlschlag beim Löschen darf den erfolgreichen Merge nicht rückgängig machen, muss aber gemeldet werden.
4. Prüfe anschließend, ob `main` den gemergten Inhalt enthält.
5. Benachrichtige den Benutzer mit PR-Nummer, Thema, Merge-Commit und dem Ergebnis der Branch-Bereinigung.

## 7. Harte Abbruchregeln

Führe keinen Merge durch, wenn mindestens eine dieser Bedingungen vorliegt:

- der PR ist jünger als zwei Stunden;
- ein erwarteter CI-Check läuft, fehlt oder ist fehlgeschlagen;
- der PR enthält Mergekonflikte oder ist nicht mergebar;
- der PR wurde nach dem letzten vollständig grünen CI-Lauf verändert;
- mehrere passende automatische PRs sind offen;
- der PR zielt nicht auf `main` oder stammt nicht aus `agent/einheit-*`;
- der Marker `<!-- adhs-daily-unit -->` fehlt;
- nach „Ready for review“ wurde noch kein neuer vollständig grüner Pull-Request-CI-Lauf abgeschlossen;
- ein vorhandener Review-Hinweis beschreibt einen nachvollziehbaren kritischen Fehler, der noch nicht behoben wurde.

CodeRabbit als solches ist **keine** harte Abbruchbedingung. Sein Fehlen, Schweigen oder mutmaßlich ausgeschöpftes Kontingent verhindert den Merge nicht.

## 8. Additive Statusübergabe für Review, Merge und Cleanup

Alle vorstehenden Zeit-, CI-, Review-, Wissenschafts-, Merge- und
Sicherheitsregeln bleiben vollständig erhalten.

1. Lies den kanonischen Generatorstatus des eindeutig bestimmten PR vom Branch
   `automation-status`. Verifiziere `run_id`, Branch, Commit und PR-Nummer gegen
   den aktuellen GitHub-Zustand.
2. Schreibe alle Wächteränderungen als neue Revision desselben Vorgangs:
   - Warten auf erste CI oder Review: `wait_review`
   - kontrollierter Reparaturzyklus: `repair`
   - Umwandlung aus Draft: `ready_for_review`
   - Prüfung der danach gestarteten zweiten CI: `verify_second_ci`
   - Squash-Merge: `merge`
   - Merge-Nachweis und Branchbereinigung: `cleanup`
   - vollständiger Abschluss: `complete`
3. Lies unmittelbar vor jedem schreibenden Statusbefehl die aktuelle
   Laufrevision in `REVISION` ein und übergib
   `--expected-revision "$REVISION"`. Die Revision darf nur für genau einen
   `phase`-, `artifact`-, `recover`-, `fail`- oder `finish`-Befehl verwendet
   werden und muss danach frisch eingelesen werden. Exitcode `20` oder eine
   abweichende Revision beendet den aktuellen Mergeversuch: Statusbranch neu
   laden, GitHub-Zustand erneut abgleichen und niemals die fremde Revision
   überschreiben.
4. Registriere CI-Run, Job, Reparaturcommit, Merge-Commit und PR als
   strukturierte Artefakte. Branch, Commit oder PR müssen bei Wiederaufnahme
   weiterverwendet werden; ein neuer Einheitenbranch ist verboten.
5. Nach `Ready for review` bleibt der Status `running`, bis eine eindeutig
   zugeordnete zweite CI vollständig abgeschlossen ist.
6. Ein erfolgreicher Merge allein genügt nicht für `success`. Dokumentiere
   zuerst Merge-Commit, `main`-Nachweis und Ergebnis der Branchbereinigung.
7. Erst danach:

   ```bash
   python scripts/automation_status.py finish \
     --workflow generator --run-id "$RUN_ID" --phase complete \
     --expected-revision "$REVISION"
   ```

8. Bei CI-, Review-, Konflikt-, Berechtigungs- oder API-Fehlern schreibe einen
   strukturierten Fehler mit Recovery-Level. Ein ungeklärter Fehler blockiert
   den nächsten Generatorlauf und verhindert dadurch eine zweite Einheit.
9. Falls `automation-status` nicht beschreibbar ist, gib den vollständigen
   Diagnoseblock aus `prompts/AUTOMATION-PROMPT.md` aus. Melde insbesondere
   konkrete Phase, vorhandene Artefakte, GitHub-Run/Job, Ursache und den nächsten
   sicheren Recovery-Schritt; eine generische Scheduled-Task-Meldung genügt
   niemals.
