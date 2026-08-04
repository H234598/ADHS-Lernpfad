#!/usr/bin/env python3
"""Einmalige, selbst zu entfernende Projektintegration für Einheit 19."""

from pathlib import Path
import json
import yaml

ROOT = Path(__file__).resolve().parents[1]


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"{relative}: erwartete genau ein Vorkommen, gefunden {count}: {old!r}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "02-Vertiefung/06-Trauma-PTBS-und-komplexe-Traumafolgen.md",
    "- Weiter: [[ROADMAP#A2 · Angst, Zwang, Trauma und episodische Störungen — P0|Bipolare Störungen, Psychosen und episodische Veränderungen]] *(geplant)*",
    "- Weiter: [[02-Vertiefung/07-Bipolare-Stoerungen-Psychosen-und-episodische-Veraenderungen|Bipolare Störungen, Psychosen und episodische Veränderungen]]",
)

replace_once("README.md", "version: 0.20.0", "version: 0.21.0")
replace_once("README.md", "last_reviewed: 2026-08-02", "last_reviewed: 2026-08-04")
replace_once(
    "README.md",
    "tags: [ADHS, Neurobiologie, Autismus, Parkinson, Angststörungen, Zwangsstörung, Trauma, PTBS, Lernpfad]",
    "tags: [ADHS, Neurobiologie, Autismus, Parkinson, Angststörungen, Zwangsstörung, Trauma, PTBS, bipolare Störung, Psychose, Lernpfad]",
)
replace_once(
    "README.md",
    "18. [[02-Vertiefung/06-Trauma-PTBS-und-komplexe-Traumafolgen|Trauma, PTBS und komplexe Traumafolgen: Zeitachsen, Abgrenzung und Koexistenz mit ADHS]]",
    "18. [[02-Vertiefung/06-Trauma-PTBS-und-komplexe-Traumafolgen|Trauma, PTBS und komplexe Traumafolgen: Zeitachsen, Abgrenzung und Koexistenz mit ADHS]]\n"
    "19. [[02-Vertiefung/07-Bipolare-Stoerungen-Psychosen-und-episodische-Veraenderungen|Bipolare Störungen, Psychosen und ADHS: Episoden, Abgrenzung und Sicherheit]]",
)

index_path = ROOT / "index.json"
index = json.loads(index_path.read_text(encoding="utf-8"))
if index.get("version") != "0.20.0" or len(index.get("chapters", [])) != 18:
    raise SystemExit("index.json besitzt nicht den erwarteten Basiszustand")
index["version"] = "0.21.0"
index["last_reviewed"] = "2026-08-04"
index["chapters"].append(
    {
        "number": 19,
        "path": "02-Vertiefung/07-Bipolare-Stoerungen-Psychosen-und-episodische-Veraenderungen.md",
        "title": "Bipolare Störungen, Psychosen und ADHS: Episoden, Abgrenzung und Sicherheit",
    }
)
index_path.write_text(
    json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

replace_once(
    "mkdocs.yml",
    "      - Trauma, PTBS und komplexe Traumafolgen: 02-Vertiefung/06-Trauma-PTBS-und-komplexe-Traumafolgen.md",
    "      - Trauma, PTBS und komplexe Traumafolgen: 02-Vertiefung/06-Trauma-PTBS-und-komplexe-Traumafolgen.md\n"
    "      - Bipolare Störungen, Psychosen und ADHS: 02-Vertiefung/07-Bipolare-Stoerungen-Psychosen-und-episodische-Veraenderungen.md",
)

replace_once("ROADMAP.md", "last_reviewed: 2026-08-02", "last_reviewed: 2026-08-04")
replace_once(
    "ROADMAP.md",
    "Der Lernpfad umfasst derzeit 18 fortlaufende Einheiten:",
    "Der Lernpfad umfasst derzeit 19 fortlaufende Einheiten:",
)
replace_once(
    "ROADMAP.md",
    "18. Trauma, PTBS und komplexe Traumafolgen: Zeitachsen, Abgrenzung und Koexistenz mit ADHS",
    "18. Trauma, PTBS und komplexe Traumafolgen: Zeitachsen, Abgrenzung und Koexistenz mit ADHS\n"
    "19. Bipolare Störungen, Psychosen und ADHS: Episoden, Abgrenzung und Sicherheit",
)
replace_once(
    "ROADMAP.md",
    "- [ ] **Bipolare Störungen, Psychosen und andere episodische Veränderungen**",
    "- [x] **Bipolare Störungen, Psychosen und andere episodische Veränderungen** — umgesetzt als Einheit 19",
)

planned_path = ROOT / "knowledge-graph/planned-nodes.yaml"
planned = yaml.safe_load(planned_path.read_text(encoding="utf-8"))
target = "02-Vertiefung/07-Bipolare-Stoerungen-Psychosen-und-episodische-Veraenderungen"
before = len(planned["nodes"])
planned["nodes"] = [node for node in planned["nodes"] if node.get("path") != target]
if len(planned["nodes"]) != before - 1:
    raise SystemExit("Geplanter Wissensgraph-Knoten für Einheit 19 fehlt oder ist doppelt")
planned_path.write_text(
    yaml.safe_dump(planned, allow_unicode=True, sort_keys=False), encoding="utf-8"
)

replace_once("Glossar.md", "last_reviewed: 2026-08-02", "last_reviewed: 2026-08-04")
glossary = ROOT / "Glossar.md"
glossary_additions = """

## Bipolare Störung
Psychische Störung mit klar abgrenzbaren manischen oder hypomanischen Episoden und häufig depressiven Episoden; die Diagnose beruht auf Verlauf, Symptomqualität, Funktionsbeeinträchtigung und Alternativerklärungen, nicht auf gewöhnlichen Stimmungsschwankungen.

## Episode
Zeitlich abgrenzbare qualitative Veränderung gegenüber dem persönlichen Ausgangsniveau, bei der mehrere zusammengehörige Symptome und Funktionsveränderungen auftreten; mehr als ein einzelner guter oder schlechter Tag.

## Halluzination
Wahrnehmungsähnliches Erlebnis ohne entsprechenden äußeren Reiz, beispielsweise Stimmenhören; diagnostisch nicht automatisch einer einzigen Störung zuzuordnen.

## Hypomanie
Episode mit deutlich veränderter Stimmung sowie erhöhter Energie und Aktivität, die gegenüber dem Ausgangsniveau auffällt, aber nicht die Schwere einer Manie erreicht; psychotische Symptome sprechen gegen eine bloße Hypomanie.

## Manie
Episode mit deutlich gehobener, gereizter oder expansiver Stimmung und gesteigerter Energie oder Aktivität, verbunden mit weiteren Symptomen und erheblicher Funktionsveränderung; kann psychotische Symptome oder stationären Behandlungsbedarf umfassen.

## Psychose
Syndrom mit relevanter Störung des Realitätsbezugs, häufig mit Halluzinationen, Wahn oder ausgeprägter Denkdesorganisation; kann bei unterschiedlichen psychischen, substanzbezogenen, neurologischen oder körperlichen Erkrankungen auftreten.

## Vermindertes Schlafbedürfnis
Deutlich weniger Schlaf als üblich bei subjektiv erhaltener oder gesteigerter Energie; von Schlafmangel mit Müdigkeit, Insomnie und zirkadianer Verschiebung zu unterscheiden.

## Wahn
Überzeugung, die trotz deutlicher Gegenbelege mit ungewöhnlicher Gewissheit festgehalten wird und nicht angemessen aus kulturellem oder religiösem Kontext erklärbar ist; genaue klinische Einordnung erfordert Fachdiagnostik.
"""
glossary.write_text(
    glossary.read_text(encoding="utf-8").rstrip() + glossary_additions + "\n",
    encoding="utf-8",
)

cards_path = ROOT / "cards/cards.yaml"
cards = yaml.safe_load(cards_path.read_text(encoding="utf-8"))
if any(card.get("id") == 1019 or card.get("unit") == 19 for card in cards["cards"]):
    raise SystemExit("Anki-Karte für Einheit 19 existiert bereits")
cards["cards"].append(
    {
        "id": 1019,
        "unit": 19,
        "front": "Warum ist eine Phase mit wenig Schlaf und hoher Aktivität nicht automatisch ADHS oder Manie?",
        "back": "Weil ADHS ein entwicklungsbezogenes Muster ist und Manie beziehungsweise Hypomanie eine klar abgrenzbare qualitative Episode erfordern. Schlafdauer, subjektives Schlafbedürfnis, Stimmung, Energie, Aktivität, Realitätsbezug, Folgen, Substanzen und Medikamente müssen gemeinsam geprüft werden.",
        "tags": [
            "ADHS",
            "Bipolare_Stoerung",
            "Psychose",
            "Vertiefung",
            "Differentialdiagnostik",
            "Einheit_19",
        ],
    }
)
cards_path.write_text(
    yaml.safe_dump(cards, allow_unicode=True, sort_keys=False, width=110),
    encoding="utf-8",
)

changelog_path = ROOT / "CHANGELOG.md"
changelog = changelog_path.read_text(encoding="utf-8")
marker = "# Änderungsverlauf\n\n"
if not changelog.startswith(marker):
    raise SystemExit("Unerwartete Changelog-Überschrift")
entry = """## 0.21.0 – 2026-08-04

- Einheit 19 „Bipolare Störungen, Psychosen und ADHS: Episoden, Abgrenzung und Sicherheit“ ergänzt
- entwicklungsbezogene ADHS-Merkmale von manischen, hypomanischen und psychotischen Episoden anhand Verlauf, Schlafbedürfnis, Stimmung, Energie und Realitätsbezug abgegrenzt
- aktuelle NICE-Leitlinie, ICD-11-Diagnosemanual, Komorbiditäts-Meta-Analyse und systematische Evidenz zu Behandlung und Psychoserisiken ergänzt
- Sicherheitsgrenzen, Glossarbegriffe, Anki-Karte, Navigation, Roadmap und Wissensgraph-Planung aktualisiert

"""
changelog_path.write_text(marker + entry + changelog[len(marker) :], encoding="utf-8")
