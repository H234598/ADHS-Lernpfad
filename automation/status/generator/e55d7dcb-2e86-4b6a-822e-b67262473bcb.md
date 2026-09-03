# Generatorstatus – Einheit 20 – Revision 14

## Zustand

- Run-ID: `e55d7dcb-2e86-4b6a-822e-b67262473bcb`
- Status: `running`
- Phase: `wait_review`
- PR: `#50`
- Branch: `agent/einheit-20-substanzgebrauch-abhaengigkeit`
- Head: `daad16b1ee45c1ed2523dab48548c3a2f386506e`
- aktueller `main`: `450a608f5ad9aa2853c86847d2f129b717be77fc`
- Branch hinter `main`: `0`
- neue Einheit erforderlich: `nein`

## Recovery-Fortsetzung

Der bisherige manuelle Infrastrukturblocker ist erfüllt: PR #51 wurde als
`450a608f5ad9aa2853c86847d2f129b717be77fc` nach `main` gemergt.

PR #50 wurde anschließend konfliktbewusst mit dem aktuellen `main`
synchronisiert. Der gemeinsame Pfad `mkdocs.yml` wurde so aufgelöst, dass
sowohl die Änderung aus `main` (Entfernung von `navigation.sections`) als auch
der Unit-20-Navigationseintrag erhalten bleiben.

Der Netto-Diff gegen aktuellen `main` umfasst weiterhin genau 17 reguläre
Inhalts-, Navigations-, Metadaten- und Literaturdateien; keine sensible
`.github/`-Infrastruktur verbleibt im Unit-Diff.

## Erster regulärer CI-Zyklus nach Synchronisation

- Validate compendium: `in_progress` – Run `33713568051`
- Remark lint: `in_progress` – Run `33713568060`
- Codacy Security Scan: `queued` – Run `33713568054`
- CodeRabbit aktueller Head: noch abzuwarten
- ungelöste historische CodeRabbit-Threads: `0`
- dokumentierter CodeRabbit-Dissens: `nein`

## Nächster zulässiger Schritt

Alle erwarteten ersten Gates auf exakt Head
`daad16b1ee45c1ed2523dab48548c3a2f386506e` abwarten.

Nur wenn Validate, Export, Remark, Codacy, qlty, CodeRabbit und
`CodeRabbit review gate (blocking)` vollständig erfolgreich sind, alle
Reviewthreads gelöst bleiben, kein Dissens besteht und der PR mergebar bleibt,
darf ein späterer Wächter `Draft -> Ready for review` setzen und muss danach
ohne Merge enden.
