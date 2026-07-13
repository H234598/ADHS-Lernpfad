# Automatisierungsprompt: nächste Einheit

Arbeite im Repository `H234598/ADHS-Lernpfad` und ergänze **genau eine** neue fortlaufende Lerneinheit.

1. Lies README, Einführung, Index, letzte zwei Kapitel, Glossar, Referenzkarten und Roadmap.
2. Führe vor dem Schreiben den Ablauf aus `prompts/DEEP-RESEARCH-PROMPT.md` durch.
3. Erstelle die Einheit im passenden Ordner mit YAML-Feldern `title`, `level`, `estimated_time`, `difficulty`, `prerequisites`, `tags`, `last_reviewed`, `evidence`, `status`, `references`.
4. Ergänze mindestens ein sinnvolles Mermaid-Diagramm; erstelle SVG nur, wenn es über das Diagramm hinaus echten Mehrwert bietet.
5. Lege neue Quellen als einzelne Dateien in `references/` an. Bearbeite `Literatur.md` nicht manuell.
6. Ergänze passende Anki-Karten in `cards/cards.yaml`.
7. Ergänze Wikilinks und den Wissensgraphen.
8. Markiere Evidenz und Forschungsstatus getrennt; vermeide starke Kausalaussagen ohne tragfähige Evidenz.
9. Führe aus:
   - `python3 scripts/build_literature.py`
   - `python3 scripts/build_graph.py`
   - `python3 scripts/validate_compendium.py`
   - `python3 scripts/build_combined.py`
   - `python3 scripts/build_anki.py`
   - `mkdocs build --strict`
10. Arbeite auf `agent/einheit-NN-kurztitel`, erstelle einen Draft-PR und merge niemals automatisch.

Der PR nennt neue Evidenz, Unsicherheiten, geänderte Alttexte und alle Prüfergebnisse.
