#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess
import textwrap
import yaml

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "agent/einheit-15-parkinson-adhs-grenzen-vergleiche"
TEMP_DIR = ROOT / ".automation-repair"
TEMP_WORKFLOW = ROOT / ".github" / "workflows" / "repair-unit15.yml"


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, cwd=ROOT, check=check, text=True)


def output(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True)


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def main_file(path: str) -> str:
    return output("git", "show", f"origin/main:{path}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Einfügestelle fehlt ({label})")
    return text.replace(old, new, 1)


run("git", "fetch", "origin", "main")
run("git", "merge", "--no-edit", "origin/main")

cards = yaml.safe_load(main_file("cards/cards.yaml"))
cards["cards"].append(
    {
        "id": 1015,
        "unit": 15,
        "front": "Warum bedeuten gemeinsame Begriffe wie Dopamin nicht, dass ADHS und Parkinson dieselbe Erkrankung sind?",
        "back": (
            "Weil Dopamin in mehreren neuronalen Netzwerken unterschiedliche Funktionen erfüllt "
            "und sich Erkrankungsklasse, Zeitverlauf, Pathophysiologie und Behandlung deutlich unterscheiden."
        ),
        "tags": ["ADHS", "Parkinson", "Vertiefung", "Differentialdiagnostik", "Einheit_15"],
    }
)
write("cards/cards.yaml", yaml.safe_dump(cards, allow_unicode=True, sort_keys=False, width=110))

index = json.loads(main_file("index.json"))
index["version"] = "0.17.0"
index["last_reviewed"] = "2026-07-25"
index["chapters"].append(
    {
        "number": 15,
        "path": "02-Vertiefung/03-Parkinson-ADHS-mechanistische-Vergleiche-und-Grenzen.md",
        "title": "Parkinson, ADHS und mechanistische Vergleiche",
    }
)
write("index.json", json.dumps(index, ensure_ascii=False, indent=2) + "\n")

glossary = main_file("Glossar.md")
glossary = glossary.replace("last_reviewed: 2026-07-22", "last_reviewed: 2026-07-25", 1)
glossary = replace_once(
    glossary,
    "## Neuroentwicklung\nVeränderung und Reifung neuronaler Systeme im Zusammenspiel mit Lernen, Umwelt und biologischen Voraussetzungen über die Entwicklung hinweg.\n",
    "## Neurodegeneration\nFortschreitende Schädigung oder Verlust von Nervenzellen und neuronalen Funktionen; nicht gleichbedeutend mit einer seit der Entwicklung bestehenden Neuroentwicklungsstörung.\n\n"
    "## Neuroentwicklung\nVeränderung und Reifung neuronaler Systeme im Zusammenspiel mit Lernen, Umwelt und biologischen Voraussetzungen über die Entwicklung hinweg.\n",
    "Glossar Neurodegeneration",
)
glossary = replace_once(
    glossary,
    "## Pharmakotherapie\nBehandlung mit Medikamenten; bei ADHS umfasst sie fachlich ausgewählte, überwachte und regelmäßig überprüfte Wirkstoffe.\n",
    "## Parkinson-Erkrankung\nNeurodegenerative Erkrankung mit motorischen und nichtmotorischen Symptomen; sie ist keine späte Form von ADHS und wird nicht durch einen einfachen allgemeinen Dopaminmangel erklärt.\n\n"
    "## Pharmakotherapie\nBehandlung mit Medikamenten; bei ADHS umfasst sie fachlich ausgewählte, überwachte und regelmäßig überprüfte Wirkstoffe.\n",
    "Glossar Parkinson",
)
write("Glossar.md", glossary)

unit14 = main_file("02-Vertiefung/02-Autismus-und-ADHS-Ueberlappung.md")
unit14 = replace_once(
    unit14,
    "- Weiter: [[ROADMAP#Milestone A – Klinische Heterogenität und Lebensspanne|Nächste Themen laut Roadmap]]",
    "- Weiter: [[02-Vertiefung/03-Parkinson-ADHS-mechanistische-Vergleiche-und-Grenzen|Parkinson, ADHS und mechanistische Vergleiche]]",
    "Navigation Einheit 14",
)
write("02-Vertiefung/02-Autismus-und-ADHS-Ueberlappung.md", unit14)

readme = main_file("README.md")
readme = readme.replace("version: 0.15.0", "version: 0.17.0", 1)
readme = readme.replace("last_reviewed: 2026-07-23", "last_reviewed: 2026-07-25", 1)
readme = replace_once(
    readme,
    "14. [[02-Vertiefung/02-Autismus-und-ADHS-Ueberlappung|Autismus und ADHS: Koexistenz, Überlappung und Abgrenzung]]",
    "14. [[02-Vertiefung/02-Autismus-und-ADHS-Ueberlappung|Autismus und ADHS: Koexistenz, Überlappung und Abgrenzung]]\n"
    "15. [[02-Vertiefung/03-Parkinson-ADHS-mechanistische-Vergleiche-und-Grenzen|Parkinson, ADHS und mechanistische Vergleiche]]",
    "README Lernpfad",
)
write("README.md", readme)

mkdocs = main_file("mkdocs.yml")
mkdocs = replace_once(
    mkdocs,
    "      - Autismus und ADHS: 02-Vertiefung/02-Autismus-und-ADHS-Ueberlappung.md",
    "      - Autismus und ADHS: 02-Vertiefung/02-Autismus-und-ADHS-Ueberlappung.md\n"
    "      - Parkinson, ADHS und mechanistische Vergleiche: 02-Vertiefung/03-Parkinson-ADHS-mechanistische-Vergleiche-und-Grenzen.md",
    "MkDocs Navigation",
)
write("mkdocs.yml", mkdocs)

planned = yaml.safe_load(main_file("knowledge-graph/planned-nodes.yaml"))
planned["nodes"] = [
    node for node in planned.get("nodes", [])
    if not (
        str(node.get("path", "")).startswith("02-Vertiefung/03-Parkinson")
        or "Parkinson" in str(node.get("title", ""))
    )
]
write("knowledge-graph/planned-nodes.yaml", yaml.safe_dump(planned, allow_unicode=True, sort_keys=False, width=120))

roadmap = main_file("ROADMAP.md")
roadmap = roadmap.replace("last_reviewed: 2026-07-22", "last_reviewed: 2026-07-25", 1)
roadmap = roadmap.replace("Der Lernpfad umfasst derzeit 14 fortlaufende Einheiten:", "Der Lernpfad umfasst derzeit 15 fortlaufende Einheiten:", 1)
roadmap = replace_once(
    roadmap,
    "14. Autismus und ADHS: Koexistenz, Überlappung und Abgrenzung",
    "14. Autismus und ADHS: Koexistenz, Überlappung und Abgrenzung\n"
    "15. Parkinson, ADHS und mechanistische Vergleiche",
    "Roadmap Einheitenliste",
)
roadmap = roadmap.replace(
    "- [ ] Parkinson: sinnvolle mechanistische Vergleiche und klare Grenzen",
    "- [x] Parkinson: sinnvolle mechanistische Vergleiche und klare Grenzen",
    1,
)
write("ROADMAP.md", roadmap)

changelog = main_file("CHANGELOG.md")
entry = """## 0.17.0 – 2026-07-25

- Einheit 15 „Parkinson, ADHS und mechanistische Vergleiche“ ergänzt
- Neuroentwicklung und Neurodegeneration sowie unterschiedliche Rollen dopaminerger Systeme klar voneinander abgegrenzt
- unsichere Beobachtungsbefunde zu möglichen späteren neurodegenerativen Diagnosen ohne kausale oder individuelle Prognose eingeordnet
- drei strukturierte Studienkarten, Glossarbegriffe, Anki-Karte, Navigation, Roadmap und Wissensgraph-Planung aktualisiert
- versehentlich verkürzte Index-, Glossar- und Anki-Dateien vollständig aus `main` wiederhergestellt

"""
if "## 0.17.0 – 2026-07-25" not in changelog:
    first_heading_end = changelog.find("\n", changelog.find("# ")) + 1
    changelog = changelog[:first_heading_end] + "\n" + entry + changelog[first_heading_end:].lstrip("\n")
write("CHANGELOG.md", changelog)
write("02-Vertiefung/03-Parkinson-ADHS-mechanistische-Vergleiche-und-Grenzen.md", r"""---
title: "Parkinson, ADHS und mechanistische Vergleiche"
level: Vertiefung
estimated_time: 10–20 min
difficulty: 3
prerequisites:
  - 01-Grundlagen/03-Dopamin-Belohnung-und-Motivation
  - 01-Grundlagen/08-Neuroentwicklung-und-Lebensspanne
  - 01-Grundlagen/09-Diagnostische-Kriterien-und-Differentialdiagnostik
  - 01-Grundlagen/10-Genetik-und-Umwelt
  - 02-Vertiefung/02-Autismus-und-ADHS-Ueberlappung
tags: [ADHS, Parkinson, Neuroentwicklung, Neurodegeneration, Dopamin, Differentialdiagnostik, Lebensspanne]
last_reviewed: 2026-07-25
evidence: high
status: consensus
references: [Faraone2021, Bloem2021, Becker2023, Dobrosavljevic2020]
minimum_reading_minutes: 10
maximum_reading_minutes: 20
---

# Einheit 15 – Parkinson, ADHS und mechanistische Vergleiche

## Lernziel

Du kannst erklären, warum ADHS und die Parkinson-Erkrankung trotz gemeinsamer Forschungsbegriffe nicht dieselbe Art von Erkrankung sind. Du unterscheidest Neuroentwicklung von Neurodegeneration, ordnest die unterschiedlichen Rollen dopaminerger Systeme ein und erkennst, welche Vergleiche wissenschaftlich sinnvoll sind. Außerdem kannst du unsichere Beobachtungsbefunde zu einem möglichen späteren Neurodegenerationsrisiko bewerten, ohne daraus eine persönliche Prognose oder die Behauptung abzuleiten, ADHS sei eine Vorstufe von Parkinson.

## 1. Der wichtigste Unterschied: Entwicklungsprofil oder fortschreitender Zellverlust

ADHS wird als heterogene **Neuroentwicklungsstörung** eingeordnet. Die diagnostisch relevanten Muster beginnen in der Entwicklung und betreffen insbesondere Unaufmerksamkeit und/oder Hyperaktivität-Impulsivität. Ihre Sichtbarkeit kann sich über die Lebensspanne verändern: Anforderungen steigen oder sinken, Strategien werden aufgebaut, Unterstützung fällt weg, und Begleiterkrankungen können das Funktionsniveau beeinflussen. Eine Veränderung der Symptome bedeutet deshalb nicht automatisch, dass ein fortschreitender krankhafter Abbau im Gehirn stattfindet.

Die Parkinson-Erkrankung ist dagegen eine **neurodegenerative Erkrankung**. Bei ihr verändern sich im Laufe des Lebens mehrere neuronale Systeme. Besonders bekannt ist der Verlust dopaminerger Nervenzellen in der Substantia nigra mit Folgen für die Signalverarbeitung in den Basalganglien. Parkinson umfasst jedoch mehr als ein motorisches Dopaminproblem: Neben Bradykinese, Rigor und häufig Tremor können Schlaf, autonome Funktionen, Stimmung, Motivation und Kognition betroffen sein. Die Erkrankung beginnt nicht erst am Tag der Diagnose, verläuft aber typischerweise fortschreitend und weist eine andere Pathophysiologie sowie einen anderen klinischen Zeitverlauf als ADHS auf.

> [!evidence] Evidenz: Konsens / hoch
> ADHS ist primär eine Neuroentwicklungsstörung; Parkinson ist eine neurodegenerative Erkrankung. Einzelne gemeinsame Symptome, Hirnnetzwerke oder Botenstoffe heben diesen grundlegenden Unterschied nicht auf.

Die Zeitachse ist diagnostisch entscheidend. Eine seit Kindheit bestehende, situationsübergreifende Unaufmerksamkeit mit wechselnder Ausprägung spricht für einen anderen Verlauf als eine im höheren Lebensalter neu auftretende Verlangsamung, motorische Veränderung oder deutliche kognitive Verschlechterung. Umgekehrt schließt ein höheres Alter ADHS nicht aus: Systematische Übersichten zeigen, dass klinisch relevante ADHS-Symptome auch bei älteren Erwachsenen vorkommen. Die Diagnostik ist dort allerdings anspruchsvoll, weil Erinnerungen an die Kindheit unvollständig sein können und Depression, Schlafstörungen, Medikamente, Hör- oder Sehprobleme sowie neurokognitive Erkrankungen ähnliche Beschwerden erzeugen können.

## 2. Dopamin ist kein einheitlicher Krankheitspegel

Der Satz „Beide haben etwas mit Dopamin zu tun“ klingt zunächst nach einer starken Verbindung, ist aber biologisch viel zu grob. Dopamin wirkt in mehreren Bahnen, Hirnregionen, Zelltypen und Rezeptorsystemen. Es beeinflusst unter anderem Lernen aus Rückmeldung, Anreizbewertung, Handlungswahl, Bewegung und die Anpassung von Verhalten an Ziele. Die Bedeutung eines dopaminergen Signals hängt davon ab, **wo**, **wann** und in welchem Netzwerk es wirkt.

Bei ADHS werden Unterschiede in katecholaminergen Systemen, einschließlich Dopamin und Noradrenalin, als Teil komplexer Modelle untersucht. Diese Modelle erklären nicht die gesamte Störung und bedeuten keinen einfachen, messbaren „Dopaminmangel“. Die Wirkung von Stimulanzien beweist ebenfalls keine einzelne Ursache: Ein Medikament kann ein Netzwerk funktionell beeinflussen, ohne dass die behandelte Störung durch einen simplen Mangel desselben Botenstoffs entstanden sein muss.

Bei Parkinson steht ein klarer beschriebener neurodegenerativer Prozess in nigrostriatalen Systemen im Vordergrund. Der Verlust dopaminerger Projektionen verändert die Aktivität motorischer Regelkreise. Dopaminerge Medikamente können motorische Symptome wirksam lindern, ersetzen aber nicht alle verlorenen Funktionen und stoppen die gesamte Erkrankung nicht. Auch bei Parkinson sind nichtmotorische Symptome nicht auf einen einzigen Botenstoff reduzierbar.

```mermaid
flowchart TD
  A[ADHS] --> B[Neuroentwicklung]
  B --> C[Aufmerksamkeit, Impulskontrolle, Motivation]
  P[Parkinson] --> N[Neurodegeneration]
  N --> M[motorische und nichtmotorische Symptome]
  D[Dopaminerge Systeme] --> C
  D --> M
  C --> G[teilweise gemeinsame Forschungsbegriffe]
  M --> G
  G --> X[keine Gleichsetzung der Erkrankungen]
```

Das Diagramm zeigt die korrekte Logik: Derselbe Oberbegriff kann in zwei verschiedenen Kausalmodellen vorkommen. Aus „Dopamin ist beteiligt“ folgt weder „identische Ursache“ noch „gleiche Behandlung“ noch „gleicher Verlauf“.

## 3. Was mechanistische Vergleiche leisten können

Vergleiche zwischen ADHS- und Parkinson-Forschung sind nicht grundsätzlich falsch. Sie werden dann nützlich, wenn die Frage eng formuliert ist. Forschende können beispielsweise untersuchen, wie Basalganglien und frontostriatale Netzwerke Handlungswahl, Reaktionshemmung, Belohnungslernen oder den Wechsel zwischen Handlungen unterstützen. Auch Motivation, Aufwandsschätzung und zeitliche Organisation hängen von verteilten Netzwerken ab, die in mehreren Erkrankungen untersucht werden.

Solche Vergleiche können allgemeine Prinzipien sichtbar machen:

- Wie verändern dopaminerge Signale die Gewichtung möglicher Handlungen?
- Wie arbeiten kortikale und subkortikale Netzwerke bei Planung und Bewegung zusammen?
- Warum kann dieselbe Testaufgabe durch unterschiedliche Mechanismen beeinträchtigt werden?
- Wie unterscheiden sich stabile Entwicklungsunterschiede von einem erworbenen Funktionsverlust?

Die Antwort auf eine gemeinsame Testauffälligkeit bleibt dabei offen. Langsamere Reaktionen können beispielsweise mit motorischer Verlangsamung, depressiver Symptomatik, Müdigkeit, Medikamentenwirkung, geringer Motivation, Verständnisproblemen oder Aufmerksamkeitsschwankungen zusammenhängen. Ein Testwert benennt deshalb zunächst eine Leistung unter bestimmten Bedingungen, nicht automatisch die zugrunde liegende Krankheit.

Mechanistische Forschung wird problematisch, wenn ein gemeinsamer Begriff ohne Zwischenschritte zu einer Diagnosebehauptung wird. „Frontostriatal“, „exekutiv“ oder „dopaminerg“ sind keine Diagnosen. Sehr viele psychische und neurologische Zustände betreffen überlappende Netzwerke. Die klinische Einordnung benötigt zusätzlich Beginn, Verlauf, Symptomqualität, neurologische Untersuchung, Beeinträchtigung und mögliche Alternativerklärungen.

## 4. Bedeutet ADHS ein erhöhtes Parkinson- oder Demenzrisiko?

Einige Register- und Krankenaktenstudien berichteten Zusammenhänge zwischen einer ADHS-Diagnose und später dokumentierten neurodegenerativen Erkrankungen. Diese Beobachtungen haben verständlicherweise Aufmerksamkeit erzeugt. Sie beweisen aber weder, dass ADHS Parkinson verursacht, noch dass eine betroffene Person wahrscheinlich erkranken wird.

Eine systematische Übersicht von Becker und Kolleg:innen aus dem Jahr 2023 fand nur sieben geeignete Beobachtungsstudien zu ADHS und späteren neurodegenerativen oder neurokognitiven Diagnosen. Die untersuchten Endpunkte waren sehr unterschiedlich: Demenz insgesamt, Alzheimer-Erkrankung, Parkinson- oder Lewy-Körper-Erkrankungen, vaskuläre Demenz und leichte kognitive Beeinträchtigung. Wegen der methodischen Heterogenität war keine gemeinsame Meta-Analyse sinnvoll. Die Autor:innen bewerteten die Literatur als begrenzt und betonten, dass Größe und Mechanismus eines möglichen direkten Effekts ungeklärt bleiben.

Mehrere Verzerrungen sind möglich:

1. **Diagnosefehler:** Ältere Krankenakten können ADHS übersehen oder unspezifische Symptome fälschlich als ADHS kodieren.
2. **Überwachungseffekt:** Menschen mit psychiatrischer oder neurologischer Behandlung haben mehr Kontakt zum Gesundheitssystem; dadurch werden weitere Diagnosen eher dokumentiert.
3. **Komorbiditäten:** Depression, Substanzgebrauch, Schlafstörungen, kardiovaskuläre Risiken oder andere Faktoren können mit ADHS und späteren Gesundheitsproblemen zusammenhängen.
4. **Medikamenten- und Indikationsverzerrung:** Ein Zusammenhang mit verschriebenen Stimulanzien kann durch Schweregrad, Behandlungszugang und Begleiterkrankungen beeinflusst sein. Verordnete Stimulanzien dürfen nicht mit hochdosiertem illegalem Stimulanzienkonsum gleichgesetzt werden.
5. **Umgekehrte oder überlappende Erklärung:** Frühe unspezifische Beschwerden einer späteren Erkrankung könnten rückblickend als ADHS interpretiert werden; zugleich kann echtes lebenslanges ADHS im Alter fälschlich als beginnende Neurodegeneration erscheinen.

> [!important] Assoziation ist keine persönliche Prognose
> Die bisherige Literatur rechtfertigt nicht die Aussage „ADHS führt zu Parkinson“ und erlaubt keine individuelle Risikoberechnung. Sie begründet weitere Forschung und eine sorgfältige Differentialdiagnostik, nicht Alarmismus.

Für die Praxis ist deshalb ein ausgewogener Satz angemessen: Mögliche Langzeitassoziationen werden untersucht, die Evidenz ist aber zu begrenzt und zu anfällig für Konfundierung, um daraus einen gesicherten kausalen Pfad abzuleiten.

## 5. Differentialdiagnostik im höheren Lebensalter

Bei einer älteren Person mit Konzentrationsproblemen sollte nicht automatisch zwischen „ADHS“ und „Demenz oder Parkinson“ gewählt werden, als könnten beide nicht koexistieren. Die sinnvollere Frage lautet: Welche Beschwerden bestehen seit wann, wie haben sie sich verändert, und welche zusätzlichen Merkmale sind vorhanden?

Hinweise, die eine erneute medizinische oder neurologische Abklärung nahelegen, sind beispielsweise:

- eine klar neue oder fortschreitende Verlangsamung,
- neu auftretender Ruhetremor, Rigor oder auffällige Gangveränderungen,
- deutliche Verschlechterung zuvor beherrschter Alltagsfertigkeiten,
- neue visuell-räumliche Probleme, Halluzinationen oder starke kognitive Schwankungen,
- Veränderungen von Geruchssinn, REM-Schlaf-Verhalten oder autonomen Funktionen im passenden Gesamtbild,
- akute oder subakute Veränderungen, die auch durch Medikamente, Infektionen oder Stoffwechselprobleme verursacht sein können.

Keines dieser Merkmale ist allein beweisend. Ebenso wenig beweist eine seit langem bestehende Vergesslichkeit automatisch ADHS. Für eine ADHS-Diagnose bleibt ein entwicklungsbezogenes Muster wichtig, auch wenn der Nachweis im höheren Alter schwieriger sein kann. Schulzeugnisse, frühere Berichte, Fremdanamnese und lebenslange Beispiele können hilfreich sein, sind aber nicht immer verfügbar. Fehlende Dokumente dürfen nicht durch erfundene Sicherheit ersetzt werden.

ADHS kann außerdem die Bewältigung einer später hinzukommenden neurologischen Erkrankung erschweren: komplexe Medikamentenpläne, Terminorganisation oder das Beobachten schwankender Symptome können höhere exekutive Anforderungen stellen. Dann müssen beide Ebenen berücksichtigt werden, statt jede Schwierigkeit nur einer Diagnose zuzuschreiben.

## 6. Behandlung: ähnliche Wirkstoffklassen bedeuten keine Austauschbarkeit

Stimulanzien bei ADHS und dopaminerge Medikamente bei Parkinson haben unterschiedliche Indikationen, Dosierungen, Zielsysteme und Evidenzgrundlagen. Ein Medikament aus dem einen Bereich ist keine allgemeine Behandlung für den anderen. Veränderungen dürfen deshalb nicht eigenständig aus einem mechanistischen Vergleich abgeleitet werden.

Bei ADHS werden Behandlungseffekte an Kernsymptomen und alltagsbezogenen Zielen geprüft; Nutzen, Nebenwirkungen, Wirkdauer und Begleiterkrankungen werden überwacht. Bei Parkinson richtet sich die Therapie nach motorischen und nichtmotorischen Symptomen, Erkrankungsphase, Nebenwirkungen und individuellen Zielen. Dopaminerge Behandlung kann unter anderem Impulskontrollstörungen oder Halluzinationen beeinflussen; auch deshalb ist „mehr Dopamin“ kein sinnvolles universelles Therapieziel.

Forschungsbefunde über mögliche Langzeitrisiken sind kein Grund, eine wirksame verordnete ADHS-Behandlung ohne fachliche Rücksprache abzusetzen. Ebenso darf eine Parkinson-Medikation nicht als Test verwendet werden, ob Konzentrationsprobleme „dopaminbedingt“ sind. Diagnostik und Behandlung folgen klinischen Kriterien, nicht einem Neurotransmitter-Selbstexperiment.

## 7. Mini-Übung: Gleiches Wort, andere Aussageebene

Wähle einen gemeinsamen Begriff, zum Beispiel „Dopamin“, „Basalganglien“, „Motivation“ oder „exekutive Funktionen“. Erstelle vier kurze Spalten:

1. **Beobachtung:** Was wurde tatsächlich gemessen oder beschrieben?
2. **Mechanismus:** Welche biologische Erklärung wird vorgeschlagen?
3. **Diagnose:** Welche zusätzlichen Kriterien wären für eine klinische Zuordnung nötig?
4. **Grenze:** Welche alternative Erklärung oder Unsicherheit bleibt?

Beispiel: „Eine Gruppe zeigt langsamere Reaktionen“ ist eine Beobachtung. Daraus folgt noch nicht, dass dieselbe dopaminerge Störung, dieselbe Diagnose oder dieselbe Behandlung vorliegt. Die Übung trainiert, zwischen Daten, Modell und klinischer Schlussfolgerung zu unterscheiden.

## 8. Wissenschaftliche Einordnung und Grenzen

**Konsens:** ADHS und Parkinson sind unterschiedliche Erkrankungsklassen. ADHS beginnt als Neuroentwicklungsstörung; Parkinson ist neurodegenerativ. Dopamin und frontostriatale Netzwerke sind in beiden Forschungsfeldern relevant, aber nicht auf dieselbe Weise.

**Wahrscheinlich:** Eng formulierte Vergleiche zu Handlungssteuerung, Motivation und Basalganglienfunktionen können allgemeine neurobiologische Prinzipien verdeutlichen. Im höheren Lebensalter ist eine sorgfältige Verlaufserhebung wichtig, weil ADHS-Symptome, Depression, Schlafprobleme, Medikamenteneffekte und neurokognitive Erkrankungen sich teilweise ähneln können.

**Umstritten:** Ob ADHS unabhängig und kausal das Risiko bestimmter neurodegenerativer Erkrankungen erhöht, wie groß ein möglicher Effekt wäre und welche Rolle Komorbiditäten oder Behandlung spielen. Die vorhandenen Beobachtungsstudien sind heterogen und erlauben keine sichere Individualprognose.

**Experimentell:** Biomarker oder kombinierte genetische, bildgebende und digitale Modelle, die bei einer Einzelperson zwischen lebenslangem ADHS, normalem Altern und früher Neurodegeneration unterscheiden. Solche Verfahren sind derzeit kein Ersatz für klinische Diagnostik.

## Review-Frage

**Warum ist die Aussage „ADHS ist eine frühe Form von Parkinson, weil beide mit Dopamin zusammenhängen“ wissenschaftlich falsch?**

<details>
<summary>Antwort</summary>

Weil ADHS und Parkinson unterschiedliche Erkrankungsklassen, Zeitverläufe und Pathophysiologien haben. Dopamin wirkt in mehreren Netzwerken und erfüllt unterschiedliche Funktionen. Ein gemeinsamer Botenstoff oder eine ähnliche Testauffälligkeit beweist weder identische Ursache noch gleiche Behandlung oder einen zwangsläufigen Übergang von ADHS zu Parkinson.

</details>

## Wissenschaftliche Quelle

[[references/Faraone2021|Faraone et al. 2021]] – internationales Konsensuspapier zur evidenzbasierten Einordnung von ADHS als heterogene Neuroentwicklungsstörung.

[[references/Bloem2021|Bloem et al. 2021]] – umfassende Lancet-Übersicht zu Pathophysiologie, klinischem Verlauf und Behandlung der Parkinson-Erkrankung.

[[references/Becker2023|Becker et al. 2023]] – systematische Übersicht zu Beobachtungsstudien über ADHS und spätere neurodegenerative beziehungsweise neurokognitive Diagnosen; betont die begrenzte und heterogene Evidenz.

[[references/Dobrosavljevic2020|Dobrosavljevic et al. 2020]] – systematische Übersicht und Meta-Analyse zur Prävalenz von ADHS bei älteren Erwachsenen und zu starken Unterschieden zwischen Erhebungsmethoden.

## Merksatz

> Gemeinsame Forschungsbegriffe sind keine gemeinsame Krankheit: ADHS ist neuroentwicklungsbezogen, Parkinson neurodegenerativ, und mögliche Langzeitassoziationen sind bislang keine kausale oder persönliche Prognose.

## Navigation

- Zurück: [[02-Vertiefung/02-Autismus-und-ADHS-Ueberlappung|Autismus und ADHS: Koexistenz, Überlappung und Abgrenzung]]
- Weiter: [[ROADMAP#Milestone A – Klinische Heterogenität und Lebensspanne|Nächste Themen laut Roadmap]]
- [[Glossar]] · [[Literatur]] · [[knowledge-graph/README|Wissensgraph]]
""")

write(
    "references/Bloem2021.md",
    r"""
---
reference_id: Bloem2021
title: Bloem et al. 2021
evidence_type: review
evidence_grade: high
status: consensus
doi: "10.1016/S0140-6736(21)00218-X"
pmid: "33848468"
last_checked: 2026-07-25
tags: [Literatur, Parkinson, Neurodegeneration, Neurologie]
citation:
  entry_type: article
  csl_type: article-journal
  authors:
    - "Bloem, B. R."
    - "Okun, M. S."
    - "Klein, C."
  et_al: false
  year: 2021
  article_title: "Parkinson's disease"
  journal: The Lancet
  volume: "397"
  issue: "10291"
  pages: "2284–2303"
---

# Bloem et al. 2021

## Vollständige Zitation

Bloem, B. R., Okun, M. S., Klein, C. (2021). Parkinson's disease. *The Lancet, 397*(10291), 2284–2303.

## Kernaussage

Umfassende klinische Übersichtsarbeit zur Parkinson-Erkrankung. Sie beschreibt Parkinson als heterogene, fortschreitende neurodegenerative Erkrankung mit motorischen und nichtmotorischen Symptomen sowie Beteiligung mehrerer neuronaler Systeme.

## Population und Design

Narrative klinische Übersichtsarbeit, die epidemiologische, genetische, pathophysiologische, diagnostische und therapeutische Forschung zusammenführt.

## Einschränkungen

Die Arbeit ist keine direkte Vergleichsstudie zu ADHS und erlaubt keine Aussage über ein individuelles Parkinson-Risiko bei ADHS. Sie dient in dieser Einheit zur belastbaren Beschreibung der Parkinson-Erkrankung und ihrer Abgrenzung von Neuroentwicklungsstörungen.

## Verhältnis zum bisherigen Konsens

Bestätigt den etablierten Konsens, dass Parkinson eine neurodegenerative Erkrankung und nicht durch einen einfachen allgemeinen Dopaminmangel vollständig erklärt ist.

## Links

- [DOI](https://doi.org/10.1016/S0140-6736(21)00218-X)
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/33848468/)
""",
)

write(
    "references/Becker2023.md",
    r"""
---
reference_id: Becker2023
title: Becker et al. 2023
evidence_type: systematic-review
evidence_grade: moderate
status: disputed
doi: "10.3389/fpsyt.2023.1158546"
pmid: "37663597"
last_checked: 2026-07-25
tags: [Literatur, ADHS, Neurodegeneration, Demenz, Parkinson, Lebensspanne]
citation:
  entry_type: article
  csl_type: article-journal
  authors:
    - "Becker, S."
    - "Chowdhury, M."
    - "Tavilsup, P."
    - "Seitz, D."
    - "Callahan, B. L."
  et_al: false
  year: 2023
  article_title: "Risk of neurodegenerative disease or dementia in adults with attention-deficit/hyperactivity disorder: a systematic review"
  journal: Frontiers in Psychiatry
  volume: "14"
  article_number: "1158546"
---

# Becker et al. 2023

## Vollständige Zitation

Becker, S., Chowdhury, M., Tavilsup, P., Seitz, D., Callahan, B. L. (2023). Risk of neurodegenerative disease or dementia in adults with attention-deficit/hyperactivity disorder: a systematic review. *Frontiers in Psychiatry, 14*, 1158546.

## Kernaussage

Die systematische Übersicht fand eine kleine und methodisch heterogene Literatur zu späteren neurodegenerativen oder neurokognitiven Diagnosen bei Erwachsenen mit ADHS. Vorhandene Assoziationen begründen weitere Forschung, erlauben aber weder einen gesicherten kausalen Schluss noch eine individuelle Prognose.

## Population und Design

Systematische, PROSPERO-registrierte Übersicht von sieben Kohorten- oder Fall-Kontroll-Studien. Untersucht wurden unterschiedliche Endpunkte, darunter Demenz, Alzheimer-Erkrankung, Parkinson- oder Lewy-Körper-Erkrankungen, vaskuläre Demenz und leichte kognitive Beeinträchtigung.

## Einschränkungen

Die Studien unterschieden sich stark hinsichtlich Diagnosedaten, Kovariaten, Risikomaßen und Endpunkten; deshalb wurde keine Meta-Analyse durchgeführt. Krankenaktenkodierung, Komorbiditäten, Überwachungseffekte und mögliche Fehlklassifikation können die beobachteten Zusammenhänge verzerren.

## Verhältnis zum bisherigen Konsens

Präzisiert den Konsens: ADHS bleibt eine Neuroentwicklungsstörung. Ein mögliches späteres Neurodegenerationsrisiko ist eine offene Forschungsfrage und kein Beleg dafür, dass ADHS eine Vorstufe von Parkinson oder Demenz ist.

## Links

- [DOI](https://doi.org/10.3389/fpsyt.2023.1158546)
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/37663597/)
""",
)

write(
    "references/Dobrosavljevic2020.md",
    r"""
---
reference_id: Dobrosavljevic2020
title: Dobrosavljevic et al. 2020
evidence_type: systematic-review-meta-analysis
evidence_grade: high
status: consensus
doi: "10.1016/j.neubiorev.2020.07.042"
pmid: "32798966"
last_checked: 2026-07-25
tags: [Literatur, ADHS, ältere Erwachsene, Prävalenz, Lebensspanne]
citation:
  entry_type: article
  csl_type: article-journal
  authors:
    - "Dobrosavljevic, M."
    - "Solares, C."
    - "Cortese, S."
    - "Andershed, H."
    - "Larsson, H."
  et_al: false
  year: 2020
  article_title: "Prevalence of attention-deficit/hyperactivity disorder in older adults: A systematic review and meta-analysis"
  journal: Neuroscience & Biobehavioral Reviews
  volume: "118"
  pages: "282–289"
---

# Dobrosavljevic et al. 2020

## Vollständige Zitation

Dobrosavljevic, M., Solares, C., Cortese, S., Andershed, H., Larsson, H. (2020). Prevalence of attention-deficit/hyperactivity disorder in older adults: A systematic review and meta-analysis. *Neuroscience & Biobehavioral Reviews, 118*, 282–289.

## Kernaussage

ADHS-Symptome und klinisch diagnostizierte ADHS kommen auch bei älteren Erwachsenen vor. Die geschätzte Prävalenz unterscheidet sich jedoch stark danach, ob validierte Skalen, klinische Diagnosen oder Behandlungsdaten verwendet werden.

## Population und Design

Systematische Übersicht und Meta-Analyse von 20 Studien mit 32 Datensätzen und insgesamt mehr als 20 Millionen Personen; die große Gesamtzahl wurde stark von Registerdaten geprägt.

## Einschränkungen

Die Heterogenität zwischen Studien und Erhebungsmethoden war erheblich. Erhöhte Fragebogenwerte sind nicht mit einer klinischen Diagnose gleichzusetzen; historische Unterdiagnostik und unterschiedliche Versorgungssysteme beeinflussen die Schätzungen.

## Verhältnis zum bisherigen Konsens

Bestätigt, dass ADHS über die Lebensspanne fortbestehen kann und bei älteren Erwachsenen differentialdiagnostisch berücksichtigt werden muss, ohne neu auftretende Beschwerden vorschnell als ADHS zu erklären.

## Links

- [DOI](https://doi.org/10.1016/j.neubiorev.2020.07.042)
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/32798966/)
""",
)

run("python", "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements-docs.txt", "-r", "requirements-export.txt")
run("python", "-m", "pip", "check")
run("python", "-m", "compileall", "-q", "scripts", "tests")
run("git", "diff", "--check")
run("python", "scripts/build_literature.py")
run("python", "scripts/validate_links.py")
run("python", "scripts/build_graph.py")
run("python", "scripts/validate_graph.py")
run("python", "scripts/validate_compendium.py")
run("python", "scripts/build_combined.py")
run("python", "scripts/build_anki.py")
run("python", "scripts/build_docs.py")
run("mkdocs", "build", "--strict")
run("python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py")
if (ROOT / "package.json").is_file():
    run("npm", "ci")
    run("npm", "test")

shutil.rmtree(TEMP_DIR, ignore_errors=True)
TEMP_WORKFLOW.unlink(missing_ok=True)

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", "-A")
run("git", "diff", "--cached", "--check")
if run("git", "diff", "--cached", "--quiet", check=False).returncode == 0:
    print("Keine Reparaturänderungen")
else:
    run("git", "commit", "-m", "fix: vervollständige und validiere Einheit 15")
    run("git", "push", "origin", f"HEAD:{BRANCH}")
