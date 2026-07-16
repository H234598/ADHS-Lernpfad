#!/usr/bin/env python3
"""Public compatibility API for shared content-link processing."""

from content_model import (
    ContentIndex, build_content_index, document_anchor, markdown_files, slugify,
)
from link_converters import convert_for_combined, convert_for_web
from link_resolution import resolve_occurrence
from link_validation import analyze_all, issue_for, resolve_target, validate_all
from link_types import (
    IMAGE_SUFFIXES, LinkError, LinkIssue, LinkOccurrence, LinkTarget, Resolution,
    placeholder_id, scan_wikilinks,
)

__all__ = [
    "ContentIndex", "IMAGE_SUFFIXES", "LinkError", "LinkIssue",
    "LinkOccurrence", "LinkTarget", "Resolution", "analyze_all",
    "build_content_index", "convert_for_combined", "convert_for_web",
    "document_anchor", "issue_for", "markdown_files", "placeholder_id",
    "resolve_occurrence", "resolve_target", "scan_wikilinks", "slugify",
    "validate_all",
]
