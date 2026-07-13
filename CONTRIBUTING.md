# Beitragen

## Single Source of Truth

- Kapitel: Markdown-Dateien
- Quellen: `references/*.md`
- Lernkarten: `cards/cards.yaml`
- Literaturverzeichnis, Graph und Exporte: generiert

## Umfang regulärer Einheiten

- harte Untergrenze: 800 Fließtextwörter
- CI-Warnung: unter 1.000 Fließtextwörtern
- Zielbereich: 1.000–2.000 Fließtextwörter
- harte Obergrenze: 2.500 Fließtextwörter

Gezählt wird der didaktische Fließtext ohne YAML-Frontmatter, Navigation und Diagrammcode. Benötigt ein Thema mehr als 2.500 Wörter, wird es in mehrere fachlich sinnvolle Einheiten geteilt. Die Grenzen dürfen nicht mit Wiederholungen oder Fülltext erreicht werden.

## Pflichtprüfungen

```bash
python3 scripts/build_literature.py
python3 scripts/build_graph.py
python3 scripts/validate_compendium.py
python3 scripts/build_combined.py
python3 scripts/build_anki.py
python3 scripts/build_docs.py
mkdocs build --strict
```

## Evidenzregeln

- Gruppenbefund ≠ Aussage über jede Einzelperson.
- Korrelation ≠ Kausalität.
- Evidenzgrad und Konsensstatus getrennt angeben.
- ADHS, Autismus und Parkinson nicht gleichsetzen.
- Bestehende Aussagen bei neuer Evidenz korrigieren und im Changelog dokumentieren.
