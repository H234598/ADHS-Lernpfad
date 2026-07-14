# GitHub-Automation

## Workflows

- `validate.yml`: Pull-Request- und `main`-Validierung einschließlich Quellen, strukturierter Bibliografie, Obsidian-Links, Struktur, Wortgrenzen, Anki und MkDocs.
- `export.yml`: erzeugt nach Änderungen an `main` Markdown-, EPUB-, HTML-, LaTeX-, PDF-, BibTeX-, CSL-JSON- und APKG-Artefakte.
- `pages.yml`: baut und veröffentlicht die MkDocs-Webseite mit funktionierenden konvertierten Links und MathJax über GitHub Pages.

## Wartung

Die Workflows verwenden aktuelle GitHub-Actions-Majors mit Node-24-Runtime. Dependabot prüft wöchentlich GitHub Actions und Python-Abhängigkeiten. Infrastrukturänderungen werden nicht automatisch gemergt.

## Sicherheits- und Qualitätsregeln

- minimale, explizite `GITHUB_TOKEN`-Berechtigungen;
- keine Ausführung von untrusted PR-Code über `pull_request_target`;
- feste Runner-Version `ubuntu-24.04`;
- Dependency-Caching nur anhand der versionierten Requirements-Dateien;
- Zeitlimits und Concurrency-Gruppen verhindern hängende oder überholte Läufe;
- Obsidian-Wikilinks müssen eindeutig auflösbar sein und werden erst im Build umgewandelt;
- `Literatur.md`, `references.bib` und `references.json` müssen gemeinsam aus den Studienkarten reproduzierbar sein;
- die sichtbare vollständige Zitation muss den strukturierten `citation`-Feldern entsprechen;
- der PDF-Export verwendet Pandoc, CiteProc und LuaLaTeX mit freien DejaVu-Schriften;
- Pages-Deployments werden nicht während einer laufenden Veröffentlichung abgebrochen.
