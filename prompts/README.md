# Prompt-Verzeichnis

Alle automatisierbaren Arbeitsanweisungen des Projekts liegen zentral in diesem Ordner.

## Dateien

- `AUTOMATION-PROMPT.md` – tägliche Erzeugung genau einer neuen Lerneinheit; wird um 06:00 Uhr Europe/Berlin ausgeführt und endet mit einem Draft-Pull-Request.
- `DEEP-RESEARCH-PROMPT.md` – verbindliche wissenschaftliche Recherche- und Evidenzprüfung für neue oder zu revidierende Kapitel.
- `MERGE-AUTOMATION-PROMPT.md` – getrennter Merge-Wächter; prüft ausschließlich CI und Mergebarkeit, wandelt einen grünen Draft in einen normalen PR um und merged erst nach einer zweiten grünen CI.

## Ablauf

```text
06:00  Erzeugungsprompt
          ↓
        Draft-PR
          ↓
ab 07:00 stündlicher Merge-Wächter
          ↓
        erste PR-CI vollständig grün
          ↓
        Ready for review
          ↓
        neue Pull-Request-CI vollständig grün
          ↓
        Squash-Merge nach main
```

CodeRabbit ist kein verpflichtendes Gate. Eine vorhandene CodeRabbit-Prüfung kann zusätzliche Hinweise liefern, ihr Fehlen oder ein ausgeschöpftes Prüflimit blockiert den automatischen Ablauf jedoch nicht.

Die Automationen selbst enthalten nur einen kurzen Startauftrag. Die ausführlichen Regeln werden bei jedem Lauf frisch aus diesen Dateien gelesen, damit Änderungen an den Prompts ohne eine erneute Anlage der Automationen wirksam werden.