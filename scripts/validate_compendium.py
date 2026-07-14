#!/usr/bin/env python3
from pathlib import Path
import json
import os
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "build" / "validation-report.txt"
MIN_WORDS = 800
WARNING_WORDS = 1000
MAX_WORDS = 2500
errors = []
warnings = []
counts = []
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
    text = re.sub(r"</?(?:details|summary)>", "", text)
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
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        errors.append(f"{path}: ungültiges YAML-Frontmatter: {str(exc).splitlines()[0]}")
        meta = {}
    if not isinstance(meta, dict):
        errors.append(f"{path}: Frontmatter ist kein Mapping")
        meta = {}
    missing = required - set(meta)
    if missing:
        errors.append(f"{path}: fehlend {sorted(missing)}")
    if meta.get("minimum_reading_minutes") != 10 or meta.get("maximum_reading_minutes") != 20:
        errors.append(f"{path}: Lernzeit muss 10–20 Minuten sein")
    words = prose_word_count(text)
    counts.append((item["number"], item["path"], words))
    if words < MIN_WORDS:
        errors.append(f"{path}: nur {words} Fließtextwörter; mindestens {MIN_WORDS} erforderlich")
    elif words < WARNING_WORDS:
        warnings.append(f"{path}: {words} Wörter; unter dem Zielbereich von {WARNING_WORDS} Wörtern")
    if words > MAX_WORDS:
        errors.append(f"{path}: {words} Fließtextwörter; Maximum sind {MAX_WORDS}")
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

REPORT.parent.mkdir(parents=True, exist_ok=True)
report_lines = [
    "ADHS-Lernpfad Validierungsbericht",
    "",
    f"Grenzen: Minimum {MIN_WORDS}, Warnung unter {WARNING_WORDS}, Maximum {MAX_WORDS} Fließtextwörter",
    "",
    "Wortzahlen:",
]
report_lines.extend(f"- Einheit {number}: {words} Wörter — {path}" for number, path, words in counts)
report_lines.extend(["", "Warnungen:"])
report_lines.extend([f"- {warning}" for warning in warnings] or ["- keine"])
report_lines.extend(["", "Fehler:"])
report_lines.extend([f"- {error}" for error in errors] or ["- keine"])
REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
print(REPORT.read_text(encoding="utf-8"))

summary = "counts=" + ",".join(f"{n}:{w}" for n, _, w in counts)
if errors:
    compact_errors = " | ".join(error.replace("\n", " ") for error in errors)
    summary += "; errors=" + compact_errors[:700]
else:
    summary += "; errors=none"
if os.getenv("GITHUB_OUTPUT"):
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
        fh.write(f"summary={summary}\n")
        fh.write(f"failed={'true' if errors else 'false'}\n")

print(f"Validierung abgeschlossen: {len(index['chapters'])} Kapitel, {len(reference_ids)} Quellen")
