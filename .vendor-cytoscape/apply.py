#!/usr/bin/env python3
"""Finalize the pinned local Cytoscape dependency and remove this bootstrap."""

from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / ".vendor-cytoscape"
WORKFLOW = ROOT / ".github" / "workflows" / "vendor-cytoscape.yml"
VENDOR = ROOT / "assets" / "vendor" / "cytoscape"


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    content = path.read_text(encoding="utf-8")
    count = content.count(old)
    if count != 1:
        raise RuntimeError(
            f"Erwartete genau einen Treffer in {relative}, gefunden: {count}"
        )
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


required = (
    "cytoscape.min.js",
    "LICENSE",
    "VERSION.txt",
    "SOURCE.txt",
    "SHA256SUMS.txt",
)
missing = [name for name in required if not (VENDOR / name).is_file()]
if missing:
    raise FileNotFoundError(f"Unvollständige Cytoscape-Auslieferung: {missing}")
if (VENDOR / "VERSION.txt").read_text(encoding="utf-8").strip() != "3.34.0":
    raise ValueError("Unerwartete Cytoscape-Version")

replace_once(
    "mkdocs.yml",
    "  - https://cdn.jsdelivr.net/npm/cytoscape@3.34.0/dist/cytoscape.min.js\n",
    "  - assets/vendor/cytoscape/cytoscape.min.js\n",
)
replace_once(
    "WARTUNG.md",
    "Cytoscape.js ist auf Version `3.34.0` festgelegt; Farbe ist bei Statusdarstellungen nicht das einzige Unterscheidungsmerkmal.",
    "Cytoscape.js wird als lokal eingecheckte Version `3.34.0` mit Lizenz, Herkunftsnachweis und SHA-256-Prüfsummen ausgeliefert; der Seitenaufbau benötigt dafür kein externes CDN. Farbe ist bei Statusdarstellungen nicht das einzige Unterscheidungsmerkmal.",
)
replace_once(
    "tests/test_graph_web.py",
    '        self.assertIn("cytoscape@3.34.0/dist/cytoscape.min.js", mkdocs)\n',
    '        self.assertIn("assets/vendor/cytoscape/cytoscape.min.js", mkdocs)\n'
    '        self.assertNotIn("cdn.jsdelivr.net/npm/cytoscape", mkdocs)\n'
    '        vendor = ROOT / "assets" / "vendor" / "cytoscape"\n'
    '        self.assertEqual(\n'
    '            (vendor / "VERSION.txt").read_text(encoding="utf-8").strip(),\n'
    '            "3.34.0",\n'
    '        )\n'
    '        self.assertIn(\n'
    '            "cytoscape.min.js",\n'
    '            (vendor / "SHA256SUMS.txt").read_text(encoding="utf-8"),\n'
    '        )\n'
    '        self.assertIn(\n'
    '            "be225eadd48edf7c73acb85355af12bfc929556e",\n'
    '            (vendor / "SOURCE.txt").read_text(encoding="utf-8"),\n'
    '        )\n',
)

shutil.rmtree(BOOTSTRAP)
WORKFLOW.unlink(missing_ok=True)
print("Cytoscape 3.34.0 lokal eingebunden und Bootstrap entfernt")
