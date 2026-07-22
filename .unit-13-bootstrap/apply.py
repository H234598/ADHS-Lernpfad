#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import textwrap

import yaml

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "agent/einheit-13-pharmakologie-psychotherapie"
BOOTSTRAP = ROOT / ".unit-13-bootstrap"
WORKFLOW = ROOT / ".github" / "workflows" / "apply-unit-13.yml"
TODAY = "2026-07-22"


def write(path: str, content: str) -> None:
    destination = ROOT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def run(*command: str) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def insert_before_heading(text: str, heading: str, block: str) -> str:
    if block.strip() in text:
        return text
    marker = f"\n{heading}\n"
    if marker not in text:
        raise RuntimeError(f"Überschrift fehlt: {heading}")
    return text.replace(marker, "\n" + block.strip() + "\n\n" + heading + "\n", 1)


chapter = r'''
---
title: Pharmakotherapie und Psychotherapie
level: Vertiefung
estimated_time: 10–20 min
difficulty: 3
prerequisites: ["01-Grundlagen/01-Was-ist-ADHS", "01-Grundlagen/09-Diagnostische-Kriterien-und-Differentialdiagnostik", "01-Grundlagen/11-Schlaf-Bewegung-und-koerperliche-Gesundheit", "01-Grundlagen/12-Komorbiditaet-Depression-und-Suizidalitaet"]
tags: [ADHS, Pharmakotherapie, Psychotherapie, Psychoedukation, gemeinsame Entscheidungsfindung]
last_reviewed: 2026-07-22
evidence: high
status: consensus
references: [Ostinelli2025, Peterson2024, Tuerk2023, Liu2023, Nourredine2026, AADPA2022, Faraone2021]
minimum_reading_minutes: 10
maximum_reading_minutes: 20
---

# Einheit 13 – Pharmakotherapie und Psychotherapie

## Lernziel

Du kannst erklären, welche Ziele Medikamente, psychologische Verfahren und Anpassungen des Umfelds bei ADHS verfolgen. Du verstehst, warum Behandlung weder ein Beweis für die Diagnose noch eine „Heilung“ ist, weshalb kurzfristige Symptomwirkung nicht automatisch langfristige Lebensqualität bedeutet und warum Alter, Begleiterkrankungen, Präferenzen, Nebenwirkungen und konkrete Alltagsziele die Auswahl mitbestimmen. Außerdem kannst du zwischen Psychoedukation, Verhaltenstherapie, kognitiver Verhaltenstherapie und allgemeiner Unterstützung unterscheiden.

## 1. Behandlung beginnt mit Zielen, nicht mit einer Lagerentscheidung

Die Frage „Medikamente oder Psychotherapie?“ klingt nach zwei konkurrierenden Weltanschauungen. Wissenschaftlich sinnvoller ist eine andere Reihenfolge: Welche Beeinträchtigung soll sich verändern, welche Bedingungen tragen zu ihr bei, welche Behandlung ist für diese Person zugänglich und wie wird geprüft, ob Nutzen und Belastung tatsächlich in einem guten Verhältnis stehen?

Ein Kind kann vor allem durch Unterrichtsabbrüche, impulsive Konflikte und familiäre Eskalationen beeinträchtigt sein. Eine erwachsene Person kann trotz weniger sichtbarer Hyperaktivität an Zeitmanagement, Arbeitsorganisation, emotionaler Überlastung oder wiederholtem Scheitern komplexer Routinen leiden. Medikamente, Elterntraining, schulische Anpassungen und kognitive Verhaltenstherapie greifen nicht an exakt derselben Stelle an. Deshalb ist eine gemeinsame Behandlungsplanung wichtiger als die Suche nach einer universellen Rangliste.

> [!evidence] Evidenz: Konsens / hoch
> ADHS-Behandlung soll individuell, zielorientiert und regelmäßig überprüft werden. Medikamente können Kernsymptome deutlich reduzieren; psychologische und verhaltensbezogene Verfahren können Strategien, Umfeld, Funktionsbeeinträchtigung und Begleitprobleme bearbeiten. Keine Methode wirkt bei allen Menschen gleich gut.

Eine Behandlung kann wirksam sein, ohne alle Schwierigkeiten zu beseitigen. Umgekehrt beweist eine fehlende Wirkung eines einzelnen Medikaments oder einer einzelnen Therapie nicht, dass keine ADHS vorliegt. Diagnose und Behandlungserfolg sind unterschiedliche Fragen.

## 2. Was Pharmakotherapie im Durchschnitt leisten kann

Für mehrere zugelassene ADHS-Medikamente zeigen randomisierte Studien eine kurzfristige Reduktion von Unaufmerksamkeit, Hyperaktivität und Impulsivität. Zu den häufig verwendeten Gruppen gehören Stimulanzien wie Methylphenidat oder Amphetaminpräparate sowie Nichtstimulanzien wie Atomoxetin und – je nach Alter, Land und Zulassung – weitere Wirkstoffe. Welche Reihenfolge empfohlen wird, unterscheidet sich zwischen Altersgruppen, Leitlinien und Zulassungen.

Bei Erwachsenen fand eine große Netzwerk-Meta-Analyse von 113 randomisierten Studien die robusteste kurzfristige Symptomwirkung für Stimulanzien und Atomoxetin, wenn sowohl Selbst- als auch Fremdbeurteilungen berücksichtigt wurden. Für Kinder und Jugendliche bestätigen systematische Reviews, dass Medikamente im Mittel Kernsymptome reduzieren. Solche Mittelwerte sagen jedoch nicht voraus, welches Präparat einer einzelnen Person hilft, welche Nebenwirkungen auftreten oder ob eine Veränderung im Alltag groß genug ist, um für sie relevant zu sein.

Wichtig ist außerdem die Messdauer. Viele kontrollierte Studien dauern nur einige Wochen oder wenige Monate. Damit lässt sich die kurzfristige Wirksamkeit besser beurteilen als die Frage, wie sich eine Behandlung über Jahre auf Bildung, Beziehungen, körperliche Gesundheit oder Lebensqualität auswirkt. Beobachtungsstudien können längere Verläufe ergänzen, sind aber anfälliger für Unterschiede zwischen behandelten und unbehandelten Gruppen.

Medikamente verändern auch nicht automatisch erlernte Strategien, Schulbedingungen, chronische Konflikte oder fehlende Unterstützung. Wenn jemand nach einer Symptomverbesserung weiterhin keine planbare Arbeitsstruktur besitzt, bleibt ein Teil der Beeinträchtigung bestehen. Das ist kein Widerspruch zur Medikamentenwirkung, sondern zeigt, dass Kernsymptome und Lebensführung nicht identisch sind.

## 3. Dosisfindung bedeutet systematisches Prüfen – nicht „mehr hilft mehr“

Die passende Dosis ist keine aus Körpergewicht, Diagnose oder Schweregrad sicher berechenbare Zahl. Fachlich wird sie schrittweise innerhalb der zugelassenen Grenzen angepasst. Beobachtet werden vorher definierte Zielbereiche, Wirkdauer, Nebenwirkungen und Alltagssituationen. Dabei kann eine zu niedrige Dosis unzureichend wirken, während eine weitere Steigerung irgendwann kaum zusätzlichen Nutzen, aber mehr unerwünschte Wirkungen bringt.

Eine 2026 veröffentlichte Dosis-Wirkungs-Netzwerk-Meta-Analyse beschreibt solche durchschnittlichen Kurven über verschiedene Medikamente und Altersgruppen. Sie unterstützt weder private Dosisexperimente noch eine starre „optimale“ Zahl. Studienmittelwerte können individuelle Unterschiede bei Aufnahme, Wirkdauer, Begleiterkrankungen, anderen Medikamenten und Empfindlichkeit nicht ersetzen. Für die Arbeit ist die korrigierte Fassung zu berücksichtigen, da die Zeitschrift später eine formale Korrektur veröffentlichte.

Typische Beobachtungsbereiche sind Appetit, Gewicht beziehungsweise Wachstum bei Kindern, Schlaf, Puls und Blutdruck, Stimmung, Reizbarkeit, Tics, Wirkung über den Tag sowie Fehlgebrauch oder Weitergabe. Nicht jede Veränderung ist automatisch durch das Medikament verursacht. Deshalb sind Ausgangswerte, zeitlicher Verlauf und kontrollierte Änderungen wichtig. Eine jährliche Gesamtüberprüfung fragt zusätzlich, ob das Mittel weiterhin benötigt wird, ob Ziele erreicht werden und welche Unterstützung trotz optimierter Medikation fehlt.

```mermaid
flowchart TD
  A[gemeinsam definierte Alltagsziele] --> B[Behandlungsbaustein auswählen]
  B --> C[Wirkung und Nebenwirkungen beobachten]
  C --> D{relevanter Nutzen bei vertretbarer Belastung?}
  D -->|ja| E[fortführen und regelmäßig überprüfen]
  D -->|teilweise| F[Dosis, Präparat oder zusätzliche Hilfen prüfen]
  D -->|nein| G[Diagnose, Ziel, Adhärenz und Alternativen neu bewerten]
  F --> C
  G --> A
```

## 4. Psychotherapie ist nicht einfach „über ADHS reden“

**Psychoedukation** vermittelt ein realistisches Verständnis von ADHS, Behandlung und Selbstbeobachtung. Sie kann Schuldzuweisungen reduzieren und gemeinsame Ziele klären, ist aber allein nicht automatisch eine vollständige Psychotherapie. Verhaltenstherapeutische Elternprogramme arbeiten beispielsweise mit klaren Regeln, unmittelbarer Rückmeldung, positiver Verstärkung, planbaren Konsequenzen und der Veränderung eskalierender Interaktionsmuster. Schulische Interventionen passen Aufgaben, Rückmeldung, Sitzordnung, Pausen und Organisationshilfen an.

Bei Erwachsenen werden häufig strukturierte ADHS-spezifische psychologische Interventionen eingesetzt. Kognitive Verhaltenstherapie kann Fertigkeiten für Planung, Priorisierung, Ablenkungsmanagement, Aufschieben, problematische Gedankenmuster und Emotionsregulation trainieren. Meta-Analysen randomisierter Studien berichten im Mittel Verbesserungen von ADHS-Symptomen und teilweise zusätzlichen Bereichen. Die Befunde sind jedoch schwieriger zu verblinden als Medikamentenstudien: Teilnehmende und Therapeuten wissen meist, welche Behandlung erfolgt, und Beurteilungen durch unblinde Personen können Effekte größer erscheinen lassen.

Für Kinder und Jugendliche zeigen zusammenfassende Reviews sowohl für pharmakologische als auch für psychologische Interventionen durchschnittliche Verbesserungen. Die Effekte psychologischer Verfahren sind oft kleiner und hängen stark davon ab, wer bewertet, welches Ziel gemessen wird und wie gut die Intervention zum Alter passt. Das bedeutet nicht, dass sie „unwirksam“ seien. Ein Elterntraining kann familiäre Abläufe und oppositionelles Verhalten verbessern, ohne jede Aufmerksamkeitsbewertung in der Schule gleich stark zu verändern.

Allgemeine Gesprächstherapie ohne ADHS-spezifische Struktur ist nicht dasselbe wie ein geprüftes Fertigkeitenprogramm. Gleichzeitig darf Therapie nicht zu einem moralischen Training werden, in dem Schwierigkeiten als mangelnde Anstrengung bewertet werden. Gute Interventionen verändern Anforderungen, üben konkrete Schritte und berücksichtigen, dass das Umsetzen einer Strategie selbst exekutive Funktionen benötigt.

## 5. Kombination heißt nicht automatisch doppelte Wirkung

Leitlinien empfehlen je nach Alter, Schwere, Kontext und Präferenz unterschiedliche Einstiege. Bei kleinen Kindern stehen verhaltensbezogene und elternbezogene Maßnahmen besonders im Vordergrund. Bei älteren Kindern, Jugendlichen und Erwachsenen kann eine Medikation bei relevanter Beeinträchtigung angeboten werden; psychologische Behandlung kommt als Alternative, Ergänzung oder gezielte Hilfe bei verbleibenden Funktionsproblemen hinzu.

Die intuitive Annahme „Medikament plus Therapie muss immer besser sein als eines allein“ ist wissenschaftlich zu einfach. Direkte vergleichende Evidenz für jede Kombination und jedes Ziel ist begrenzt. Ein zusätzlicher Baustein ist vor allem dann sinnvoll, wenn er ein noch bestehendes Problem adressiert: etwa Elterntraining bei eskalierenden Familienkonflikten, schulische Unterstützung bei organisatorischen Barrieren oder kognitive Verhaltenstherapie bei fortbestehendem Aufschieben und Selbstabwertung.

Auch praktische Zugänglichkeit zählt. Eine theoretisch geeignete Therapie hilft wenig, wenn Wartezeiten, Kosten, Reizüberlastung, Sprachbarrieren oder komplexe Terminorganisation ihre Nutzung verhindern. Gemeinsame Entscheidungsfindung bedeutet daher nicht bloß, mehrere Optionen aufzuzählen. Fachperson und betroffene Person besprechen erwartbaren Nutzen, Unsicherheit, Belastung, Werte und Umsetzbarkeit und legen fest, woran Erfolg oder ein notwendiger Wechsel erkannt werden.

## 6. Sicherheit und Begleiterkrankungen gehören in denselben Plan

Vor einer Medikation werden Diagnose, Behandlungsbedarf, psychische und soziale Situation, körperliche Vorgeschichte, bestehende Medikamente sowie relevante Herz-Kreislauf-Risiken geprüft. Ein unauffälliges Standard-EKG ist nicht bei jeder Person zwingend erforderlich; auffällige Vorgeschichte, Untersuchung oder andere Risiken verändern jedoch die Abklärung. Im Verlauf gehören Blutdruck, Puls, Appetit, Gewicht, Schlaf und psychische Veränderungen in die Beobachtung.

Komorbiditäten verändern Prioritäten. Bei akuter Suizidalität oder schwerer Depression steht Sicherheit im Vordergrund. Angst, Substanzkonsum, Tics, Autismus, Lernstörungen und körperliche Erkrankungen können Auswahl, Tempo und Zielsetzung beeinflussen. Sie schließen eine ADHS-Behandlung nicht automatisch aus. Zugleich darf eine Verbesserung der Aufmerksamkeit nicht dazu führen, andere Erkrankungen zu übersehen.

Besondere Vorsicht gilt Selbstmedikation und Weitergabe. Verschreibungspflichtige Stimulanzien sind keine allgemeinen Leistungssteigerer. Eine fremde Dosis, ein nicht ärztlich begleitetes Präparat oder eine eigenständige Veränderung kann körperliche und psychische Risiken erhöhen. Sichere Behandlung umfasst Aufbewahrung, Einnahmeplan, kontrollierte Verschreibung und offene Gespräche über Konsum und Fehlgebrauch.

## 7. Mini-Übung: Ziele in beobachtbare Veränderungen übersetzen

Wähle ein konkretes Problem, etwa „Ich verliere bei langen Aufgaben den Faden“. Formuliere dazu drei Ebenen:

1. **Kernsymptom:** Wie oft schweift die Aufmerksamkeit ab oder wird die Aufgabe verlassen?
2. **Funktion:** Welcher konkrete Schritt gelingt oder misslingt, beispielsweise 20 Minuten an einem Abschnitt zu arbeiten?
3. **Lebensziel:** Warum ist die Veränderung wichtig, etwa ein Projekt verlässlich abschließen zu können?

Notiere anschließend, welcher Baustein welche Ebene plausibel adressiert: Medikament, Arbeitsumgebung, Erinnerungssystem, Therapieübung oder Unterstützung durch andere. Diese Tabelle entscheidet keine Behandlung. Sie macht sichtbar, warum ein Symptomfragebogen allein nicht genügt und weshalb verschiedene Maßnahmen unterschiedliche Erfolge haben können.

## 8. Wissenschaftliche Einordnung und Grenzen

**Konsens:** Medikamente und strukturierte psychosoziale beziehungsweise psychologische Interventionen sind evidenzbasierte Behandlungsbausteine. Auswahl und Verlaufskontrolle sollen individuell und gemeinsam erfolgen. Medikamente benötigen fachliche Einleitung und Monitoring.

**Wahrscheinlich:** Stimulanzien und Atomoxetin gehören bei Erwachsenen kurzfristig zu den wirksamsten Optionen für Kernsymptome. Bei Kindern und Jugendlichen wirken mehrere Medikamente; Elterntraining, schulische Maßnahmen und weitere psychologische Interventionen können Symptome, Verhalten oder Funktionsbereiche verbessern. ADHS-spezifische kognitive Verhaltenstherapie kann Erwachsenen zusätzliche Strategien vermitteln.

**Umstritten:** Welche Kombination für welche Person langfristig den größten funktionellen Nutzen bietet, wie stark kurzfristige Symptomverbesserungen Lebensqualität und Teilhabe verändern und welche Merkmale eine individuelle Wirkung zuverlässig vorhersagen.

**Experimentell:** digitale Therapeutika, neurofeedbackbasierte Verfahren, Neurostimulation und algorithmische Auswahlmodelle. Für einige Verfahren gibt es positive Einzelbefunde, aber keine Grundlage, etablierte Behandlung pauschal zu ersetzen.

## 9. Verbindung zu Autismus und Parkinson

Bei gleichzeitigem Autismus können ADHS-Medikamente und psychologische Interventionen grundsätzlich erwogen werden. Kommunikation, sensorische Belastung, Routinen, Ziele und Nebenwirkungsbeobachtung müssen jedoch angepasst werden. Eine gemeinsame Medikamentenwirkung macht Autismus und ADHS nicht zu derselben Diagnose.

Bei Parkinson werden ebenfalls Medikamente eingesetzt, die dopaminerge Systeme beeinflussen. Daraus folgt keine Gleichsetzung: Parkinson ist eine neurodegenerative Erkrankung mit anderen Zielstrukturen, Symptomen und Behandlungsentscheidungen. Der Begriff „Dopamin“ allein erklärt weder eine ADHS-Behandlung noch eine Verbindung beider Erkrankungen.

## Review-Frage

**Warum ist die Frage „Medikament oder Psychotherapie – was ist besser?“ für eine gute ADHS-Behandlung zu grob?**

<details>
<summary>Antwort</summary>

Weil unterschiedliche Behandlungsbausteine unterschiedliche Ziele adressieren. Medikamente können Kernsymptome kurzfristig deutlich reduzieren, während psychologische, familiäre, schulische und organisatorische Interventionen Strategien, Umfeld und verbleibende Funktionsprobleme bearbeiten. Die passende Auswahl hängt von Alter, Beeinträchtigung, Begleiterkrankungen, Präferenzen, Nebenwirkungen, Zugänglichkeit und den vorher festgelegten Alltagszielen ab.

</details>

## Wissenschaftliche Quelle

[[references/Ostinelli2025|Ostinelli et al. 2025]] – umfassende Netzwerk-Meta-Analyse randomisierter Behandlungen bei Erwachsenen.

[[references/Peterson2024|Peterson et al. 2024]] – systematische Übersicht kontrollierter Behandlungen bei Kindern und Jugendlichen.

[[references/Tuerk2023|Türk et al. 2023]] – Umbrella-Review und Meta-Meta-Analyse pharmakologischer und psychologischer Interventionen bei jungen Menschen.

[[references/Liu2023|Liu et al. 2023]] – Meta-Analyse randomisierter kognitiv-verhaltenstherapeutischer Interventionen bei Erwachsenen.

[[references/Nourredine2026|Nourredine et al. 2026]] – Dosis-Wirkungs-Netzwerk-Meta-Analyse von ADHS-Medikamenten über Altersgruppen.

[[references/AADPA2022|AADPA 2022]] – evidenzbasierte Leitlinie zu gemeinsamer Planung, Pharmakotherapie, psychologischen Interventionen und Monitoring.

## Merksatz

> Gute ADHS-Behandlung ist kein Wettbewerb zwischen Medikament und Psychotherapie, sondern ein überprüfbarer Plan: Der passende Baustein muss ein relevantes Ziel erreichen, im Alltag umsetzbar sein und mehr Nutzen als Belastung erzeugen.

## Navigation

- Zurück: [[01-Grundlagen/12-Komorbiditaet-Depression-und-Suizidalitaet|Komorbidität, Depression und Suizidalität]]
- Weiter: [[README|Übersicht]]
- [[Glossar]] · [[Literatur]] · [[knowledge-graph/README|Wissensgraph]]
'''
write("02-Vertiefung/01-Pharmakologie-und-Psychotherapie.md", chapter)

references = {
    "Ostinelli2025": r'''
---
reference_id: Ostinelli2025
title: Ostinelli et al. 2025
evidence_type: systematic-review-component-network-meta-analysis
evidence_grade: high
status: consensus
doi: "10.1016/S2215-0366(24)00360-2"
pmid: "39701638"
last_checked: 2026-07-22
tags: [Literatur, ADHS, Erwachsene, Pharmakotherapie, Psychotherapie]
citation:
  entry_type: article
  csl_type: article-journal
  authors:
    - "Ostinelli, E. G."
    - "Schulze, M."
    - "Zangani, C."
  et_al: true
  year: 2025
  article_title: "Comparative efficacy and acceptability of pharmacological, psychological, and neurostimulatory interventions for ADHD in adults: A systematic review and component network meta-analysis"
  journal: "The Lancet Psychiatry"
  volume: "12"
  issue: "1"
  pages: "32–43"
---

# Ostinelli et al. 2025

## Vollständige Zitation

Ostinelli, E. G., Schulze, M., Zangani, C., et al. (2025). Comparative efficacy and acceptability of pharmacological, psychological, and neurostimulatory interventions for ADHD in adults: A systematic review and component network meta-analysis. *The Lancet Psychiatry, 12*(1), 32–43.

## Evidenztyp und Design

Systematische Übersichtsarbeit und komponentenbasierte Netzwerk-Meta-Analyse von 113 randomisierten kontrollierten Studien mit 14.887 Erwachsenen. Verglichen wurden pharmakologische, psychologische, neurostimulatorische und Kontrollinterventionen, überwiegend über ungefähr zwölf Wochen.

## Population

Erwachsene mit diagnostizierter ADHS aus randomisierten Studien. Die eingeschlossenen Untersuchungen unterschieden sich bei Intervention, Vergleichsbedingung, Begleiterkrankungen und Messinstrumenten.

## Kernaussage

Stimulanzien und Atomoxetin reduzierten kurzfristig ADHS-Kernsymptome sowohl in Selbst- als auch Fremdbeurteilungen im Mittel zuverlässiger als Placebo. Für mehrere psychologische Verfahren zeigten sich günstige Fremdbeurteilungen, während Selbstbeurteilungen und breitere Funktions- oder Lebensqualitätsmaße weniger konsistent waren.

## Einschränkungen

Die Evidenz war zwischen Vergleichen unterschiedlich sicher. Langzeitdaten über zwölf Wochen hinaus waren knapp, und kombinierte pharmakologische plus psychologische Behandlung wurde nicht umfassend verglichen. Wesentlich mehr Teilnehmende lagen für Medikamente als für viele nichtpharmakologische Verfahren vor.

## Verhältnis zum bisherigen Konsens

Bestätigt die kurzfristige Wirksamkeit etablierter Medikamente bei Erwachsenen und präzisiert, dass Kernsymptomwirkung nicht automatisch breitere Lebensqualität oder langfristige Funktion abbildet.

## Links

- [DOI](https://doi.org/10.1016/S2215-0366(24)00360-2)
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/39701638/)
''',
    "Peterson2024": r'''
---
reference_id: Peterson2024
title: Peterson et al. 2024
evidence_type: systematic-review
evidence_grade: high
status: consensus
doi: "10.1542/peds.2024-065787"
pmid: "38523592"
last_checked: 2026-07-22
tags: [Literatur, ADHS, Kinder, Jugendliche, Behandlung]
citation:
  entry_type: article
  csl_type: article-journal
  authors:
    - "Peterson, B. S."
    - "Trampush, J."
    - "Maglione, M."
  et_al: true
  year: 2024
  article_title: "Treatments for ADHD in Children and Adolescents: A Systematic Review"
  journal: Pediatrics
  volume: "153"
  issue: "4"
  article_number: "e2024065787"
---

# Peterson et al. 2024

## Vollständige Zitation

Peterson, B. S., Trampush, J., Maglione, M., et al. (2024). Treatments for ADHD in Children and Adolescents: A Systematic Review. *Pediatrics, 153*(4), e2024065787.

## Evidenztyp und Design

Breite systematische Übersichtsarbeit kontrollierter Behandlungsstudien aus zwölf Datenbanken bis Juni 2023. Eingeschlossen wurden 312 Studien in 540 Publikationen zu Medikamenten, psychosozialen Interventionen, Elternunterstützung, Schule, Ernährung, Neurofeedback, Bewegung und weiteren Ansätzen.

## Population

Kinder und Jugendliche mit klinisch diagnostizierter ADHS. Altersgruppen, Komorbiditäten, Behandlungsdauer, Endpunkte und Versorgungssettings waren heterogen.

## Kernaussage

Mehrere Medikamente reduzieren ADHS-Symptome im Mittel. Psychosoziale, elternbezogene und schulische Interventionen können je nach Ziel Symptome, Verhalten, Elternbelastung oder Funktionsbereiche verbessern. Die Evidenz ist nicht für alle Interventionen, Altersgruppen und langfristigen Endpunkte gleich stark.

## Einschränkungen

Viele Studien waren kurz, nutzten unterschiedliche Beurteiler und berichteten breitere Alltags- oder Langzeitergebnisse uneinheitlich. Direkte Vergleiche und zuverlässige Aussagen zu individuell optimalen Kombinationen bleiben begrenzt.

## Verhältnis zum bisherigen Konsens

Bestätigt die multimodale Lehrmeinung und präzisiert, dass Behandlungswahl nach Ziel und Altersgruppe erfolgen muss, statt alle Interventionen über einen einzigen Symptomwert zu bewerten.

## Links

- [DOI](https://doi.org/10.1542/peds.2024-065787)
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/38523592/)
''',
    "Tuerk2023": r'''
---
reference_id: Tuerk2023
title: Türk et al. 2023
evidence_type: umbrella-review-meta-meta-analysis
evidence_grade: moderate
status: consensus
doi: "10.1016/j.cpr.2023.102271"
pmid: "37030086"
last_checked: 2026-07-22
tags: [Literatur, ADHS, Kinder, Jugendliche, Pharmakotherapie, Psychotherapie]
citation:
  entry_type: article
  csl_type: article-journal
  authors:
    - "Türk, S."
    - "Korfmacher, A.-K."
    - "Gerger, H."
    - "van der Oord, S."
    - "Christiansen, H."
  et_al: false
  year: 2023
  article_title: "Interventions for ADHD in childhood and adolescence: A systematic umbrella review and meta-meta-analysis"
  journal: "Clinical Psychology Review"
  volume: "102"
  article_number: "102271"
---

# Türk et al. 2023

## Vollständige Zitation

Türk, S., Korfmacher, A.-K., Gerger, H., van der Oord, S., & Christiansen, H. (2023). Interventions for ADHD in childhood and adolescence: A systematic umbrella review and meta-meta-analysis. *Clinical Psychology Review, 102*, 102271.

## Evidenztyp und Design

Systematischer Umbrella-Review mit Meta-Meta-Analysen bereits veröffentlichter Meta-Analysen. Die Suche bis Juli 2022 identifizierte 16 Meta-Analysen für quantitative Synthesen pharmakologischer und psychologischer Interventionen.

## Population

Kinder und Jugendliche mit ADHS. Die zugrunde liegenden Meta-Analysen unterschieden sich bei Alter, Interventionen, Kontrollgruppen, Dauer und Beurteilern.

## Kernaussage

Sowohl pharmakologische als auch psychologische Interventionen waren im Mittel mit Symptomverbesserungen verbunden. Medikamentöse Effekte fielen in den zusammengefassten Bewertungen größer aus; psychologische Effekte waren vorhanden, aber zwischen Eltern- und Lehrerurteilen unterschiedlich.

## Einschränkungen

Umbrella-Reviews übernehmen methodische Grenzen und Überschneidungen der zugrunde liegenden Meta-Analysen. Für kombinierte Behandlungen ließ sich wegen fehlender geeigneter Meta-Analysen kein stabiler gemeinsamer Effekt berechnen; Jugendliche waren vergleichsweise wenig untersucht.

## Verhältnis zum bisherigen Konsens

Bestätigt, dass beide Behandlungskategorien evidenzbasierte Bausteine sind, widerspricht aber der Annahme, ihre Kombination sei automatisch und für jedes Ziel nachweislich überlegen.

## Links

- [DOI](https://doi.org/10.1016/j.cpr.2023.102271)
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/37030086/)
''',
    "Liu2023": r'''
---
reference_id: Liu2023
title: Liu et al. 2023
evidence_type: meta-analysis-randomized-controlled-trials
evidence_grade: moderate
status: probable
doi: "10.1111/papt.12455"
pmid: "36794797"
last_checked: 2026-07-22
tags: [Literatur, ADHS, Erwachsene, Kognitive Verhaltenstherapie]
citation:
  entry_type: article
  csl_type: article-journal
  authors:
    - "Liu, C.-I."
    - "Hua, M.-H."
    - "Lu, M.-L."
    - "Goh, K. K."
  et_al: false
  year: 2023
  article_title: "Effectiveness of cognitive behavioural-based interventions for adults with attention-deficit/hyperactivity disorder extends beyond core symptoms: A meta-analysis of randomized controlled trials"
  journal: "Psychology and Psychotherapy: Theory, Research and Practice"
  volume: "96"
  issue: "3"
  pages: "543–559"
---

# Liu et al. 2023

## Vollständige Zitation

Liu, C.-I., Hua, M.-H., Lu, M.-L., & Goh, K. K. (2023). Effectiveness of cognitive behavioural-based interventions for adults with attention-deficit/hyperactivity disorder extends beyond core symptoms: A meta-analysis of randomized controlled trials. *Psychology and Psychotherapy: Theory, Research and Practice, 96*(3), 543–559.

## Evidenztyp und Design

Meta-Analyse randomisierter kontrollierter Studien zu kognitiv-verhaltenstherapeutisch basierten Interventionen bei Erwachsenen mit ADHS. Untersucht wurden Kernsymptome und weitere psychologische Endpunkte.

## Population

Erwachsene mit diagnostizierter ADHS in strukturierten psychologischen Behandlungsstudien; ein Teil erhielt parallel Medikamente oder übliche Versorgung.

## Kernaussage

Kognitiv-verhaltenstherapeutische Interventionen waren im Mittel mit Verbesserungen von ADHS-Symptomen und mehreren zusätzlichen psychologischen Bereichen verbunden. Sie können daher besonders für erlernbare Strategien und verbleibende Funktionsprobleme relevant sein.

## Einschränkungen

Psychotherapie lässt sich nur begrenzt verblinden. Studien, Programme, Vergleichsgruppen und Begleitmedikation unterschieden sich; Stichproben waren häufig kleiner als in Medikamentenstudien. Langfristige und funktionelle Endpunkte sind nicht vollständig geklärt.

## Verhältnis zum bisherigen Konsens

Unterstützt Leitlinienempfehlungen für strukturierte ADHS-spezifische psychologische Interventionen bei Erwachsenen, als Alternative oder Ergänzung entsprechend Präferenz und verbleibender Beeinträchtigung.

## Links

- [DOI](https://doi.org/10.1111/papt.12455)
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/36794797/)
''',
    "Nourredine2026": r'''
---
reference_id: Nourredine2026
title: Nourredine et al. 2026
evidence_type: systematic-review-dose-effect-network-meta-analysis
evidence_grade: high
status: probable
doi: "10.1016/S2215-0366(26)00091-X"
pmid: "42134365"
last_checked: 2026-07-22
tags: [Literatur, ADHS, Pharmakotherapie, Dosisfindung, Nebenwirkungen]
citation:
  entry_type: article
  csl_type: article-journal
  authors:
    - "Nourredine, M."
    - "Jurek, L."
    - "Hamza, T."
  et_al: true
  year: 2026
  article_title: "Pharmacological interventions for ADHD: A systematic review and dose–effect network meta-analysis"
  journal: "The Lancet Psychiatry"
  volume: "13"
  issue: "6"
  pages: "485–495"
---

# Nourredine et al. 2026

## Vollständige Zitation

Nourredine, M., Jurek, L., Hamza, T., et al. (2026). Pharmacological interventions for ADHD: A systematic review and dose–effect network meta-analysis. *The Lancet Psychiatry, 13*(6), 485–495.

## Evidenztyp und Design

Systematische Übersichtsarbeit und Dosis-Wirkungs-Netzwerk-Meta-Analyse doppelblinder randomisierter Studien oraler ADHS-Monotherapien bei Personen ab fünf Jahren. Modelliert wurden durchschnittliche Zusammenhänge zwischen Dosis, Symptomwirkung und Abbruch wegen Nebenwirkungen.

## Population

Kinder, Jugendliche und Erwachsene mit standardisiert diagnostizierter ADHS. Wirkstoffe, Präparate, Dosierungsbereiche und Studiendauer unterschieden sich zwischen den Altersgruppen.

## Kernaussage

Die durchschnittliche Dosis-Wirkungs-Beziehung ist nicht bei allen Wirkstoffen linear. Eine schrittweise fachliche Dosisfindung kann Unterbehandlung vermeiden, während unkritische Steigerung zusätzlichen Nutzen überschätzen und Nebenwirkungen erhöhen kann.

## Einschränkungen

Aggregierte Studienkurven bestimmen keine individuelle Dosis und ersetzen weder Zulassungsgrenzen noch klinisches Monitoring. Für manche Wirkstoffe und Dosisbereiche waren Daten dünn. Die Zeitschrift veröffentlichte 2026 eine formale Korrektur; die Studie ist anhand der korrigierten Fassung zu lesen.

## Verhältnis zum bisherigen Konsens

Präzisiert die etablierte Empfehlung zur individuellen Titration und widerspricht sowohl starrer Minimaldosierung als auch der Annahme, höhere Dosen seien grundsätzlich wirksamer.

## Links

- [DOI](https://doi.org/10.1016/S2215-0366(26)00091-X)
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/42134365/)
- [Veröffentlichte Korrektur](https://doi.org/10.1016/S2215-0366(26)00175-6)
''',
}
for reference_id, content in references.items():
    write(f"references/{reference_id}.md", content)

# Update index.json.
index_path = ROOT / "index.json"
index = json.loads(index_path.read_text(encoding="utf-8"))
if any(item.get("number") == 13 for item in index["chapters"]):
    raise RuntimeError("Einheit 13 ist bereits im Index vorhanden")
index["version"] = "0.12.0"
index["last_reviewed"] = TODAY
index["chapters"].append({
    "number": 13,
    "path": "02-Vertiefung/01-Pharmakologie-und-Psychotherapie.md",
    "title": "Pharmakotherapie und Psychotherapie",
})
index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# README: version, review date and learning path.
readme_path = ROOT / "README.md"
readme = readme_path.read_text(encoding="utf-8")
readme = re.sub(r"(?m)^version: .*$',", "", readme) if False else readme
readme = re.sub(r"(?m)^version: .*?$", "version: 0.12.0", readme, count=1)
readme = re.sub(r"(?m)^last_reviewed: .*?$", f"last_reviewed: {TODAY}", readme, count=1)
line13 = "13. [[02-Vertiefung/01-Pharmakologie-und-Psychotherapie|Pharmakotherapie und Psychotherapie]]"
if line13 not in readme:
    anchor = "12. [[01-Grundlagen/12-Komorbiditaet-Depression-und-Suizidalitaet|Komorbidität, Depression und Suizidalität]]"
    readme = readme.replace(anchor, anchor + "\n" + line13, 1)
readme_path.write_text(readme, encoding="utf-8")

# Previous chapter navigation.
previous_path = ROOT / "01-Grundlagen/12-Komorbiditaet-Depression-und-Suizidalitaet.md"
previous = previous_path.read_text(encoding="utf-8")
previous = previous.replace(
    "- Weiter: [[README|Übersicht]]",
    "- Weiter: [[02-Vertiefung/01-Pharmakologie-und-Psychotherapie|Pharmakotherapie und Psychotherapie]]",
    1,
)
previous_path.write_text(previous, encoding="utf-8")

# MkDocs navigation: first Vertiefung section.
mkdocs_path = ROOT / "mkdocs.yml"
mkdocs = mkdocs_path.read_text(encoding="utf-8")
nav_line = "  - Vertiefung:\n      - Pharmakologie und Psychotherapie: 02-Vertiefung/01-Pharmakologie-und-Psychotherapie.md\n"
if "02-Vertiefung/01-Pharmakologie-und-Psychotherapie.md" not in mkdocs:
    mkdocs = mkdocs.replace("  - Wissenssystem:\n", nav_line + "  - Wissenssystem:\n", 1)
mkdocs_path.write_text(mkdocs, encoding="utf-8")

# Web build: use index.json for all learning chapters instead of a hard-coded Grundlagen folder.
build_docs_path = ROOT / "scripts" / "build_docs.py"
build_docs = build_docs_path.read_text(encoding="utf-8")
if "import json\n" not in build_docs:
    build_docs = build_docs.replace("from pathlib import Path\n", "from pathlib import Path\nimport json\n", 1)
old_glob = 'files.extend(str(path.relative_to(ROOT)) for path in sorted((ROOT / "01-Grundlagen").glob("*.md")))'
new_index = 'chapter_index = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))\nfiles.extend(item["path"] for item in chapter_index["chapters"])'
if old_glob in build_docs:
    build_docs = build_docs.replace(old_glob, new_index, 1)
elif new_index not in build_docs:
    raise RuntimeError("Kapitelaufnahme in build_docs.py nicht eindeutig auffindbar")
build_docs_path.write_text(build_docs, encoding="utf-8")

# Obsidian ZIP must include the new phase folder.
exports_path = ROOT / "scripts" / "build_exports.py"
exports = exports_path.read_text(encoding="utf-8")
if '    "02-Vertiefung",\n' not in exports:
    exports = exports.replace('    "01-Grundlagen",\n', '    "01-Grundlagen",\n    "02-Vertiefung",\n', 1)
exports_path.write_text(exports, encoding="utf-8")

# Remove the fulfilled planned node while preserving the remaining registry.
planned_path = ROOT / "knowledge-graph" / "planned-nodes.yaml"
planned = yaml.safe_load(planned_path.read_text(encoding="utf-8"))
planned["nodes"] = [
    node for node in planned.get("nodes", [])
    if node.get("path") != "02-Vertiefung/01-Pharmakologie-und-Psychotherapie"
]
planned_path.write_text(
    "# Bewusst geplante, noch nicht vorhandene Seiten.\n"
    "# Nur hier registrierte fehlende Ziele dürfen als \"planned\" veröffentlicht werden.\n"
    + yaml.safe_dump(planned, allow_unicode=True, sort_keys=False),
    encoding="utf-8",
)

# Glossary additions in alphabetical positions.
glossary_path = ROOT / "Glossar.md"
glossary = glossary_path.read_text(encoding="utf-8")
glossary = insert_before_heading(
    glossary,
    "## Dopamin",
    "## Dosisfindung\nSchrittweise Anpassung einer Medikamentendosis anhand vorher definierter Ziele, Wirkdauer und Nebenwirkungen innerhalb fachlicher und zugelassener Grenzen.",
)
glossary = insert_before_heading(
    glossary,
    "## Persistenz",
    "## Pharmakotherapie\nBehandlung mit Medikamenten; bei ADHS umfasst sie fachlich ausgewählte, überwachte und regelmäßig überprüfte Wirkstoffe.\n\n## Psychoedukation\nStrukturierte Vermittlung wissenschaftlich fundierten Wissens über Diagnose, Verlauf, Behandlung und Selbstbeobachtung; keine bloße Informationsbroschüre und nicht automatisch eine vollständige Psychotherapie.\n\n## Psychotherapie\nGeplante Behandlung psychischer oder verhaltensbezogener Probleme mit wissenschaftlich begründeten psychologischen Methoden und einer therapeutischen Arbeitsbeziehung.",
)
glossary = insert_before_heading(
    glossary,
    "## Screening",
    "## Shared Decision Making\nGemeinsame Entscheidungsfindung, bei der Fachperson und betroffene Person Evidenz, Unsicherheit, Ziele, Werte, Belastungen und praktische Umsetzbarkeit einer Behandlung zusammen abwägen.",
)
if "## Titration" not in glossary:
    glossary = glossary.rstrip() + "\n\n## Titration\nKontrollierte schrittweise Veränderung einer Dosis, bis ein sinnvolles Verhältnis aus Nutzen, Wirkdauer und Nebenwirkungen erreicht ist oder ein Wechsel notwendig wird.\n"
glossary = re.sub(r"(?m)^last_reviewed: .*?$", f"last_reviewed: {TODAY}", glossary, count=1)
glossary_path.write_text(glossary, encoding="utf-8")

# Anki card.
cards_path = ROOT / "cards" / "cards.yaml"
cards = yaml.safe_load(cards_path.read_text(encoding="utf-8"))
if not any(card.get("unit") == 13 for card in cards.get("cards", [])):
    cards["cards"].append({
        "id": 1013,
        "unit": 13,
        "front": "Warum ist ‚Medikament oder Psychotherapie – was ist besser?‘ für ADHS zu grob?",
        "back": "Weil Medikamente, psychologische Verfahren und Umfeldanpassungen unterschiedliche Ziele adressieren; Auswahl und Kombination richten sich nach Alter, Beeinträchtigung, Begleiterkrankungen, Präferenzen, Nebenwirkungen und beobachtbaren Alltagszielen.",
        "tags": ["ADHS", "Vertiefung", "Behandlung", "Einheit_13"],
    })
cards_path.write_text(yaml.safe_dump(cards, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")

# Changelog.
changelog_path = ROOT / "CHANGELOG.md"
changelog = changelog_path.read_text(encoding="utf-8")
entry = """## 0.12.0 – 2026-07-22

- Einheit 13 „Pharmakotherapie und Psychotherapie“ als Einstieg in die Vertiefung ergänzt
- kurzfristige Medikamentenwirkung, psychologische Interventionen, Dosisfindung, Monitoring und gemeinsame Entscheidungsfindung differenziert eingeordnet
- fünf aktuelle Studienkarten, Glossarbegriffe, Anki-Karte und Wissensgraph-Verknüpfungen ergänzt
- Kapitelbuild und Obsidian-Export auf indexbasierte phasenübergreifende Ordner erweitert

"""
if "## 0.12.0 – 2026-07-22" not in changelog:
    changelog = changelog.replace("# Änderungsverlauf\n", "# Änderungsverlauf\n\n" + entry, 1)
changelog_path.write_text(changelog, encoding="utf-8")

# Remove temporary transport before all checks and final commit.
shutil.rmtree(BOOTSTRAP)
WORKFLOW.unlink(missing_ok=True)

# Generate and stage the single-source bibliography outputs; a second unstaged diff must be empty.
run("python3", "scripts/build_literature.py")
run("git", "add", "Literatur.md", "references.bib", "references.json")
run("git", "diff", "--exit-code", "--", "Literatur.md", "references.bib", "references.json")

# Required project checks.
run("git", "diff", "--check")
run("python", "-m", "compileall", "-q", "scripts")
run("python", "-m", "pip", "check")
run("python3", "scripts/validate_links.py")
run("python3", "scripts/build_graph.py")
if (ROOT / "scripts" / "validate_graph.py").is_file():
    run("python3", "scripts/validate_graph.py")
run("python3", "scripts/validate_compendium.py")
run("python3", "scripts/build_combined.py")
run("python3", "scripts/build_anki.py")
run("python3", "scripts/build_docs.py")
run("mkdocs", "build", "--strict")

# Calculate the project's prose word count exactly as the validator does.
text = (ROOT / "02-Vertiefung/01-Pharmakologie-und-Psychotherapie.md").read_text(encoding="utf-8")
text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
text = re.sub(r"```.*?```", "", text, flags=re.S)
text = re.sub(r"</?(?:details|summary)>", "", text)
text = re.sub(r"## Navigation.*\Z", "", text, flags=re.S)
text = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda match: match.group(2) or match.group(1), text)
words = len(re.findall(r"\b[\wÄÖÜäöüß]+(?:[-’'][\wÄÖÜäöüß]+)*\b", text))
print(f"UNIT_13_PROSE_WORDS={words}")
if not 1000 <= words <= 2000:
    raise RuntimeError(f"Einheit 13 liegt mit {words} Wörtern außerhalb des Zielbereichs 1000–2000")

# Commit only the final unit changes.
run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", "-A")
run("git", "commit", "-m", "Einheit 13: Pharmakotherapie und Psychotherapie")
run("git", "push", "origin", f"HEAD:{BRANCH}")
print(f"UNIT_13_COMPLETE words={words} branch={BRANCH}")
