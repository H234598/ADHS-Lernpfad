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
AUDIT_BYPASS = re.compile(
    r"\baudit(?:[:\w-]*)?\b[^#]*(?:\|\||;)\s*(?:true|:)(?:\s|$)",
    re.IGNORECASE,
)
CONTINUE_ON_ERROR = re.compile(
    r"(?mi)^\s*continue-on-error\s*:\s*true\s*(?:#.*)?$"
)
STEPS_HEADER = re.compile(r"^(?P<indent>\s*)steps\s*:\s*(?:#.*)?$")
LIST_ITEM = re.compile(r"^(?P<indent>\s*)-\s+")
PAYLOAD_MARKER = re.compile(
    r"\.payload\.|payload\.(?:b64|tar(?:\.gz)?)|payload[_-]?checksum",
    re.IGNORECASE,
)
ACTUAL_ASSIGNMENT = re.compile(
    r"(?:actual|computed)(?:_payload)?_?checksum[^\n]*sha256sum",
    re.IGNORECASE,
)
ACTUAL_OUTPUT = re.compile(
    r"(?:computed|actual)[^\n]*payload[^\n]*checksum",
    re.IGNORECASE,
)
EXPECTED_VALUE = re.compile(
    r"expected(?:_payload)?_?checksum",
    re.IGNORECASE,
)
EXPECTED_OUTPUT = re.compile(
    r"expected[^\n]*payload[^\n]*checksum",
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
    r"(?:\[\[?|\btest\b)[^\n]*(?:actual|computed)(?:_payload)?_?checksum"
    r"[^\n]*(?:==|!=|-eq|-ne)[^\n]*expected(?:_payload)?_?checksum"
    r"|(?:\[\[?|\btest\b)[^\n]*expected(?:_payload)?_?checksum"
    r"[^\n]*(?:==|!=|-eq|-ne)[^\n]*(?:actual|computed)(?:_payload)?_?checksum",
    re.IGNORECASE,
)
NONZERO_EXIT = re.compile(
    r"\bexit\s+(?:[1-9][0-9]*|\$\{?[A-Za-z_][A-Za-z0-9_]*\}?)\b"
)


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

        steps_indent = len(header.group("indent"))
        item_indent: Optional[int] = None
        index += 1
        while index < len(lines):
            line = lines[index]
            if not line.strip() or line.lstrip().startswith("#"):
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

            start = index
            index += 1
            while index < len(lines):
                candidate = lines[index]
                if candidate.strip() and not candidate.lstrip().startswith("#"):
                    if indentation(candidate) <= steps_indent:
                        break
                    next_item = LIST_ITEM.match(candidate)
                    if next_item:
                        next_indent = len(next_item.group("indent"))
                        if next_indent == item_indent:
                            break
                index += 1
            blocks.append(
                StepBlock(start + 1, index, tuple(lines[start:index]))
            )
    return blocks


def staged_diff(line: str, quiet: bool) -> bool:
    """Return whether ``line`` contains the required staged diff form."""

    has_diff = bool(GIT_DIFF.search(line))
    is_staged = "--cached" in line or "--staged" in line
    has_quiet = "--quiet" in line
    return has_diff and is_staged and (has_quiet is quiet)


def logical_shell_lines(step: StepBlock) -> List[Tuple[int, str]]:
    """Join common shell continuations before bypass inspection."""

    result: List[Tuple[int, str]] = []
    buffer = ""
    start_line = step.start_line
    for number, line in step.active_lines():
        stripped = line.strip()
        if not stripped:
            continue
        if not buffer:
            start_line = number
        continuation = stripped.endswith("\\")
        if continuation:
            stripped = stripped[:-1].rstrip()
        buffer = f"{buffer} {stripped}".strip()
        ends_with_operator = bool(re.search(r"(?:\|\||&&|;)\s*$", stripped))
        if continuation or ends_with_operator:
            continue
        result.append((start_line, buffer))
        buffer = ""
    if buffer:
        result.append((start_line, buffer))
    return result


def writer_issues(step: StepBlock, path: str) -> List[SafetyIssue]:
    """Validate one Git-writing workflow step."""

    active = step.active_lines()
    mutations = [number for number, line in active if GIT_MUTATION.search(line)]
    if not mutations:
        return []

    lines = [line for _, line in active]
    anchor = mutations[0]
    has_status = False
    has_staged_diagnostic = False
    for line in lines:
        concise_status = "--short" in line or "--porcelain" in line
        diagnostic_diff = "--name-status" in line or "--stat" in line
        if GIT_STATUS.search(line) and concise_status:
            has_status = True
        if staged_diff(line, False) and diagnostic_diff:
            has_staged_diagnostic = True

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


def payload_issues(step: StepBlock, path: str) -> List[SafetyIssue]:
    """Validate transparent and enforced payload verification."""

    text = step.text
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
    compared = bool(CHECKSUM_COMPARISON.search(text))
    failed_closed = bool(NONZERO_EXIT.search(text))
    enforced = compared and failed_closed

    issues: List[SafetyIssue] = []
    if not actual:
        issues.append(
            SafetyIssue(
                path, line, "CIW004",
                "Payload muss die berechnete SHA-256 ausgeben.",
            )
        )
    if not expected:
        issues.append(
            SafetyIssue(
                path, line, "CIW005",
                "Payload muss die erwartete SHA-256 ausgeben.",
            )
        )
    if not fragments:
        issues.append(
            SafetyIssue(
                path, line, "CIW006",
                "Payload muss Größe und SHA-256 jedes Fragments ausgeben.",
            )
        )
    if not archive:
        issues.append(
            SafetyIssue(
                path, line, "CIW007",
                "Payload-Fehler braucht eine tar -tzf-Diagnose.",
            )
        )
    if not enforced:
        issues.append(
            SafetyIssue(
                path, line, "CIW010",
                "Prüfsummenabweichungen müssen mit Fehlercode enden.",
            )
        )
    return issues


def audit_issues(step: StepBlock, path: str) -> List[SafetyIssue]:
    """Reject attempts to soften an audit failure."""

    issues: List[SafetyIssue] = []
    for number, line in logical_shell_lines(step):
        if AUDIT_BYPASS.search(line):
            issues.append(
                SafetyIssue(
                    path,
                    number,
                    "CIW008",
                    "Audit darf nicht per Shell-Bypass entkräftet werden.",
                )
            )
    if AUDIT.search(step.text) and CONTINUE_ON_ERROR.search(step.text):
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

    for number, line in enumerate(text.splitlines(), 1):
        uncovered = number not in covered
        active = not line.lstrip().startswith("#")
        mutating = bool(GIT_MUTATION.search(line))
        if uncovered and active and mutating:
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
