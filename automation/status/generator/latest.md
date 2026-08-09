ADHS-Automation benötigt einen weiteren Reparaturzyklus
Lauf: generator/e55d7dcb-2e86-4b6a-822e-b67262473bcb
Status: failed
Phase: repair
Revision: 8
Erfolgreich: initialize, load_main, check_previous_run, check_existing_pr, read_prompts, research, create_branch, create_content, generate_outputs, validate, commit, push, create_pr, verify_pr, repair
Vorhanden: Draft-PR #50 auf Branch agent/einheit-20-substanzgebrauch-abhaengigkeit
Aktueller Head: c57f5bdf315b587cd9dbf253ffa4c35624e17bae
Einheit: 20 – Substanzgebrauch, Abhängigkeit und ADHS
Umfang: 1.931 Fließtextwörter, 53 Literaturquellen, 20 Anki-Karten
Reparaturversuch dieses Wächterlaufs: temporärer Workflow 31293890245 führte scripts/build_literature.py aus und bestätigte deterministisch ausschließlich Literatur.md mit last_reviewed=2026-08-08; references.bib und references.json blieben unverändert; npm-Audit meldete 0 Schwachstellen; der kanonische changed-Remark-lint prüfte 12 geänderte Markdown-Dateien ohne Befund
Blocker dieses Reparaturversuchs: anschließend wurde zusätzlich npx remark Literatur.md -q ausgeführt; im Repository ist dafür kein ausführbares remark-CLI bereitgestellt, npm brach mit "could not determine executable to run" ab; diese zusätzliche Prüfung gehört nicht zum kanonischen Projektvertrag
Cleanup: der fehlgeschlagene Einmal-Workflow wurde mit Commit c57f5bdf315b587cd9dbf253ffa4c35624e17bae wieder aus dem PR-Diff entfernt; aktueller Netto-Diff enthält weiterhin 17 reguläre Dateien und keine sensiblen Workflowpfade
CodeRabbit: success; sämtliche Reviewthreads gelöst; ungelöste Threads 0; kein Agent-CodeRabbit-Dissens
Aktueller Inhaltssollzustand: Literatur.md muss weiterhin per scripts/build_literature.py von last_reviewed 2026-08-06 auf 2026-08-08 regeneriert und committed werden; dieser geprüfte Output wurde wegen des späteren Workflowabbruchs nicht gepusht
Recovery: retry_same_phase / repair; im nächsten Wächterlauf denselben Generatorlauf und PR #50 fortsetzen, Literaturregeneration erneut ausführen, den nichtkanonischen npx-remark-Aufruf weglassen, anschließend die vollständige projektdefinierte Validierung durchführen
Neuer Inhalt erforderlich: nein
Ready for review: nein
Merge: nein
Blockiert nächsten Generatorlauf: ja
