# Änderungsverlauf

## 0.14.0 – 2026-07-22

- Wissensgraph 2.0 Phase 2 und 3 vollständig materialisiert: interaktive, lokale Cytoscape-Webansicht mit Suche, Filtern, Detailpanel und semantischem No-JS-Fallback
- geplante, in Arbeit befindliche und veröffentlichte Inhalte durch einen eigenen Lebenszyklusstatus vom Linkstatus getrennt
- schema-validierten, atomaren Runtime-Status mit Phasen, Dauer, Commit, Metriken, Fehlerklasse und Recovery-Hinweis eingeführt
- verbindlichen Graphvalidator für Schema, Typen, Kantenendpunkte, interne Links und erwarteten Commit in CI und Veröffentlichungsbuilds integriert
- JSON, GraphML, Mermaid, Qualitätsberichte und Runtime-Status in Downloadmanifest und SHA-256-Prüfsummen aufgenommen
- Playwright-Smoke-Tests sowie idempotente PR-Zusammenfassung und Diagnoseartefakte ergänzt
- Wortzahlvertrag auf harte Grenzen 800–3.000 und Zielbereich 1.200–2.500 vereinheitlicht; Einheiten 1–10 bleiben nur von Zielbereichswarnungen ausgenommen
- tote Bootstrap-Dateien und die dazugehörigen Einmal-Workflows entfernt

## 0.13.0 – 2026-07-22

- vollständige plattformübergreifende Sync-Pakete für Linux, Android/Termux, Windows, macOS, BSD und iOS/iSH ergänzt
- gemeinsame, getestete Bash-Engine sowie funktional gleichwertige PowerShell-Engine eingeführt
- Installer, Deinstaller, native Zeitplaner, Diagnoseanleitungen und reproduzierbare ZIP-Pakete ergänzt
- Modi `safe-pull`, `prompt-pull`, `forced-pull`, `additive-pull` und Gerätebranch-basierter `full-sync` umgesetzt
- Schutz vor Pfadüberlappung, unbeabsichtigtem Überschreiben, parallelen Läufen und divergierenden Gerätebranches ergänzt
- echte Git-/rsync-Integrationstests und PowerShell-Parserprüfung in die CI aufgenommen

## 0.12.0 – 2026-07-22

- Einheit 13 „Pharmakotherapie und Psychotherapie“ als Einstieg in die Vertiefung ergänzt
- kurzfristige Medikamentenwirkung, psychologische Interventionen, Dosisfindung, Monitoring und gemeinsame Entscheidungsfindung differenziert eingeordnet
- fünf aktuelle Studienkarten, Glossarbegriffe, Anki-Karte und Wissensgraph-Verknüpfungen ergänzt
- Kapitelbuild und Obsidian-Export auf indexbasierte phasenübergreifende Ordner erweitert

## 0.8.1 – 2026-07-14

- Obsidian-Callouts beim Web-Build in native MkDocs-Material-Admonitions umgewandelt
- `[!evidence]` in der Webfassung durch ein eigenes Evidenzfeld mit Wissenschafts-Icon ersetzt
- Titel wie „Evidenz: Konsens / hoch“ und der zugehörige Text bleiben vollständig erhalten
- auch vorhandene `important`-, `warning`-, `info`- und `note`-Callouts webgerecht dargestellt
- Obsidian-Quelldateien unverändert und weiterhin nativ nutzbar belassen

## 0.8.0 – 2026-07-14

- sämtliche Synchronisationsdateien unter `Sync/` gebündelt
- Linux-Paket einschließlich systemd-Service, Timer, Installer und Sync-Skript aus dem Repository-Stamm verschoben
- Android-Termux-Gesamtpaket in Installer und eigenständiges Sync-Skript aufgeteilt
- Plattformordner für Windows, macOS, iOS und BSD als klar gekennzeichnete Planungsziele angelegt
- gemeinsame Modi `safe-pull`, `prompt-pull`, `forced-pull`, `additive-pull` und geplanter `full-sync` dokumentiert
- Wartungsunterseiten für alle Plattformen mit direkt herunterladbaren Dateien ergänzt
- Web-Build so erweitert, dass Sync-Anleitungen und ausführbare Hilfsdateien gemeinsam veröffentlicht werden
- veraltete Stammdatei `SYNC-OBSIDIAN.md`, alten `systemd/`-Ordner und verstreute Sync-Skripte entfernt

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
