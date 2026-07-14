#!/usr/bin/env python3
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "build" / "docs"

if DOCS.exists():
    shutil.rmtree(DOCS)
DOCS.mkdir(parents=True)

files = [
    "README.md",
    "00-Einfuehrung.md",
    "Glossar.md",
    "Literatur.md",
    "ROADMAP.md",
    "WARTUNG.md",
    "SYNC-OBSIDIAN.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    ".github/README.md",
    "references/README.md",
    "knowledge-graph/README.md",
    "cards/README.md",
    "figures/README.md",
    "prompts/README.md",
    "prompts/AUTOMATION-PROMPT.md",
    "prompts/DEEP-RESEARCH-PROMPT.md",
    "prompts/MERGE-AUTOMATION-PROMPT.md",
    "prompts/PR-REPAIR-PROMPT.md",
]
files.extend(str(path.relative_to(ROOT)) for path in sorted((ROOT / "01-Grundlagen").glob("*.md")))

for relative_path in files:
    source = ROOT / relative_path
    destination = DOCS / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)

for directory in ("figures", "assets"):
    source = ROOT / directory
    if source.exists():
        shutil.copytree(source, DOCS / directory, dirs_exist_ok=True)

shutil.copy2(ROOT / "CNAME", DOCS / "CNAME")
print(f"MkDocs-Quellen: {len(files)} Markdown-Dateien plus Assets und CNAME")
