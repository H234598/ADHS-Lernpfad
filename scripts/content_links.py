#!/usr/bin/env python3
"""Obsidian-Wikilinks für Web- und Export-Builds auflösen und validieren."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import unicodedata

WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]\n]+)\]\]")
EMBED_RE = re.compile(r"!\[\[([^\]\n]+)\]\]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(```+|~~~+)")

EXCLUDED_DIRS = {".git", "build", "site", "__pycache__"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif"}


class LinkError(ValueError):
    pass


@dataclass(frozen=True)
class LinkTarget:
    path: Path
    heading: str | None = None


def slugify(value: str) -> str:
    """Python-Markdown-kompatibler, ASCII-basierter Überschriften-Slug."""
    value = re.sub(r"\{#[-\w]+\}\s*$", "", value)
    value = re.sub(r"[`*_~]", "", value)
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")


def document_anchor(relative_path: Path) -> str:
    without_suffix = relative_path.with_suffix("").as_posix()
    return "doc-" + slugify(without_suffix)


def _is_inside_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def markdown_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if not any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts)
    )


def _split_link(raw: str) -> tuple[str, str | None, str | None]:
    if "|" in raw:
        target_raw, label = raw.split("|", 1)
        label = label.strip() or None
    else:
        target_raw, label = raw, None
    target_raw = target_raw.strip()
    if "#" in target_raw:
        target, heading = target_raw.split("#", 1)
        heading = heading.strip() or None
    else:
        target, heading = target_raw, None
    target = target.strip()
    if not label:
        label = heading or Path(target).stem or target
    return target, heading, label


def _candidate_paths(root: Path, source: Path, target: str) -> list[Path]:
    target_path = Path(target.replace("\\", "/"))
    if target_path.suffix.lower() == ".md":
        target_path = target_path.with_suffix("")

    bases = [root] if str(target).startswith("/") else [source.parent, root]
    candidates: list[Path] = []
    for base in bases:
        base_target = base / str(target_path).lstrip("/")
        candidates.extend(
            [
                base_target,
                base_target.with_suffix(".md"),
                base_target / "README.md",
            ]
        )
    return candidates


def _basename_matches(root: Path, target: str) -> list[Path]:
    normalized = Path(target).stem.casefold()
    return [
        path
        for path in markdown_files(root)
        if path.stem.casefold() == normalized
    ]


def resolve_target(root: Path, source: Path, target: str, heading: str | None = None) -> LinkTarget:
    if not target:
        target_path = source
    else:
        seen: set[Path] = set()
        matches: list[Path] = []
        for candidate in _candidate_paths(root, source, target):
            candidate = candidate.resolve()
            if candidate in seen or not _is_inside_root(candidate, root):
                continue
            seen.add(candidate)
            if candidate.is_file():
                matches.append(candidate)

        if not matches and "/" not in target and "\\" not in target:
            matches = _basename_matches(root, target)

        unique = sorted(set(matches))
        if not unique:
            raise LinkError(f"{source.relative_to(root)}: Ziel nicht gefunden: [[{target}]]")
        if len(unique) > 1:
            options = ", ".join(str(path.relative_to(root)) for path in unique)
            raise LinkError(
                f"{source.relative_to(root)}: mehrdeutiges Ziel [[{target}]]: {options}"
            )
        target_path = unique[0]

    if heading:
        headings = {
            slugify(match.group(2)): match.group(2)
            for line in target_path.read_text(encoding="utf-8").splitlines()
            if (match := HEADING_RE.match(line))
        }
        wanted = slugify(heading)
        if wanted not in headings:
            raise LinkError(
                f"{source.relative_to(root)}: Überschrift nicht gefunden: "
                f"[[{target}#{heading}]] in {target_path.relative_to(root)}"
            )

    return LinkTarget(target_path, heading)


def _relative_link(source: Path, target: Path) -> str:
    return Path(os.path.relpath(target, start=source.parent)).as_posix()


def _replace_outside_fences(text: str, replacer) -> str:
    output: list[str] = []
    fence: str | None = None
    for line in text.splitlines(keepends=True):
        fence_match = FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)[0]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            output.append(line)
            continue
        output.append(line if fence else replacer(line))
    return "".join(output)


def convert_for_web(text: str, source: Path, root: Path) -> str:
    """Wikilinks in relative Standard-Markdown-Links für MkDocs umwandeln."""

    def replace_line(line: str) -> str:
        def embed(match: re.Match[str]) -> str:
            target, heading, label = _split_link(match.group(1))
            resolved = resolve_target(root, source, target, heading)
            relative = _relative_link(source, resolved.path)
            if resolved.heading:
                relative += "#" + slugify(resolved.heading)
            if resolved.path.suffix.lower() in IMAGE_SUFFIXES:
                return f"![{label}]({relative})"
            return f"[{label}]({relative})"

        def link(match: re.Match[str]) -> str:
            target, heading, label = _split_link(match.group(1))
            resolved = resolve_target(root, source, target, heading)
            relative = _relative_link(source, resolved.path)
            if resolved.heading:
                relative += "#" + slugify(resolved.heading)
            return f"[{label}]({relative})"

        line = EMBED_RE.sub(embed, line)
        return WIKILINK_RE.sub(link, line)

    return _replace_outside_fences(text, replace_line)


def convert_for_combined(
    text: str,
    source: Path,
    root: Path,
    included_paths: set[Path],
) -> str:
    """Wikilinks in interne Pandoc-Anker des Gesamtdokuments umwandeln."""

    def combined_target(target: LinkTarget) -> tuple[Path, str | None]:
        path = target.path
        heading = target.heading
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] == "references" and path.name != "README.md":
            path = root / "Literatur.md"
            heading = target.path.stem
        return path, heading

    def replace_line(line: str) -> str:
        def replace(match: re.Match[str]) -> str:
            target_raw, heading, label = _split_link(match.group(1))
            resolved = resolve_target(root, source, target_raw, heading)
            target_path, target_heading = combined_target(resolved)
            if target_path.resolve() not in included_paths:
                return label or target_raw
            anchor = document_anchor(target_path.relative_to(root))
            if target_heading:
                anchor += "--" + slugify(target_heading)
            return f"[{label}](#{anchor})"

        line = EMBED_RE.sub(replace, line)
        return WIKILINK_RE.sub(replace, line)

    converted = _replace_outside_fences(text, replace_line)

    anchor_prefix = document_anchor(source.relative_to(root))
    output: list[str] = [f"[]{{#{anchor_prefix}}}\n"]
    fence: str | None = None
    for line in converted.splitlines(keepends=True):
        fence_match = FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)[0]
            fence = marker if fence is None else (None if fence == marker else fence)
            output.append(line)
            continue
        if fence is None and (heading_match := HEADING_RE.match(line.rstrip("\n"))):
            level, heading_text = heading_match.groups()
            heading_id = f"{anchor_prefix}--{slugify(heading_text)}"
            newline = "\n" if line.endswith("\n") else ""
            output.append(f"{level} {heading_text} {{#{heading_id}}}{newline}")
        else:
            output.append(line)
    return "".join(output)


def validate_all(root: Path) -> list[str]:
    errors: list[str] = []
    for source in markdown_files(root):
        text = source.read_text(encoding="utf-8")
        try:
            convert_for_web(text, source, root)
        except LinkError as exc:
            errors.append(str(exc))
    return errors
