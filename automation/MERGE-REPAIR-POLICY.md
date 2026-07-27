# Merge- und Reparaturpolicy

## Verbindliche Gates

Automatische Einheiten dürfen nur freigegeben und gemergt werden, wenn alle Prüfungen denselben aktuellen Head-Commit betreffen:

- erste beziehungsweise zweite Projekt-CI vollständig grün,
- `Remark lint (blocking)` erfolgreich,
- CodeRabbit-Signal erfolgreich,
- `CodeRabbit review gate (blocking)` erfolgreich,
- sämtliche CodeRabbit-Threads gelöst,
- kein dokumentierter Agent-CodeRabbit-Dissens offen,
- PR konfliktfrei und mergebar.

CodeRabbit ist ein hartes Gate. Schweigen, ausstehende Prüfung, Limiterschöpfung oder ein fehlendes Signal werden nicht als Zustimmung interpretiert.

## Zeitmodell

Für einen PR mit Erstellungszeit `created_at` gelten in `Europe/Berlin`:

```text
review_eligible_at = created_at + 2 Stunden
repair_eligible_at = max(review_eligible_at, 20:00 am Erstellungstag)
```

Bis `repair_eligible_at` prüft der Merge-Wächter weiter, sammelt Diagnosen und wartet. Eine rote CI startet vor dieser Frist keine inhaltliche Reparatur. Der Wächter beendet die Bearbeitung nicht nach einer festen Anzahl roter Läufe.

Ab dem Reparaturfenster ist pro Wächterlauf genau ein sicherer Reparaturzyklus auf dem bestehenden PR-Branch zulässig. Neue oder veränderte Ursachen können in späteren Läufen erneut repariert werden. Identische Fehler dürfen keine identischen Wiederholungscommits erzeugen.

## CodeRabbit-Threads

Jeder Thread wird als eine von drei Kategorien behandelt:

1. **gültig:** Ursache beheben, prüfen, antworten und danach auflösen;
2. **gegenstandslos:** aktuellen Diff prüfen, konkrete Begründung dokumentieren und danach auflösen;
3. **Dissens:** nicht auflösen, sondern mit dem Marker `coderabbit-disagreement` als manuellen harten Blocker dokumentieren.

Auch veraltete Threads bleiben blockierend, solange sie nicht begründet abgeschlossen sind.

## Evidenzreparatur

Betrifft ein Hinweis Aktualität, Risiko, Kausalität, Leitlinien oder das Reviewdatum, muss der Reparaturzyklus die wissenschaftliche Recherche bis zum aktuellen Datum erneut ausführen. Text, Frontmatter, Studienkarten und generierte Literaturausgaben werden gemeinsam aktualisiert. Relative Gruppenmaße, absolute Risiken, Kausalität, Endpunkte und individuelle Prognosen werden getrennt dargestellt.

## Remark-lint

Markdown wird über den exakt gepinnten direkten `remark`-Prozessor geprüft; die veraltete CLI-Abhängigkeitskette wird nicht verwendet. Der Lintlauf sanitisiert ausschließlich Obsidian-spezifische Wikilink-, Embed- und Callout-Syntax für den Parser, während die eigentliche interne Linkvalidierung unverändert durch die Projektvalidatoren erfolgt. Auf Pull Requests werden die gegenüber `main` geänderten Markdown-Dateien geprüft; jede Remark-lint-Meldung blockiert den Check. Zusätzlich muss das npm-Abhängigkeitsaudit ohne hohe oder kritische Befunde bestehen.

```bash
npm ci
npm run audit:dependencies
REMARK_BASE_SHA=origin/main REMARK_HEAD_SHA=HEAD \
  npm run lint:markdown:changed
```

Der Codacy-SARIF-Workflow bleibt eine zusätzliche Analyse. Sein erfolgreicher Upload ersetzt weder den blockierenden Remark-lint-Check noch das npm-Abhängigkeitsaudit.

## Reproduzierbare Policyentscheidung

`scripts/merge_repair_policy.py` berechnet Review- und Reparaturfristen und liefert eine maschinenlesbare Aktion. `scripts/review_gate.py` prüft den aktuellen CodeRabbit-Status, ungelöste Threads und dokumentierte Dissense. Beide Komponenten besitzen Regressionstests.
