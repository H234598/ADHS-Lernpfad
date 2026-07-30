#!/usr/bin/env python3
"""Integrate Unit 16 into project registries without generating outputs."""

from __future__ import annotations

import json
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Integrationsanker fehlt in {path}: {old[:100]!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    replace_once(
        "02-Vertiefung/03-Parkinson-ADHS-mechanistische-Vergleiche-und-Grenzen.md",
        "- Weiter: [[ROADMAP#Milestone A – Klinische Heterogenität und Lebensspanne|Nächste Themen laut Roadmap]]",
        "- Weiter: [[02-Vertiefung/04-Angststoerungen-und-ADHS|Angststörungen und ADHS: Komorbidität, Abgrenzung und Wechselwirkungen]]",
    )

    replace_once("README.md", "version: 0.17.0", "version: 0.18.0")
    replace_once("README.md", "last_reviewed: 2026-07-25", "last_reviewed: 2026-07-30")
    replace_once(
        "README.md",
        "tags: [ADHS, Neurobiologie, Autismus, Parkinson, Lernpfad]",
        "tags: [ADHS, Neurobiologie, Autismus, Parkinson, Angststörungen, Lernpfad]",
    )
    replace_once(
        "README.md",
        "15. [[02-Vertiefung/03-Parkinson-ADHS-mechanistische-Vergleiche-und-Grenzen|Parkinson, ADHS und mechanistische Vergleiche]]",
        "15. [[02-Vertiefung/03-Parkinson-ADHS-mechanistische-Vergleiche-und-Grenzen|Parkinson, ADHS und mechanistische Vergleiche]]\n"
        "16. [[02-Vertiefung/04-Angststoerungen-und-ADHS|Angststörungen und ADHS: Komorbidität, Abgrenzung und Wechselwirkungen]]",
    )

    replace_once("ROADMAP.md", "last_reviewed: 2026-07-25", "last_reviewed: 2026-07-30")
    replace_once(
        "ROADMAP.md",
        "Der Lernpfad umfasst derzeit 15 fortlaufende Einheiten:",
        "Der Lernpfad umfasst derzeit 16 fortlaufende Einheiten:",
    )
    replace_once(
        "ROADMAP.md",
        "15. Parkinson, ADHS und mechanistische Vergleiche",
        "15. Parkinson, ADHS und mechanistische Vergleiche\n"
        "16. Angststörungen und ADHS: Komorbidität, Abgrenzung und Wechselwirkungen",
    )
    replace_once(
        "ROADMAP.md",
        "- [ ] **Angststörungen und ADHS**",
        "- [x] **Angststörungen und ADHS** — umgesetzt als Einheit 16",
    )

    replace_once("Glossar.md", "last_reviewed: 2026-07-25", "last_reviewed: 2026-07-30")
    replace_once(
        "Glossar.md",
        "## Arbeitsgedächtnis\nSystem zur kurzfristigen aktiven Speicherung und Bearbeitung von Information.",
        "## Angststörung\nPsychische Störung mit anhaltender oder wiederkehrender Furcht, Sorge, körperlicher Aktivierung oder Vermeidung, die über eine vorübergehende angemessene Angstreaktion hinausgeht und relevante Beeinträchtigung verursacht.\n\n"
        "## Arbeitsgedächtnis\nSystem zur kurzfristigen aktiven Speicherung und Bearbeitung von Information.",
    )
    replace_once(
        "Glossar.md",
        "## Screening\nKurze systematische Prüfung, die eine Wahrscheinlichkeit abschätzt, aber keine vollständige Diagnose ersetzt.",
        "## Sicherheitsverhalten\nHandlung zur kurzfristigen Verringerung einer befürchteten Gefahr oder Unsicherheit, etwa Rückversicherung oder wiederholte Kontrolle; kann eine realistische Kompensation sein, bei Angst aber auch korrigierende Erfahrungen verhindern.\n\n"
        "## Screening\nKurze systematische Prüfung, die eine Wahrscheinlichkeit abschätzt, aber keine vollständige Diagnose ersetzt.",
    )
    replace_once(
        "Glossar.md",
        "## Zirkadianer Rhythmus",
        "## Vermeidung\nNichtausführen oder Verlassen einer gefürchteten Situation, Aufgabe oder inneren Erfahrung; vermindert Belastung oft kurzfristig, kann Angst und Funktionsbeeinträchtigung langfristig jedoch aufrechterhalten.\n\n"
        "## Zirkadianer Rhythmus",
    )

    cards = Path("cards/cards.yaml")
    cards_text = cards.read_text(encoding="utf-8")
    if "  unit: 16\n" not in cards_text:
        cards_text += """
- id: 1016
  unit: 16
  front: Warum kann Aufschieben bei ADHS und einer Angststörung ähnlich aussehen, obwohl unterschiedliche Mechanismen beteiligt sein können?
  back: Bei ADHS können unklare Schritte, geringe unmittelbare Rückmeldung oder instabile Zielaktivierung den Start erschweren; bei Angst kann Aufschub erwartete Fehler, Bewertung oder körperliche Aktivierung vermeiden. Beide Mechanismen können gleichzeitig vorkommen.
  tags:
  - ADHS
  - Angststörungen
  - Vertiefung
  - Differentialdiagnostik
  - Einheit_16
"""
        cards.write_text(cards_text, encoding="utf-8")

    index_path = Path("index.json")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["version"] = "0.18.0"
    index["last_reviewed"] = "2026-07-30"
    if not any(chapter.get("number") == 16 for chapter in index["chapters"]):
        index["chapters"].append(
            {
                "number": 16,
                "path": "02-Vertiefung/04-Angststoerungen-und-ADHS.md",
                "title": "Angststörungen und ADHS: Komorbidität, Abgrenzung und Wechselwirkungen",
            }
        )
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    replace_once(
        "knowledge-graph/planned-nodes.yaml",
        "02-Vertiefung/04-Studienmethodik-Effektgroessen-Bias-und-Kausalitaet",
        "02-Vertiefung/05-Studienmethodik-Effektgroessen-Bias-und-Kausalitaet",
    )
    replace_once(
        "mkdocs.yml",
        "      - Parkinson, ADHS und mechanistische Vergleiche: 02-Vertiefung/03-Parkinson-ADHS-mechanistische-Vergleiche-und-Grenzen.md",
        "      - Parkinson, ADHS und mechanistische Vergleiche: 02-Vertiefung/03-Parkinson-ADHS-mechanistische-Vergleiche-und-Grenzen.md\n"
        "      - Angststörungen und ADHS: 02-Vertiefung/04-Angststoerungen-und-ADHS.md",
    )

    changelog = Path("CHANGELOG.md")
    text = changelog.read_text(encoding="utf-8")
    heading = "## 0.18.0 – 2026-07-30"
    if heading not in text:
        entry = """## 0.18.0 – 2026-07-30

- Einheit 16 „Angststörungen und ADHS: Komorbidität, Abgrenzung und Wechselwirkungen“ ergänzt
- Angstsymptome, diagnostizierte Angststörungen und ADHS-bezogene Regulationsprobleme methodisch getrennt
- wechselseitige Verstärkung, Differentialdiagnostik, Sicherheitsverhalten und Vermeidung ohne pauschale Kausalbehauptung eingeordnet
- zwei aktuelle Meta-Analysen, Glossarbegriffe, Anki-Karte, Navigation, Roadmap und Wissensgraph-Planung ergänzt

"""
        changelog.write_text(text.replace("# Änderungsverlauf\n\n", "# Änderungsverlauf\n\n" + entry, 1), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
