#!/usr/bin/env python3
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "build"
out.mkdir(exist_ok=True)
index = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))
paths = [ROOT / "00-Einfuehrung.md"]
paths.extend(ROOT / item["path"] for item in index["chapters"])
paths.extend([ROOT / "Glossar.md", ROOT / "Literatur.md"])
parts = ["# ADHS-Lernpfad – Gesamtdokument\n"]
for path in paths:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    parts.extend([text.strip(), "\n---\n"])
(out / "ADHS-Lernpfad-Gesamtdokument.md").write_text("\n\n".join(parts) + "\n", encoding="utf-8")
print("Gesamtdokument erstellt")
