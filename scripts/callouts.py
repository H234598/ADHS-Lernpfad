#!/usr/bin/env python3
"""Convert selected Obsidian callouts into MkDocs Material admonitions."""

from __future__ import annotations

import re

FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
CALLOUT_START_RE = re.compile(
    r"^(?P<indent>\s*)>\s*\[!(?P<kind>[A-Za-z0-9_-]+)\]"
    r"(?P<fold>[+-])?\s*(?P<title>.*?)\s*(?P<newline>\r?\n)?$"
)
CALLOUT_BODY_RE = re.compile(
    r"^(?P<indent>\s*)>\s?(?P<body>.*?)(?P<newline>\r?\n)?$"
)

CALLOUT_TYPES = {
    "evidence": "evidence",
    "important": "important",
    "warning": "warning",
    "info": "info",
    "note": "note",
}

DEFAULT_TITLES = {
    "evidence": "Evidenz",
    "important": "Wichtig",
    "warning": "Warnung",
    "info": "Hinweis",
    "note": "Hinweis",
}


def _quoted_title(title: str) -> str:
    """Escape an admonition title for Python-Markdown syntax."""

    return title.replace("\\", "\\\\").replace('"', '\\"')


def convert_obsidian_callouts_for_web(text: str) -> str:
    """Convert supported callout blockquotes outside fenced code blocks.

    Obsidian source files retain their native ``> [!type]`` syntax. Only the
    generated MkDocs sources receive ``!!!`` or collapsible ``???`` admonitions.
    Unsupported callout types remain untouched rather than being guessed.
    """

    lines = text.splitlines(keepends=True)
    output: list[str] = []
    fence: str | None = None
    index = 0

    while index < len(lines):
        line = lines[index]
        fence_match = FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)[0]
            fence = marker if fence is None else (None if fence == marker else fence)
            output.append(line)
            index += 1
            continue

        if fence is not None:
            output.append(line)
            index += 1
            continue

        callout_match = CALLOUT_START_RE.match(line)
        if not callout_match:
            output.append(line)
            index += 1
            continue

        source_kind = callout_match.group("kind").casefold()
        target_kind = CALLOUT_TYPES.get(source_kind)
        if target_kind is None:
            output.append(line)
            index += 1
            continue

        indent = callout_match.group("indent")
        title = callout_match.group("title").strip() or DEFAULT_TITLES[source_kind]
        fold = callout_match.group("fold")
        directive = "???+" if fold == "+" else ("???" if fold == "-" else "!!!")

        body: list[str] = []
        index += 1
        while index < len(lines):
            body_match = CALLOUT_BODY_RE.match(lines[index])
            if not body_match or body_match.group("indent") != indent:
                break
            body.append(body_match.group("body"))
            index += 1

        output.append(
            f'{indent}{directive} {target_kind} "{_quoted_title(title)}"\n'
        )
        if body:
            output.extend(f"{indent}    {body_line}\n" for body_line in body)
        else:
            output.append("\n")

    return "".join(output)
