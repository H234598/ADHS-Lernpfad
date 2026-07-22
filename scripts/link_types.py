#!/usr/bin/env python3
"""Typed Obsidian-link occurrences, resolutions and source scanning."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

from content_model import (
    Document, FenceState, PlannedNode, advance_fence_state, slugify,
)

WIKILINK_RE = re.compile(r"(?P<embed>!)?\[\[(?P<body>[^\]\n]+)\]\]")
ATX_HEADING_RE = re.compile(r"^ {0,3}#{1,6}(?:[ \t]+|$)")
BLOCK_PREFIX_RE = re.compile(
    r"^ {0,3}(?:>|(?:[-+*]|\d{1,9}[.)])[ \t]+|<!--)"
)
SETEXT_OR_RULE_RE = re.compile(r"^ {0,3}(?:=+[ \t]*|-{3,}[ \t]*)\r?\n?$")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif"}


class LinkError(ValueError):
    """A missing, ambiguous or malformed internal link."""


@dataclass(frozen=True)
class LinkTarget:
    path: Path
    heading: str | None = None


@dataclass(frozen=True)
class LinkOccurrence:
    source: Path
    raw: str
    target: str
    heading: str | None
    label: str
    embed: bool
    line: int
    column: int
    start: int
    end: int


@dataclass(frozen=True)
class Resolution:
    status: str
    target_id: str | None
    path: Path | None = None
    document: Document | None = None
    heading: str | None = None
    planned: PlannedNode | None = None
    candidates: tuple[str, ...] = ()
    message: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass(frozen=True)
class LinkIssue:
    code: str
    severity: str
    message: str
    path: str
    line: int
    column: int
    raw: str
    requested_target: str
    candidates: tuple[str, ...] = ()

    def format(self) -> str:
        candidates = (
            f"; Kandidaten: {', '.join(self.candidates)}"
            if self.candidates else ""
        )
        return f"{self.path}:{self.line}:{self.column}: {self.message}{candidates}"

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "raw": self.raw,
            "requested_target": self.requested_target,
        }
        if self.candidates:
            payload["candidates"] = list(self.candidates)
        return payload


def split_link(raw: str) -> tuple[str, str | None, str]:
    """Split an Obsidian target into document, heading and visible label."""

    if "|" in raw:
        target_raw, label_raw = raw.split("|", 1)
        label = label_raw.strip()
    else:
        target_raw, label = raw, ""
    target_raw = target_raw.strip()
    if "#" in target_raw:
        target, heading_raw = target_raw.split("#", 1)
        heading = heading_raw.strip() or None
    else:
        target, heading = target_raw, None
    target = target.strip()
    if not label:
        label = heading or Path(target).stem or target or "Link"
    return target, heading, label


def _mask_comments_and_inline_code(
    line: str,
    in_comment: bool,
    inline_ticks: int,
    following_text: str,
) -> tuple[str, bool, int]:
    """Mask comments and inline code while preserving source offsets."""

    chars = list(line)
    index = 0
    while index < len(chars):
        if in_comment:
            end = line.find("-->", index)
            if end == -1:
                for position in range(index, len(chars)):
                    if chars[position] != "\n":
                        chars[position] = " "
                return "".join(chars), True, inline_ticks
            for position in range(index, end + 3):
                if chars[position] != "\n":
                    chars[position] = " "
            index = end + 3
            in_comment = False
            continue
        if inline_ticks:
            if chars[index] == "`":
                run = 1
                while index + run < len(chars) and chars[index + run] == "`":
                    run += 1
                for position in range(index, index + run):
                    chars[position] = " "
                if run == inline_ticks:
                    inline_ticks = 0
                index += run
                continue
            if chars[index] != "\n":
                chars[index] = " "
            index += 1
            continue
        if line.startswith("<!--", index):
            in_comment = True
            continue
        if chars[index] == "`":
            run = 1
            while index + run < len(chars) and chars[index + run] == "`":
                run += 1
            future = line[index + run:] + following_text
            if any(len(match.group(0)) == run for match in re.finditer(r"`+", future)):
                for position in range(index, index + run):
                    chars[position] = " "
                inline_ticks = run
                index += run
                continue
            index += run
            continue
        index += 1
    return "".join(chars), in_comment, inline_ticks


def _inline_block_boundary(line: str) -> bool:
    """Whether a line starts a new block that an inline span cannot cross."""

    if not line.strip():
        return True
    if line.startswith("    ") or line.startswith("\t"):
        return True
    if ATX_HEADING_RE.match(line) or BLOCK_PREFIX_RE.match(line):
        return True
    if SETEXT_OR_RULE_RE.match(line):
        return True
    _, is_fenced = advance_fence_state(line, None)
    return is_fenced


def _inline_block_tail(lines: list[str], index: int) -> str:
    """Return only following text in the current Markdown inline block."""

    if _inline_block_boundary(lines[index]):
        return ""
    tail: list[str] = []
    for line in lines[index + 1:]:
        if _inline_block_boundary(line):
            break
        tail.append(line)
    return "".join(tail)


def scan_wikilinks(text: str, source: Path) -> list[LinkOccurrence]:
    """Find Wikilinks outside frontmatter, fences, comments and inline code."""

    frontmatter = re.match(
        r"\A---[ \t]*\n.*?\n---[ \t]*(?:\n|\Z)", text, re.S,
    )
    frontmatter_end = frontmatter.end() if frontmatter else 0
    occurrences: list[LinkOccurrence] = []
    lines = text.splitlines(keepends=True)
    fence: FenceState | None = None
    in_comment = False
    inline_ticks = 0
    offset = 0
    for line_index, line in enumerate(lines):
        line_number = line_index + 1
        line_end = offset + len(line)
        if line_end <= frontmatter_end:
            offset = line_end
            continue

        # While an HTML comment is open, fence-looking or indented text is
        # still comment content. Only update the comment state; a closing
        # marker may expose ordinary content later on the same line.
        if in_comment or inline_ticks:
            masked, in_comment, inline_ticks = _mask_comments_and_inline_code(
                line, in_comment, inline_ticks,
                _inline_block_tail(lines, line_index),
            )
            if in_comment or inline_ticks or line.startswith("    ") or line.startswith("\t"):
                offset = line_end
                continue
            for match in WIKILINK_RE.finditer(masked):
                target, heading, label = split_link(match.group("body"))
                occurrences.append(LinkOccurrence(
                    source, match.group(0), target, heading, label,
                    bool(match.group("embed")), line_number, match.start() + 1,
                    offset + match.start(), offset + match.end(),
                ))
            offset = line_end
            continue

        fence, is_fenced = advance_fence_state(line, fence)
        if is_fenced:
            offset = line_end
            continue
        # Indented Markdown code is literal source just like fenced and inline
        # code, and must not create links, graph edges, comment state or build
        # failures.
        if line.startswith("    ") or line.startswith("\t"):
            offset = line_end
            continue
        masked, in_comment, inline_ticks = _mask_comments_and_inline_code(
            line, False, 0, _inline_block_tail(lines, line_index),
        )
        for match in WIKILINK_RE.finditer(masked):
            target, heading, label = split_link(match.group("body"))
            occurrences.append(LinkOccurrence(
                source, match.group(0), target, heading, label,
                bool(match.group("embed")), line_number, match.start() + 1,
                offset + match.start(), offset + match.end(),
            ))
        offset = line_end
    return occurrences


def placeholder_id(status: str, requested_target: str) -> str:
    digest = hashlib.sha256(
        f"{status}\0{requested_target}".encode("utf-8")
    ).hexdigest()[:12]
    readable = slugify(requested_target)[:48] or "leer"
    return f"placeholder:{status}:{readable}:{digest}"
