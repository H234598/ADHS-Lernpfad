# Beitragen

## Single Source of Truth

- Kapitel und Lerntexte: Markdown-Dateien
- Quellen und bibliografische Metadaten: `references/*.md`
- Lernkarten: `cards/cards.yaml`
- `Literatur.md`, `references.bib`, `references.json`, Wissensgraph und Exporte: generiert

Die drei Literaturausgaben dürfen nicht unabhängig voneinander editiert werden. Änderungen erfolgen an den Studienkarten und anschließend über `scripts/build_literature.py`.

## Umfang regulärer Einheiten

- harte Untergrenze: 800 Fließtextwörter
- CI-Warnung: unter 1.000 Fließtextwörtern
- Zielbereich: 1.000–2.000 Fließtextwörter
- harte Obergrenze: 2.500 Fließtextwörter

Gezählt wird der didaktische Fließtext ohne YAML-Frontmatter, Navigation und Diagrammcode. Benötigt ein Thema mehr als 2.500 Wörter, wird es in mehrere fachlich sinnvolle Einheiten geteilt. Die Grenzen dürfen nicht mit Wiederholungen oder Fülltext erreicht werden.

## Links

Die Quelldateien verwenden Obsidian-Wikilinks. Unterstützt werden:

```markdown
[[Glossar]]
[[01-Grundlagen/08-Neuroentwicklung-und-Lebensspanne|Neuroentwicklung und Lebensspanne]]
[[Glossar#Remission|Begriff Remission]]
```

Beim Web- und Export-Build werden daraus reguläre Links beziehungsweise interne Dokumentanker. Ziele müssen eindeutig existieren; Codeblöcke werden nicht verändert. Manuell doppelte HTML-Links neben Wikilinks sind unerwünscht.

## Studienkarten und Zitationen

Jede Studienkarte enthält:

- eine stabile `reference_id`, die dem Dateinamen entspricht,
- DOI ohne URL-Präfix und PubMed-ID, soweit vorhanden,
- strukturierte bibliografische Angaben unter `citation`,
- einen aus diesen Angaben reproduzierbaren Abschnitt `Vollständige Zitation`,
- Evidenztyp, Kernaussage und Limitationen.

Das genaue Schema steht in `references/README.md`. Unvollständige historische Karten werden ausdrücklich gekennzeichnet und bei fachlicher Überarbeitung vervollständigt; fehlende Daten dürfen nicht erfunden werden.

## Pflichtprüfungen

```bash
python3 scripts/build_literature.py
git diff --exit-code -- Literatur.md references.bib references.json
python3 scripts/validate_links.py
python3 scripts/build_graph.py
python3 scripts/validate_compendium.py
python3 scripts/build_combined.py
python3 scripts/build_anki.py
python3 scripts/build_docs.py
mkdocs build --strict
```

Zusätzlich müssen `git diff --check`, `python -m compileall -q scripts` und `python -m pip check` erfolgreich sein.

## Branch-Hygiene

- `main` ist die einzige dauerhafte Hauptlinie.
- Jeder Nicht-`main`-Branch muss einem offenen Pull Request oder einer ausdrücklich dokumentierten Wiederherstellung zugeordnet sein.
- Nach Merge, Squash-Merge oder partieller Übernahme muss geprüft werden, ob der Ursprungsbranch noch einzigartige Änderungen enthält.
- Veraltete Parallelzweige dürfen nicht still liegen bleiben: fehlende sinnvolle Änderungen werden gezielt übernommen, überholte Varianten dokumentiert verworfen und der Branch anschließend entfernt.
- Automatische Einheitenbranches verwenden `agent/einheit-NN-kurztitel`.
- Direkte Inhalts- oder Konfigurationsänderungen auf `main` sind außerhalb eines begründeten Notfalls unzulässig.

## Automatische Merge-Grenzen

Normale Einheiten-, Quellen-, Karten-, Glossar-, Index- und Navigationsänderungen dürfen nach den definierten Prüfungen automatisch gemergt werden. Änderungen an `.github/`, `prompts/`, Validatoren, `CNAME`, Abhängigkeiten, Build-, Veröffentlichungs-, Sicherheits- oder Synchronisationsinfrastruktur benötigen eine bewusste manuelle Prüfung.

## Evidenzregeln

- Gruppenbefund ≠ Aussage über jede Einzelperson.
- Korrelation ≠ Kausalität.
- Evidenzgrad und Konsensstatus getrennt angeben.
- ADHS, Autismus und Parkinson nicht gleichsetzen.
- Bestehende Aussagen bei neuer Evidenz korrigieren und im Changelog dokumentieren.
