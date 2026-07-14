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

Zusätzlich müssen `git diff --check`, `python -m compileall -q scripts`, `python -m pip check` und die Konsistenz der generierten `Literatur.md` erfolgreich sein.

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
