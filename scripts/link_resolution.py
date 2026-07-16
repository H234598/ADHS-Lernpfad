#!/usr/bin/env python3
"""Resolve indexed internal targets without guessing."""

from __future__ import annotations

from pathlib import Path
import re

from content_model import (
    ContentIndex, Document, PlannedNode, build_content_index,
    canonical_document_path, slugify,
)
from link_types import (
    LinkError, LinkIssue, LinkOccurrence, LinkTarget, Resolution,
    scan_wikilinks,
)


def _inside_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _candidate_paths(
    index: ContentIndex, source: Path, target: str,
) -> tuple[list[Path], bool]:
    normalized = target.replace("\\", "/")
    target_path = Path(normalized)
    roots = [index.root] if normalized.startswith("/") else [source.parent, index.root]
    candidates: list[Path] = []
    escaped = False
    for base in roots:
        base_target = base / normalized.lstrip("/")
        if target_path.suffix and target_path.suffix.lower() != ".md":
            possible = [base_target]
        else:
            if base_target.suffix.lower() == ".md":
                base_target = base_target.with_suffix("")
            possible = [
                base_target, base_target.with_suffix(".md"),
                base_target / "README.md",
            ]
        for candidate in possible:
            resolved = candidate.resolve()
            if not _inside_root(resolved, index.root):
                escaped = True
                continue
            if resolved.is_file() and resolved not in candidates:
                candidates.append(resolved)
    return candidates, escaped


def _planned_candidates(
    index: ContentIndex, source: Path, target: str,
) -> list[PlannedNode]:
    normalized = canonical_document_path(Path(target.replace("\\", "/")))
    try:
        source_relative = source.resolve().relative_to(index.root)
    except ValueError:
        source_relative = source
    values = [normalized.lstrip("/")]
    if not target.startswith("/"):
        values.insert(0, canonical_document_path(source_relative.parent / normalized))
    matches: dict[str, PlannedNode] = {}
    for value in values:
        for planned in index.lookup_planned(value):
            matches[planned.id] = planned
    return [matches[key] for key in sorted(matches)]


def _asset_id(path: Path, root: Path) -> str:
    return "asset:" + path.resolve().relative_to(root.resolve()).as_posix()


def _section_id(document: Document, anchor: str) -> str:
    return f"section:{document.id}#{anchor}"


def resolve_occurrence(
    index: ContentIndex, occurrence: LinkOccurrence,
) -> Resolution:
    target = occurrence.target.strip()
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", target):
        return Resolution(
            "malformed", None,
            message=f"Wikilink darf kein externes URL-Ziel enthalten: {occurrence.raw}",
        )
    if not target:
        source_document = index.document_for_path(occurrence.source)
        if source_document is None:
            return Resolution(
                "missing-document", None, message="Quelldokument ist nicht indexiert",
            )
        documents, assets, escaped = [source_document], [], False
    else:
        direct, escaped = _candidate_paths(index, occurrence.source, target)
        documents: list[Document] = []
        assets: list[Path] = []
        for candidate in direct:
            document = index.document_for_path(candidate)
            if document is not None:
                documents.append(document)
            else:
                assets.append(candidate)
        if not documents and not assets:
            documents = index.lookup_documents(target)
    document_map = {document.id: document for document in documents}
    asset_map = {path.resolve(): path for path in assets}
    candidates = [
        *[doc.relative_path.as_posix() for doc in document_map.values()],
        *[path.resolve().relative_to(index.root).as_posix() for path in asset_map.values()],
    ]
    if len(document_map) + len(asset_map) > 1:
        return Resolution(
            "ambiguous", None, candidates=tuple(sorted(candidates)),
            message=f"Mehrdeutiges Ziel {occurrence.raw}",
        )
    if asset_map:
        path = next(iter(asset_map.values()))
        if occurrence.heading:
            return Resolution(
                "missing-heading", _asset_id(path, index.root), path=path,
                message=f"Nicht-Markdown-Ziel besitzt keine Überschrift: {occurrence.raw}",
            )
        return Resolution("ok", _asset_id(path, index.root), path=path)
    if document_map:
        document = next(iter(document_map.values()))
        if occurrence.heading:
            wanted = slugify(occurrence.heading)
            headings = [item for item in document.headings if item.anchor == wanted]
            if len(headings) != 1:
                return Resolution(
                    "missing-heading", document.id, path=document.path,
                    document=document, heading=occurrence.heading,
                    message=(f"Überschrift nicht gefunden: {occurrence.raw} in "
                             f"{document.relative_path.as_posix()}"),
                )
            return Resolution(
                "ok", _section_id(document, headings[0].anchor),
                path=document.path, document=document, heading=headings[0].title,
            )
        return Resolution("ok", document.id, path=document.path, document=document)
    planned = _planned_candidates(index, occurrence.source, target) if target else []
    if not planned:
        planned = index.lookup_planned(target)
    planned_map = {item.id: item for item in planned}
    if len(planned_map) > 1:
        return Resolution(
            "ambiguous", None,
            candidates=tuple(sorted(item.path for item in planned_map.values())),
            message=f"Mehrdeutiges geplantes Ziel {occurrence.raw}",
        )
    if planned_map:
        item = next(iter(planned_map.values()))
        if occurrence.heading:
            return Resolution(
                "missing-heading", item.id, planned=item,
                heading=occurrence.heading,
                message=f"Geplante Seite besitzt noch keine prüfbare Überschrift: {occurrence.raw}",
            )
        return Resolution(
            "planned", item.id, planned=item,
            message=f"Geplantes, noch nicht vorhandenes Ziel: {occurrence.raw}",
        )
    if escaped:
        return Resolution(
            "malformed", None,
            message=f"Linkziel verlässt die Repositorywurzel: {occurrence.raw}",
        )
    return Resolution(
        "missing-document", None, message=f"Ziel nicht gefunden: {occurrence.raw}",
    )
