---
title: ADHS-Lernpfad
subtitle: Wissenschaftlich fundierte Lerneinheiten von den Grundlagen bis zur Forschung
language: de
status: fortlaufend
version: 0.4.1
last_reviewed: 2026-07-13
tags: [ADHS, Neurobiologie, Autismus, Parkinson, Lernpfad]
---

# ADHS-Lernpfad

Ein quelloffenes, Obsidian-taugliches Lernkompendium zu ADHS. Es beginnt bei den Grundlagen und wächst schrittweise bis zum Lesen, Bewerten und Einordnen aktueller Forschung.

**Webfassung:** https://ADHS.telacore.org/

## Wissenschaftlicher Rahmen

Die Texte unterscheiden konsequent zwischen:

- diagnostischen Merkmalen und häufigen Begleiterscheinungen,
- Gruppenbefunden und Aussagen über Einzelpersonen,
- Konsens, wahrscheinlichen Modellen und offenen Fragen,
- gemeinsamen Mechanismen und einer Gleichsetzung von ADHS, Autismus oder Parkinson.

> [!important]
> Das Kompendium ersetzt keine ärztliche oder psychotherapeutische Diagnostik oder Behandlung.

## Umfang der Einheiten

Jede reguläre Einheit ist als **10- bis 20-minütige Lerneinheit** angelegt.

- mindestens **800 Fließtextwörter**,
- CI-Warnung unter **1.000 Fließtextwörtern**,
- Zielbereich ungefähr **1.000–2.000 Wörter**,
- maximal **2.500 Fließtextwörter**.

Diagramm, Übung und Review gehören zusätzlich zum Lernumfang. Komplexe Themen dürfen den oberen Zielbereich ausschöpfen; würden mehr als 2.500 Wörter benötigt, wird das Thema in mehrere Einheiten geteilt. Künstliche Fülltexte sind ausdrücklich unerwünscht.

## Lernpfad

1. [[01-Grundlagen/01-Was-ist-ADHS|Was ist ADHS?]]
2. [[01-Grundlagen/02-Inhibition-und-Handlungssteuerung|Inhibition und Handlungssteuerung]]
3. [[01-Grundlagen/03-Dopamin-Belohnung-und-Motivation|Dopamin, Belohnung und Motivation]]
4. [[01-Grundlagen/04-Arbeitsgedaechtnis|Arbeitsgedächtnis]]
5. [[01-Grundlagen/05-Aufmerksamkeit-und-Stabilitaet|Aufmerksamkeit und Stabilität]]
6. [[01-Grundlagen/06-Zeitverarbeitung|Zeitverarbeitung]]
7. [[01-Grundlagen/07-Emotionsregulation|Emotionsregulation]]

## Wissenssystem

- [[00-Einfuehrung|Wie der Lernpfad gelesen wird]]
- [[Glossar|Glossar]]
- [[Literatur|automatisch erzeugtes Literaturverzeichnis]]
- [[references/README|Studienkarten]]
- [[knowledge-graph/README|Wissensgraph]]
- [[cards/README|Anki-Karten und APKG-Export]]
- [[figures/README|Abbildungen und Diagramme]]

## Betrieb

- [[prompts/README|Übersicht aller Prompts]]
- [[prompts/AUTOMATION-PROMPT|06-Uhr-Prompt für neue Einheiten]]
- [[prompts/DEEP-RESEARCH-PROMPT|Deep-Research-Prompt]]
- [[prompts/MERGE-AUTOMATION-PROMPT|Prüf- und Merge-Prompt ab 08 Uhr]]
- [[SYNC-OBSIDIAN|GitHub → Obsidian per systemd]]
- [[CONTRIBUTING|Beitrags- und Evidenzregeln]]

## Automatisierter Tagesablauf

Um 06:00 Uhr Europe/Berlin erzeugt die erste Automation genau eine neue Einheit und einen Draft-Pull-Request. Ab 08:00 Uhr prüft ein getrennter Wächter regelmäßig CodeRabbit, Review-Threads und CI. Erst nach erfolgreicher Draft-Prüfung wird der PR als bereit markiert; nach einer weiteren vollständig grünen Pull-Request-CI wird er per Squash-Merge nach `main` übernommen.

## Automatische Ausgaben

GitHub Actions prüfen Struktur, Mindest- und Maximallänge sowie Links, bauen die MkDocs-Webseite und erzeugen Markdown-, HTML-, EPUB- und APKG-Artefakte.