# Prompt-Verzeichnis

Alle automatisierbaren Arbeitsanweisungen des Projekts liegen zentral in diesem Ordner.

## Dateien

- `AUTOMATION-PROMPT.md` – tägliche Erzeugung genau einer neuen Lerneinheit; wird um 06:00 Uhr Europe/Berlin ausgeführt und endet mit einem Draft-Pull-Request.
- `DEEP-RESEARCH-PROMPT.md` – verbindliche wissenschaftliche Recherche- und Evidenzprüfung für neue oder zu revidierende Kapitel.
- `MERGE-AUTOMATION-PROMPT.md` – getrennte Prüfung ab 08:00 Uhr; wartet über wiederkehrende Prüfläufe auf CodeRabbit und vollständig grüne CI, wandelt den Draft in einen normalen PR um und merged erst nach einer zweiten grünen CI.

## Ablauf

```text
06:00  Erzeugungsprompt
          ↓
        Draft-PR
          ↓
        mindestens zwei Stunden Zeit für CodeRabbit und CI
          ↓
ab 08:00 stündlicher Merge-Wächter
          ↓
        CodeRabbit + CI grün
          ↓
        Ready for review
          ↓
        neue Pull-Request-CI grün
          ↓
        Squash-Merge nach main
```

Die Automationen selbst enthalten nur einen kurzen Startauftrag. Die ausführlichen Regeln werden bei jedem Lauf frisch aus diesen Dateien gelesen, damit Änderungen an den Prompts ohne eine erneute Anlage der Automationen wirksam werden.