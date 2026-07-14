#!/usr/bin/env python3
from pathlib import Path
import json
import re

from content_links import convert_for_combined

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "build"
out.mkdir(exist_ok=True)
index = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))
paths = [ROOT / "00-Einfuehrung.md"]
paths.extend(ROOT / item["path"] for item in index["chapters"])
paths.extend([ROOT / "Glossar.md", ROOT / "Literatur.md"])
included_paths = {path.resolve() for path in paths}

parts = [
    "---\n"
    "title: ADHS-Lernpfad – Gesamtdokument\n"
    "lang: de\n"
    "bibliography: references.bib\n"
    "link-citations: true\n"
    "---\n"
]
for path in paths:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = convert_for_combined(text, path, ROOT, included_paths)
    parts.extend([text.strip(), "\n---\n"])

(out / "ADHS-Lernpfad-Gesamtdokument.md").write_text(
    "\n\n".join(parts) + "\n", encoding="utf-8"
)
print("Gesamtdokument mit exportfähigen internen Links erstellt")
