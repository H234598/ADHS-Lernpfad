ADHS-Automation blockiert
Lauf: generator/e55d7dcb-2e86-4b6a-822e-b67262473bcb
Status: failed
Phase: repair
Revision: 5
Erfolgreich: initialize, load_main, check_previous_run, check_existing_pr, read_prompts, research, create_branch, create_content, generate_outputs, validate, commit, push, create_pr, verify_pr
Vorhanden: Draft-PR #50 auf Branch agent/einheit-20-substanzgebrauch-abhaengigkeit
Aktueller Head: 408e78da90ac6809aa3612b83752f8e0ce7206dd
Einheit: 20 – Substanzgebrauch, Abhängigkeit und ADHS
Umfang: 1.931 Fließtextwörter, 53 Literaturquellen, 20 Anki-Karten
Validierter Basisstand: 159 Pytest-Tests plus 2 Subtests, 4 Playwright-Tests, Remark-lint über 104 Dateien, Wissensgraph 250 Knoten/892 Kanten ohne Befunde
CodeRabbit: 5 offene Threads; kein fachlicher Agent-CodeRabbit-Dissens
Reparaturversuche: 3
Versuch 1: exakter Autorenblock passte nicht zur realen Datei
Versuch 2: automatisch erzeugte Autorenliste hatte ungültige YAML-Einrückung
Versuch 3: 22 Autor:innen erfolgreich geparst, 53 Literaturquellen regeneriert und Abhängigkeits-, Sync-, Pytest-, JavaScript- und Remark-Prüfungen bestanden; danach wurden die beabsichtigten generierten Literaturänderungen durch git diff --exit-code fälschlich als Fehler behandelt
Fehlercode: repair_generated_diff_misclassified
Recovery: Reparatur- und Stagingarchitektur prüfen; danach denselben Branch und PR #50 fortsetzen
Wichtig: keine neue Einheit und keine neue Run-ID erzeugen
Aktueller Diff: 17 reguläre Dateien, keine temporären Workflows; manual-merge-required gesetzt
Frühestes zusätzliches Reviewfenster: 2026-08-06T18:00:00Z / 20:00 Europe/Berlin
Neuer Inhalt erforderlich: nein
Blockiert nächsten Generatorlauf: ja
