#!/usr/bin/env python3
"""Block unsafe Git writers, opaque payload checks, and softened audits in CI."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys


@dataclass(frozen=True, order=True)
class SafetyIssue:
    path: str
    line: int
    code: str
    message: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.code} {self.message}"


@dataclass(frozen=True)
class StepBlock:
    start_line: int
    end_line: int
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    def active_lines(self) -> list[tuple[int, str]]:
        return [
            (self.start_line + offset, line)
            for offset, line in enumerate(self.lines)
            if not line.lstrip().startswith("#")
        ]


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


def workflow_files(root: Path) -> list[Path]:
    directory = root / ".github" / "workflows"
    if not directory.is_dir():
        return []
    return sorted((*directory.glob("*.yml"), *directory.glob("*.yaml")))


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def workflow_step_blocks(text: str) -> list[StepBlock]:
    """Return immediate list items under every workflow ``steps:`` mapping."""

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
    return (
        bool(GIT_DIFF.search(line))
        and ("--cached" in line or "--staged" in line)
        and (("--quiet" in line) is quiet)
    )


def logical_shell_lines(step: StepBlock) -> list[tuple[int, str]]:
    """Join common shell continuations so bypasses cannot hide on the next line."""

    result: list[tuple[int, str]] = []
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
    lower = text.lower()
    return bool(
        re.search(
            r"\.payload\.|payload\.(?:b64|tar(?:\.gz)?)|payload[_-]?checksum",
            lower,
        )
        and "sha256sum" in lower
    )


def validate_step(step: StepBlock, relative: str) -> list[SafetyIssue]:
    active = step.active_lines()
    raw = [line for _, line in active]
    text = step.text
    lower = text.lower()
    issues: list[SafetyIssue] = []

    def add(code: str, line: int, message: str) -> None:
        issues.append(SafetyIssue(relative, line, code, message))

    mutations = [number for number, line in active if GIT_MUTATION.search(line)]
    if mutations:
        anchor = mutations[0]
        if not any(line_has_staged_diff(line, quiet=True) for line in raw):
            add(
                "CIW001",
                anchor,
                "Jeder Git-Writer-Schritt benötigt einen staged No-op-Guard mit --quiet.",
            )
        if not any(
            GIT_STATUS.search(line)
            and ("--short" in line or "--porcelain" in line)
            for line in raw
        ):
            add(
                "CIW002",
                anchor,
                "Jeder Git-Writer-Schritt muss git status --short/--porcelain ausgeben.",
            )
        if not any(
            line_has_staged_diff(line, quiet=False)
            and ("--name-status" in line or "--stat" in line)
            for line in raw
        ):
            add(
                "CIW003",
                anchor,
                "Jeder Git-Writer-Schritt muss einen staged --name-status/--stat-Diff ausgeben.",
            )

    if _payload_signature(text):
        checksum_line = next(
            (number for number, line in active if "sha256sum" in line),
            step.start_line,
        )
        actual = bool(
            re.search(
                r"(?:actual|computed)(?:_payload)?_?checksum[^\n]*sha256sum",
                lower,
            )
            and re.search(
                r"(?:computed|actual)[^\n]*payload[^\n]*checksum",
                lower,
            )
        )
        expected = bool(
            re.search(r"expected(?:_payload)?_?checksum", lower)
            and re.search(r"expected[^\n]*payload[^\n]*checksum", lower)
        )
        fragments = bool(
            re.search(r"\bfragment\w*\b", lower)
            and re.search(r"\bwc\s+-c\b|\bstat\b[^\n]*(?:%s|size)", lower)
            and re.search(r"sha256sum[^\n]*\$\{?fragment", lower)
        )
        archive = bool(re.search(r"\btar\b[^\n]*-tzf", text))
        enforced = bool(
            CHECKSUM_COMPARISON.search(text) and NONZERO_EXIT.search(text)
        )
        if not actual:
            add(
                "CIW004",
                checksum_line,
                "Payload muss die berechnete SHA-256 ausgeben.",
            )
        if not expected:
            add(
                "CIW005",
                checksum_line,
                "Payload muss die erwartete SHA-256 ausgeben.",
            )
        if not fragments:
            add(
                "CIW006",
                checksum_line,
                "Payload muss Größe und SHA-256 jedes Fragments ausgeben.",
            )
        if not archive:
            add(
                "CIW007",
                checksum_line,
                "Payload-Fehler braucht eine bestmögliche tar -tzf-Diagnose.",
            )
        if not enforced:
            add(
                "CIW010",
                checksum_line,
                "Ist- und Soll-Prüfsumme müssen verglichen werden; eine Abweichung muss ungleich null enden.",
            )

    for number, line in logical_shell_lines(step):
        if AUDIT_BYPASS.search(line):
            add(
                "CIW008",
                number,
                "Audit darf nicht per Shell-Bypass entkräftet werden.",
            )
    if AUDIT.search(text) and re.search(
        r"(?mi)^\s*continue-on-error\s*:\s*true\s*(?:#.*)?$",
        text,
    ):
        add(
            "CIW009",
            step.start_line,
            "Audit-Schritt darf continue-on-error nicht aktivieren.",
        )

    return issues


def validate_workflow(path: Path, root: Path) -> list[SafetyIssue]:
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
                SafetyIssue(
                    relative,
                    number,
                    "CIW011",
                    "Git-Mutation liegt außerhalb eines analysierbaren Workflow-Schritts.",
                )
            )
    return issues


def validate_repository(root: Path) -> list[SafetyIssue]:
    root = root.resolve()
    return sorted(
        issue
        for workflow in workflow_files(root)
        for issue in validate_workflow(workflow, root)
    )


def main(argv: list[str] | None = None) -> int:
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
