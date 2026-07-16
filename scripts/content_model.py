#!/usr/bin/env python3
"""Canonical data types and stable identifiers for project content."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

EXCLUDED_DIRS = {
    ".git", ".venv", "build", "node_modules", "site", "__pycache__",
}
FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.S)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
EXPLICIT_ID_RE = re.compile(r"\s*\{#([-\w:.]+)\}\s*$")
ATTR_LIST_RE = re.compile(r"\s*\{[^{}]+\}\s*$")


def slugify(value: str) -> str:
    value = ATTR_LIST_RE.sub("", value)
    value = re.sub(r"[`*_~]", "", value)
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")


def document_anchor(relative_path: Path) -> str:
    return "doc-" + slugify(relative_path.with_suffix("").as_posix())


def canonical_document_path(relative_path: Path) -> str:
    path = relative_path.as_posix().lstrip("/")
    return path[:-3] if path.lower().endswith(".md") else path


def markdown_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if not any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts)
    )


def json_compatible(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {
            str(key): json_compatible(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple, set)):
        return [json_compatible(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def normalize_key(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


@dataclass(frozen=True)
class Heading:
    title: str
    anchor: str
    level: int
    line: int


@dataclass(frozen=True)
class Document:
    path: Path
    relative_path: Path
    id: str
    title: str
    aliases: tuple[str, ...]
    metadata: dict[str, Any]
    headings: tuple[Heading, ...]
    type: str
    scope: str
    url: str
    raw_text: str = field(repr=False)
    body_start_line: int = 1

    @property
    def path_without_suffix(self) -> str:
        return canonical_document_path(self.relative_path)

    @property
    def stem(self) -> str:
        return self.relative_path.stem

    @property
    def reference_id(self) -> str | None:
        value = self.metadata.get("reference_id")
        return str(value) if value else None


@dataclass(frozen=True)
class PlannedNode:
    id: str
    path: str
    title: str
    type: str
    scope: str
    level: str | None = None
    roadmap: str | None = None
    reason: str | None = None
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModelIssue:
    code: str
    severity: str
    message: str
    path: str | None = None
    line: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "code": self.code,
                "severity": self.severity,
                "message": self.message,
                "path": self.path,
                "line": self.line,
            }.items()
            if value is not None
        }


@dataclass
class ContentIndex:
    root: Path
    documents: dict[str, Document]
    planned_nodes: dict[str, PlannedNode]
    model_issues: list[ModelIssue]
    chapter_ids: list[str]
    by_relative_path: dict[str, str] = field(default_factory=dict)
    lookup: dict[str, set[str]] = field(default_factory=dict)
    planned_lookup: dict[str, set[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.by_relative_path or self.lookup or self.planned_lookup:
            return
        for document_id, document in self.documents.items():
            relative = document.relative_path.as_posix()
            without_suffix = canonical_document_path(document.relative_path)
            self.by_relative_path[relative.casefold()] = document_id
            self.by_relative_path[without_suffix.casefold()] = document_id
            keys = {
                document.title, document.stem, relative, without_suffix,
                document_id, *document.aliases,
            }
            for key in keys:
                self.lookup.setdefault(normalize_key(key), set()).add(document_id)
            if document.reference_id:
                self.lookup.setdefault(
                    normalize_key(document.reference_id), set()
                ).add(document_id)
        for planned_id, planned in self.planned_nodes.items():
            keys = {
                planned.path, Path(planned.path).stem, planned.title,
                planned_id, *planned.aliases,
            }
            for key in keys:
                self.planned_lookup.setdefault(
                    normalize_key(key), set()
                ).add(planned_id)

    def document_for_path(self, path: Path) -> Document | None:
        try:
            relative = path.resolve().relative_to(self.root.resolve())
        except ValueError:
            relative = path
        document_id = self.by_relative_path.get(relative.as_posix().casefold())
        return self.documents.get(document_id) if document_id else None

    def lookup_documents(self, key: str) -> list[Document]:
        return [
            self.documents[item]
            for item in sorted(self.lookup.get(normalize_key(key), set()))
        ]

    def lookup_planned(self, key: str) -> list[PlannedNode]:
        return [
            self.planned_nodes[item]
            for item in sorted(self.planned_lookup.get(normalize_key(key), set()))
        ]

    def glossary_section(self, label: str) -> tuple[Document, Heading] | None:
        glossary = next(
            (doc for doc in self.documents.values() if doc.type == "glossary"), None
        )
        if glossary is None:
            return None
        matches = [
            heading for heading in glossary.headings
            if heading.anchor == slugify(label)
        ]
        return (glossary, matches[0]) if len(matches) == 1 else None


# Lazy compatibility import for existing callers.
def build_content_index(root: Path) -> ContentIndex:
    from content_index import build_content_index as build
    return build(root)
