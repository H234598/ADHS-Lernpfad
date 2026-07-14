#!/usr/bin/env python3
"""Validate Obsidian links and web-only callout conversion."""

from pathlib import Path

from callouts import convert_obsidian_callouts_for_web
from content_links import markdown_files, validate_all

ROOT = Path(__file__).resolve().parents[1]
errors = validate_all(ROOT)

sample = (
    "> [!evidence] Evidenz: Konsens / hoch\n"
    "> Eine wissenschaftliche Kernaussage.\n"
)
expected = (
    '!!! evidence "Evidenz: Konsens / hoch"\n'
    "    Eine wissenschaftliche Kernaussage.\n"
)
if convert_obsidian_callouts_for_web(sample) != expected:
    errors.append("Interner Test der Evidenz-Callout-Konvertierung ist fehlgeschlagen")

for source in markdown_files(ROOT):
    converted = convert_obsidian_callouts_for_web(source.read_text(encoding="utf-8"))
    if "> [!evidence]" in converted:
        errors.append(
            f"{source.relative_to(ROOT)}: [!evidence] bleibt nach Web-Konvertierung sichtbar"
        )

if errors:
    print("Link- oder Callout-Validierung fehlgeschlagen:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print(
    "Validierung erfolgreich: Wikilinks sind eindeutig und "
    "Obsidian-Callouts werden webgerecht umgewandelt"
)
