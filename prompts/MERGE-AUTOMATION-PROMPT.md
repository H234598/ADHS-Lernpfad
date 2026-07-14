# Automatisierungsprompt: Draft-Prüfung und Merge

Dieser Prompt wird durch einen getrennten Merge-Wächter ausgeführt. Er prüft den von der 06-Uhr-Automation erzeugten Draft-Pull-Request in wiederkehrenden, voneinander unabhängigen Läufen. Es gibt weder eine feste Wartezeit noch eine Abhängigkeit von CodeRabbit.

Arbeite im Repository `H234598/ADHS-Lernpfad`.

## 1. Geeigneten Pull Request bestimmen

1. Suche offene Pull Requests gegen `main`, deren Head-Branch dem Muster `agent/einheit-*` entspricht und deren Beschreibung den Marker `<!-- adhs-daily-unit -->` enthält.
2. Falls kein geeigneter PR vorhanden ist, beende den Lauf ohne Benachrichtigung.
3. Falls mehrere geeignete PRs vorhanden sind, verändere keinen davon und benachrichtige den Benutzer über den Mehrdeutigkeitsfehler.
4. Arbeite ausschließlich mit dem eindeutig bestimmten PR und seinem aktuellen Head-Commit.

## 2. CI vollständig grün

„CI vollständig grün“ bedeutet:

- alle zum aktuellen Head-Commit gehörenden Checks und Workflow-Läufe sind abgeschlossen;
- kein Check ist `queued`, `in_progress`, `pending`, `action_required`, `cancelled`, `timed_out`, `failure` oder `startup_failure`;
- alle erforderlichen Checks enden mit `success`, `neutral` oder einem ausdrücklich zulässigen `skipped`;
- insbesondere `Validate compendium` einschließlich Literatur-, Graph-, Validator-, Gesamt-, Anki-, Dokumentations- und MkDocs-Schritten ist erfolgreich;
- es fehlt kein für den PR erwarteter Validierungslauf;
- der PR ist konfliktfrei und GitHub meldet ihn als mergebar.

Falls CI noch läuft oder noch kein erwarteter Prüflauf vorhanden ist, beende den Lauf ohne Benachrichtigung. Falls CI fehlgeschlagen oder der PR nicht mergebar ist, benachrichtige den Benutzer mit den betroffenen Checks beziehungsweise Konflikten und merge nicht.

## 3. Draft in normalen Pull Request umwandeln

Wenn der PR noch ein Draft ist und die CI für den aktuellen Head-Commit vollständig erfolgreich ist:

1. Markiere den PR als **Ready for review**.
2. Verändere in diesem Lauf keine Dateien und pushe keinen neuen Commit.
3. Merge den PR in diesem Lauf noch nicht.
4. Beende den Lauf. Dadurch erhält GitHub Gelegenheit, die durch `ready_for_review` ausgelösten Prüfungen erneut auszuführen.

## 4. Zweite Prüfung nach der Umwandlung

Wenn der PR kein Draft mehr ist:

1. Stelle fest, dass nach der Umwandlung zu „Ready for review“ mindestens ein neuer Pull-Request-CI-Lauf gestartet und für den aktuellen Head-Commit vollständig grün abgeschlossen wurde.
2. Prüfe erneut sämtliche Checks, Konflikte und die Mergebarkeit.
3. Falls nach der Umwandlung noch keine neue grüne CI vorliegt, beende den Lauf ohne Benachrichtigung.

## 5. Merge

Nur wenn alle Bedingungen aus den vorherigen Abschnitten erneut erfüllt sind:

1. Merge den PR per **Squash-Merge** nach `main`.
2. Verwende einen sachlichen Commit-Titel mit Einheitsnummer und Thema.
3. Lösche den Head-Branch nach dem Merge, sofern die verfügbare GitHub-Schnittstelle dies unterstützt. Ein Fehlschlag beim Löschen des Branches darf den bereits erfolgreichen Merge nicht rückgängig machen, muss aber gemeldet werden.
4. Prüfe anschließend, ob `main` den gemergten Commit beziehungsweise dessen Inhalt enthält.
5. Benachrichtige den Benutzer mit PR-Nummer, Thema, Merge-Commit und dem Ergebnis der Branch-Bereinigung.

## 6. Harte Abbruchregeln

Führe keinen Merge durch, wenn mindestens eine dieser Bedingungen vorliegt:

- ein CI-Check läuft, fehlt oder ist fehlgeschlagen;
- der PR enthält Mergekonflikte;
- der PR wurde nach dem letzten vollständig grünen CI-Lauf verändert;
- mehrere passende automatische PRs sind offen;
- der PR zielt nicht auf `main` oder stammt nicht aus `agent/einheit-*`;
- der Marker `<!-- adhs-daily-unit -->` fehlt;
- nach „Ready for review“ wurde noch kein neuer vollständig grüner Pull-Request-CI-Lauf abgeschlossen.

Nimm in diesem Prüf- und Merge-Lauf keine eigenständigen inhaltlichen Korrekturen vor. Erfordert die CI Änderungen, bleibt der PR offen und der Benutzer wird über den konkreten Blocker informiert.