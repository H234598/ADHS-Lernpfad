#!/usr/bin/env python3
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "agent/einheit-12-depression-und-suizidalitaet"
BOOTSTRAP = ROOT / ".unit12-bootstrap"
WORKFLOW = ROOT / ".github" / "workflows" / "apply-unit-12.yml"


def write(path: str, content: str) -> None:
    destination = ROOT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content.strip() + "\n", encoding="utf-8")


def run(*command: str) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def insert_glossary_term(term: str, definition: str) -> None:
    path = ROOT / "Glossar.md"
    text = path.read_text(encoding="utf-8")
    marker = f"## {term}\n"
    if marker in text:
        return
    matches = list(re.finditer(r"(?m)^## (.+)$", text))
    position = len(text)
    for match in matches:
        if match.group(1).casefold() > term.casefold():
            position = match.start()
            break
    block = f"## {term}\n{definition}\n\n"
    text = text[:position] + block + text[position:]
    text = re.sub(r"(?m)^last_reviewed: .+$", "last_reviewed: 2026-07-21", text, count=1)
    path.write_text(text, encoding="utf-8")


unit = r'''---
title: Komorbidität, Depression und Suizidalität
level: Grundlagen
estimated_time: 10–20 min
difficulty: 3
prerequisites: ["01-Grundlagen/01-Was-ist-ADHS", "01-Grundlagen/07-Emotionsregulation", "01-Grundlagen/09-Diagnostische-Kriterien-und-Differentialdiagnostik", "01-Grundlagen/11-Schlaf-Bewegung-und-koerperliche-Gesundheit"]
tags: [ADHS, Komorbidität, Depression, Suizidalität, Selbstverletzung, Krisenhilfe]
last_reviewed: 2026-07-21
evidence: high
status: consensus
references: [AADPA2022, Fitzgerald2019, Garas2025, NICE2022SelfHarm, NVLDepression2022, Septier2019, Zhang2025Depression, Zhang2025Medication]
minimum_reading_minutes: 10
maximum_reading_minutes: 20
---

# Einheit 12 – Komorbidität, Depression und Suizidalität

## Lernziel

Du kannst ADHS und Depression als unterscheidbare, aber häufig gemeinsam auftretende Störungen einordnen. Du erkennst, warum ein erhöhtes Suizidalitätsrisiko auf Gruppenebene keine Vorhersage für eine einzelne Person erlaubt, weshalb Selbstverletzung und Suizidabsicht getrennt erfragt werden müssen und wann unmittelbare Hilfe wichtiger ist als weitere Selbstbeobachtung. Außerdem verstehst du, warum Behandlung und Sicherheitsplanung beide Störungsbilder sowie die konkrete Lebenssituation berücksichtigen müssen.

## 1. Komorbidität bedeutet gleichzeitig, nicht identisch

**[[Glossar#Komorbidität|Komorbidität]]** bedeutet, dass bei einer Person mehrere klinisch relevante Störungen oder Erkrankungen gleichzeitig vorliegen. ADHS erhöht nicht automatisch die Wahrscheinlichkeit, dass jede betroffene Person eine Depression entwickelt. Umgekehrt erklären depressive Symptome nicht rückwirkend jedes seit der Kindheit bestehende Aufmerksamkeits- oder Impulsivitätsproblem.

Systematische Übersichten finden bei Erwachsenen mit ADHS häufiger affektive Störungen als in Vergleichsgruppen. Bei Kindern und Jugendlichen zeigte eine aktuelle Meta-Analyse ungefähr ein verdoppeltes Risiko für depressive Störungen. Solche Zahlen beschreiben Gruppen. Sie sagen nicht, ob eine konkrete Person depressiv ist, wann eine Episode beginnt oder wie schwer sie verläuft.

> [!evidence] Evidenz: Konsens / hoch
> Depression und Suizidalität gehören nicht zu den diagnostischen Kernmerkmalen der ADHS. Sie treten jedoch häufiger gemeinsam mit ADHS auf und müssen bei Diagnostik, Verlaufskontrolle und Krisenbeurteilung ausdrücklich berücksichtigt werden.

Mehrere Wege können zur Überschneidung beitragen: genetische Gemeinsamkeiten, wiederholte Misserfolge und soziale Ausgrenzung, chronische Überforderung, Schlafprobleme, Substanzgebrauch, traumatische Erfahrungen oder weitere psychische Störungen. Diese Faktoren sind weder bei allen Menschen vorhanden noch beweisen sie eine einfache Ursache-Wirkungs-Kette.

## 2. Ähnliche Oberfläche, unterschiedliche Zeitgeschichte

Unaufmerksamkeit, geringe Aktivierung, Schlafstörungen, Reizbarkeit und Schwierigkeiten beim Beginnen von Aufgaben können sowohl bei ADHS als auch bei Depression auftreten. Für die Einordnung sind deshalb **Verlauf und Veränderung gegenüber dem persönlichen Ausgangsniveau** zentral.

ADHS beginnt definitionsgemäß in der Entwicklung und zeigt sich typischerweise über längere Zeit in mehreren Situationen. Eine [[Glossar#Depressive Episode|depressive Episode]] ist dagegen ein zeitlich abgrenzbares Syndrom. Zu ihr können anhaltend gedrückte Stimmung, deutliche [[Glossar#Anhedonie|Anhedonie]], Hoffnungslosigkeit, Schuldgefühle, psychomotorische Veränderungen, ausgeprägte Erschöpfung und Suizidgedanken gehören. Bei Kindern und Jugendlichen kann Reizbarkeit stärker im Vordergrund stehen.

Ein Beispiel: Eine Person hat seit der Schulzeit Probleme mit Zeitplanung und Arbeitsbeginn. Seit sechs Wochen verliert sie zusätzlich nahezu jedes Interesse, zieht sich zurück, erlebt sich als wertlos und sieht keine Zukunft. Die neuen Veränderungen sollten nicht als „nur mehr ADHS“ erklärt werden. Umgekehrt reicht eine vorübergehende Frustration nach einem chaotischen Tag nicht für die Diagnose einer Depression.

Die Trennung ist klinisch wichtig, aber nicht immer einfach. ADHS kann den Alltag so unregelmäßig machen, dass Beginn und Dauer depressiver Symptome schwer zu erinnern sind. Depression kann wiederum Gedächtnis, Konzentration und Selbstbeurteilung beeinflussen. Fremdanamnese, zeitliche Verläufe und wiederholte Gespräche können deshalb hilfreicher sein als ein einzelner Fragebogenwert.

## 3. Erhöhtes Risiko ist kein individuelles Schicksal

Meta-Analysen und Registerstudien zeigen konsistent einen statistischen Zusammenhang zwischen ADHS und Suizidgedanken, Suizidversuchen sowie Suizidtod. Eine aktuelle Meta-Analyse longitudinaler Studien bei jungen Menschen fand im Mittel etwa dreifach erhöhte Chancen für verschiedene suizidale Verläufe. Die eingeschlossenen Studien unterschieden sich jedoch stark nach Alter, Geschlecht, ADHS-Ausprägung, Begleiterkrankungen, sozialer Situation und Messmethode.

Das bedeutet zweierlei gleichzeitig:

1. Das Thema darf in Versorgung und Prävention nicht übersehen werden.
2. Aus der Diagnose ADHS lässt sich nicht ableiten, ob eine bestimmte Person suizidal ist.

Ein großes dänisches Register zeigte, dass zusätzliche psychische Erkrankungen das Risiko deutlich weiter erhöhten. Besonders wichtig sind daher aktuelle Depression, frühere Suizidversuche, Substanzkonsum, akute Verluste oder Konflikte, Gewalt- und Traumaerfahrungen, starke Hoffnungslosigkeit, fehlende Unterstützung sowie der unmittelbare Zugang zu Hilfe. Auch Schutzfaktoren zählen: tragfähige Beziehungen, erreichbare Behandlung, ein konkreter Sicherheitsplan und die Bereitschaft, Warnzeichen mitzuteilen.

```mermaid
flowchart TD
  A[ADHS-bezogene Beeinträchtigung] --> B[Belastung und wiederholte Misserfolge]
  C[Depression oder andere Komorbidität] --> D[Hoffnungslosigkeit und Krisendruck]
  E[Substanzgebrauch, Konflikte oder Trauma] --> D
  F[Impulsivität und geringe Krisendistanz] --> G[verkürzte Zeit zwischen Impuls und Handlung]
  B --> D
  D --> H[Suizidgedanken oder Selbstgefährdung]
  G --> H
  I[Behandlung, Beziehungen, Sicherheitsplan und erreichbare Hilfe] --> J[Schutz und Unterbrechung]
  J --> B
  J --> D
  J --> G
```

Das Diagramm ist kein Vorhersagemodell. Es zeigt, warum eine einzelne Risikozahl die konkrete Situation nicht ersetzt.

## 4. Suizidgedanken, Suizidversuch und Selbstverletzung unterscheiden

**[[Glossar#Suizidalität|Suizidalität]]** umfasst Gedanken an den Tod oder Suizid, Absichten, Planungen und suizidale Handlungen. Diese Bereiche unterscheiden sich in Dringlichkeit und Bedeutung. Sie müssen direkt, respektvoll und ohne moralische Bewertung erfragt werden.

**[[Glossar#Nichtsuizidales selbstverletzendes Verhalten|Nichtsuizidales selbstverletzendes Verhalten]]** bezeichnet absichtliche Selbstverletzung ohne die Absicht zu sterben. In der Praxis ist die Absicht jedoch nicht immer eindeutig oder stabil. Ein Mensch kann ambivalente Motive haben, und Selbstverletzung ist mit einem erhöhten späteren Suizidrisiko verbunden. Deshalb darf weder automatisch Suizidabsicht unterstellt noch eine Selbstverletzung als „nur Aufmerksamkeit“ abgewertet werden.

Leitlinien raten davon ab, Menschen mit einer einfachen Skala als „niedriges“, „mittleres“ oder „hohes“ Risiko einzusortieren und daraus Behandlung oder Entlassung abzuleiten. Sinnvoller ist eine individuelle Formulierung: Was ist gerade geschehen? Welche Gedanken, Absichten und Vorbereitungen bestehen? Was hat sich verändert? Welche Mittel und Hilfen sind erreichbar? Was hilft, die nächste Zeit sicher zu überstehen?

> [!important] Bei akuter Gefahr
> Bei konkreter Suizidabsicht, unmittelbar drohender Selbstgefährdung oder wenn eine Person sich nicht bis zum Erreichen von Hilfe sicher halten kann: nicht allein bleiben, gefährliche Mittel soweit ohne Eigengefährdung entfernen und sofort den örtlichen Notruf, einen psychiatrischen Krisendienst oder eine Notaufnahme kontaktieren. In Deutschland ist der Notruf **112**. Eine Lernübung oder Onlineinformation darf akute Hilfe nicht verzögern.

## 5. Sicherheitsplanung ist konkret, nicht nur ein Versprechen

Ein **[[Glossar#Sicherheitsplan|Sicherheitsplan]]** ist eine kurze, gemeinsam erarbeitete Reihenfolge konkreter Schritte für eine Krise. Er ist mehr als die Zusage „Ich tue mir nichts an“. Er kann enthalten:

- persönliche Warnzeichen,
- Aktivitäten, die kurzfristig Distanz schaffen,
- erreichbare Personen und sichere Orte,
- professionelle Anlaufstellen,
- Maßnahmen, die den Zugang zu gefährlichen Mitteln verringern,
- die Vereinbarung, wann sofort Notfallhilfe eingeschaltet wird.

Der Plan muss realistisch sein. Eine Kontaktperson, die nachts nicht erreichbar ist, reicht nicht als einzige Option. Bei ADHS helfen kurze Formulierungen, sichtbare Speicherung, wenige Prioritäten und ein leicht auffindbarer Zugang. Ein Sicherheitsplan ersetzt keine Behandlung und keine akute fachliche Beurteilung.

## 6. Behandlung muss beide Störungsbilder und die Dringlichkeit berücksichtigen

Bei gleichzeitig bestehender ADHS und Depression wird nicht nach einer starren Reihenfolge behandelt. Akute Suizidalität oder eine schwere depressive Episode haben zunächst hohe Priorität. In stabileren Situationen kann eine wirksame ADHS-Behandlung Funktionsprobleme, Konflikte und Überforderung reduzieren; eine spezifische Depressionsbehandlung bleibt dennoch erforderlich, wenn eine depressive Störung vorliegt.

Beobachtungsdaten sprechen nicht dafür, dass eine leitliniengerechte medikamentöse ADHS-Behandlung das Suizidalitätsrisiko generell erhöht. Eine große schwedische Target-Trial-Emulation fand bei Behandlungsbeginn niedrigere Raten suizidalen Verhaltens. Auch eine Meta-Analyse bei jungen Menschen fand eine Assoziation von Stimulanzien mit geringerem Depressionsrisiko. Beide Befunde sind wichtig, beweisen aber keine schützende Wirkung für jede Person: Indikation, Auswahl, Begleiterkrankungen, Behandlungskontakt und nicht gemessene Unterschiede können Ergebnisse beeinflussen.

Medikamente dürfen deshalb weder pauschal als Gefahr noch als Suizidprävention dargestellt werden. Neue oder zunehmende Suizidgedanken, starke Stimmungsschwankungen, Aktivierungszustände oder andere auffällige Veränderungen gehören unabhängig von der vermuteten Ursache rasch in fachliche Beurteilung.

## 7. Mini-Übung: Hilfekette vor der Krise festlegen

Diese Übung ist für stabile Situationen gedacht. Bei aktueller Suizidabsicht gilt stattdessen der Notfallhinweis oben.

Schreibe auf eine gut erreichbare Karte:

1. zwei persönliche Warnzeichen, bei denen du nicht mehr allein weiterprobierst,
2. eine Person, die du direkt informieren kannst,
3. eine professionelle Anlaufstelle,
4. den örtlichen Notruf,
5. einen Satz, mit dem du das Gespräch beginnst, zum Beispiel: „Mir geht es psychisch deutlich schlechter und ich brauche heute Unterstützung.“

Prüfe, ob Telefonnummern und Wege aktuell sind. Für Menschen mit ADHS kann es helfen, die Karte zusätzlich auf dem Sperrbildschirm, im Portemonnaie oder bei einer vertrauten Person zu hinterlegen.

## 8. Wissenschaftliche Einordnung und Grenzen

**Konsens:** Depressionen und suizidale Verläufe treten bei Menschen mit ADHS häufiger auf als in Vergleichsgruppen. Suizidalität soll direkt und individuell erfragt werden. Depression, Substanzgebrauch und weitere Komorbiditäten sind wichtige, aber nicht alleinige Risikofaktoren.

**Wahrscheinlich:** Mehrere Pfade verbinden ADHS mit Krisen, darunter funktionelle Beeinträchtigung, soziale Belastung, Impulsivität, Emotionsregulation und Komorbiditäten. Gute Behandlung und erreichbare Unterstützung können einzelne Pfade unterbrechen.

**Umstritten:** Wie stark einzelne ADHS-Merkmale unabhängig von Depression und anderen Faktoren zum Risiko beitragen. Studien verwenden unterschiedliche Definitionen und Populationen; seltene Ereignisse erzeugen breite Unsicherheiten.

**Experimentell:** Individuelle Vorhersagemodelle aus klinischen, digitalen oder biologischen Daten. Derzeit kann kein Algorithmus zuverlässig entscheiden, wer einen Suizidversuch unternehmen wird. Klinische Aufmerksamkeit und konkrete Sicherheitsunterstützung bleiben unverzichtbar.

## 9. Verbindung zu Autismus und Parkinson

Auch bei Autismus können Depression, Selbstverletzung und Suizidalität auftreten. Kommunikationsunterschiede, soziale Ausgrenzung, sensorische Belastung und Masking können die Erfassung verändern. Eine gemeinsame Krise macht ADHS und Autismus nicht identisch; Fragen und Hilfen müssen verständlich und individuell angepasst werden.

Bei Parkinson können Depression und Suizidgedanken ebenfalls vorkommen, etwa im Zusammenhang mit Erkrankungsbelastung, neurobiologischen Veränderungen oder Behandlung. Parkinson ist eine neurodegenerative Erkrankung und verlangt eine andere medizinische Einordnung. Neu auftretende Depression oder Suizidalität darf in keiner Diagnosegruppe als „typisch und deshalb harmlos“ abgetan werden.

## Review-Frage

**Warum reicht die Feststellung „ADHS erhöht das Suizidrisiko“ weder für eine individuelle Vorhersage noch für eine gute Krisenbeurteilung aus?**

<details>
<summary>Antwort</summary>

Weil der Zusammenhang ein Gruppenbefund mit großer Heterogenität ist. Die konkrete Beurteilung muss aktuelle Suizidgedanken und Absichten, frühere Handlungen, Depression und weitere Komorbiditäten, Substanzgebrauch, Belastungen, erreichbare Mittel, Schutzfaktoren und verfügbare Hilfe berücksichtigen. Risikoskalen oder die ADHS-Diagnose allein dürfen weder Behandlung noch Entlassung entscheiden.

</details>

## Wissenschaftliche Quelle

[[references/Zhang2025Depression|Zhang et al. 2025]] – systematische Übersichtsarbeit und Meta-Analyse zu Depression und Angst bei Kindern und Jugendlichen mit ADHS.

[[references/Septier2019|Septier et al. 2019]] – präregistrierte systematische Übersichtsarbeit und Meta-Analyse zum Zusammenhang zwischen ADHS und suizidalen Verläufen.

[[references/Garas2025|Garas et al. 2025]] – Meta-Analyse longitudinaler Studien zu Suizidalität bei Kindern und Jugendlichen mit ADHS.

[[references/Fitzgerald2019|Fitzgerald et al. 2019]] – nationale dänische Registerkohorte zur Bedeutung zusätzlicher psychischer Störungen.

[[references/NVLDepression2022|NVL Unipolare Depression 2022]] und [[references/NICE2022SelfHarm|NICE NG225]] – Leitlinien zur Erfassung und zum Management von Depression, Suizidalität und Selbstverletzung.

## Merksatz

> ADHS kann mit Depression und erhöhtem Suizidalitätsrisiko verbunden sein; gute Versorgung trennt Diagnosen, fragt Krisen direkt und ersetzt Gruppenstatistik durch eine konkrete, respektvolle Sicherheitsbeurteilung.

## Navigation

- Zurück: [[01-Grundlagen/11-Schlaf-Bewegung-und-koerperliche-Gesundheit|Schlaf, Bewegung und körperliche Gesundheit]]
- Weiter: [[README|Übersicht]]
- [[Glossar]] · [[Literatur]] · [[knowledge-graph/README|Wissensgraph]]
'''

write("01-Grundlagen/12-Komorbiditaet-Depression-und-Suizidalitaet.md", unit)

references = {
"references/Fitzgerald2019.md": r'''---
reference_id: Fitzgerald2019
title: Fitzgerald et al. 2019
evidence_type: national-register-cohort
evidence_grade: moderate
status: consensus
doi: "10.1192/bjp.2019.128"
pmid: "31172893"
last_checked: 2026-07-21
tags: [Literatur, ADHS, Suizidalität, Komorbidität, Registerstudie]
citation:
  entry_type: article
  csl_type: article-journal
  authors:
    - "Fitzgerald, C."
    - "Dalsgaard, S."
    - "Nordentoft, M."
    - "Erlangsen, A."
  et_al: false
  year: 2019
  article_title: "Suicidal behaviour among persons with attention-deficit hyperactivity disorder"
  journal: The British Journal of Psychiatry
  volume: "215"
  issue: "4"
  pages: "615–620"
---

# Fitzgerald et al. 2019

## Vollständige Zitation

Fitzgerald, C., Dalsgaard, S., Nordentoft, M., & Erlangsen, A. (2019). Suicidal behaviour among persons with attention-deficit hyperactivity disorder. *The British Journal of Psychiatry, 215*(4), 615–620.

## Evidenztyp und Design

Nationale populationsbasierte Registerkohorte mit Poisson-Regressionsmodellen und Anpassung für soziodemografische Faktoren sowie elterliches suizidales Verhalten.

## Population

2,9 Millionen in Dänemark registrierte Personen ab zehn Jahren mit dänisch geborenen Eltern; mehr als 46 Millionen Personenjahre zwischen 1995 und 2014.

## Kernaussage

ADHS war mit höheren Raten suizidalen Verhaltens verbunden. Gleichzeitig bestehende psychische Störungen gingen mit einer nochmals deutlich höheren Rate einher und sind für Prävention und Versorgung besonders relevant.

## Einschränkungen

Registerdiagnosen und kodierte Ereignisse erfassen nicht alle Symptome oder nicht behandelte Verläufe. Die Beobachtungsstudie kann trotz Anpassungen keine einfache Kausalität beweisen und ist an den dänischen Versorgungskontext gebunden.

## Verhältnis zum bisherigen Konsens

Bestätigt den Gruppenbefund eines erhöhten Risikos und präzisiert die Bedeutung zusätzlicher psychischer Störungen; erlaubt keine individuelle Vorhersage.

## Links

- [DOI](https://doi.org/10.1192/bjp.2019.128)
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/31172893/)
''',
"references/Garas2025.md": r'''---
reference_id: Garas2025
title: Garas et al. 2025
evidence_type: systematic-review-and-meta-analysis-longitudinal
evidence_grade: moderate
status: consensus
doi: "10.1002/brb3.70618"
pmid: "40534226"
last_checked: 2026-07-21
tags: [Literatur, ADHS, Suizidalität, Kinder, Jugendliche, Longitudinal]
citation:
  entry_type: article
  csl_type: article-journal
  authors:
    - "Garas, P."
    - "Takacs, Z. K."
    - "Balázs, J."
  et_al: false
  year: 2025
  article_title: "Longitudinal Suicide Risk in Children and Adolescents With Attention Deficit and Hyperactivity Disorder: A Systematic Review and Meta-Analysis"
  journal: Brain and Behavior
  volume: "15"
  issue: "6"
  article_number: "e70618"
---

# Garas et al. 2025

## Vollständige Zitation

Garas, P., Takacs, Z. K., & Balázs, J. (2025). Longitudinal Suicide Risk in Children and Adolescents With Attention Deficit and Hyperactivity Disorder: A Systematic Review and Meta-Analysis. *Brain and Behavior, 15*(6), e70618.

## Evidenztyp und Design

Systematische Übersichtsarbeit und Meta-Analyse ausschließlich longitudinaler Studien mit klinischer ADHS-Diagnose und suizidalen Verlaufsmaßen.

## Population

Neun Studien, in denen die Mehrheit der Teilnehmenden zu Studienbeginn unter 18 Jahre alt war. Die Stichprobengrößen und Beobachtungszeiträume unterschieden sich stark; Jungen waren überrepräsentiert.

## Kernaussage

ADHS war longitudinal mit erhöhten Chancen für Suizidgedanken, Suizidversuche und Suizidtod verbunden. Der Zusammenhang war jedoch heterogen und wurde durch Alter, Geschlecht, soziale Faktoren, ADHS-Ausprägung und Komorbiditäten mitgeprägt.

## Einschränkungen

Nur neun Studien erfüllten die Kriterien. Definitionen und Messmethoden variierten; seltene Ereignisse erzeugen Unsicherheit. Die Ergebnisse sind Gruppenbefunde und kein individuelles Vorhersageinstrument.

## Verhältnis zum bisherigen Konsens

Bestätigt frühere Querschnitts- und Registerbefunde mit longitudinalen Daten und betont zugleich die Heterogenität.

## Links

- [DOI](https://doi.org/10.1002/brb3.70618)
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/40534226/)
''',
"references/NICE2022SelfHarm.md": r'''---
reference_id: NICE2022SelfHarm
title: NICE NG225 2022
evidence_type: clinical-practice-guideline
evidence_grade: high
status: consensus
doi: ""
pmid: ""
last_checked: 2026-07-21
tags: [Literatur, Selbstverletzung, Suizidalität, Sicherheitsplanung, Leitlinie]
citation:
  entry_type: misc
  csl_type: report
  authors:
    - "National Institute for Health and Care Excellence"
  et_al: false
  year: 2022
  article_title: "Self-harm: assessment, management and preventing recurrence"
---

# NICE NG225 2022

## Vollständige Zitation

National Institute for Health and Care Excellence (2022). Self-harm: assessment, management and preventing recurrence.

## Evidenztyp und Design

Evidenzbasierte klinische Leitlinie für die Beurteilung, Behandlung und Prävention erneuter Selbstverletzung. Die Empfehlungen beruhen auf systematischen Evidenzreviews und einem multidisziplinären Leitlinienprozess.

## Population

Kinder, Jugendliche und Erwachsene nach Selbstverletzung, einschließlich Menschen mit psychischen Störungen, Neuroentwicklungsstörungen oder Lernbehinderung.

## Kernaussage

Globale Risikokategorien oder Skalen sollen nicht verwendet werden, um zukünftigen Suizid vorherzusagen, Behandlung vorzuenthalten oder über Entlassung zu entscheiden. Die Beurteilung soll Bedürfnisse sowie unmittelbare und langfristige psychische und körperliche Sicherheit in den Mittelpunkt stellen.

## Einschränkungen

Die Leitlinie bezieht sich auf den britischen Versorgungskontext. Zuständigkeiten und konkrete Notfallwege müssen lokal angepasst werden; Empfehlungen ersetzen keine individuelle fachliche Beurteilung.

## Verhältnis zum bisherigen Konsens

Bestätigt die Abkehr von scheingenauen Risikokategorien zugunsten individueller psychosozialer Beurteilung und Sicherheitsplanung.

## Links

- [Leitlinie](https://www.nice.org.uk/guidance/ng225)
- [Empfehlungen](https://www.nice.org.uk/guidance/ng225/chapter/Recommendations)
''',
"references/NVLDepression2022.md": r'''---
reference_id: NVLDepression2022
title: NVL Unipolare Depression 2022
evidence_type: national-clinical-practice-guideline
evidence_grade: high
status: consensus
doi: ""
pmid: ""
last_checked: 2026-07-21
tags: [Literatur, Depression, Suizidalität, Diagnostik, Leitlinie]
citation:
  entry_type: misc
  csl_type: report
  authors:
    - "Bundesärztekammer"
    - "Kassenärztliche Bundesvereinigung"
    - "Arbeitsgemeinschaft der Wissenschaftlichen Medizinischen Fachgesellschaften"
  et_al: false
  year: 2022
  article_title: "Nationale VersorgungsLeitlinie Unipolare Depression, Version 3.2"
---

# NVL Unipolare Depression 2022

## Vollständige Zitation

Bundesärztekammer, Kassenärztliche Bundesvereinigung, & Arbeitsgemeinschaft der Wissenschaftlichen Medizinischen Fachgesellschaften (2022). Nationale VersorgungsLeitlinie Unipolare Depression, Version 3.2.

## Evidenztyp und Design

Nationale evidenz- und konsensbasierte Versorgungsleitlinie mit Kapiteln zu Diagnostik, Monitoring, Therapieplanung, Behandlung und Management bei Suizidalität und anderen Notfallsituationen.

## Population

Erwachsene mit möglicher oder diagnostizierter unipolarer Depression im deutschen Versorgungssystem.

## Kernaussage

Depressive Störungen werden anhand von Symptomkonstellation, Dauer, Schweregrad, Funktionsbeeinträchtigung, Verlauf, Differentialdiagnosen und Komorbiditäten beurteilt. Suizidalität muss ausdrücklich erfasst und bei akuter Gefährdung unmittelbar behandelt werden.

## Einschränkungen

Die Leitlinie ist nicht speziell für ADHS entwickelt und deckt Kinder und Jugendliche nicht ab. Sie ersetzt keine individuelle Diagnostik oder lokale Notfallplanung.

## Verhältnis zum bisherigen Konsens

Liefert den aktuellen deutschen Versorgungsrahmen für die Abgrenzung depressiver Episoden und das Management von Suizidalität.

## Links

- [Leitlinienübersicht](https://www.leitlinien.de/themen/depression)
- [Aktuelle Version](https://www.leitlinien.de/themen/depression/version-3)
''',
"references/Septier2019.md": r'''---
reference_id: Septier2019
title: Septier et al. 2019
evidence_type: preregistered-systematic-review-and-meta-analysis
evidence_grade: moderate
status: consensus
doi: "10.1016/j.neubiorev.2019.05.022"
pmid: "31129238"
last_checked: 2026-07-21
tags: [Literatur, ADHS, Suizidalität, Meta-Analyse]
citation:
  entry_type: article
  csl_type: article-journal
  authors:
    - "Septier, M."
    - "Stordeur, C."
    - "Zhang, J."
    - "Delorme, R."
    - "Cortese, S."
  et_al: false
  year: 2019
  article_title: "Association between suicidal spectrum behaviors and Attention-Deficit/Hyperactivity Disorder: A systematic review and meta-analysis"
  journal: Neuroscience & Biobehavioral Reviews
  volume: "103"
  pages: "109–118"
---

# Septier et al. 2019

## Vollständige Zitation

Septier, M., Stordeur, C., Zhang, J., Delorme, R., & Cortese, S. (2019). Association between suicidal spectrum behaviors and Attention-Deficit/Hyperactivity Disorder: A systematic review and meta-analysis. *Neuroscience & Biobehavioral Reviews, 103*, 109–118.

## Evidenztyp und Design

Präregistrierte systematische Übersichtsarbeit und Random-Effects-Meta-Analyse von 57 Studien zu ADHS und suizidalen Verhaltensspektren; Studienqualität und mögliche Moderatoren wurden geprüft.

## Population

Kinder, Jugendliche und Erwachsene aus unterschiedlichen klinischen und bevölkerungsbezogenen Stichproben.

## Kernaussage

ADHS war mit Suizidgedanken, Planungen, Versuchen und Suizidtod assoziiert. Die Befunde blieben in mehreren Sensitivitätsanalysen bestehen, unterschieden sich aber erheblich zwischen Studien.

## Einschränkungen

Bei mehreren Endpunkten war die statistische Heterogenität sehr hoch. Beobachtungsstudien, unterschiedliche Definitionen und verbleibende Konfundierung begrenzen kausale und individuelle Aussagen.

## Verhältnis zum bisherigen Konsens

Begründet die systematische Beachtung von Suizidalität bei ADHS, ohne aus der Diagnose eine individuelle Vorhersage abzuleiten.

## Links

- [DOI](https://doi.org/10.1016/j.neubiorev.2019.05.022)
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/31129238/)
''',
"references/Zhang2025Depression.md": r'''---
reference_id: Zhang2025Depression
title: Zhang et al. 2025 – Depression und Angst
evidence_type: systematic-review-and-meta-analysis
evidence_grade: moderate
status: consensus
doi: "10.1016/j.jpsychires.2024.12.022"
pmid: "39740618"
last_checked: 2026-07-21
tags: [Literatur, ADHS, Depression, Angst, Kinder, Jugendliche]
citation:
  entry_type: article
  csl_type: article-journal
  authors:
    - "Zhang, Y."
    - "Liao, W."
    - "Rao, Y."
    - "Gao, W."
    - "Yang, R."
  et_al: false
  year: 2025
  article_title: "Effects of ADHD and ADHD medications on depression and anxiety in children and adolescents: A systematic review and meta-analysis"
  journal: Journal of Psychiatric Research
  volume: "181"
  pages: "623–639"
---

# Zhang et al. 2025 – Depression und Angst

## Vollständige Zitation

Zhang, Y., Liao, W., Rao, Y., Gao, W., & Yang, R. (2025). Effects of ADHD and ADHD medications on depression and anxiety in children and adolescents: A systematic review and meta-analysis. *Journal of Psychiatric Research, 181*, 623–639.

## Evidenztyp und Design

Systematische Übersichtsarbeit und Meta-Analyse mit Suche in vier Datenbanken bis Januar 2024; 33 Studien zu Depression, Angst und ADHS-Medikation wurden eingeschlossen.

## Population

Kinder und Jugendliche mit und ohne ADHS aus beobachtenden und behandlungsbezogenen Studien.

## Kernaussage

ADHS war auf Gruppenebene mit einem ungefähr verdoppelten Risiko depressiver Störungen verbunden. Stimulanzienexposition war mit einem niedrigeren Depressionsrisiko assoziiert.

## Einschränkungen

Die eingeschlossenen Studien unterschieden sich nach Population, Messung, Behandlung und Beobachtungsdauer. Die Medikamentenbefunde sind überwiegend beobachtend und beweisen weder Schutzwirkung noch eine Empfehlung für die einzelne Person.

## Verhältnis zum bisherigen Konsens

Aktualisiert die quantitative Evidenz für depressive Komorbidität bei jungen Menschen und widerspricht einer pauschalen Darstellung von ADHS-Medikation als Depressionsursache.

## Links

- [DOI](https://doi.org/10.1016/j.jpsychires.2024.12.022)
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/39740618/)
''',
"references/Zhang2025Medication.md": r'''---
reference_id: Zhang2025Medication
title: Zhang et al. 2025 – ADHS-Medikation und schwere Ereignisse
evidence_type: target-trial-emulation-register-study
evidence_grade: moderate
status: probable
doi: "10.1136/bmj-2024-083658"
pmid: "40803836"
last_checked: 2026-07-21
tags: [Literatur, ADHS, Medikation, Suizidalität, Registerstudie]
citation:
  entry_type: article
  csl_type: article-journal
  authors:
    - "Zhang, L."
    - "Zhu, N."
    - "Sjölander, A."
  et_al: true
  year: 2025
  article_title: "ADHD drug treatment and risk of suicidal behaviours, substance misuse, accidental injuries, transport accidents, and criminality: emulation of target trials"
  journal: BMJ
  volume: "390"
  article_number: "e083658"
---

# Zhang et al. 2025 – ADHS-Medikation und schwere Ereignisse

## Vollständige Zitation

Zhang, L., Zhu, N., Sjölander, A., et al. (2025). ADHD drug treatment and risk of suicidal behaviours, substance misuse, accidental injuries, transport accidents, and criminality: emulation of target trials. *BMJ, 390*, e083658.

## Evidenztyp und Design

Emulation von Target Trials anhand verknüpfter schwedischer nationaler Registerdaten. Behandlungsbeginn und Nichtbeginn wurden für mehrere schwere Ereignisse über zwei Jahre verglichen.

## Population

148.581 Personen im Alter von 6 bis 64 Jahren mit neuer ADHS-Diagnose zwischen 2007 und 2020.

## Kernaussage

Der Beginn einer ADHS-Medikation war mit niedrigeren Raten erstmaligen und wiederkehrenden suizidalen Verhaltens assoziiert. Der Befund spricht gegen eine pauschale Annahme eines generell erhöhten Suizidalitätsrisikos durch leitliniengerechte ADHS-Medikation.

## Einschränkungen

Trotz Target-Trial-Methodik bleibt die Untersuchung beobachtend. Nicht gemessene Unterschiede, Behandlungsauswahl, Versorgungskontakt und Fehlklassifikation können die Ergebnisse beeinflussen; eine individuelle Schutzwirkung ist nicht bewiesen.

## Verhältnis zum bisherigen Konsens

Präzisiert ältere Beobachtungsdaten und unterstützt eine differenzierte Nutzen-Risiko-Bewertung statt pauschaler Warnungen oder Schutzversprechen.

## Links

- [DOI](https://doi.org/10.1136/bmj-2024-083658)
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/40803836/)
'''
}

for path, content in references.items():
    write(path, content)

# Update README and project metadata.
readme_path = ROOT / "README.md"
readme = readme_path.read_text(encoding="utf-8")
readme = re.sub(r"(?m)^version: .+$", "version: 0.11.0", readme, count=1)
readme = re.sub(r"(?m)^last_reviewed: .+$", "last_reviewed: 2026-07-21", readme, count=1)
unit12_line = "12. [[01-Grundlagen/12-Komorbiditaet-Depression-und-Suizidalitaet|Komorbidität, Depression und Suizidalität]]"
if unit12_line not in readme:
    anchor = "11. [[01-Grundlagen/11-Schlaf-Bewegung-und-koerperliche-Gesundheit|Schlaf, Bewegung und körperliche Gesundheit]]"
    readme = readme.replace(anchor, anchor + "\n" + unit12_line, 1)
readme_path.write_text(readme, encoding="utf-8")

index_path = ROOT / "index.json"
index = json.loads(index_path.read_text(encoding="utf-8"))
index["version"] = "0.11.0"
index["last_reviewed"] = "2026-07-21"
if not any(item.get("number") == 12 for item in index["chapters"]):
    index["chapters"].append({
        "number": 12,
        "path": "01-Grundlagen/12-Komorbiditaet-Depression-und-Suizidalitaet.md",
        "title": "Komorbidität, Depression und Suizidalität",
    })
index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

mkdocs_path = ROOT / "mkdocs.yml"
mkdocs = mkdocs_path.read_text(encoding="utf-8")
nav_line = "      - Komorbidität, Depression und Suizidalität: 01-Grundlagen/12-Komorbiditaet-Depression-und-Suizidalitaet.md"
if nav_line not in mkdocs:
    anchor = "      - Schlaf, Bewegung und körperliche Gesundheit: 01-Grundlagen/11-Schlaf-Bewegung-und-koerperliche-Gesundheit.md"
    mkdocs = mkdocs.replace(anchor, anchor + "\n" + nav_line, 1)
mkdocs_path.write_text(mkdocs, encoding="utf-8")

# Complete the previous chapter's navigation.
unit11_path = ROOT / "01-Grundlagen/11-Schlaf-Bewegung-und-koerperliche-Gesundheit.md"
unit11 = unit11_path.read_text(encoding="utf-8")
unit11 = unit11.replace(
    "- Weiter: [[README|Übersicht]]",
    "- Weiter: [[01-Grundlagen/12-Komorbiditaet-Depression-und-Suizidalitaet|Komorbidität, Depression und Suizidalität]]",
    1,
)
unit11_path.write_text(unit11, encoding="utf-8")

# Glossary additions in alphabetical order.
insert_glossary_term("Anhedonie", "Deutlicher Verlust von Interesse oder Freude an Tätigkeiten, die zuvor als angenehm oder bedeutsam erlebt wurden; ein mögliches Kernsymptom depressiver Episoden.")
insert_glossary_term("Depressive Episode", "Zeitlich abgrenzbare Konstellation depressiver Symptome mit klinisch relevanter Dauer, Schwere und Funktionsbeeinträchtigung; nicht gleichbedeutend mit vorübergehender Traurigkeit oder Frustration.")
insert_glossary_term("Nichtsuizidales selbstverletzendes Verhalten", "Absichtliche Selbstverletzung ohne beabsichtigten Tod; die Absicht kann ambivalent oder veränderlich sein, weshalb eine individuelle fachliche Beurteilung erforderlich bleibt.")
insert_glossary_term("Sicherheitsplan", "Kurze, gemeinsam entwickelte Folge konkreter Schritte, Kontakte und Schutzmaßnahmen für eine psychische Krise; ersetzt weder Behandlung noch akute Notfallhilfe.")
insert_glossary_term("Suizidalität", "Spektrum von Todes- oder Suizidgedanken über Absichten und Planungen bis zu suizidalen Handlungen; Dringlichkeit und Bedeutung müssen individuell und direkt beurteilt werden.")

# Add one Anki card without reformatting the existing deck.
cards_path = ROOT / "cards/cards.yaml"
cards = cards_path.read_text(encoding="utf-8").rstrip() + "\n"
if "- id: 1012\n" not in cards:
    cards += '''- id: 1012
  unit: 12
  front: Warum erlaubt ein erhöhtes Suizidalitätsrisiko bei ADHS keine Vorhersage für eine einzelne Person?
  back: Weil es ein heterogener Gruppenbefund ist; die konkrete Beurteilung muss aktuelle
    Gedanken und Absichten, frühere Handlungen, Depression und weitere Komorbiditäten,
    Belastungen, Schutzfaktoren und erreichbare Hilfe berücksichtigen.
  tags:
  - ADHS
  - Grundlagen
  - Depression
  - Suizidalität
  - Einheit_12
'''
cards_path.write_text(cards, encoding="utf-8")

# Remove the now implemented planned node.
planned_path = ROOT / "knowledge-graph/planned-nodes.yaml"
planned = planned_path.read_text(encoding="utf-8")
planned = re.sub(
    r"(?ms)^  - path: 01-Grundlagen/12-Komorbiditaet-Depression-und-Suizidalitaet\n(?:    .*\n)+\n?",
    "",
    planned,
    count=1,
)
planned_path.write_text(planned, encoding="utf-8")

# Changelog entry.
changelog_path = ROOT / "CHANGELOG.md"
changelog = changelog_path.read_text(encoding="utf-8")
entry = '''## 0.11.0 – 2026-07-21

- Einheit 12 „Komorbidität, Depression und Suizidalität“ ergänzt
- Depression, Suizidalität und nichtsuizidale Selbstverletzung voneinander abgegrenzt
- Gruppenrisiken, individuelle Krisenbeurteilung, Sicherheitsplanung und Akuthilfe differenziert eingeordnet
- sieben aktuelle Leitlinien-, Meta-Analyse- und Register-Studienkarten ergänzt
- Glossar, Anki, Navigation, Index und Wissensgraphplanung aktualisiert

'''
if "## 0.11.0 – 2026-07-21" not in changelog:
    match = re.search(r"(?m)^# Änderungsverlauf\s*\n", changelog)
    if not match:
        raise RuntimeError("Changelog-Überschrift fehlt")
    changelog = changelog[:match.end()] + "\n" + entry + changelog[match.end():].lstrip("\n")
changelog_path.write_text(changelog, encoding="utf-8")

# Generate all derived bibliography formats, then verify deterministic reproduction.
run("python", "scripts/build_literature.py")
generated = [ROOT / "Literatur.md", ROOT / "references.bib", ROOT / "references.json"]
first_hashes = {path.name: sha256(path.read_bytes()).hexdigest() for path in generated}
run("python", "scripts/build_literature.py")
second_hashes = {path.name: sha256(path.read_bytes()).hexdigest() for path in generated}
if first_hashes != second_hashes:
    raise RuntimeError("Bibliografieausgaben sind nicht deterministisch")

# Full project checks required by the automation prompt, plus repository-level checks.
run("python", "-m", "pip", "check")
run("git", "diff", "--check")
run("python", "-m", "compileall", "-q", "scripts")
if (ROOT / "tests").is_dir():
    run("python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py")
run("python", "scripts/validate_links.py")
run("python", "scripts/build_graph.py")
run("python", "scripts/validate_compendium.py")
run("python", "scripts/build_combined.py")
run("python", "scripts/build_anki.py")
run("python", "scripts/build_docs.py")
run("mkdocs", "build", "--strict")

# Compute the same prose-word count used by the project validator.
def prose_word_count(text: str) -> int:
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"</?(?:details|summary)>", "", text)
    text = re.sub(r"## Navigation.*\Z", "", text, flags=re.S)
    text = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda match: match.group(2) or match.group(1), text)
    return len(re.findall(r"\b[\wÄÖÜäöüß]+(?:[-’'][\wÄÖÜäöüß]+)*\b", text))

word_count = prose_word_count(unit)
if not 800 <= word_count <= 2500:
    raise RuntimeError(f"Ungültige Fließtextwortzahl: {word_count}")
(ROOT / "build" / "unit-12-word-count.txt").write_text(f"{word_count}\n", encoding="utf-8")
print(f"Einheit 12: {word_count} Fließtextwörter")

# Transport files must not appear in the final pull-request diff.
shutil.rmtree(BOOTSTRAP)
WORKFLOW.unlink(missing_ok=True)

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", "-A")
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
    raise RuntimeError("Keine Änderungen für Einheit 12 vorhanden")
run("git", "commit", "-m", "Einheit 12: Komorbidität, Depression und Suizidalität")
run("git", "push", "origin", f"HEAD:{BRANCH}")
print("Einheit 12 vollständig geprüft und gepusht")
