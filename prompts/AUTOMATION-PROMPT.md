# Automatisierungsprompt: tägliche neue Einheit

Dieser Prompt wird durch die externe Automation täglich um **06:00 Uhr Europe/Berlin** ausgeführt. Der Lauf erzeugt genau eine neue Lerneinheit und endet nach dem Erstellen eines Draft-Pull-Requests. Er wartet nicht auf CodeRabbit und führt keinen Merge durch.

Arbeite im Repository `H234598/ADHS-Lernpfad`.

## 1. Sicherheits- und Vorabprüfung

1. Lade den aktuellen Stand von `main`.
2. Suche nach offenen Pull Requests gegen `main`, deren Head-Branch dem Muster `agent/einheit-*` entspricht oder deren Beschreibung den Marker `<!-- adhs-daily-unit -->` enthält.
3. Falls bereits ein solcher Pull Request offen ist, erstelle **keine** weitere Einheit und keinen weiteren Branch. Melde den vorhandenen PR als Blocker.
4. Stelle sicher, dass das Arbeitsverzeichnis sauber ist und der neue Branch vom aktuellen `main` ausgeht.
5. Lies `README.md`, `00-Einfuehrung.md`, `index.json`, die letzten zwei Kapitel, `Glossar.md`, die Referenzkarten, `ROADMAP.md` und alle einschlägigen Dateien unter `prompts/`.
6. Führe vor dem Schreiben vollständig `prompts/DEEP-RESEARCH-PROMPT.md` aus.

## 2. Auftrag

Ergänze **genau eine** neue fortlaufende Lerneinheit. Bestimme die nächste freie Einheitsnummer und den fachlich logischen nächsten Baustein. Prüfe, ob bestehende Kapitel wegen neuer Evidenz korrigiert werden müssen. Änderungen an Alttexten müssen im PR ausdrücklich begründet werden.

## 3. Verbindlicher Umfang

Eine Einheit ist eine echte **10- bis 20-minütige Lerneinheit**, nicht nur eine Kurznotiz mit entsprechendem YAML-Etikett.

- Harte Untergrenze: **800 Fließtextwörter** nach Abzug von YAML, Navigation und Diagrammcode.
- CI-Warnung unter **1.000 Fließtextwörtern**.
- Zielbereich: **1.000–2.000 Fließtextwörter**.
- Harte Obergrenze: **2.500 Fließtextwörter**.
- Wird mehr Platz benötigt, teile das Thema in mehrere logisch aufeinanderfolgende Einheiten; in diesem Lauf wird dennoch nur die erste Einheit erstellt.
- Niemals künstlich durch Wiederholung, Füllsätze oder erzwungene Autismus-/Parkinson-Bezüge verlängern.

## 4. Pflichtstruktur jeder Einheit

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

## 5. Wissenschaftliche Regeln

- Trenne gut abgesicherte Befunde, plausible Modelle und offene Fragen.
- Kennzeichne Gruppenbefunde; leite daraus keine sicheren Aussagen über Einzelpersonen ab.
- Vermeide populäre Verkürzungen wie „ADHS ist Dopaminmangel“ und „Dopamin ist das Glückshormon“.
- Stelle ADHS, Autismus und Parkinson niemals als dieselbe Art von Erkrankung dar.
- Verwende keine Foren, SEO-Ratgeber oder Herstellertexte als Evidenz.
- Gib DOI, PubMed-ID oder stabilen Verlagslink an, soweit vorhanden.
- Formuliere keine Diagnose- oder Therapieversprechen.
- Bevorzuge die aktuelle wissenschaftliche Lehrmeinung gegenüber veralteten Darstellungen und dokumentiere relevante Abweichungen.

## 6. Dateipflege

1. Lege die Einheit im fachlich passenden Ordner ab.
2. Lege neue Quellen als einzelne Dateien in `references/` an; `Literatur.md` wird generiert.
3. Ergänze neue Fachbegriffe in `Glossar.md`.
4. Ergänze passende Anki-Karten in `cards/cards.yaml`.
5. Aktualisiere README, Index, MkDocs-Navigation und Wissensgraph-Verknüpfungen.
6. Erhalte die Datei `CNAME` exakt mit dem Inhalt `ADHS.telacore.org`.
7. Verändere keine Prompt-, Workflow-, Validator- oder Infrastrukturdateien, sofern dies nicht für die neue Einheit zwingend erforderlich ist. Solche Änderungen müssen im PR besonders hervorgehoben werden.

## 7. Pflichtprüfungen

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

Alle Prüfungen müssen erfolgreich beendet sein. Die Validierung muss insbesondere Mindest- und Maximallänge, Pflichtabschnitte, Quellen, Wikilinks und fortlaufende Nummerierung prüfen.

## 8. Git-Arbeitsweise

1. Erstelle vom aktuellen `main` einen Branch nach dem Schema `agent/einheit-NN-kurztitel`.
2. Committe ausschließlich die zur Einheit gehörenden Änderungen.
3. Pushe den Branch zu `origin`.
4. Erstelle einen **Draft-Pull-Request** gegen `main`.
5. Füge in die PR-Beschreibung den unsichtbaren Marker `<!-- adhs-daily-unit -->` ein.
6. Nenne im PR:
   - Umfang und Fließtextwortzahl,
   - verwendete Evidenzarten,
   - zentrale Quellen,
   - Unsicherheiten und Limitationen,
   - geänderte Alttexte mit Begründung,
   - sämtliche lokalen Prüfergebnisse,
   - Branch und Head-Commit.
7. Lasse den PR im Draft-Status. Markiere ihn nicht als „Ready for review“ und merge ihn nicht.
8. Melde abschließend PR-Nummer, PR-Link, Branch, Head-Commit, Wortzahl und Prüfergebnisse.

Falls Push oder PR-Erstellung wegen fehlender Berechtigungen scheitern, dokumentiere Branch, lokalen Commit und die genaue Fehlermeldung. Führe keinen stillen oder direkten Commit auf `main` aus.