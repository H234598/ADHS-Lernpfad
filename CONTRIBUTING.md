# Beitragen

## Single Source of Truth

- Kapitel: Markdown-Dateien
- Quellen: `references/*.md`
- Lernkarten: `cards/cards.yaml`
- Literaturverzeichnis, Graph und Exporte: generiert

## Pflichtprüfungen

```bash
python3 scripts/build_literature.py
python3 scripts/build_graph.py
python3 scripts/validate_compendium.py
python3 scripts/build_combined.py
python3 scripts/build_anki.py
mkdocs build --strict
```

## Evidenzregeln

- Gruppenbefund ≠ Aussage über jede Einzelperson.
- Korrelation ≠ Kausalität.
- Evidenzgrad und Konsensstatus getrennt angeben.
- ADHS, Autismus und Parkinson nicht gleichsetzen.
- Bestehende Aussagen bei neuer Evidenz korrigieren und im Changelog dokumentieren.
