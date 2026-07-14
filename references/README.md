# Studienkarten

Jede Kernquelle besitzt eine eigene Markdown-Datei mit stabiler ID, strukturierter Zitation, Evidenztyp, Kernaussagen und Einschränkungen. Die Studienkarten sind die **Single Source of Truth** für:

- `Literatur.md` – lesbares Literaturverzeichnis,
- `references.bib` – BibTeX/BibLaTeX,
- `references.json` – CSL JSON für CiteProc, Zotero und andere Literaturwerkzeuge.

## Regeln

- Dateiname = stabile `reference_id`
- DOI ohne URL-Präfix speichern
- PubMed-ID separat speichern
- bibliografische Felder unter `citation` strukturiert pflegen
- der Abschnitt `Vollständige Zitation` muss exakt aus diesen Feldern reproduzierbar sein
- `et_al: true` nur verwenden, wenn die Studienkarte die Autorenliste bewusst abkürzt
- Kernaussagen paraphrasieren, nicht Abstracts kopieren
- methodische Grenzen sichtbar machen

## Zitationsschema

```yaml
citation:
  entry_type: article
  csl_type: article-journal
  authors:
    - "Familienname, Initialen"
  et_al: false
  year: 2026
  article_title: Titel des Beitrags
  journal: Zeitschrift
  volume: "12"
  issue: "3"
  pages: "100–120"
  article_number: "42"
```

Nicht zutreffende Felder werden weggelassen. Unvollständige Altquellen dürfen als `entry_type: misc` gekennzeichnet werden; sie sollen bei der nächsten fachlichen Überarbeitung vervollständigt werden.

## Bequeme Nutzung

- Zotero und viele Literaturverwaltungen können `references.bib` oder `references.json` importieren.
- Pandoc verwendet beide Formate zusammen mit CiteProc für formatierte Zitate und Literaturverzeichnisse.
- LaTeX-Projekte können `references.bib` direkt mit BibLaTeX/Biber oder klassischem BibTeX laden.
