# Automation Runtime Status

Der kanonische Laufstatus liegt unter `build/runtime-status.json`. Generatoren,
Validatoren, GitHub Actions und die veröffentlichte Wissensgraph-Seite lesen
dasselbe, durch `automation/schema/run-status.schema.json` definierte Dokument.

## Lebenszyklus

`scripts/automation_run_status.py` schreibt atomar und erhält bei jedem Update
Run-ID, Startzeit und bereits gemeldete Metriken. Unterstützte Zustände sind
`started`, `running`, `success`, `failed`, `blocked` und `recovered`; die
Graphpipeline verwendet diese Phasen:

1. `initialization`
2. `load_content`
3. `build_nodes`
4. `build_edges`
5. `validate_graph`
6. `export`
7. `success` oder `failed`

Ein Abschluss enthält Start- und Endzeit, Laufzeit, Commit-SHA, Kennzahlen,
Artefaktpfade und – bei Fehlern – `error_class`, eine bereinigte Fehlermeldung
sowie `recovery_action`. Mögliche Recovery-Aktionen sind strukturierte Hinweise;
ein Scheduler, automatischer Retry oder Merge-Wächter wird in Phase 3 bewusst
nicht gestartet.

## Lokal verwenden

```bash
python scripts/runtime_status_cli.py --new-run \
  --workflow knowledge-graph --phase initialization
python scripts/build_graph.py
python scripts/validate_graph.py
python scripts/runtime_status_cli.py --finish success --phase success
python scripts/validate_runtime_status.py
```

Mit `RUNTIME_STATUS_MANAGED=1` besitzt ein äußerer Workflow den Start und das
Ende des Laufs. Die Buildskripte aktualisieren dann nur ihre tatsächlichen
Phasen und Metriken und erzeugen keine neue Run-ID. Ohne diese Variable ist
jeder Generator eigenständig nutzbar und beendet seinen eigenen Status.

## Fehlerklassen und Recovery

Die Pipeline unterscheidet insbesondere Lade-, Schema-, Link-, Graph-, Export-
und unerwartete Laufzeitfehler. Fehlermeldungen dürfen keine Secrets enthalten
und werden vor dem Speichern gekürzt. Der Recovery-Hinweis benennt die nächste
sichere Prüfung, beispielsweise `fix_graph_validation`, `rebuild_outputs` oder
`inspect_logs`.

## Qualitätsgate

`scripts/validate_runtime_status.py` prüft sowohl das JSON Schema als auch den
vertraglichen Gleichlauf von Schema und Implementierung. Die CI validiert den
Status vor der Zusammenfassung; ungeprüfte Laufdaten werden weder als
PR-Kommentar noch als öffentliches Artefakt ausgegeben.
