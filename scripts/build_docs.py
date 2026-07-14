#!/usr/bin/env python3
"""Prepare converted Markdown, assets and downloads for the MkDocs build."""

from pathlib import Path
import shutil

from content_links import convert_for_web, validate_all

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "build" / "docs"

errors = validate_all(ROOT)
if errors:
    raise ValueError("Ungültige Obsidian-Links:\n" + "\n".join(f"- {error}" for error in errors))

if DOCS.exists():
    shutil.rmtree(DOCS)
DOCS.mkdir(parents=True)

files = [
    "README.md",
    "00-Einfuehrung.md",
    "DOWNLOADS.md",
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
files.extend(
    str(path.relative_to(ROOT))
    for path in sorted((ROOT / "references").glob("*.md"))
    if path.name != "README.md"
)

for relative_path in files:
    source = ROOT / relative_path
    destination = DOCS / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    converted = convert_for_web(source.read_text(encoding="utf-8"), source, ROOT)
    destination.write_text(converted, encoding="utf-8")

for generated_reference_file in ("references.bib", "references.json"):
    source = ROOT / generated_reference_file
    if source.exists():
        shutil.copy2(source, DOCS / generated_reference_file)

for directory in ("figures", "assets"):
    source = ROOT / directory
    if source.exists():
        shutil.copytree(source, DOCS / directory, dirs_exist_ok=True)

artifact_source = ROOT / "build" / "artifacts"
if artifact_source.is_dir():
    shutil.copytree(artifact_source, DOCS / "artifacts", dirs_exist_ok=True)

shutil.copy2(ROOT / "CNAME", DOCS / "CNAME")
print(
    f"MkDocs-Quellen: {len(files)} konvertierte Markdown-Dateien, "
    "Bibliografiedaten, Assets, optionale Downloads und CNAME"
)
