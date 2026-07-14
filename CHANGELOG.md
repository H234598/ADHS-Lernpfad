# Änderungsverlauf

## 0.7.0 – 2026-07-14

- eigenständige, responsive Downloadseite mit Formatberatung ergänzt
- PDF, EPUB 3, Offline-HTML, Markdown, LaTeX, BibTeX, CSL JSON und Anki unter stabilen Webadressen veröffentlicht
- schlanken Obsidian-Vault als ZIP-Download ergänzt
- zentrale Exportlogik für GitHub-Actions-Artefakte und Website vereinheitlicht
- SHA-256-Prüfsummen und maschinenlesbares Download-Manifest erzeugt
- Offline-HTML mit eingebetteten Ressourcen und EPUB ausdrücklich als EPUB 3 gebaut
- Dateiformate mit ihren Standards, Stärken und Einschränkungen erklärt

## 0.6.0 – 2026-07-14

- Obsidian-Wikilinks beim Web-Build in reguläre relative Markdown- und HTML-Ziele umgewandelt
- Aliasnamen, Unterordner und Überschriftenanker unterstützt und in der CI validiert
- individuelle Studienkarten als versteckte, direkt verlinkbare Webseiten veröffentlicht
- Studienkarten als gemeinsame Quelle für `Literatur.md`, `references.bib` und `references.json` strukturiert
- Konsistenzprüfung zwischen sichtbarer Zitation und strukturierten Metadaten ergänzt
- BibTeX- und CSL-JSON-Downloads in das Literaturverzeichnis aufgenommen
- Gesamtdokument mit stabilen internen Ankern für HTML, EPUB, LaTeX und PDF ausgestattet
- LaTeX-Quelltext und LuaLaTeX-PDF als Exportartefakte ergänzt
- MathJax-Unterstützung für Formeln in der Webfassung aktiviert

## 0.5.0 – 2026-07-14

- Einheit 8 „Neuroentwicklung und Lebensspanne“ ergänzt
- Persistenz, Teilremission, zeitweise Remission und Adult-onset-Debatte differenziert eingeordnet
- zwei longitudinale Studienkarten, Glossarbegriffe, Anki-Karte und Wissensgraph-Verknüpfungen ergänzt

## 0.4.4 – 2026-07-14

- 404-Fehler des Wartungssymbols durch einen von MkDocs und Obsidian auflösbaren Markdown-Link behoben
- sichtbare Seitenbearbeitungs-Aktion aus der Webfassung entfernt
- GitHub-Repository-Symbol in der Kopfzeile bewusst beibehalten
- Lernoberfläche weiter auf Inhalte statt Projekttechnik fokussiert

## 0.4.3 – 2026-07-14

- Startseite auf Lerninhalte, Schnellstart und Wissenssystem reduziert
- technischen Betrieb, Tagesautomation, CI, Wartung und Ausgaben auf `WARTUNG.md` gebündelt
- Wartungszugang über ein kleines Werkzeug-Symbol auf der Startseite ergänzt
- vollständige Automationsprompt-Sektion aus der sichtbaren MkDocs-Navigation entfernt
- Wartungs- und Promptseiten weiterhin gebaut, aber über `not_in_nav` bewusst im Hintergrund gehalten
- zurückhaltende, barrierearme Gestaltung für Wartungslink und Startseite ergänzt
- Wartungs-, Beitrags-, Sync- und CI-Dokumentation in den Dokumentationsbuild aufgenommen

## 0.4.2 – 2026-07-14

- sämtliche Agentenprompts unter `prompts/` zentralisiert
- tägliche Erzeugungsautomation auf 06:00 Uhr Europe/Berlin festgelegt
- getrennten Prüf-, Reparatur- und Merge-Wächter ab 08:00 Uhr ergänzt
- zweistündige Gelegenheit für CodeRabbit-Draftprüfungen eingerichtet, ohne CodeRabbit zum Pflicht-Gate zu machen
- automatische Reparaturzyklen für fehlgeschlagene CI auf dem bestehenden PR-Branch ergänzt
- automatische Merge-Sperren für Workflow-, Prompt-, Validator-, `CNAME`- und Infrastrukturänderungen ergänzt
- erneute CI-Ausführung beim Übergang von Draft zu `ready_for_review` eingerichtet
- Promptpipeline in README und MkDocs dokumentiert
- Branch-Hygiene und Kontrolle auf zurückgebliebene einzigartige Änderungen verbindlich festgelegt
- GitHub Actions auf aktuelle Node-24-Majors aktualisiert und veraltete Action-Runtimes entfernt
- CI mit Dependency-Caching, Zeitlimits, Generator-Konsistenzchecks und klaren Concurrency-Regeln gehärtet
- Dependabot für GitHub Actions und Python-Abhängigkeiten aktiviert

## 0.4.1 – 2026-07-13

- harte Mindestlänge auf 800 Fließtextwörter erhöht
- CI-Warnung für Kapitel unter 1.000 Fließtextwörtern ergänzt
- harte Obergrenze von 2.500 Fließtextwörtern eingeführt
- Zielbereich für neue Einheiten auf 1.000–2.000 Wörter präzisiert
- alle sieben Grundlagenkapitel fachlich erweitert, damit der Bestand die neue Mindestgrenze erfüllt
- Automatisierungsprompt, README, Beitragsregeln und Validierungsbericht synchronisiert

## 0.4.0 – 2026-07-13

- alle sieben Grundlagenkapitel von Kurzfassungen zu echten 10–20-Minuten-Einheiten erweitert
- Mindestumfang in CI verankert
- Pflichtabschnitte und Mermaid-Diagramme werden automatisch geprüft
- Automatisierungsprompt gegen zukünftige Kurzfassungen gehärtet
- Custom Domain `ADHS.telacore.org` per CNAME im Pages-Artefakt gesichert

## 0.3.0 – 2026-07-13

- sieben Grundlagenkapitel mit Mermaid-Modellen und Evidenzmetadaten
- modulare Studienkarten als Literaturdatenbank
- automatisch erzeugtes Literaturverzeichnis
- Wissensgraph als JSON und Mermaid
- SVG-Regulationsmodell
- Anki-Quelle und APKG-Generator
- Deep-Research-Prompt
- MkDocs, CI, Pages und Exporte
- robuster systemd-Sync nach Obsidian
