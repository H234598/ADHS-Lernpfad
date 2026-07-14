# Automatisierungsprompt: fehlgeschlagenen Einheiten-PR reparieren

Dieser Prompt wird ausschließlich vom Merge-Wächter aufgerufen, wenn die CI eines automatischen Einheiten-Pull-Requests fehlgeschlagen ist oder vorhandene CodeRabbit-Hinweise eine fachlich oder technisch notwendige Korrektur erkennen lassen.

Arbeite im Repository `H234598/ADHS-Lernpfad` und ausschließlich auf dem bereits bestehenden Head-Branch des betroffenen Pull Requests.

## 1. Ausgangslage sichern

1. Ermittle PR-Nummer, Head-Branch und aktuellen Head-Commit erneut.
2. Prüfe, dass der PR gegen `main` zielt, der Branch `agent/einheit-*` entspricht und der Marker `<!-- adhs-daily-unit -->` vorhanden ist.
3. Arbeite niemals direkt auf `main` und führe keinen Force-Push durch.
4. Prüfe unmittelbar vor Änderungen, dass der Head-Commit seit Beginn des Laufs nicht durch einen anderen Prozess verändert wurde.

## 2. Fehler und vorhandenes Review auswerten

1. Lies die vollständigen Logs aller fehlgeschlagenen GitHub-Checks und Workflow-Jobs des aktuellen Head-Commits.
2. Bestimme die konkrete Ursache; behandle nicht bloß den letzten Folgefehler.
3. Prüfe vorhandene CodeRabbit-Reviews, PR-Kommentare und Inline-Kommentare. CodeRabbit ist **kein Pflicht-Gate**. Falls keine Prüfung vorhanden ist, fahre allein anhand von CI und Projektregeln fort.
4. Übernimm CodeRabbit-Hinweise nur, wenn sie nachvollziehbar, für den aktuellen Head-Commit relevant und mit den wissenschaftlichen sowie technischen Projektregeln vereinbar sind.
5. Ändere nur Dateien, die zur neuen Einheit, ihren Quellen, Karten, Navigation, generierten Quellen oder zur unmittelbaren Behebung des konkreten Fehlers gehören.

## 3. Reparatur

1. Behebe alle eindeutig zusammenhängenden Fehler in einem konsistenten Reparaturschritt.
2. Verändere Prompts, Workflows, Validatoren oder Infrastruktur nur, wenn der CI-Fehler nachweislich dort liegt und keine engere Lösung möglich ist. Melde solche Änderungen ausdrücklich.
3. Erfinde keine Quellenangaben und schwäche keine Validierung ab, nur damit die CI grün wird.
4. Bei wissenschaftlichen Korrekturen gilt weiterhin `prompts/DEEP-RESEARCH-PROMPT.md`.

## 4. Lokale Prüfung

Führe nach der Reparatur vollständig aus:

```bash
python3 scripts/build_literature.py
python3 scripts/build_graph.py
python3 scripts/validate_compendium.py
python3 scripts/build_combined.py
python3 scripts/build_anki.py
python3 scripts/build_docs.py
mkdocs build --strict
```

Alle Prüfungen müssen lokal erfolgreich sein. Prüfe außerdem `git diff`, damit keine fremden oder generierten Mülländerungen committed werden.

## 5. Commit und Push

1. Committe ausschließlich die Reparatur auf dem bestehenden PR-Branch.
2. Verwende eine sachliche Commit-Nachricht wie `fix: repariere CI für Einheit NN`.
3. Pushe normal zu `origin`; kein Force-Push.
4. Ergänze im PR einen kurzen Kommentar mit Ursache, geänderten Dateien und lokalen Prüfergebnissen.
5. Markiere den PR in diesem Lauf nicht als „Ready for review“ und merge ihn nicht. Der nächste Merge-Wächter-Lauf bewertet die neu gestartete CI.

## 6. Nicht automatisch reparierbare Fälle

Nimm keine spekulativen Änderungen vor, wenn:

- die Ursache nicht sicher bestimmbar ist;
- Zugangsdaten, externe Dienste oder Repository-Einstellungen fehlen;
- die Reparatur eine wissenschaftlich unsichere Aussage erzwingen würde;
- Branch oder PR während des Laufs parallel verändert wurden;
- ein wiederholter identischer Fehler trotz sachgerechter Reparatur fortbesteht.

Lasse den PR dann offen und benachrichtige den Benutzer mit PR-Nummer, fehlgeschlagenem Check, relevanter Logstelle und dem konkreten Grund, weshalb keine sichere automatische Reparatur möglich war.
