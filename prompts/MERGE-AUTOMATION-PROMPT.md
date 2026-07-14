# Automatisierungsprompt: Draft-Prüfung und Merge

Dieser Prompt wird durch einen getrennten Merge-Wächter **frühestens ab 08:00 Uhr Europe/Berlin** ausgeführt. Er hält keinen Agenten zwei Stunden lang künstlich offen, sondern prüft den von der 06-Uhr-Automation erzeugten Draft-Pull-Request in getrennten Läufen.

Arbeite im Repository `H234598/ADHS-Lernpfad`.

## 1. Geeigneten Pull Request bestimmen

1. Suche offene Pull Requests gegen `main`, deren Head-Branch dem Muster `agent/einheit-*` entspricht und deren Beschreibung den Marker `<!-- adhs-daily-unit -->` enthält.
2. Berücksichtige nur Pull Requests, die mindestens **zwei Stunden** alt sind.
3. Falls kein geeigneter PR vorhanden ist, beende den Lauf ohne Benachrichtigung.
4. Falls mehrere geeignete PRs vorhanden sind, verändere keinen davon und benachrichtige den Benutzer über den Mehrdeutigkeitsfehler.
5. Arbeite ausschließlich mit dem eindeutig bestimmten PR und seinem aktuellen Head-Commit.

## 2. CodeRabbit-Prüfung

Vor jeder Statusänderung muss CodeRabbit den **aktuellen Head-Commit** geprüft haben.

Als abgeschlossen gilt die Prüfung nur, wenn:

- ein CodeRabbit-Review, eine CodeRabbit-Zusammenfassung oder ein entsprechender Check für den aktuellen PR nach dem letzten Push vorhanden ist;
- kein formelles `REQUEST_CHANGES` offen ist;
- keine ungelösten CodeRabbit-Review-Threads mit konkretem Änderungsbedarf bestehen;
- keine als kritisch, hoch, blocking oder must-fix gekennzeichneten Feststellungen offen sind.

Falls CodeRabbit noch nicht geprüft hat, die Prüfung noch läuft oder offene Änderungsforderungen bestehen, ändere den PR-Status nicht. Bei bloß laufender Prüfung beende den Lauf ohne Benachrichtigung. Bei konkreten blockierenden Feststellungen benachrichtige den Benutzer mit einer präzisen Zusammenfassung und merge nicht.

## 3. CI vollständig grün

„CI vollständig grün“ bedeutet:

- alle zum aktuellen Head-Commit gehörenden Checks und Workflow-Läufe sind abgeschlossen;
- kein Check ist `queued`, `in_progress`, `pending`, `action_required`, `cancelled`, `timed_out`, `failure` oder `startup_failure`;
- alle erforderlichen Checks enden mit `success`, `neutral` oder einem ausdrücklich zulässigen `skipped`;
- insbesondere `Validate compendium` einschließlich Literatur-, Graph-, Validator-, Gesamt-, Anki-, Dokumentations- und MkDocs-Schritten ist erfolgreich;
- der PR ist konfliktfrei und GitHub meldet ihn als mergebar.

Falls CI noch läuft, beende den Lauf ohne Benachrichtigung. Falls CI fehlgeschlagen oder der PR nicht mergebar ist, benachrichtige den Benutzer mit den betroffenen Checks beziehungsweise Konflikten und merge nicht.

## 4. Draft in normalen Pull Request umwandeln

Wenn der PR noch ein Draft ist und sowohl CodeRabbit als auch die CI für den aktuellen Head-Commit vollständig erfolgreich sind:

1. Markiere den PR als **Ready for review**.
2. Verändere in diesem Lauf keine Dateien und pushe keinen neuen Commit.
3. Merge den PR in diesem Lauf noch nicht.
4. Beende den Lauf. Dadurch erhält GitHub Gelegenheit, die durch `ready_for_review` ausgelösten Prüfungen erneut auszuführen.

## 5. Zweite Prüfung nach der Umwandlung

Wenn der PR kein Draft mehr ist:

1. Stelle fest, dass nach der Umwandlung zu „Ready for review“ mindestens ein neuer Pull-Request-CI-Lauf gestartet und für den aktuellen Head-Commit vollständig grün abgeschlossen wurde.
2. Prüfe CodeRabbit erneut auf offene oder nachträglich hinzugekommene Feststellungen.
3. Prüfe erneut sämtliche Review-Threads, Checks, Konflikte und Mergebarkeit.
4. Falls nach der Umwandlung noch keine neue grüne CI vorliegt, beende den Lauf ohne Benachrichtigung.

## 6. Merge

Nur wenn alle Bedingungen aus den vorherigen Abschnitten erneut erfüllt sind:

1. Merge den PR per **Squash-Merge** nach `main`.
2. Verwende einen sachlichen Commit-Titel mit Einheitsnummer und Thema.
3. Lösche den Head-Branch nach dem Merge, sofern die verfügbare GitHub-Schnittstelle dies unterstützt. Ein Fehlschlag beim Löschen des Branches darf den bereits erfolgreichen Merge nicht rückgängig machen, muss aber gemeldet werden.
4. Prüfe anschließend, ob `main` den gemergten Commit beziehungsweise dessen Inhalt enthält.
5. Benachrichtige den Benutzer mit PR-Nummer, Thema, Merge-Commit und dem Ergebnis der Branch-Bereinigung.

## 7. Harte Abbruchregeln

Führe keinen Merge durch, wenn mindestens eine dieser Bedingungen vorliegt:

- CodeRabbit hat den aktuellen Head-Commit nicht geprüft;
- ein Review fordert Änderungen;
- ein relevanter Review-Thread ist ungelöst;
- ein CI-Check läuft, fehlt oder ist fehlgeschlagen;
- der PR enthält Mergekonflikte;
- der PR ist jünger als zwei Stunden;
- der PR wurde nach der letzten CodeRabbit- oder CI-Prüfung verändert;
- mehrere passende automatische PRs sind offen;
- der PR zielt nicht auf `main` oder stammt nicht aus `agent/einheit-*`;
- der Marker `<!-- adhs-daily-unit -->` fehlt.

Nimm in diesem Prüf- und Merge-Lauf keine eigenständigen inhaltlichen Korrekturen vor. Erfordern CodeRabbit oder CI Änderungen, bleibt der PR offen und der Benutzer wird über den konkreten Blocker informiert.