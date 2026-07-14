# GitHub-Automation

## Workflows

- `validate.yml`: Pull-Request- und `main`-Validierung einschließlich Quellen, Struktur, Wortgrenzen, Exporte, Anki und MkDocs.
- `export.yml`: erzeugt nach Änderungen an `main` die Markdown-, EPUB-, HTML- und APKG-Artefakte.
- `pages.yml`: baut und veröffentlicht die MkDocs-Webseite über GitHub Pages.

## Wartung

Die Workflows verwenden aktuelle GitHub-Actions-Majors mit Node-24-Runtime. Dependabot prüft wöchentlich GitHub Actions und Python-Abhängigkeiten. Infrastrukturänderungen werden nicht automatisch gemergt.

## Sicherheits- und Qualitätsregeln

- minimale, explizite `GITHUB_TOKEN`-Berechtigungen;
- keine Ausführung von untrusted PR-Code über `pull_request_target`;
- feste Runner-Version `ubuntu-24.04`;
- Dependency-Caching nur anhand der versionierten Requirements-Dateien;
- Zeitlimits und Concurrency-Gruppen verhindern hängende oder überholte Läufe;
- generierte `Literatur.md` muss mit den Referenzkarten übereinstimmen;
- Pages-Deployments werden nicht während einer laufenden Veröffentlichung abgebrochen.
