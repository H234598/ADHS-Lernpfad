#!/usr/bin/env python3
"""Parse Markdown, YAML, headings, index.json and planned-node metadata."""

from __future__ import annotations

from collections.abc import Iterable
import json
from pathlib import Path
import re
from typing import Any

import yaml

from content_model import (
    ContentIndex, Document, EXPLICIT_ID_RE, FRONTMATTER_RE, HEADING_RE,
    FenceState, Heading, ModelIssue, advance_fence_state,
    canonical_document_path, json_compatible, markdown_files, slugify,
)


def _as_string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, Iterable) and not isinstance(value, (dict, bytes)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return (str(value).strip(),)


def split_frontmatter(
    text: str,
) -> tuple[dict[str, Any], str, int, list[ModelIssue]]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text, 1, []
    issues: list[ModelIssue] = []
    try:
        loaded = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        issues.append(ModelIssue(
            "invalid-frontmatter", "error",
            f"Ungültiges YAML-Frontmatter: {str(exc).splitlines()[0]}", line=1,
        ))
        loaded = {}
    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        issues.append(ModelIssue(
            "invalid-frontmatter-type", "error",
            "YAML-Frontmatter muss ein Mapping sein", line=1,
        ))
        loaded = {}
    body_start = text[: match.end()].count("\n") + 1
    return json_compatible(loaded), text[match.end():], body_start, issues


def _strip_heading_markup(value: str) -> tuple[str, str | None]:
    explicit = EXPLICIT_ID_RE.search(value)
    explicit_id = explicit.group(1) if explicit else None
    if explicit:
        value = value[: explicit.start()]
    value = re.sub(r"\s+#+\s*$", "", value).strip()
    return re.sub(r"[`*_~]", "", value).strip(), explicit_id


def parse_headings(
    body: str, body_start_line: int,
) -> tuple[list[Heading], list[ModelIssue]]:
    headings: list[Heading] = []
    issues: list[ModelIssue] = []
    fence: FenceState | None = None
    seen: dict[str, Heading] = {}
    for offset, line in enumerate(body.splitlines()):
        fence, is_fenced = advance_fence_state(line, fence)
        if is_fenced:
            continue
        match = HEADING_RE.match(line)
        if not match:
            continue
        level, raw_title = match.groups()
        title, explicit_id = _strip_heading_markup(raw_title)
        anchor = explicit_id or slugify(title)
        heading = Heading(title, anchor, len(level), body_start_line + offset)
        if anchor in seen:
            issues.append(ModelIssue(
                "duplicate-heading-anchor", "error",
                f"Doppelter Überschriftenanker #{anchor}: "
                f"Zeilen {seen[anchor].line} und {heading.line}",
                line=heading.line,
            ))
        else:
            seen[anchor] = heading
        headings.append(heading)
    return headings, issues


def classify_document(path: Path, metadata: dict[str, Any]) -> tuple[str, str]:
    parts, name = path.parts, path.name
    if parts and parts[0] == "references" and name != "README.md":
        return "reference", "reference"
    if name == "Glossar.md":
        return "glossary", "learning"
    if name == "00-Einfuehrung.md":
        return "intro", "learning"
    if parts and re.match(r"^\d{2}-", parts[0]) and metadata.get("level"):
        return "chapter", "learning"
    if parts and parts[0] in {".github", "prompts", "Sync"}:
        return "technical", "technical"
    if name in {
        "TECHNISCHE_ROADMAP.md", "WARTUNG.md", "CONTRIBUTING.md", "CHANGELOG.md",
    }:
        return "technical", "technical"
    learning = {"README.md", "ROADMAP.md", "Literatur.md", "DOWNLOADS.md"}
    return "document", "learning" if name in learning else "support"


def document_url(path: Path) -> str:
    if path.name == "README.md":
        parent = path.parent.as_posix()
        return "/" if parent == "." else f"/{parent.strip('/')}/"
    return "/" + canonical_document_path(path).strip("/") + "/"


def document_id(path: Path, metadata: dict[str, Any]) -> str:
    if path.parts and path.parts[0] == "references" and path.name != "README.md":
        return f"ref:{metadata.get('reference_id') or path.stem}"
    return "doc:" + canonical_document_path(path)


def _chapter_order(
    root: Path, documents: dict[str, Document],
) -> tuple[list[str], list[ModelIssue]]:
    path = root / "index.json"
    if not path.exists():
        return [], []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [], [ModelIssue(
            "invalid-index-json", "error",
            f"index.json kann nicht gelesen werden: {exc}", "index.json",
        )]
    by_path = {doc.relative_path.as_posix(): doc.id for doc in documents.values()}
    ids: list[str] = []
    issues: list[ModelIssue] = []
    for entry in payload.get("chapters", []):
        target = str(entry.get("path", ""))
        if target in by_path:
            ids.append(by_path[target])
        elif target:
            issues.append(ModelIssue(
                "missing-index-document", "error",
                f"index.json verweist auf fehlende Datei: {target}", "index.json",
            ))
    return ids, issues


def build_content_index(root: Path) -> ContentIndex:
    from planned_nodes import load_planned_nodes

    root = root.resolve()
    documents: dict[str, Document] = {}
    issues: list[ModelIssue] = []
    for path in markdown_files(root):
        relative = path.relative_to(root)
        raw = path.read_text(encoding="utf-8")
        metadata, body, body_start, frontmatter_issues = split_frontmatter(raw)
        headings, heading_issues = parse_headings(body, body_start)
        for issue in [*frontmatter_issues, *heading_issues]:
            issues.append(ModelIssue(
                issue.code, issue.severity, issue.message,
                relative.as_posix(), issue.line,
            ))
        doc_type, scope = classify_document(relative, metadata)
        doc_id = document_id(relative, metadata)
        title = str(
            metadata.get("title")
            or next((heading.title for heading in headings if heading.level == 1), None)
            or relative.stem
        )
        document = Document(
            path, relative, doc_id, title, _as_string_tuple(metadata.get("aliases")),
            metadata, tuple(headings), doc_type, scope, document_url(relative), raw,
            body_start,
        )
        if doc_id in documents:
            issues.append(ModelIssue(
                "duplicate-document-id", "error",
                f"Doppelte kanonische Dokument-ID: {doc_id}", relative.as_posix(),
            ))
        documents[doc_id] = document
    planned, planned_issues = load_planned_nodes(root)
    issues.extend(planned_issues)
    actual_paths = {doc.path_without_suffix.casefold() for doc in documents.values()}
    for node in planned.values():
        if node.path.casefold() in actual_paths:
            issues.append(ModelIssue(
                "stale-planned-node", "error",
                f"Geplanter Knoten existiert bereits als Datei: {node.path}",
                "knowledge-graph/planned-nodes.yaml",
            ))
    chapters, index_issues = _chapter_order(root, documents)
    issues.extend(index_issues)
    return ContentIndex(root, documents, planned, issues, chapters)
