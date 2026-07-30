#!/usr/bin/env python3
"""Block unsafe Git writers, opaque payload checks, and softened audits in CI."""

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import List, Optional, Sequence, Tuple


@dataclass(frozen=True, order=True)
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
    """A single immediate list item below a GitHub Actions ``steps:`` key."""

    start_line: int
    end_line: int
    lines: Tuple[str, ...]

    @property
    def text(self) -> str:
        """Return the complete YAML text of the step."""

        return "\n".join(self.lines)

    def active_lines(self) -> List[Tuple[int, str]]:
        """Return non-comment lines paired with their one-based line numbers."""

        return [
            (self.start_line + offset, line)
            for offset, line in enumerate(self.lines)
            if not line.lstrip().startswith("#")
        ]


@dataclass(frozen=True)
class PayloadEvidence:
    """Boolean evidence collected from one payload-verification step."""

    actual_checksum: bool
    expected_checksum: bool
    fragment_diagnostics: bool
    archive_diagnostics: bool
    enforced_comparison: bool


GIT_MUTATION = re.compile(r"\bgit\b[^\n#]*(?:\bcommit\b|\bpush\b)")
GIT_DIFF = re.compile(r"\bgit\b[^\n#]*\bdiff\b")
GIT_STATUS = re.compile(r"\bgit\b[^\n#]*\bstatus\b")
AUDIT = re.compile(r"\baudit(?:[:\w-]*)?\b", re.IGNORECASE)
AUDIT_BYPASS = re.compile(
    r"\baudit(?:[:\w-]*)?\b[^#]*(?:\|\||;)\s*(?:true|:)(?:\s|$)",
    re.IGNORECASE,
)
STEPS_HEADER = re.compile(r"^(?P<indent>\s*)steps\s*:\s*(?:#.*)?$")
LIST_ITEM = re.compile(r"^(?P<indent>\s*)-\s+")
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
    """Return all YAML workflow files below ``.github/workflows``."""

    directory = root / ".github" / "workflows"
    if not directory.is_dir():
        return []
    return sorted((*directory.glob("*.yml"), *directory.glob("*.yaml")))


def _indent(line: str) -> int:
    """Return the number of leading whitespace characters in ``line``."""

    return len(line) - len(line.lstrip())


def workflow_step_blocks(text: str) -> List[StepBlock]:
    """Return immediate list items under every workflow ``steps:`` mapping."""

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
            if _indent(line) <= steps_indent:
                break

            item = LIST_ITEM.match(line)
            if not item:
                index += 1
                continue
            candidate_indent = len(item.group("indent"))
            if item_indent is None:
                item_indent = candidate_indent
            if candidate_indent != item_indent:
                index += 1
                continue

            start = index
            index += 1
            while index < len(lines):
                candidate = lines[index]
                if candidate.strip() and not candidate.lstrip().startswith("#"):
                    candidate_indent = _indent(candidate)
                    if candidate_indent <= steps_indent:
                        break
                    candidate_item = LIST_ITEM.match(candidate)
                    if (
                        candidate_item
                        and len(candidate_item.group("indent")) == item_indent
                    ):
                        break
                index += 1
            blocks.append(
                StepBlock(
                    start_line=start + 1,
                    end_line=index,
                    lines=tuple(lines[start:index]),
                )
            )

    return blocks


def line_has_staged_diff(line: str, *, quiet: bool) -> bool:
    """Return whether ``line`` contains the required staged diff form."""

    return (
        bool(GIT_DIFF.search(line))
        and ("--cached" in line or "--staged" in line)
        and (("--quiet" in line) is quiet)
    )


def logical_shell_lines(step: StepBlock) -> List[Tuple[int, str]]:
    """Join common shell continuations so bypasses cannot hide on the next line."""

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
        if continuation or re.search(r"(?:\|\||&&|;)\s*$", stripped):
            continue
        result.append((start_line, buffer))
        buffer = ""
    if buffer:
        result.append((start_line, buffer))
    return result


def _payload_signature(text: str) -> bool:
    """Return whether a step appears to verify a fragmented payload."""

    lower = text.lower()
    return bool(
        re.search(
            r"\.payload\.|payload\.(?:b64|tar(?:\.gz)?)|payload[_-]?checksum",
            lower,
        )
        and "sha256sum" in lower
    )


def _new_issue(relative: str, line: int, code: str, message: str) -> SafetyIssue:
    """Create one consistently structured workflow finding."""

    return SafetyIssue(relative, line, code, message)


def _validate_writer_step(step: StepBlock, relative: str) -> List[SafetyIssue]:
    """Require a complete no-op guard and diagnostics in one writer step."""

    active = step.active_lines()
    mutation_lines = [
        number for number, line in active if GIT_MUTATION.search(line)
    ]
    if not mutation_lines:
        return []

    raw_lines = [line for _, line in active]
    anchor = mutation_lines[0]
    issues: List[SafetyIssue] = []
    if not any(line_has_staged_diff(line, quiet=True) for line in raw_lines):
        issues.append(
            _new_issue(
                relative,
                anchor,
                "CIW001",
                "Jeder Git-Writer-Schritt benötigt einen staged No-op-Guard mit --quiet.",
            )
        )
    if not any(
        GIT_STATUS.search(line) and ("--short" in line or "--porcelain" in line)
        for line in raw_lines
    ):
        issues.append(
            _new_issue(
                relative,
                anchor,
                "CIW002",
                "Jeder Git-Writer-Schritt muss git status --short/--porcelain ausgeben.",
            )
        )
    if not any(
        line_has_staged_diff(line, quiet=False)
        and ("--name-status" in line or "--stat" in line)
        for line in raw_lines
    ):
        issues.append(
            _new_issue(
                relative,
                anchor,
                "CIW003",
                "Jeder Git-Writer-Schritt muss einen staged --name-status/--stat-Diff ausgeben.",
            )
        )
    return issues


def _collect_payload_evidence(text: str) -> PayloadEvidence:
    """Collect diagnostic and enforcement evidence from one payload step."""

    lower = text.lower()
    actual_checksum = bool(
        re.search(
            r"(?:actual|computed)(?:_payload)?_?checksum[^\n]*sha256sum",
            lower,
        )
        and re.search(
            r"(?:computed|actual)[^\n]*payload[^\n]*checksum",
            lower,
        )
    )
    expected_checksum = bool(
        re.search(r"expected(?:_payload)?_?checksum", lower)
        and re.search(r"expected[^\n]*payload[^\n]*checksum", lower)
    )
    fragment_diagnostics = bool(
        re.search(r"\bfragment\w*\b", lower)
        and re.search(r"\bwc\s+-c\b|\bstat\b[^\n]*(?:%s|size)", lower)
        and re.search(r"sha256sum[^\n]*\$\{?fragment", lower)
    )
    return PayloadEvidence(
        actual_checksum=actual_checksum,
        expected_checksum=expected_checksum,
        fragment_diagnostics=fragment_diagnostics,
        archive_diagnostics=bool(re.search(r"\btar\b[^\n]*-tzf", text)),
        enforced_comparison=bool(
            CHECKSUM_COMPARISON.search(text) and NONZERO_EXIT.search(text)
        ),
    )


def _validate_payload_step(step: StepBlock, relative: str) -> List[SafetyIssue]:
    """Require transparent and enforced checksums for one payload step."""

    text = step.text
    if not _payload_signature(text):
        return []

    checksum_line = next(
        (number for number, line in step.active_lines() if "sha256sum" in line),
        step.start_line,
    )
    evidence = _collect_payload_evidence(text)
    issues: List[SafetyIssue] = []
    if not evidence.actual_checksum:
        issues.append(
            _new_issue(
                relative,
                checksum_line,
                "CIW004",
                "Payload muss die berechnete SHA-256 ausgeben.",
            )
        )
    if not evidence.expected_checksum:
        issues.append(
            _new_issue(
                relative,
                checksum_line,
                "CIW005",
                "Payload muss die erwartete SHA-256 ausgeben.",
            )
        )
    if not evidence.fragment_diagnostics:
        issues.append(
            _new_issue(
                relative,
                checksum_line,
                "CIW006",
                "Payload muss Größe und SHA-256 jedes Fragments ausgeben.",
            )
        )
    if not evidence.archive_diagnostics:
        issues.append(
            _new_issue(
                relative,
                checksum_line,
                "CIW007",
                "Payload-Fehler braucht eine bestmögliche tar -tzf-Diagnose.",
            )
        )
    if not evidence.enforced_comparison:
        issues.append(
            _new_issue(
                relative,
                checksum_line,
                "CIW010",
                "Ist- und Soll-Prüfsumme müssen verglichen werden; eine Abweichung muss ungleich null enden.",
            )
        )
    return issues


def _validate_audit_step(step: StepBlock, relative: str) -> List[SafetyIssue]:
    """Reject shell and workflow-level attempts to soften an audit failure."""

    issues: List[SafetyIssue] = []
    for number, line in logical_shell_lines(step):
        if AUDIT_BYPASS.search(line):
            issues.append(
                _new_issue(
                    relative,
                    number,
                    "CIW008",
                    "Audit darf nicht per Shell-Bypass entkräftet werden.",
                )
            )
    if AUDIT.search(step.text) and re.search(
        r"(?mi)^\s*continue-on-error\s*:\s*true\s*(?:#.*)?$",
        step.text,
    ):
        issues.append(
            _new_issue(
                relative,
                step.start_line,
                "CIW009",
                "Audit-Schritt darf continue-on-error nicht aktivieren.",
            )
        )
    return issues


def validate_step(step: StepBlock, relative: str) -> List[SafetyIssue]:
    """Validate one workflow step against all Variant-B requirements."""

    issues: List[SafetyIssue] = []
    issues.extend(_validate_writer_step(step, relative))
    issues.extend(_validate_payload_step(step, relative))
    issues.extend(_validate_audit_step(step, relative))
    return issues


def validate_workflow(path: Path, root: Path) -> List[SafetyIssue]:
    """Validate one workflow file and report all findings with line numbers."""

    text = path.read_text(encoding="utf-8")
    relative = path.relative_to(root).as_posix()
    steps = workflow_step_blocks(text)
    issues = [
        issue
        for step in steps
        for issue in validate_step(step, relative)
    ]

    covered = {
        number
        for step in steps
        for number in range(step.start_line, step.end_line + 1)
    }
    for number, line in enumerate(text.splitlines(), 1):
        if (
            number not in covered
            and not line.lstrip().startswith("#")
            and GIT_MUTATION.search(line)
        ):
            issues.append(
                _new_issue(
                    relative,
                    number,
                    "CIW011",
                    "Git-Mutation liegt außerhalb eines analysierbaren Workflow-Schritts.",
                )
            )
    return issues


def validate_repository(root: Path) -> List[SafetyIssue]:
    """Validate all workflows in ``root`` and return a stable sorted result."""

    resolved_root = root.resolve()
    return sorted(
        issue
        for workflow in workflow_files(resolved_root)
        for issue in validate_workflow(workflow, resolved_root)
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the command-line validator and return a process exit code."""

    parser = argparse.ArgumentParser(
        description="Prüft GitHub-Actions-Workflows auf Variante-B-Sicherheit."
    )
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    root = args.root.resolve()
    issues = validate_repository(root)
    if issues:
        for issue in issues:
            print(issue.render(), file=sys.stderr)
        print(
            f"CI-Mutationssicherheit: {len(issues)} Problem(e).",
            file=sys.stderr,
        )
        return 1
    print(
        f"CI-Mutationssicherheit: OK ({len(workflow_files(root))} Workflows geprüft)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
