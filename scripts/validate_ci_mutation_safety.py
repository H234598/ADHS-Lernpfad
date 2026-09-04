#!/usr/bin/env python3
"""Enforce safe Git writers, payload checks, and blocking audits in CI."""

import argparse
from pathlib import Path
import re
import sys
from typing import List, NamedTuple, Optional, Sequence, Tuple


class SafetyIssue(NamedTuple):
    """One actionable mutation-safety finding in a workflow file."""

    path: str
    line: int
    code: str
    message: str

    def render(self) -> str:
        """Render the finding in compiler-style path/line form."""

        return f"{self.path}:{self.line}: {self.code} {self.message}"


class StepBlock(NamedTuple):
    """One immediate list item below a GitHub Actions ``steps:`` key."""

    start_line: int
    end_line: int
    lines: Tuple[str, ...]

    @property
    def text(self) -> str:
        """Return the complete YAML text of the step."""

        return "\n".join(self.lines)

    def active_lines(self) -> List[Tuple[int, str]]:
        """Return non-comment lines with one-based line numbers."""

        result: List[Tuple[int, str]] = []
        for offset, line in enumerate(self.lines):
            if line.lstrip().startswith("#"):
                continue
            result.append((self.start_line + offset, line))
        return result


GIT_MUTATION = re.compile(r"\bgit\b[^\n#]*(?:\bcommit\b|\bpush\b)")
GIT_DIFF = re.compile(r"\bgit\b[^\n#]*\bdiff\b")
GIT_STATUS = re.compile(r"\bgit\b[^\n#]*\bstatus\b")
AUDIT = re.compile(r"\baudit(?:[:\w-]*)?\b", re.IGNORECASE)
AUDIT_FALLBACK = re.compile(
    r"\baudit(?:[:\w-]*)?\b[^#]*(?:\|\||;)\s*(?P<fallback>.+)$",
    re.IGNORECASE,
)
BLOCKING_AUDIT_FALLBACK = re.compile(
    r"^exit\s+[1-9][0-9]*\b",
    re.IGNORECASE,
)
CONTINUE_ON_ERROR = re.compile(
    r"(?mi)^\s*continue-on-error\s*:\s*(?P<value>[^#\r\n]+?)\s*(?:#.*)?$"
)
STEPS_HEADER = re.compile(r"^(?P<indent>\s*)steps\s*:\s*(?:#.*)?$")
LIST_ITEM = re.compile(r"^(?P<indent>\s*)-\s+")
RUN_BLOCK_HEADER = re.compile(
    r"^(?P<indent>\s*)(?P<item>-\s+)?run\s*:\s*"
    r"(?P<style>[|>])(?:[+-])?\s*(?:#.*)?$"
)
PAYLOAD_MARKER = re.compile(
    r"\.payload\.|payload\.(?:b64|tar(?:\.gz)?)|payload[_-]?checksum",
    re.IGNORECASE,
)
ACTUAL_ASSIGNMENT = re.compile(
    r"(?:actual|computed)(?:_payload)?_?checksum[^\n]*sha256sum",
    re.IGNORECASE,
)
ACTUAL_OUTPUT = re.compile(
    r"\b(?:echo|printf)\b[^\n]*"
    r"\$\{?(?:actual|computed)(?:_payload)?_?checksum\}?",
    re.IGNORECASE,
)
EXPECTED_VALUE = re.compile(
    r"expected(?:_payload)?_?checksum",
    re.IGNORECASE,
)
EXPECTED_OUTPUT = re.compile(
    r"\b(?:echo|printf)\b[^\n]*"
    r"\$\{?expected(?:_payload)?_?checksum\}?",
    re.IGNORECASE,
)
FRAGMENT_MARKER = re.compile(r"\bfragment\w*\b", re.IGNORECASE)
FRAGMENT_SIZE = re.compile(
    r"\bwc\s+-c\b|\bstat\b[^\n]*(?:%s|size)",
    re.IGNORECASE,
)
FRAGMENT_CHECKSUM = re.compile(
    r"sha256sum[^\n]*\$\{?fragment",
    re.IGNORECASE,
)
ARCHIVE_LISTING = re.compile(r"\btar\b[^\n]*-tzf")
CHECKSUM_COMPARISON = re.compile(
    r"(?:actual|computed)(?:_payload)?_?checksum"
    r"[^;\n]*(?:!=|-ne)[^;\n]*expected(?:_payload)?_?checksum"
    r"|expected(?:_payload)?_?checksum"
    r"[^;\n]*(?:!=|-ne)[^;\n]*(?:actual|computed)(?:_payload)?_?checksum",
    re.IGNORECASE,
)
IF_BLOCK = re.compile(
    r"\bif\b(?P<condition>.*?)\bthen\b(?P<body>.*?)\bfi\b",
    re.IGNORECASE | re.DOTALL,
)
NONZERO_EXIT = re.compile(r"\bexit\s+[1-9][0-9]*\b")
SHELL_OPERATOR_END = re.compile(r"(?:\|\||&&|;)\s*$")


def workflow_files(root: Path) -> List[Path]:
    """Return YAML workflows below ``.github/workflows``."""

    directory = root / ".github" / "workflows"
    if not directory.is_dir():
        return []
    files = list(directory.glob("*.yml"))
    files.extend(directory.glob("*.yaml"))
    return sorted(files)


def indentation(line: str) -> int:
    """Return the number of leading whitespace characters."""

    return len(line) - len(line.lstrip())


def _yaml_noise(line: str) -> bool:
    """Return whether a YAML line is blank or comment-only."""

    return not line.strip() or line.lstrip().startswith("#")


def _step_block_end(
    lines: Sequence[str],
    start: int,
    steps_indent: int,
    item_indent: int,
) -> int:
    """Return the exclusive end index of one immediate step list item."""

    index = start + 1
    while index < len(lines):
        candidate = lines[index]
        if _yaml_noise(candidate):
            index += 1
            continue
        if indentation(candidate) <= steps_indent:
            break
        item = LIST_ITEM.match(candidate)
        if item and len(item.group("indent")) == item_indent:
            break
        index += 1
    return index


def _steps_section(
    lines: Sequence[str],
    header_index: int,
    steps_indent: int,
) -> Tuple[List[StepBlock], int]:
    """Parse immediate step items following one ``steps:`` header."""

    blocks: List[StepBlock] = []
    item_indent: Optional[int] = None
    index = header_index + 1
    while index < len(lines):
        line = lines[index]
        if _yaml_noise(line):
            index += 1
            continue
        if indentation(line) <= steps_indent:
            break

        item = LIST_ITEM.match(line)
        if not item:
            index += 1
            continue
        current_indent = len(item.group("indent"))
        if item_indent is None:
            item_indent = current_indent
        if current_indent != item_indent:
            index += 1
            continue

        end = _step_block_end(lines, index, steps_indent, item_indent)
        blocks.append(StepBlock(index + 1, end, tuple(lines[index:end])))
        index = end
    return blocks, index


def workflow_step_blocks(text: str) -> List[StepBlock]:
    """Extract immediate list items below every workflow ``steps:`` key."""

    lines = text.splitlines()
    blocks: List[StepBlock] = []
    index = 0
    while index < len(lines):
        header = STEPS_HEADER.match(lines[index])
        if not header:
            index += 1
            continue
        section, index = _steps_section(
            lines,
            index,
            len(header.group("indent")),
        )
        blocks.extend(section)
    return blocks


def staged_diff(line: str, quiet: bool) -> bool:
    """Return whether ``line`` contains the required staged diff form."""

    has_diff = bool(GIT_DIFF.search(line))
    is_staged = "--cached" in line or "--staged" in line
    has_quiet = "--quiet" in line
    return has_diff and is_staged and (has_quiet is quiet)


def _normalize_shell_lines(
    numbered_lines: Sequence[Tuple[int, str]],
    *,
    join_operators: bool,
) -> List[Tuple[int, str]]:
    """Join shell continuations while preserving the first physical line."""

    result: List[Tuple[int, str]] = []
    buffer = ""
    start_line = 1
    for number, line in numbered_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if not buffer:
            start_line = number
        continuation = stripped.endswith("\\")
        if continuation:
            stripped = stripped[:-1].rstrip()
        buffer = f"{buffer} {stripped}".strip()
        operator_continuation = join_operators and bool(
            SHELL_OPERATOR_END.search(stripped)
        )
        if continuation or operator_continuation:
            continue
        result.append((start_line, buffer))
        buffer = ""
    if buffer:
        result.append((start_line, buffer))
    return result


def _run_block(step: StepBlock) -> Tuple[Optional[str], List[Tuple[int, str]]]:
    """Return block-scalar style and physical shell lines for one step."""

    numbered = list(enumerate(step.lines, step.start_line))
    for index, (number, line) in enumerate(numbered):
        match = RUN_BLOCK_HEADER.match(line)
        if not match:
            continue
        header_indent = len(match.group("indent")) + len(match.group("item") or "")
        body: List[Tuple[int, str]] = []
        for body_number, candidate in numbered[index + 1 :]:
            if candidate.strip() and indentation(candidate) <= header_indent:
                break
            if candidate.lstrip().startswith("#"):
                continue
            body.append((body_number, candidate))
        return match.group("style"), body
    return None, []


def _folded_shell_lines(
    numbered_lines: Sequence[Tuple[int, str]],
) -> List[Tuple[int, str]]:
    """Conservatively fold YAML ``run: >`` content into logical commands."""

    result: List[Tuple[int, str]] = []
    buffer: List[str] = []
    start_line = 1
    for number, line in numbered_lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                result.append((start_line, " ".join(buffer)))
                buffer = []
            continue
        if not buffer:
            start_line = number
        buffer.append(stripped)
    if buffer:
        result.append((start_line, " ".join(buffer)))
    return result


def logical_shell_lines(step: StepBlock) -> List[Tuple[int, str]]:
    """Normalize YAML block style and shell continuations for one step."""

    style, body = _run_block(step)
    if style == ">":
        return _folded_shell_lines(body)
    if style == "|":
        return _normalize_shell_lines(body, join_operators=True)
    return _normalize_shell_lines(step.active_lines(), join_operators=True)


def logical_workflow_lines(text: str) -> List[Tuple[int, str]]:
    """Normalize physical continuations for whole-workflow mutation detection."""

    numbered = [
        (number, line)
        for number, line in enumerate(text.splitlines(), 1)
        if not line.lstrip().startswith("#")
    ]
    return _normalize_shell_lines(numbered, join_operators=False)


def writer_issues(step: StepBlock, path: str) -> List[SafetyIssue]:
    """Validate one Git-writing workflow step."""

    logical = logical_shell_lines(step)
    mutations = [number for number, line in logical if GIT_MUTATION.search(line)]
    if not mutations:
        return []

    lines = [line for _, line in logical]
    anchor = mutations[0]
    has_status = any(
        GIT_STATUS.search(line) and ("--short" in line or "--porcelain" in line)
        for line in lines
    )
    has_staged_diagnostic = any(
        staged_diff(line, False) and ("--name-status" in line or "--stat" in line)
        for line in lines
    )

    issues: List[SafetyIssue] = []
    if not any(staged_diff(line, True) for line in lines):
        issues.append(
            SafetyIssue(
                path,
                anchor,
                "CIW001",
                "Git-Writer braucht einen staged No-op-Guard mit --quiet.",
            )
        )
    if not has_status:
        issues.append(
            SafetyIssue(
                path,
                anchor,
                "CIW002",
                "Git-Writer muss git status --short/--porcelain ausgeben.",
            )
        )
    if not has_staged_diagnostic:
        issues.append(
            SafetyIssue(
                path,
                anchor,
                "CIW003",
                "Git-Writer muss staged --name-status/--stat ausgeben.",
            )
        )
    return issues


def checksum_line(step: StepBlock) -> int:
    """Return the first line containing ``sha256sum`` in a step."""

    for number, line in step.active_lines():
        if "sha256sum" in line:
            return number
    return step.start_line


def _active_step_text(step: StepBlock) -> str:
    """Return non-comment step text for semantic shell checks."""

    return "\n".join(line for _, line in step.active_lines())


def checksum_mismatch_fails_closed(text: str) -> bool:
    """Return whether an actual/expected mismatch branch exits nonzero."""

    for block in IF_BLOCK.finditer(text):
        condition = block.group("condition")
        if not CHECKSUM_COMPARISON.search(condition):
            continue
        if NONZERO_EXIT.search(block.group("body")):
            return True
    return False


def payload_issues(step: StepBlock, path: str) -> List[SafetyIssue]:
    """Validate transparent and enforced payload verification."""

    text = _active_step_text(step)
    if not PAYLOAD_MARKER.search(text) or "sha256sum" not in text.lower():
        return []

    line = checksum_line(step)
    actual = bool(ACTUAL_ASSIGNMENT.search(text) and ACTUAL_OUTPUT.search(text))
    expected = bool(EXPECTED_VALUE.search(text) and EXPECTED_OUTPUT.search(text))
    fragment_marker = bool(FRAGMENT_MARKER.search(text))
    fragment_size = bool(FRAGMENT_SIZE.search(text))
    fragment_checksum = bool(FRAGMENT_CHECKSUM.search(text))
    fragments = fragment_marker and fragment_size and fragment_checksum
    archive = bool(ARCHIVE_LISTING.search(text))
    enforced = checksum_mismatch_fails_closed(text)

    issues: List[SafetyIssue] = []
    if not actual:
        issues.append(
            SafetyIssue(
                path,
                line,
                "CIW004",
                "Payload muss die berechnete SHA-256 ausgeben.",
            )
        )
    if not expected:
        issues.append(
            SafetyIssue(
                path,
                line,
                "CIW005",
                "Payload muss die erwartete SHA-256 ausgeben.",
            )
        )
    if not fragments:
        issues.append(
            SafetyIssue(
                path,
                line,
                "CIW006",
                "Payload muss Größe und SHA-256 jedes Fragments ausgeben.",
            )
        )
    if not archive:
        issues.append(
            SafetyIssue(
                path,
                line,
                "CIW007",
                "Payload-Fehler braucht eine tar -tzf-Diagnose.",
            )
        )
    if not enforced:
        issues.append(
            SafetyIssue(
                path,
                line,
                "CIW010",
                "Prüfsummenabweichungen müssen mit Fehlercode enden.",
            )
        )
    return issues


def audit_fallback_masks_failure(line: str) -> bool:
    """Return whether a fallback can replace a failed audit exit status."""

    fallback = AUDIT_FALLBACK.search(line)
    if not fallback:
        return False
    command = fallback.group("fallback").strip()
    return not BLOCKING_AUDIT_FALLBACK.match(command)


def continue_on_error_masks_failure(step: StepBlock) -> bool:
    """Accept only an explicit YAML ``false`` for audit continue-on-error."""

    matches = list(CONTINUE_ON_ERROR.finditer(step.text))
    if not matches:
        return False
    return any(match.group("value").strip().lower() != "false" for match in matches)


def audit_issues(step: StepBlock, path: str) -> List[SafetyIssue]:
    """Reject attempts to soften an audit failure."""

    issues: List[SafetyIssue] = []
    for number, line in logical_shell_lines(step):
        if audit_fallback_masks_failure(line):
            issues.append(
                SafetyIssue(
                    path,
                    number,
                    "CIW008",
                    "Audit darf nicht per Shell-Bypass entkräftet werden.",
                )
            )
    if AUDIT.search(_active_step_text(step)) and continue_on_error_masks_failure(step):
        issues.append(
            SafetyIssue(
                path,
                step.start_line,
                "CIW009",
                "Audit-Schritt darf continue-on-error nicht aktivieren.",
            )
        )
    return issues


def validate_step(step: StepBlock, path: str) -> List[SafetyIssue]:
    """Validate one workflow step against Variant B."""

    issues = writer_issues(step, path)
    issues.extend(payload_issues(step, path))
    issues.extend(audit_issues(step, path))
    return issues


def validate_workflow(path: Path, root: Path) -> List[SafetyIssue]:
    """Validate one workflow file."""

    text = path.read_text(encoding="utf-8")
    relative = path.relative_to(root).as_posix()
    steps = workflow_step_blocks(text)
    issues: List[SafetyIssue] = []
    covered = set()
    for step in steps:
        issues.extend(validate_step(step, relative))
        covered.update(range(step.start_line, step.end_line + 1))

    for number, line in logical_workflow_lines(text):
        if number in covered or not GIT_MUTATION.search(line):
            continue
        issues.append(
            SafetyIssue(
                relative,
                number,
                "CIW011",
                "Git-Mutation liegt außerhalb eines analysierbaren Schritts.",
            )
        )
    return issues


def validate_repository(root: Path) -> List[SafetyIssue]:
    """Validate every workflow in ``root``."""

    resolved = root.resolve()
    issues: List[SafetyIssue] = []
    for workflow in workflow_files(resolved):
        issues.extend(validate_workflow(workflow, resolved))
    return sorted(issues)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the command-line validator."""

    parser = argparse.ArgumentParser(
        description="Prüft GitHub-Actions-Workflows auf Variante-B-Sicherheit."
    )
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    root = parser.parse_args(argv).root.resolve()
    issues = validate_repository(root)
    if issues:
        for issue in issues:
            print(issue.render(), file=sys.stderr)
        print(
            f"CI-Mutationssicherheit: {len(issues)} Problem(e).",
            file=sys.stderr,
        )
        return 1
    count = len(workflow_files(root))
    print(f"CI-Mutationssicherheit: OK ({count} Workflows geprüft).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
