#!/usr/bin/env python3
"""Report all link-resolution issues and provide strict compatibility APIs."""

from __future__ import annotations

from pathlib import Path

from content_model import ContentIndex, build_content_index
from link_resolution import resolve_occurrence
from link_types import (
    LinkError, LinkIssue, LinkOccurrence, LinkTarget, Resolution, scan_wikilinks,
)


def issue_for(
    index: ContentIndex, occurrence: LinkOccurrence, resolution: Resolution,
) -> LinkIssue | None:
    if resolution.status == "ok":
        return None
    return LinkIssue(
        resolution.status, "warning" if resolution.status == "planned" else "error",
        resolution.message or resolution.status,
        occurrence.source.resolve().relative_to(index.root).as_posix(),
        occurrence.line, occurrence.column, occurrence.raw, occurrence.target,
        resolution.candidates,
    )


def analyze_all(
    root: Path, index: ContentIndex | None = None,
) -> tuple[ContentIndex, list[LinkIssue]]:
    index = index or build_content_index(root)
    issues: list[LinkIssue] = []
    documents = sorted(index.documents.values(), key=lambda item: item.relative_path.as_posix())
    for document in documents:
        for occurrence in scan_wikilinks(document.raw_text, document.path):
            issue = issue_for(index, occurrence, resolve_occurrence(index, occurrence))
            if issue is not None:
                issues.append(issue)
    return index, sorted(
        issues, key=lambda item: (item.path, item.line, item.column, item.code),
    )


def validate_all(root: Path) -> list[str]:
    index, link_issues = analyze_all(root)
    errors = [
        f"{issue.path or 'Repository'}"
        + (f":{issue.line}" if issue.line else "")
        + f": {issue.message}"
        for issue in index.model_issues if issue.severity == "error"
    ]
    errors.extend(item.format() for item in link_issues if item.severity == "error")
    return errors


def resolve_target(
    root: Path, source: Path, target: str, heading: str | None = None,
    *, index: ContentIndex | None = None,
) -> LinkTarget:
    index = index or build_content_index(root)
    occurrence = LinkOccurrence(
        source, f"[[{target}{'#' + heading if heading else ''}]]", target,
        heading, heading or Path(target).stem or target, False, 1, 1, 0, 0,
    )
    resolution = resolve_occurrence(index, occurrence)
    if not resolution.ok or resolution.path is None:
        raise LinkError(resolution.message or f"Ungültiges Linkziel: {occurrence.raw}")
    return LinkTarget(resolution.path, resolution.heading)
