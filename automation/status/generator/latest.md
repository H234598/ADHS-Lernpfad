ADHS-Automation – Laufstatus
Lauf: generator/e55d7dcb-2e86-4b6a-822e-b67262473bcb
Status: blocked
Phase: wait_review
Revision: 13
Erfolgreich: initialize, load_main, check_previous_run, check_existing_pr, read_prompts, research, create_branch, create_content, generate_outputs, validate, commit, push, create_pr, verify_pr, repair
Vorhanden: Draft-PR #50 auf Branch agent/einheit-20-substanzgebrauch-abhaengigkeit; Unit-Head a89572b938201d36c85e73b91e9d2710b2406897; Infrastruktur-PR #51 auf Branch fix/codacy-timeout, Head 3ee002683ea0245f34fb66755a4aef105ad26541.
Aktueller main: db908011ba0d16fd0c3b0508fc84edab57d4e0a1; Unit-Branch ist 1 Commit hinter main und weiterhin mergebar.
Einheit-20-Reparatur: Literatur mit 53 Quellen deterministisch; Literatur.md last_reviewed=2026-08-08; vollständige Reparaturvalidierung erfolgreich; 159 Pytest-Tests plus 2 Subtests, npm-Audit 0 Schwachstellen, 4 Playwright-Webtests, 250 Graphknoten / 892 Kanten, 20 Kapitel / 53 Quellen.
Erster regulärer Unit-CI-Zyklus: Validate compendium Run 31354538933 Attempt 2 = success; Validate and build Job 93647145580 = success; Build all download formats Job 93647462779 = success; Remark lint Run 31354538922 Attempt 2 = success; CodeRabbit = success; qlty = success; ungelöste CodeRabbit-Threads = 0; Dissens = nein. Codacy Security Scan Run 31354538928 Attempt 2 hing im Legacy-CLI-Schritt und wurde nach mehr als fünf Stunden abgebrochen; der erste Unit-CI-Zyklus ist deshalb nicht vollständig grün.
Infrastrukturreparatur: PR #51 behebt den Legacy-Codacy-Hänger. Auf Head 3ee002683ea0245f34fb66755a4aef105ad26541 sind Validate compendium Run 31665706102, Remark lint Run 31665706117, Codacy Security Scan Run 31665706165, qlty, CodeRabbit und CodeRabbit hard gate Run 31665704873 Attempt 2 erfolgreich; alle Reviewthreads sind gelöst; kein Dissens; PR ist mergebar.
Fehlerklasse: security_policy
Fehlercode: sensitive_infrastructure_merge_required
Fehler: PR #51 ändert .github/workflows/codacy.yml. Die Repositorypolicy verbietet den automatischen Merge sensibler Infrastruktur durch den Einheiten-Wächter.
Recovery-Level: manual_intervention
Recovery: PR #51 menschlich nach main mergen. Danach denselben Generatorlauf fortsetzen, PR #50 mit dem neuen main synchronisieren und einen neuen vollständigen ersten Unit-CI-Zyklus ausführen. Erst bei vollständig grünem ersten Zyklus Ready for review; Merge erst nach dem vorgeschriebenen zweiten vollständig grünen Zyklus.
Neuer Inhalt erforderlich: nein
Ready for review: nein
Merge: nein
Blockiert neuen Generatorlauf: ja
