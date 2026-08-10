ADHS-Automation – Laufstatus
Lauf: generator/e55d7dcb-2e86-4b6a-822e-b67262473bcb
Status: running
Phase: wait_review
Revision: 12
Erfolgreich: initialize, load_main, check_previous_run, check_existing_pr, read_prompts, research, create_branch, create_content, generate_outputs, validate, commit, push, create_pr, verify_pr, repair
Vorhanden: Draft-PR #50 auf Branch agent/einheit-20-substanzgebrauch-abhaengigkeit
Aktueller Head: a89572b938201d36c85e73b91e9d2710b2406897
Reparatur: scripts/build_literature.py hat 53 Quellen deterministisch regeneriert; Literatur.md enthält last_reviewed=2026-08-08; references.bib und references.json blieben reproduzierbar unverändert; der temporäre Reparaturworkflow wurde vor dem finalen Commit entfernt.
Validierung des Reparaturstands: pip check erfolgreich; npm-Audit 0 Schwachstellen; kanonischer changed-Remark-lint erfolgreich; Prompt-Baseline intakt; POSIX-Sync-Tests erfolgreich; 159 Pytest-Tests plus 2 Subtests bestanden; npm-Test erfolgreich; Link-, Wissensgraph- und Kompendiumsvalidierung erfolgreich; 250 Graphknoten und 892 Kanten; 20 Kapitel und 53 Quellen; Combined-, Anki-, Dokumentations- und MkDocs-Build erfolgreich; vier Playwright-Webtests bestanden.
CodeRabbit: success auf dem finalen Head; qlty: success; ungelöste Reviewthreads: 0; Agent-CodeRabbit-Dissens: nein.
Erster regulärer CI-Zyklus des finalen Heads: Validate compendium Run 31354538933 = action_required; Remark lint Run 31354538922 = action_required; Codacy Security Scan Run 31354538928 = action_required; Build all download formats noch nicht gestartet.
Einordnung: Der Reparaturpush wurde aus GitHub Actions mit dem Repository-GITHUB_TOKEN erzeugt. Die dadurch ausgelösten pull_request-Läufe stehen vor Ausführung auf action_required und benötigen eine GitHub-Freigabe beziehungsweise einen zulässigen user-authentifizierten Neustart. Es wurde kein Gate als grün vorgetäuscht.
Nächster zulässiger Schritt: die drei action_required-Läufe freigeben oder user-authentifiziert neu starten; danach im nächsten Wächterlauf denselben unveränderten Head prüfen. Erst bei vollständig grüner erster CI darf Ready for review gesetzt werden. Dieser Reparaturwächter endet nach dem erfolgreichen Reparaturpush und der Statusübergabe.
Neuer Inhalt erforderlich: nein
Ready for review: nein
Merge: nein
Blockiert neuen Generatorlauf: ja
