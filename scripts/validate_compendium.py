#!/usr/bin/env python3
from pathlib import Path
import json
import re
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
errors = []
index = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))
numbers = [item["number"] for item in index["chapters"]]
if numbers != list(range(1, len(numbers) + 1)):
    errors.append(f"Nummern nicht fortlaufend: {numbers}")

reference_ids = {p.stem for p in (ROOT / "references").glob("*.md") if p.name != "README.md"}
required = {
    "title", "level", "estimated_time", "difficulty", "prerequisites", "tags",
    "last_reviewed", "evidence", "status", "references",
    "minimum_reading_minutes", "maximum_reading_minutes",
}
required_sections = [
    "## Lernziel", "## Review-Frage", "## Wissenschaftliche Quelle",
    "## Merksatz", "## Navigation",
]

def prose_word_count(text: str) -> int:
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"<details>.*?</details>", "", text, flags=re.S)
    text = re.sub(r"## Navigation.*\Z", "", text, flags=re.S)
    text = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1), text)
    return len(re.findall(r"\b[\wÄÖÜäöüß]+(?:[-’'][\wÄÖÜäöüß]+)*\b", text))

for item in index["chapters"]:
    path = ROOT / item["path"]
    if not path.exists():
        errors.append(f"Fehlt: {item['path']}")
        continue
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---", text, re.S)
    if not match:
        errors.append(f"Kein Frontmatter: {path}")
        continue
    meta = yaml.safe_load(match.group(1))
    missing = required - set(meta)
    if missing:
        errors.append(f"{path}: fehlend {sorted(missing)}")
    if meta.get("minimum_reading_minutes") != 10 or meta.get("maximum_reading_minutes") != 20:
        errors.append(f"{path}: Lernzeit muss 10–20 Minuten sein")
    words = prose_word_count(text)
    if words < 700:
        errors.append(f"{path}: nur {words} Fließtextwörter; mindestens 700 erforderlich")
    for section in required_sections:
        if section not in text:
            errors.append(f"{path}: Pflichtabschnitt fehlt: {section}")
    if "```mermaid" not in text:
        errors.append(f"{path}: Mermaid-Diagramm fehlt")
    for reference_id in meta.get("references", []):
        if reference_id not in reference_ids:
            errors.append(f"{path}: unbekannte Quelle {reference_id}")

wikilink = re.compile(r"\[\[([^\]|#]+)")
for path in ROOT.rglob("*.md"):
    if any(part in {"build", "site"} for part in path.parts):
        continue
    for target in wikilink.findall(path.read_text(encoding="utf-8")):
        candidates = [ROOT / f"{target}.md", ROOT / target, ROOT / "01-Grundlagen" / f"{target}.md"]
        if not any(candidate.exists() for candidate in candidates):
            errors.append(f"{path.relative_to(ROOT)}: ungelöster Link [[{target}]]")

cname = ROOT / "CNAME"
if not cname.exists() or cname.read_text(encoding="utf-8").strip() != "ADHS.telacore.org":
    errors.append("CNAME fehlt oder enthält nicht ADHS.telacore.org")

if errors:
    print("Validierung fehlgeschlagen:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)
print(f"Validierung grün: {len(index['chapters'])} Kapitel, {len(reference_ids)} Quellen; alle Kapitel >= 700 Wörter")
