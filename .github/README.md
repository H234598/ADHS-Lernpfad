# GitHub-Automation

## Workflows

- `validate.yml`: stabiles Pflichtgate `Validate and build` für Python- und Browsertests, Quellen, strukturierte Bibliografie, Obsidian-Links, Graphschema, Runtime-Status, Wortgrenzen, Anki und MkDocs.
- `remark-lint.yml`: reproduzierbares Pflichtgate `Remark lint (blocking)` für die gegenüber `main` geänderten Markdown-Dateien; installiert ausschließlich das versionierte Lockfile, prüft hohe und kritische npm-Sicherheitsbefunde und behandelt jede Lintmeldung als Fehler.
- `coderabbit-hard-gate.yml`: vertrauenswürdiges Pflichtgate `CodeRabbit review gate (blocking)` für ein aktuelles erfolgreiches CodeRabbit-Signal, vollständig gelöste Threads und das Fehlen ungeklärter Agent-CodeRabbit-Dissense.
- `coderabbit-after-green.yml`: kostenbewusster Requester, der CodeRabbit für einen Head-SHA exakt einmal und erst dann anfordert, wenn sämtliche Non-CodeRabbit-Checks und Statuskontexte grün sind.
- `runtime-status-check.yml`: fokussierter Vertragscheck für Statusschema, CLI und atomare Aktualisierungen.
- `persist-automation-status.yml`: validiert Diagnoseartefakte ausschließlich mit vertrauenswürdigem Code von `main` und persistiert sie auf dem orphan Branch `automation-status`.
- `export.yml`: erzeugt nach Änderungen an `main` alle Dokument-, Literatur-, Graph-, Berichts- und Statusartefakte samt Manifest und Prüfsummen.
- `pages.yml`: baut und veröffentlicht die MkDocs-Webseite, den interaktiven Wissensgraphen, dessen No-JS-Fallback und stabile Downloads über GitHub Pages.

## Wartung

Die Workflows verwenden aktuelle GitHub-Actions-Majors mit Node-24-Runtime. Dependabot prüft wöchentlich GitHub Actions und Python-Abhängigkeiten. Infrastrukturänderungen werden nicht automatisch gemergt.

## Sicherheits- und Qualitätsregeln

- minimale, explizite `GITHUB_TOKEN`-Berechtigungen;
- `pull_request_target` führt ausschließlich die auf `main` liegende vertrauenswürdige Gate-Implementierung aus und checkt keinen untrusted PR-Code aus;
- CodeRabbit-Auto-Review, Draft-Review und Auto-Incremental-Review sind deaktiviert; bezahlte Reviews werden ausschließlich durch den After-Green-Requester ausgelöst;
- der CodeRabbit-Requester dedupliziert pro aktuellem Head-SHA und fordert bei einem Fix-Commit erst nach erneut vollständig grünen Non-CodeRabbit-Gates einen weiteren Review an;
- Fork-PRs erhalten aus Kosten- und Vertrauensgründen keinen automatischen bezahlten CodeRabbit-Request;
- das CodeRabbit-Gate zählt seinen eigenen Check nicht als externes CodeRabbit-Signal;
- ein dokumentierter Dissens bleibt auch nach späteren Head-Commits blockierend, bis er passend zum ursprünglichen Marker aufgelöst wird;
- feste Runner-Version `ubuntu-24.04`;
- Dependency-Caching nur anhand versionierter Lock- und Requirements-Dateien;
- `npm ci` und `npm audit --audit-level=high` sichern die Markdown-Prüfkette reproduzierbar ab;
- Remark verarbeitet Obsidian-spezifische Wikilink-, Embed- und Callout-Syntax über deterministische Sanitierung, während die eigentliche Linksemantik weiterhin durch die Projektvalidatoren geprüft wird;
- `.codacy.yml` schließt Markdown ausschließlich aus Codacys nicht Obsidian-kompatiblem `remark-lint` aus; die Auswahl des lokalen Codacy-Hardgates wird im Workflow explizit und testbar festgelegt;
- `codacy.yml` führt die repositoryrelevanten Analyzer Bandit, Prospector, Pylint (`pylintpython3`), Ruff, ShellCheck, PSScriptAnalyzer, ESLint 9, Biome und Stylelint isoliert in einer fail-closed Matrix aus; jeder Analyzer besitzt ein 10-Minuten-Werkzeuglimit, jede Matrixzeile eine eigene SARIF-Kategorie und jeder Matrixjob ein 20-Minuten-Gesamtlimit;
- Opengrep ist bewusst nicht Teil dieses lokalen Codacy-Pflichtgates: Codacy Analysis CLI 7.9.25 startet bei `--tool opengrep` innerhalb eines einzigen Aufrufs wiederholt Opengrep-Container; mehrere Läufe enden schnell erfolgreich, während ein weiterer reproduzierbar bis zum 15-Minuten-Tooltimeout hängen kann. Das bloße Erhöhen des Timeouts würde den Hänger nur verlängern. Eine spätere Codacy-CLI-Migration kann Opengrep separat wieder qualifizieren;
- bekannte inkompatible, redundante oder ohne Projektkonfiguration nicht ausführbare Legacy-/Default-Analyzer werden ebenfalls nicht in das lokale Pflichtgate aufgenommen;
- die Markdown-Qualität bleibt durch den projektinternen Pflichtcheck und die separate Obsidian-Linkvalidierung blockierend abgesichert;
- Zeitlimits und Concurrency-Gruppen verhindern hängende oder überholte Läufe;
- Obsidian-Wikilinks müssen eindeutig auflösbar sein und werden erst im Build umgewandelt;
- `Literatur.md`, `references.bib` und `references.json` müssen gemeinsam aus den Studienkarten reproduzierbar sein;
- der Wissensgraph muss schema-valide sein, nur bekannte Knoten- und Relationstypen enthalten und darf keine ungeplant defekten Ziele besitzen;
- jeder Laufstatus muss vor Zusammenfassung und Veröffentlichung gegen das versionierte Schema validiert werden;
- der schreibberechtigte Persistenzworkflow führt niemals Code aus PR-Artefakten aus und akzeptiert nur Runs aus demselben Repository;
- verspätete Workflow-Ereignisse werden append-orientiert übernommen, ohne neuere Laufrevisionen oder `latest.json` zurückzusetzen;
- Graphbericht, Laufstatus und PR-Zusammenfassung werden auch bei einem fehlgeschlagenen Gate als Diagnoseartefakte hochgeladen;
- bei blockierenden Links erzeugt der Diagnosemodus zusätzlich eine nicht veröffentlichte Webvorschau, in der Fehler und fehlende Ziele sichtbar markiert sind;
- der idempotente PR-Kommentar wird anhand eines stabilen HTML-Markers aktualisiert, nicht bei jedem Lauf dupliziert;
- die Weboberfläche wird mit Playwright einschließlich Suche, Tagfilter, Tastaturbedienung und No-JS-Tabelle geprüft;
- die sichtbare vollständige Zitation muss den strukturierten `citation`-Feldern entsprechen;
- der PDF-Export verwendet Pandoc, CiteProc und LuaLaTeX mit freien DejaVu-Schriften;
- Pages-Deployments werden nicht während einer laufenden Veröffentlichung abgebrochen.

## Variante B für schreibende Workflows

`scripts/validate_ci_mutation_safety.py` ist ein blockierender, ausschließlich mit der Python-Standardbibliothek arbeitender Vertragscheck und läuft direkt in `Validate and build`. Er verändert keine Berechtigungen und macht keinen read-only Workflow schreibend. Jeder einzelne Workflow-Schritt mit einem tatsächlich ausführbaren `git commit` oder `git push` muss vollständig enthalten:

- `git status --short` oder `--porcelain` **vor** dem No-op-Guard;
- einen staged `--name-status`- oder `--stat`-Diff **vor** dem No-op-Guard;
- einen staged No-op-Guard mit `git diff --cached --quiet` oder `git diff --staged --quiet` **vor** dem ersten Commit/Push;
- bei fragmentierten Payloads explizite Ist-/Soll-SHA-256-Ausgaben, Fragmentgrößen und Fragmentprüfsummen sowie eine bestmögliche `tar -tzf`-Diagnose im Fehlerfall;
- einen tatsächlichen Ist-/Soll-Prüfsummenvergleich, der bei Abweichung mit einem von null verschiedenen Exitcode endet;
- weiterhin blockierende Audits: weder `|| true`, `|| exit 0`, mehrzeilige Shell-Bypässe noch `continue-on-error: true` sind für Audit-Schritte zulässig.

Der Parser bewertet ausführbare Shell-Kommandos statt bloßer Texttreffer: Ausgaben wie `echo "git commit"` sind kein Writer, während über Backslash fortgesetzte `git`-Kommandos weiterhin erkannt werden. Kommentierte Checksum-/Diagnosezeilen zählen nicht als Sicherheitsnachweis. Die Regeln sind durch synthetische Positiv-, Negativ- und Zwei-Writer-Tests abgesichert.

## CodeRabbit-Kostenregel

`.coderabbit.yaml` deaktiviert automatische, Draft- und inkrementelle Reviews. `coderabbit-after-green.yml` beobachtet die abgeschlossenen Non-CodeRabbit-Workflows und prüft anschließend den **aktuellen PR-Head**. Mindestens `Validate and build`, `Build all download formats`, `Remark lint (blocking)`, `Learning card policy (blocking)`, `Codacy Security Scan` und der Status `qlty check` müssen erfolgreich sein; zusätzlich darf kein weiterer beobachteter Non-CodeRabbit-Check rot oder noch laufend sein.

Erst dann wird ein Kommentar mit `@coderabbitai review` und einem Head-SHA-Marker erzeugt. Existiert für denselben Head bereits ein CodeRabbit-Review oder ein solcher Request-Marker, wird nichts erneut ausgelöst. Nach einem Fix-Commit beginnt der Prozess für den neuen SHA wieder bei den kostenlosen/anderen Gates.

## Laufstatus und Graphdiagnose

Die Workflows setzen `RUNTIME_STATUS_MANAGED=1`, starten genau einen Lauf und lassen die einzelnen Generatoren dessen Phase fortschreiben. Der kanonische Status liegt während des Builds in `build/runtime-status.json`. `scripts/graph_ci_summary.py` validiert ihn erneut, bevor es `build/graph-ci-summary.md` und die GitHub-Actions-Zusammenfassung erzeugt. Der vertrauenswürdige `workflow_run`-Persistenzworkflow veröffentlicht den PR-Kommentar mit den Markern `<!-- adhs-graph-ci-summary -->` und `<!-- adhs-automation-recovery-status -->`.

Nach Abschluss überträgt der getrennte `workflow_run`-Workflow die validierte Laufdatei und den vollständigen redigierten Diagnoseblock nach `automation/status/<workflow>/` auf dem Branch `automation-status`. Wenn dieser Branch nicht beschreibbar ist, bleiben beide Dateien 90 Tage als Fallbackartefakt erhalten; der fachliche CI-Exitstatus wird dadurch nicht verändert.
