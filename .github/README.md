# GitHub-Automation

## Workflows

- `validate.yml`: stabiles Pflichtgate `Validate and build` für Python- und Browsertests, Quellen, strukturierte Bibliografie, Obsidian-Links, Graphschema, Runtime-Status, Wortgrenzen, Anki und MkDocs.
- `runtime-status-check.yml`: fokussierter Vertragscheck für Statusschema, CLI und atomare Aktualisierungen.
- `persist-automation-status.yml`: validiert Diagnoseartefakte ausschließlich
  mit vertrauenswürdigem Code von `main` und persistiert sie auf dem orphan
  Branch `automation-status`.
- `export.yml`: erzeugt nach Änderungen an `main` alle Dokument-, Literatur-, Graph-, Berichts- und Statusartefakte samt Manifest und Prüfsummen.
- `pages.yml`: baut und veröffentlicht die MkDocs-Webseite, den interaktiven Wissensgraphen, dessen No-JS-Fallback und stabile Downloads über GitHub Pages.

## Wartung

Die Workflows verwenden aktuelle GitHub-Actions-Majors mit Node-24-Runtime. Dependabot prüft wöchentlich GitHub Actions und Python-Abhängigkeiten. Infrastrukturänderungen werden nicht automatisch gemergt.

## Sicherheits- und Qualitätsregeln

- minimale, explizite `GITHUB_TOKEN`-Berechtigungen;
- keine Ausführung von untrusted PR-Code über `pull_request_target`;
- feste Runner-Version `ubuntu-24.04`;
- Dependency-Caching nur anhand der versionierten Requirements-Dateien;
- Zeitlimits und Concurrency-Gruppen verhindern hängende oder überholte Läufe;
- Obsidian-Wikilinks müssen eindeutig auflösbar sein und werden erst im Build umgewandelt;
- `Literatur.md`, `references.bib` und `references.json` müssen gemeinsam aus den Studienkarten reproduzierbar sein;
- der Wissensgraph muss schema-valide sein, nur bekannte Knoten- und Relationstypen enthalten und darf keine ungeplant defekten Ziele besitzen;
- jeder Laufstatus muss vor Zusammenfassung und Veröffentlichung gegen das versionierte Schema validiert werden;
- der schreibberechtigte Persistenzworkflow führt niemals Code aus
  PR-Artefakten aus und akzeptiert nur Runs aus demselben Repository;
- verspätete Workflow-Ereignisse werden append-orientiert übernommen, ohne
  neuere Laufrevisionen oder `latest.json` zurückzusetzen;
- Graphbericht, Laufstatus und PR-Zusammenfassung werden auch bei einem fehlgeschlagenen Gate als Diagnoseartefakte hochgeladen;
- bei blockierenden Links erzeugt der Diagnosemodus zusätzlich eine nicht veröffentlichte Webvorschau, in der Fehler und fehlende Ziele sichtbar markiert sind;
- der idempotente PR-Kommentar wird anhand eines stabilen HTML-Markers aktualisiert, nicht bei jedem Lauf dupliziert;
- die Weboberfläche wird mit Playwright einschließlich Suche, Tagfilter, Tastaturbedienung und No-JS-Tabelle geprüft;
- die sichtbare vollständige Zitation muss den strukturierten `citation`-Feldern entsprechen;
- der PDF-Export verwendet Pandoc, CiteProc und LuaLaTeX mit freien DejaVu-Schriften;
- Pages-Deployments werden nicht während einer laufenden Veröffentlichung abgebrochen.

## Laufstatus und Graphdiagnose

Die Workflows setzen `RUNTIME_STATUS_MANAGED=1`, starten genau einen Lauf und
lassen die einzelnen Generatoren dessen Phase fortschreiben. Der kanonische
Status liegt während des Builds in `build/runtime-status.json`.
`scripts/graph_ci_summary.py` validiert ihn erneut, bevor es
`build/graph-ci-summary.md` und die GitHub-Actions-Zusammenfassung erzeugt. Der
Der vertrauenswürdige `workflow_run`-Persistenzworkflow veröffentlicht den
PR-Kommentar mit den Markern
`<!-- adhs-graph-ci-summary -->` und
`<!-- adhs-automation-recovery-status -->`.

Nach Abschluss überträgt der getrennte `workflow_run`-Workflow die validierte
Laufdatei und den vollständigen redigierten Diagnoseblock nach
`automation/status/<workflow>/` auf dem Branch `automation-status`. Wenn dieser
Branch nicht beschreibbar ist, bleiben beide Dateien 90 Tage als
Fallbackartefakt erhalten; der fachliche CI-Exitstatus wird dadurch nicht
verändert.
