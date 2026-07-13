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
}
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

if errors:
    print("Validierung fehlgeschlagen:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)
print(f"Validierung grün: {len(index['chapters'])} Kapitel, {len(reference_ids)} Quellen")
