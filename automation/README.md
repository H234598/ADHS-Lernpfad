# Automation Runtime Status

Der Runtime-Status ist eine gemeinsame Infrastruktur für lang laufende Repository-Automationen.

## Zweck

Ein Lauf soll nicht nur `success` oder `failed` liefern, sondern seine aktuelle Phase, erzeugte Artefakte und Recovery-Informationen nachvollziehbar speichern.

## Statusmodell

- `started`
- `running`
- `success`
- `failed`
- `blocked`
- `recovered`

## Verantwortungsgrenzen

Die Wissensgraph-Phase nutzt den Runtime-Status für Build- und Validierungsläufe.

Die vollständige Scheduler-, Retry- und Merge-Wächter-Logik bleibt Teil von Issue #34.

## Sicherheit

Statusdateien werden atomar geschrieben. Ein Lauf darf niemals eine halbgeschriebene JSON-Datei als gültigen Zustand hinterlassen.
