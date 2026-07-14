# Prompt-Verzeichnis

Alle automatisierbaren Arbeitsanweisungen des Projekts liegen zentral in diesem Ordner.

## Dateien

- `AUTOMATION-PROMPT.md` – tägliche Erzeugung genau einer neuen Lerneinheit; wird um 06:00 Uhr Europe/Berlin ausgeführt und endet mit einem Draft-Pull-Request.
- `DEEP-RESEARCH-PROMPT.md` – verbindliche wissenschaftliche Recherche- und Evidenzprüfung für neue oder zu revidierende Kapitel.
- `MERGE-AUTOMATION-PROMPT.md` – getrennter Merge-Wächter; wartet mindestens zwei Stunden, berücksichtigt vorhandene CodeRabbit-Hinweise optional, repariert fehlgeschlagene CI und merged erst nach einer zweiten grünen CI.
- `PR-REPAIR-PROMPT.md` – sicherer Reparaturzyklus für fehlgeschlagene Checks auf dem bestehenden Einheiten-Branch.

## Ablauf

```text
06:00  Erzeugungsprompt
          ↓
        Draft-PR
          ↓
        mindestens zwei Stunden Prüfzeit
          ↓
ab 08:00 stündlicher Merge-Wächter
          ↓
        CodeRabbit-Signale auswerten, falls vorhanden
          ↓
        CI rot? → genau ein Reparaturzyklus → neue CI
          ↓
        erste PR-CI vollständig grün
          ↓
        Ready for review
          ↓
        zweite Pull-Request-CI
          ↓
        bei Fehler erneut reparieren
          ↓
        bei vollständig grüner CI Squash-Merge nach main
```

CodeRabbit ist kein verpflichtendes Gate. GitHub kann sichtbare Reviews, Kommentare, Threads und Checks abbilden, aber nicht zuverlässig das verbleibende CodeRabbit-Kontingent oder dessen Erholungszeit. Nach Ablauf der Zwei-Stunden-Frist darf der Ablauf deshalb auch ohne CodeRabbit-Prüfung fortfahren.

Die Automationen selbst enthalten nur einen kurzen Startauftrag. Die ausführlichen Regeln werden bei jedem Lauf frisch aus diesen Dateien gelesen, damit Änderungen an den Prompts ohne eine erneute Anlage der Automationen wirksam werden.
