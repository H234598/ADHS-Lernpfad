#!/usr/bin/env python3
"""Reproduce the complete validation build and persist the exact MkDocs output."""

from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / ".graph-web-final" / "mkdocs-report.txt"
BRANCH = "agent/wissensgraph-web-final-8"

if REPORT.exists():
    print("MkDocs-Diagnosebericht ist bereits vorhanden.")
    raise SystemExit(0)

commands = (
    ("python", "scripts/validate_links.py"),
    ("python", "scripts/build_literature.py"),
    ("python", "scripts/build_graph.py"),
    ("python", "scripts/validate_compendium.py"),
    ("python", "scripts/build_combined.py"),
    ("python", "scripts/build_anki.py"),
    ("python", "scripts/build_docs.py"),
    ("mkdocs", "build", "--strict"),
)
sections: list[str] = ["Complete MkDocs diagnostic\n"]
failed = False

for command in commands:
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    sections.extend(
        (
            f"$ {' '.join(command)}\n",
            f"exit={result.returncode}\n",
            "--- stdout ---\n",
            result.stdout or "",
            "\n--- stderr ---\n",
            result.stderr or "",
            "\n\n",
        )
    )
    if result.returncode != 0:
        failed = True
        break

REPORT.write_text("".join(sections), encoding="utf-8")
subprocess.run(("git", "config", "user.name", "github-actions[bot]"), cwd=ROOT, check=True)
subprocess.run(
    ("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"),
    cwd=ROOT,
    check=True,
)
subprocess.run(("git", "add", str(REPORT.relative_to(ROOT))), cwd=ROOT, check=True)
subprocess.run(("git", "commit", "-m", "Record complete MkDocs diagnostic"), cwd=ROOT, check=True)
subprocess.run(("git", "push", "origin", f"HEAD:refs/heads/{BRANCH}"), cwd=ROOT, check=True)
raise SystemExit(1 if failed else 0)
