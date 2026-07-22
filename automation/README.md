# Automation Run Recovery Status

## Ziel

Automatische Läufe sollen bei Fehlern nicht nur einen generischen Fehler melden, sondern den exakten Zustand des Laufs dokumentieren.

## Statusdateien

Jeder Agentenlauf kann eine Datei unter `automation/runs/` erzeugen:

```text
automation/runs/YYYY-MM-DDTHH-MM-SSZ.yml
```

Sie enthält:

- Lauf-ID
- Workflowname
- Repositorybasis
- aktuelle Phase
- abgeschlossene Phasen
- Fehlerkategorie
- vorhandene Artefakte
- Wiederholbarkeit
- empfohlene Recovery-Aktion

## Phasen

- `load_main`
- `check_existing_pr`
- `read_prompts`
- `research`
- `create_branch`
- `create_content`
- `validate`
- `commit`
- `push`
- `create_pr`
- `verify_pr`

## Fehlerklassen

- `github_api`
- `repository`
- `automation`
- `validation`
- `external`

## Recovery

Ein Fehler darf nicht automatisch einen neuen Inhalt erzeugen. Zuerst wird geprüft, ob vorhandene Artefakte wiederverwendet werden können.

Beispiele:

- Branch vorhanden, PR fehlt → nur PR-Erstellung wiederholen
- Commit vorhanden, Push fehlgeschlagen → Push wiederholen
- Timeout → gleiche Phase erneut versuchen
- wissenschaftlicher oder Validierungsfehler → manueller Eingriff
