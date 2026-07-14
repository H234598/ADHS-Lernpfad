# Änderungsverlauf

## 0.4.2 – 2026-07-14

- sämtliche Agentenprompts unter `prompts/` zentralisiert
- tägliche Erzeugungsautomation auf 06:00 Uhr Europe/Berlin festgelegt
- getrennten Prüf-, Reparatur- und Merge-Wächter ab 08:00 Uhr ergänzt
- zweistündige Gelegenheit für CodeRabbit-Draftprüfungen eingerichtet, ohne CodeRabbit zum Pflicht-Gate zu machen
- automatische Reparaturzyklen für fehlgeschlagene CI auf dem bestehenden PR-Branch ergänzt
- automatische Merge-Sperren für Workflow-, Prompt-, Validator-, `CNAME`- und Infrastrukturänderungen ergänzt
- erneute CI-Ausführung beim Übergang von Draft zu `ready for review` eingerichtet
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
