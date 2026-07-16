#!/usr/bin/env python3
"""Validate internal links, planned targets and web-only callout conversion."""

from pathlib import Path

from callouts import convert_obsidian_callouts_for_web
from content_links import analyze_all, markdown_files

ROOT = Path(__file__).resolve().parents[1]
index, link_issues = analyze_all(ROOT)
errors = [
    f"{issue.path or 'Repository'}"
    + (f":{issue.line}" if issue.line else "")
    + f": {issue.message}"
    for issue in index.model_issues
    if issue.severity == "error"
]
warnings = [
    f"{issue.path or 'Repository'}"
    + (f":{issue.line}" if issue.line else "")
    + f": {issue.message}"
    for issue in index.model_issues
    if issue.severity != "error"
]
errors.extend(issue.format() for issue in link_issues if issue.severity == "error")
warnings.extend(issue.format() for issue in link_issues if issue.severity != "error")

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

if warnings:
    print("Linkwarnungen:")
    for warning in warnings:
        print(f"- {warning}")

if errors:
    print("Link- oder Callout-Validierung fehlgeschlagen:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print(
    "Validierung erfolgreich: interne Links sind eindeutig oder ausdrücklich geplant; "
    "Obsidian-Callouts werden webgerecht umgewandelt"
)
