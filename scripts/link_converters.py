#!/usr/bin/env python3
"""Convert resolved Wikilinks for MkDocs and combined Pandoc exports."""

from __future__ import annotations

from collections.abc import Iterable
import html
import os
from pathlib import Path
import re

from content_model import (
    ContentIndex, FenceState, advance_fence_state, build_content_index,
    document_anchor, slugify,
)
from link_resolution import resolve_occurrence
from link_types import IMAGE_SUFFIXES, LinkError, LinkOccurrence, Resolution, scan_wikilinks


def _relative_link(source: Path, target: Path) -> str:
    return Path(os.path.relpath(target, start=source.parent)).as_posix()


def _replace_occurrences(
    text: str, replacements: Iterable[tuple[LinkOccurrence, str]],
) -> str:
    output = text
    for occurrence, replacement in sorted(
        replacements, key=lambda item: item[0].start, reverse=True,
    ):
        output = output[: occurrence.start] + replacement + output[occurrence.end:]
    return output


def _web_replacement(
    occurrence: LinkOccurrence, resolution: Resolution, tolerate: bool,
) -> str:
    if resolution.ok and resolution.path is not None:
        relative = _relative_link(occurrence.source, resolution.path)
        if resolution.heading:
            relative += "#" + slugify(resolution.heading)
        if occurrence.embed and resolution.path.suffix.lower() in IMAGE_SUFFIXES:
            return f"![{occurrence.label}]({relative})"
        return f"[{occurrence.label}]({relative})"
    if not tolerate:
        raise LinkError(resolution.message or f"Ungültiges Linkziel: {occurrence.raw}")
    status = resolution.status
    label = html.escape(occurrence.label)
    message = html.escape(resolution.message or status, quote=True)
    return (
        f'<span class="internal-link internal-link--{status}" '
        f'data-link-status="{status}" title="{message}">'
        f"{label} <small>[{status}]</small></span>"
    )


def convert_for_web(
    text: str, source: Path, root: Path, *, index: ContentIndex | None = None,
    tolerate_issues: bool = False,
) -> str:
    index = index or build_content_index(root)
    replacements = []
    for occurrence in scan_wikilinks(text, source):
        resolution = resolve_occurrence(index, occurrence)
        replacements.append((
            occurrence, _web_replacement(occurrence, resolution, tolerate_issues),
        ))
    return _replace_occurrences(text, replacements)


def convert_for_combined(
    text: str, source: Path, root: Path, included_paths: set[Path], *,
    index: ContentIndex | None = None, tolerate_issues: bool = False,
) -> str:
    index = index or build_content_index(root)
    included = {path.resolve() for path in included_paths}
    replacements: list[tuple[LinkOccurrence, str]] = []
    for occurrence in scan_wikilinks(text, source):
        resolution = resolve_occurrence(index, occurrence)
        if resolution.ok and resolution.path is not None:
            if occurrence.embed and resolution.path.suffix.lower() in IMAGE_SUFFIXES:
                replacement = (
                    f"![{occurrence.label}]"
                    f"({resolution.path.relative_to(root).as_posix()})"
                )
            else:
                target_path = resolution.path
                target_heading = resolution.heading
                relative = target_path.relative_to(root)
                if (
                    relative.parts and relative.parts[0] == "references"
                    and target_path.name != "README.md"
                ):
                    target_path = root / "Literatur.md"
                    target_heading = resolution.path.stem
                if target_path.resolve() not in included:
                    replacement = occurrence.label
                else:
                    anchor = document_anchor(target_path.relative_to(root))
                    if target_heading:
                        anchor += "--" + slugify(target_heading)
                    replacement = f"[{occurrence.label}](#{anchor})"
        elif tolerate_issues:
            replacement = f"{occurrence.label} [{resolution.status}]"
        else:
            raise LinkError(resolution.message or f"Ungültiges Linkziel: {occurrence.raw}")
        replacements.append((occurrence, replacement))

    converted = _replace_occurrences(text, replacements)
    anchor_prefix = document_anchor(source.relative_to(root))
    output = [f"[]{{#{anchor_prefix}}}\n"]
    fence: FenceState | None = None
    for line in converted.splitlines(keepends=True):
        fence, is_fenced = advance_fence_state(line, fence)
        if is_fenced:
            output.append(line)
            continue
        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line.rstrip("\n"))
        if heading_match:
            level, heading_text = heading_match.groups()
            clean = re.sub(r"\s*\{#[-\w:.]+\}\s*$", "", heading_text)
            heading_id = f"{anchor_prefix}--{slugify(clean)}"
            newline = "\n" if line.endswith("\n") else ""
            output.append(f"{level} {clean} {{#{heading_id}}}{newline}")
        else:
            output.append(line)
    return "".join(output)
