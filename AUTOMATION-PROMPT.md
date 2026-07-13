# Automatisierungsprompt: nächste Einheit

Arbeite im Repository `H234598/ADHS-Lernpfad` und ergänze **genau eine** neue fortlaufende Lerneinheit.

## Verbindlicher Umfang

Eine Einheit ist eine echte **10- bis 20-minütige Lerneinheit**, nicht nur eine Kurznotiz mit entsprechendem YAML-Etikett.

- Zielbereich: ungefähr **800–1.600 Wörter** didaktischer Haupttext.
- Harte Untergrenze für Grundlagenkapitel: **700 Wörter** nach Abzug von YAML, Navigation und Codeblöcken.
- Komplexe Themen dürfen mehr Raum erhalten, wenn die zusätzliche Länge fachlich nötig und klar gegliedert ist.
- Niemals künstlich durch Wiederholung, Füllsätze oder erzwungene Autismus-/Parkinson-Bezüge verlängern.
- Lieber ein komplexes Thema in zwei aufeinanderfolgende Einheiten teilen, als eine unstrukturierte Textwand zu erzeugen.

## Vor dem Schreiben

1. Lies README, Einführung, Index, die letzten zwei Kapitel, Glossar, Referenzkarten und Roadmap.
2. Führe den Ablauf aus `prompts/DEEP-RESEARCH-PROMPT.md` durch und gleiche den Stand mit aktuellen Leitlinien, Konsensuspapieren, Reviews und Meta-Analysen ab.
3. Bestimme die nächste freie Einheitsnummer und den fachlich logischen nächsten Baustein.
4. Prüfe, ob bestehende Kapitel wegen neuer Evidenz korrigiert werden müssen. Änderungen an Alttexten müssen im PR begründet werden.

## Pflichtstruktur jeder Einheit

Jede Einheit enthält mindestens:

1. YAML-Frontmatter mit `title`, `level`, `estimated_time: 10–20 min`, `difficulty`, `prerequisites`, `tags`, `last_reviewed`, `evidence`, `status`, `references`, `minimum_reading_minutes: 10` und `maximum_reading_minutes: 20`;
2. ein klares Lernziel;
3. eine verständliche Einführung und Begriffsabgrenzung;
4. mindestens drei inhaltliche Erklärungsabschnitte;
5. eine wissenschaftliche Einordnung mit Grenzen und Heterogenität;
6. mindestens ein sinnvolles Mermaid-Diagramm, wenn ein Prozess oder Zusammenhang dargestellt wird;
7. eine kleine alltagstaugliche Übung oder Beobachtungsaufgabe, sofern fachlich sinnvoll;
8. Verbindungen zu Autismus oder Parkinson nur, wenn sie fachlich relevant sind;
9. eine Review-Frage mit in `<details>` ausklappbarer Antwort;
10. eine hochwertige Kernquelle als Studienkarte;
11. einen präzisen Merksatz;
12. Navigation zur vorherigen und nächsten Einheit.

## Wissenschaftliche Regeln

- Trenne gut abgesicherte Befunde, plausible Modelle und offene Fragen.
- Kennzeichne Gruppenbefunde; leite daraus keine sicheren Aussagen über Einzelpersonen ab.
- Vermeide populäre Verkürzungen wie „ADHS ist Dopaminmangel“ und „Dopamin ist das Glückshormon“.
- Stelle ADHS, Autismus und Parkinson niemals als dieselbe Art von Erkrankung dar.
- Verwende keine Foren, SEO-Ratgeber oder Herstellertexte als Evidenz.
- Gib DOI, PubMed-ID oder stabilen Verlagslink an, soweit vorhanden.
- Formuliere keine Diagnose- oder Therapieversprechen.

## Dateipflege

1. Lege die Einheit im fachlich passenden Ordner ab.
2. Lege neue Quellen als einzelne Dateien in `references/` an; `Literatur.md` wird generiert.
3. Ergänze neue Fachbegriffe in `Glossar.md`.
4. Ergänze passende Anki-Karten in `cards/cards.yaml`.
5. Aktualisiere README, Index, MkDocs-Navigation und Wissensgraph-Verknüpfungen.
6. Erhalte die Datei `CNAME` mit dem Inhalt `ADHS.telacore.org`.

## Pflichtprüfungen

Führe aus:

```bash
python3 scripts/build_literature.py
python3 scripts/build_graph.py
python3 scripts/validate_compendium.py
python3 scripts/build_combined.py
python3 scripts/build_anki.py
python3 scripts/build_docs.py
mkdocs build --strict
```

Die Validierung muss insbesondere Mindestlänge, Pflichtabschnitte, Quellen, Wikilinks und fortlaufende Nummerierung prüfen.

## Git-Arbeitsweise

1. Arbeite auf `agent/einheit-NN-kurztitel`.
2. Committe ausschließlich die zur Einheit gehörenden Änderungen.
3. Erstelle einen Draft-PR gegen `main`.
4. Nenne im PR Umfang, Evidenzarten, Unsicherheiten, geänderte Alttexte und Prüfergebnisse.
5. Führe keinen automatischen Merge durch.
