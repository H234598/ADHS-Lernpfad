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


GIT_MUTATION = re.compile(r"\bgit\b[^\n#]*(?:\bcommit\b|\bpush\b)")
GIT_DIFF = re.compile(r"\bgit\b[^\n#]*\bdiff\b")
GIT_STATUS = re.compile(r"\bgit\b[^\n#]*\bstatus\b")
AUDIT = re.compile(r"\baudit(?:[:\w-]*)?\b", re.IGNORECASE)
AUDIT_BYPASS = re.compile(r"(?:\|\||;|&&)\s*(?:true|:)\s*(?:#.*)?$")
STEP = re.compile(r"^(?P<indent>\s*)-\s+")


def workflow_files(root: Path) -> list[Path]:
    directory = root / ".github" / "workflows"
    if not directory.is_dir():
        return []
    return sorted((*directory.glob("*.yml"), *directory.glob("*.yaml")))


def active_lines(text: str) -> list[tuple[int, str]]:
    return [
        (number, line)
        for number, line in enumerate(text.splitlines(), 1)
        if not line.lstrip().startswith("#")
    ]


def line_has_staged_diff(line: str, *, quiet: bool) -> bool:
    return (
        bool(GIT_DIFF.search(line))
        and ("--cached" in line or "--staged" in line)
        and (("--quiet" in line) is quiet)
    )


def step_blocks(lines: list[str]) -> list[tuple[int, str]]:
    blocks: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        match = STEP.match(lines[index])
        if not match:
            index += 1
            continue
        indent, start = len(match.group("indent")), index
        index += 1
        while index < len(lines):
            candidate = STEP.match(lines[index])
            if candidate and len(candidate.group("indent")) == indent:
                break
            index += 1
        blocks.append((start + 1, "\n".join(lines[start:index])))
    return blocks


def validate_workflow(path: Path, root: Path) -> list[SafetyIssue]:
    text = path.read_text(encoding="utf-8")
    lines = active_lines(text)
    raw = [line for _, line in lines]
    relative = path.relative_to(root).as_posix()
    issues: list[SafetyIssue] = []

    def add(code: str, line: int, message: str) -> None:
        issues.append(SafetyIssue(relative, line, code, message))

    mutations = [number for number, line in lines if GIT_MUTATION.search(line)]
    if mutations:
        anchor = mutations[0]
        if not any(line_has_staged_diff(line, quiet=True) for line in raw):
            add("CIW001", anchor, "Git-Writer benötigt staged No-op-Guard mit --quiet.")
        if not any(
            GIT_STATUS.search(line)
            and ("--short" in line or "--porcelain" in line)
            for line in raw
        ):
            add("CIW002", anchor, "Git-Writer muss git status --short/--porcelain ausgeben.")
        if not any(
            line_has_staged_diff(line, quiet=False)
            and ("--name-status" in line or "--stat" in line)
            for line in raw
        ):
            add("CIW003", anchor, "Git-Writer muss staged --name-status/--stat ausgeben.")

    lower = text.lower()
    payload = bool(
        re.search(r"\.payload\.|payload\.(?:b64|tar(?:\.gz)?)|payload[_-]?checksum", lower)
        and "sha256sum" in lower
    )
    if payload:
        checksum_line = next(
            (number for number, line in lines if "sha256sum" in line), 1
        )
        actual = bool(
            re.search(r"(?:actual|computed)(?:_payload)?_?checksum[^\n]*sha256sum", lower)
            and re.search(r"(?:computed|actual)[^\n]*payload[^\n]*checksum", lower)
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
        if not actual:
            add("CIW004", checksum_line, "Payload muss berechnete SHA-256 ausgeben.")
        if not expected:
            add("CIW005", checksum_line, "Payload muss erwartete SHA-256 ausgeben.")
        if not fragments:
            add("CIW006", checksum_line, "Payload muss Größe und SHA-256 jedes Fragments ausgeben.")
        if not archive:
            add("CIW007", checksum_line, "Payload-Fehler braucht bestmögliche tar -tzf-Diagnose.")

    for number, line in lines:
        if AUDIT.search(line) and AUDIT_BYPASS.search(line):
            add("CIW008", number, "Audit darf nicht per Shell-Bypass entkräftet werden.")
    for number, block in step_blocks(text.splitlines()):
        if AUDIT.search(block) and re.search(
            r"(?mi)^\s*continue-on-error\s*:\s*true\s*(?:#.*)?$", block
        ):
            add("CIW009", number, "Audit-Schritt darf continue-on-error nicht aktivieren.")

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
        print(f"CI-Mutationssicherheit: {len(issues)} Problem(e).", file=sys.stderr)
        return 1
    print(f"CI-Mutationssicherheit: OK ({len(workflow_files(root))} Workflows geprüft).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
