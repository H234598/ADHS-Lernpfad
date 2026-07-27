#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SELF_DIR = ROOT / ".review-fix"
WORKFLOW = ROOT / ".github" / "workflows" / "apply-review-fix.yml"
BRANCH = "feat/hard-review-repair-policy"


def run(*command: str, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def replace_exact(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Erwarteter Link fehlt in {path.relative_to(ROOT)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_exact(
    ROOT / "WARTUNG.md",
    "Die vollständige technische Policy steht unter [[automation/MERGE-REPAIR-POLICY|Merge- und Reparaturpolicy]].",
    "Die vollständige technische Policy steht unter [Merge- und Reparaturpolicy](automation/MERGE-REPAIR-POLICY.md).",
)
replace_exact(
    ROOT / "automation" / "README.md",
    "Die verbindliche Merge- und Reparaturpolicy ist unter [[automation/MERGE-REPAIR-POLICY|Merge- und Reparaturpolicy]] dokumentiert.",
    "Die verbindliche Merge- und Reparaturpolicy ist unter [Merge- und Reparaturpolicy](MERGE-REPAIR-POLICY.md) dokumentiert.",
)

# Transportdateien vor Prüfung und Commit entfernen.
shutil.rmtree(SELF_DIR)
WORKFLOW.unlink(missing_ok=True)

run("python", "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements-docs.txt", "-r", "requirements-export.txt")
run("python", "-m", "pip", "check")
run("npm", "ci")
run("npm", "run", "audit:dependencies")
run("git", "diff", "--check")
run("python", "-m", "compileall", "-q", "scripts", "tests")
run("python", "scripts/validate_prompt_baselines.py")
run("python", "-m", "pytest", "-q")
run("npm", "test")
run(
    "node",
    "scripts/remark_lint.mjs",
    "--files",
    "WARTUNG.md",
    "automation/README.md",
)
run("python", "scripts/validate_links.py")
run("python", "scripts/build_graph.py")
run("python", "scripts/validate_graph.py")
run("python", "scripts/build_docs.py")
run("mkdocs", "build", "--strict")

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", "WARTUNG.md", "automation/README.md")
run("git", "add", "-u", ".review-fix", ".github/workflows/apply-review-fix.yml")
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
    print("Keine Markdown-Linkkorrektur zu committen")
    raise SystemExit(0)
run("git", "commit", "-m", "docs: use portable links for merge-repair policy")
run("git", "push", "origin", f"HEAD:{BRANCH}")
