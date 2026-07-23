# Persistente Automationsstatus

Dieser orphan Branch wird ausschließlich durch den vertrauenswürdigen
`Persist automation status`-Workflow aktualisiert. Er enthält keine Lerninhalte
und keinen ausführbaren Code.

Kanonische Pfade:

```text
automation/status/<workflow>/<run_id>.json
automation/status/<workflow>/<run_id>.md
automation/status/<workflow>/latest.json
automation/status/<workflow>/latest.md
```

Statusdateien werden vor dem Commit gegen `automation/run-status.schema.json`
und die semantischen Invarianten validiert. Erfolgreiche Läufe werden 30 Tage,
fehlgeschlagene oder blockierte Läufe 90 Tage aufbewahrt; `latest.*` bleibt
dauerhaft erhalten.
