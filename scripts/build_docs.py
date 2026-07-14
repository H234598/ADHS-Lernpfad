#!/usr/bin/env python3
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "build" / "docs"
if DOCS.exists():
    shutil.rmtree(DOCS)
DOCS.mkdir(parents=True)

files = [
    "README.md", "00-Einfuehrung.md", "Glossar.md", "Literatur.md", "ROADMAP.md",
    "references/README.md", "knowledge-graph/README.md", "cards/README.md", "figures/README.md",
    "prompts/README.md", "prompts/AUTOMATION-PROMPT.md",
    "prompts/DEEP-RESEARCH-PROMPT.md", "prompts/MERGE-AUTOMATION-PROMPT.md",
    "prompts/PR-REPAIR-PROMPT.md",
]
files.extend(str(p.relative_to(ROOT)) for p in sorted((ROOT / "01-Grundlagen").glob("*.md")))
for rel in files:
    src = ROOT / rel
    dst = DOCS / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
shutil.copytree(ROOT / "figures", DOCS / "figures", dirs_exist_ok=True)
shutil.copy2(ROOT / "CNAME", DOCS / "CNAME")
print(f"MkDocs-Quellen: {len(files)} Markdown-Dateien plus CNAME")