#!/usr/bin/env python3
"""Enforce safe Git writers, payload checks, and blocking audits in CI."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import shlex
import sys
from typing import NamedTuple


@dataclass(frozen=True)
class SafetyIssue:
    """One actionable mutation-safety finding in a workflow file."""

    path: str
    line: int
    code: str
    message: str

    def render(self) -> str:
        """Render the finding in compiler-style path/line form."""
        return f"{self.path}:{self.line}: {self.code} {self.message}"


@dataclass(frozen=True)
class StepBlock:
    """One immediate list item below a GitHub Actions ``steps:`` key."""

    start_line: int
    end_line: int
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        """Return the complete YAML text of the step."""
        return "\n".join(self.lines)

    def active_lines(self) -> list[tuple[int, str]]:
        """Return uncommented lines with one-based line numbers."""
        result: list[tuple[int, str]] = []
        for offset, line in enumerate(self.lines):
            stripped = strip_shell_comment(line)
            if not stripped.strip():
                continue
            result.append((self.start_line + offset, stripped))
        return result


class GitCommand(NamedTuple):
    """One executable git command with a stable source position."""

    line: int
    ordinal: int
    tokens: tuple[str, ...]
    git_index: int

    @property
    def position(self) -> tuple[int, int]:
        """Return the command position for ordering checks."""
        return (self.line, self.ordinal)

    @property
    def subcommand(self) -> str | None:
        """Return the git subcommand after common global options."""
        index = self.git_index + 1
        options_with_value = {
            "-C",
            "-c",
            "--git-dir",
            "--work-tree",
            "--namespace",
            "--exec-path",
        }
        while index < len(self.tokens):
            token = self.tokens[index]
            if token == "--":
                index += 1
                break
            if token in options_with_value:
                index += 2
                continue
            if any(
                token.startswith(f"{option}=")
                for option in options_with_value
                if option.startswith("--")
            ):
                index += 1
                continue
            if token.startswith("-"):
                index += 1
                continue
            return token
        if index < len(self.tokens):
            return self.tokens[index]
        return None


AUDIT = re.compile(r"\baudit(?:[:\w-]*)?\b", re.IGNORECASE)
AUDIT_BYPASS = re.compile(
    r"\baudit(?:[:\w-]*)?\b[^#]*(?:\|\||;)\s*(?:true|:|exit\s+0)(?:\s|$)",
    re.IGNORECASE,
)
CONTINUE_ON_ERROR = re.compile(r"(?mi)^\s*continue-on-error\s*:\s*true\s*$")
STEPS_HEADER = re.compile(r"^(?P<indent>\s*)steps\s*:\s*(?:#.*)?$")
LIST_ITEM = re.compile(r"^(?P<indent>\s*)-\s+")
SHELL_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
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
EXPECTED_VALUE = re.compile(r"expected(?:_payload)?_?checksum", re.IGNORECASE)
EXPECTED_OUTPUT = re.compile(
    r"expected[^\n]*payload[^\n]*checksum",
    re.IGNORECASE,
)
FRAGMENT_MARKER = re.compile(r"\bfragment\w*\b", re.IGNORECASE)
FRAGMENT_SIZE = re.compile(
    r"\bwc\s+-c\b|\bstat\b[^\n]*(?:%s|size)",
    re.IGNORECASE,
)
FRAGMENT_CHECKSUM = re.compile(r"sha256sum[^\n]*\$\{?fragment", re.IGNORECASE)
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

SHELL_PREFIXES = {"if", "then", "elif", "while", "until", "do", "!", "{"}
SHELL_WRAPPERS = {"command", "exec", "env", "time"}
CONTROL_TOKENS = {";", "&&", "||", "|", "&"}


def workflow_files(root: Path) -> list[Path]:
    """Return YAML workflows below ``.github/workflows``."""
    directory = root / ".github" / "workflows"
    if not directory.is_dir():
        return []
    return sorted([*directory.glob("*.yml"), *directory.glob("*.yaml")])


def indentation(line: str) -> int:
    """Return the number of leading whitespace characters."""
    return len(line) - len(line.lstrip())


def strip_shell_comment(line: str) -> str:
    """Strip an unquoted shell/YAML comment without altering quoted hashes."""
    single = False
    double = False
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\" and not single:
            escaped = True
            continue
        if char == "'" and not double:
            single = not single
            continue
        if char == '"' and not single:
            double = not double
            continue
        if char == "#" and not single and not double:
            if index == 0 or line[index - 1].isspace():
                return line[:index].rstrip()
    return line.rstrip()


def workflow_step_blocks(text: str) -> list[StepBlock]:
    """Extract immediate list items below every workflow ``steps:`` key."""
    lines = text.splitlines()
    blocks: list[StepBlock] = []
    index = 0
    while index < len(lines):
        header = STEPS_HEADER.match(lines[index])
        if not header:
            index += 1
            continue
        steps_indent = len(header.group("indent"))
        item_indent: int | None = None
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
                    if next_item and len(next_item.group("indent")) == item_indent:
                        break
                index += 1
            blocks.append(StepBlock(start + 1, index, tuple(lines[start:index])))
    return blocks


def logical_shell_lines(step: StepBlock) -> list[tuple[int, str]]:
    """Join shell continuations and operator continuations."""
    result: list[tuple[int, str]] = []
    buffer = ""
    start_line = step.start_line
    for number, raw_line in step.active_lines():
        stripped = raw_line.strip()
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


def _shell_segments(text: str) -> list[list[str]]:
    """Tokenize one logical shell line into executable command segments."""
    try:
        lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|()")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return []

    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in CONTROL_TOKENS or token in {"(", ")"}:
            if current:
                segments.append(current)
                current = []
            continue
        current.append(token)
    if current:
        segments.append(current)
    return segments


def _git_index(tokens: list[str]) -> int | None:
    """Return the executable git token when git is command-positioned."""
    index = 0
    while index < len(tokens) and tokens[index] in SHELL_PREFIXES:
        index += 1
    while index < len(tokens) and SHELL_ASSIGNMENT.match(tokens[index]):
        index += 1
    while index < len(tokens) and tokens[index] in SHELL_WRAPPERS:
        wrapper = tokens[index]
        index += 1
        if wrapper == "env":
            while index < len(tokens) and (
                tokens[index].startswith("-")
                or SHELL_ASSIGNMENT.match(tokens[index])
            ):
                index += 1
        while index < len(tokens) and SHELL_ASSIGNMENT.match(tokens[index]):
            index += 1
    if index < len(tokens) and tokens[index] == "git":
        return index
    return None


def git_commands(step: StepBlock) -> list[GitCommand]:
    """Return command-aware git invocations, including split continuations."""
    commands: list[GitCommand] = []
    for line, logical in logical_shell_lines(step):
        for ordinal, segment in enumerate(_shell_segments(logical)):
            git_index = _git_index(segment)
            if git_index is not None:
                commands.append(GitCommand(line, ordinal, tuple(segment), git_index))
    return commands


def _has_flag(command: GitCommand, *flags: str) -> bool:
    """Return whether a parsed git command contains any requested flag."""
    return any(flag in command.tokens for flag in flags)


def staged_diff(command: GitCommand, quiet: bool) -> bool:
    """Return whether a command contains the required staged diff form."""
    if command.subcommand != "diff":
        return False
    is_staged = _has_flag(command, "--cached", "--staged")
    has_quiet = _has_flag(command, "--quiet")
    return is_staged and has_quiet is quiet


def writer_issues(step: StepBlock, path: str) -> list[SafetyIssue]:
    """Validate one Git-writing workflow step and command ordering."""
    commands = git_commands(step)
    mutations = [
        command for command in commands if command.subcommand in {"commit", "push"}
    ]
    if not mutations:
        return []

    first_mutation = min(mutations, key=lambda command: command.position)
    guards = [command for command in commands if staged_diff(command, True)]
    guards_before_mutation = [
        command for command in guards if command.position < first_mutation.position
    ]
    guard = (
        min(guards_before_mutation, key=lambda command: command.position)
        if guards_before_mutation
        else None
    )

    issues: list[SafetyIssue] = []
    if guard is None:
        issues.append(
            SafetyIssue(
                path,
                first_mutation.line,
                "CIW001",
                "Git-Writer braucht vor Commit/Push einen staged No-op-Guard mit --quiet.",
            )
        )

    boundary = guard.position if guard is not None else first_mutation.position
    status_before_guard = any(
        command.subcommand == "status"
        and _has_flag(command, "--short", "--porcelain")
        and command.position < boundary
        for command in commands
    )
    diagnostic_before_guard = any(
        staged_diff(command, False)
        and _has_flag(command, "--name-status", "--stat")
        and command.position < boundary
        for command in commands
    )

    if not status_before_guard:
        issues.append(
            SafetyIssue(
                path,
                first_mutation.line,
                "CIW002",
                "Git-Writer muss vor dem No-op-Guard git status --short/--porcelain ausgeben.",
            )
        )
    if not diagnostic_before_guard:
        issues.append(
            SafetyIssue(
                path,
                first_mutation.line,
                "CIW003",
                "Git-Writer muss vor dem No-op-Guard einen staged --name-status/--stat-Diff ausgeben.",
            )
        )
    return issues


def checksum_line(step: StepBlock) -> int:
    """Return the first active line containing ``sha256sum`` in a step."""
    for number, line in step.active_lines():
        if "sha256sum" in line:
            return number
    return step.start_line


def evidence_text(step: StepBlock) -> str:
    """Return only active, uncommented evidence lines from a workflow step."""
    return "\n".join(line for _, line in step.active_lines())


def payload_issues(step: StepBlock, path: str) -> list[SafetyIssue]:
    """Validate transparent and enforced payload verification."""
    text = evidence_text(step)
    if not PAYLOAD_MARKER.search(text):
        return []

    line = checksum_line(step)
    actual = bool(ACTUAL_ASSIGNMENT.search(text) and ACTUAL_OUTPUT.search(text))
    expected = bool(EXPECTED_VALUE.search(text) and EXPECTED_OUTPUT.search(text))
    fragments = bool(
        FRAGMENT_MARKER.search(text)
        and FRAGMENT_SIZE.search(text)
        and FRAGMENT_CHECKSUM.search(text)
    )
    archive = bool(ARCHIVE_LISTING.search(text))
    enforced = bool(CHECKSUM_COMPARISON.search(text) and NONZERO_EXIT.search(text))

    issues: list[SafetyIssue] = []
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


def audit_issues(step: StepBlock, path: str) -> list[SafetyIssue]:
    """Reject attempts to soften an audit failure."""
    issues: list[SafetyIssue] = []
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
    text = evidence_text(step)
    if AUDIT.search(text) and CONTINUE_ON_ERROR.search(text):
        issues.append(
            SafetyIssue(
                path,
                step.start_line,
                "CIW009",
                "Audit-Schritt darf continue-on-error nicht aktivieren.",
            )
        )
    return issues


def validate_step(step: StepBlock, path: str) -> list[SafetyIssue]:
    """Validate one workflow step against Variant B."""
    issues = writer_issues(step, path)
    issues.extend(payload_issues(step, path))
    issues.extend(audit_issues(step, path))
    return issues


def validate_workflow(path: Path, root: Path) -> list[SafetyIssue]:
    """Validate one workflow file."""
    text = path.read_text(encoding="utf-8")
    relative = path.relative_to(root).as_posix()
    steps = workflow_step_blocks(text)
    issues: list[SafetyIssue] = []
    covered: set[int] = set()
    for step in steps:
        issues.extend(validate_step(step, relative))
        covered.update(range(step.start_line, step.end_line + 1))

    lines = tuple(text.splitlines())
    whole_file = StepBlock(1, len(lines), lines)
    for command in git_commands(whole_file):
        if command.subcommand not in {"commit", "push"}:
            continue
        if command.line in covered:
            continue
        issues.append(
            SafetyIssue(
                relative,
                command.line,
                "CIW011",
                "Git-Mutation liegt außerhalb eines analysierbaren Schritts.",
            )
        )
    return issues


def validate_repository(root: Path) -> list[SafetyIssue]:
    """Validate every workflow in ``root``."""
    resolved = root.resolve()
    issues: list[SafetyIssue] = []
    for workflow in workflow_files(resolved):
        issues.extend(validate_workflow(workflow, resolved))
    return sorted(issues, key=lambda issue: (issue.path, issue.line, issue.code))


def main(argv: list[str] | None = None) -> int:
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
    print(f"CI-Mutationssicherheit: OK ({len(workflow_files(root))} Workflows geprüft).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
