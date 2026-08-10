ADHS-Automation – Laufstatus
Lauf: generator/e55d7dcb-2e86-4b6a-822e-b67262473bcb
Status: recovered
Phase: repair
Revision: 10
Erfolgreich: initialize, load_main, check_previous_run, check_existing_pr, read_prompts, research, create_branch, create_content, generate_outputs, validate, commit, push, create_pr, verify_pr, repair
Vorhanden: Branch: agent/einheit-20-substanzgebrauch-abhaengigkeit, branch: agent/einheit-20-substanzgebrauch-abhaengigkeit, pull_request: #50, workflow_run: 31074034736, commit: d7ce58cfefb5501ce006ee9f8c32add5a184cc14, workflow_run: 31074836338, workflow_run: 31074836341, workflow_run: 31074836327, commit: 55d50abb978f2f89c4f02d8dca1ce8e005e02793, workflow_run: 31238902177, commit: c57f5bdf315b587cd9dbf253ffa4c35624e17bae, workflow_run: 31354454312, commit: a89572b938201d36c85e73b91e9d2710b2406897, Commit: a89572b938201d36c85e73b91e9d2710b2406897, PR: #50
Fehlerklasse: validation
Fehlercode: repair_workflow_noncanonical_remark_cli
Fehler: Der Reparaturlauf bestätigte den deterministischen Literatur-Output und bestand den kanonischen changed-Remark-lint, brach danach aber an der zusätzlich eingefügten, im Repository nicht bereitgestellten Prüfung 'npx remark Literatur.md -q' mit 'could not determine executable to run' ab. Literatur.md wurde deshalb nicht committed; der temporäre Workflow wurde anschließend wieder aus dem PR-Diff entfernt.
Recovery-Level: retry_same_phase
Recovery: retry_literature_sync_without_noncanonical_npx_remark_cli
Neuer Inhalt erforderlich: nein
Blockiert nächsten Generatorlauf: nein
