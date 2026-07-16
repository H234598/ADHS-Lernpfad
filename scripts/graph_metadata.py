#!/usr/bin/env python3
"""Populate typed graph relations from links and YAML metadata."""

from __future__ import annotations

from content_links import LinkOccurrence, issue_for, resolve_occurrence
from content_model import Document, slugify
from graph_model import GraphBuilder, as_list


def _metadata_occurrence(
    document: Document, field: str, value: str,
) -> LinkOccurrence:
    return LinkOccurrence(
        document.path, f"{field}: {value}", value, None, value,
        False, 1, 1, 0, 0,
    )


def _append_link_issue(
    builder: GraphBuilder, occurrence: LinkOccurrence, resolution: object,
    field: str | None = None,
) -> None:
    issue = issue_for(builder.index, occurrence, resolution)
    if issue is not None:
        payload = issue.as_dict()
        if field:
            payload["field"] = field
        builder.issues.append(payload)


def add_link_occurrence(
    builder: GraphBuilder, document: Document, occurrence: LinkOccurrence,
) -> None:
    resolution = resolve_occurrence(builder.index, occurrence)
    target_id = builder.target_for_resolution(occurrence, resolution)
    builder.add_edge(
        "embed" if occurrence.embed else "wikilink",
        document.id, target_id, status=resolution.status,
        occurrence={
            "path": document.relative_path.as_posix(), "line": occurrence.line,
            "column": occurrence.column, "raw": occurrence.raw,
        },
    )
    _append_link_issue(builder, occurrence, resolution)


def add_prerequisites(builder: GraphBuilder, document: Document) -> None:
    for value in as_list(document.metadata.get("prerequisites")):
        occurrence = _metadata_occurrence(document, "prerequisites", value)
        resolution = resolve_occurrence(builder.index, occurrence)
        target_id = builder.target_for_resolution(occurrence, resolution)
        builder.add_edge(
            "prerequisite", target_id, document.id, status=resolution.status,
            occurrence={
                "path": document.relative_path.as_posix(),
                "field": "prerequisites", "value": value,
            },
        )
        _append_link_issue(builder, occurrence, resolution, "prerequisites")


def add_tags(builder: GraphBuilder, document: Document) -> None:
    for tag in as_list(document.metadata.get("tags")):
        glossary_target = builder.index.glossary_section(tag)
        if glossary_target:
            target_id = builder.add_section(*glossary_target)
        else:
            target_id = builder.add_node({
                "id": f"concept:{slugify(tag)}", "type": "concept",
                "label": tag, "scope": "concept", "exists": True,
                "planned": False,
            })
        builder.add_edge(
            "tagged_with", document.id, target_id,
            occurrence={
                "path": document.relative_path.as_posix(),
                "field": "tags", "value": tag,
            },
        )


def add_references(builder: GraphBuilder, document: Document) -> None:
    for reference_id in as_list(document.metadata.get("references")):
        matches = [
            candidate for candidate in builder.index.lookup_documents(reference_id)
            if candidate.type == "reference"
        ]
        if len(matches) == 1:
            target_id, status = matches[0].id, "ok"
        elif len(matches) > 1:
            candidates = [item.relative_path.as_posix() for item in matches]
            target_id = builder.add_placeholder("ambiguous", reference_id, candidates)
            status = "ambiguous"
            builder.add_issue(
                code="ambiguous-reference", severity="error",
                message=f"Mehrdeutige reference_id {reference_id}",
                path=document.relative_path.as_posix(), field="references",
                candidates=candidates,
            )
        else:
            target_id = builder.add_placeholder("missing-reference", reference_id)
            status = "missing-reference"
            builder.add_issue(
                code="missing-reference", severity="error",
                message=f"Unbekannte Studienkarte {reference_id}",
                path=document.relative_path.as_posix(), field="references",
            )
        builder.add_edge(
            "cites", document.id, target_id, status=status,
            occurrence={
                "path": document.relative_path.as_posix(),
                "field": "references", "value": reference_id,
            },
        )


def add_related(builder: GraphBuilder, document: Document) -> None:
    for value in as_list(document.metadata.get("related")):
        occurrence = _metadata_occurrence(document, "related", value)
        resolution = resolve_occurrence(builder.index, occurrence)
        target_id = builder.target_for_resolution(occurrence, resolution)
        builder.add_edge(
            "related", document.id, target_id, status=resolution.status,
            occurrence={
                "path": document.relative_path.as_posix(),
                "field": "related", "value": value,
            },
        )
        _append_link_issue(builder, occurrence, resolution, "related")
