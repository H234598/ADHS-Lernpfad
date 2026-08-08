ADHS-Automation benötigt einen weiteren Reparaturzyklus
Lauf: generator/e55d7dcb-2e86-4b6a-822e-b67262473bcb
Status: failed
Phase: repair
Revision: 7
Erfolgreich: initialize, load_main, check_previous_run, check_existing_pr, read_prompts, research, create_branch, create_content, generate_outputs, validate, commit, push, create_pr, verify_pr, repair
Vorhanden: Draft-PR #50 auf Branch agent/einheit-20-substanzgebrauch-abhaengigkeit
Aktueller Head: 55d50abb978f2f89c4f02d8dca1ce8e005e02793
Einheit: 20 – Substanzgebrauch, Abhängigkeit und ADHS
Umfang: 1.931 Fließtextwörter, 53 Literaturquellen, 20 Anki-Karten
Reparatur dieses Laufs: CodeRabbit-Hinweis zu Comiskey2026 fachlich geprüft und korrigiert; bidirektionale Versorgungsempfehlung korrekt Young2023 zugeordnet; drei obsolete Workflow-Threads nach Prüfung des aktuellen Diffs aufgelöst; CodeRabbit hat die Comiskey-Korrektur akzeptiert; ungelöste Threads 0; kein Dissens
Aktuelle Gates: Remark-lint success; CodeRabbit success; qlty success; Validate compendium failure; Export wegen Validate-Fehler übersprungen; Codacy beim Status-Snapshot noch laufend
Fehlerfingerabdruck: scripts/build_literature.py regeneriert Literatur.md nach last_checked=2026-08-08 deterministisch mit last_reviewed=2026-08-08; im aktuellen Head steht dort noch 2026-08-06
Validierungsnachweis: Abhängigkeiten ohne Konflikte, npm 0 Schwachstellen, 159 Pytest-Tests plus 2 Subtests erfolgreich; Fehler tritt anschließend bei git diff --exit-code nach build_literature.py auf
Recovery: retry_same_phase / repair; im nächsten Wächterlauf Literaturausgaben mit scripts/build_literature.py regenerieren, den daraus resultierenden Literatur.md-Header committen und die vollständige Validierung erneut ausführen
Neuer Inhalt erforderlich: nein
Ready for review: nein
Merge: nein
Blockiert nächsten Generatorlauf: ja
