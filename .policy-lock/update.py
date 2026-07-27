#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SELF_DIR = ROOT / ".policy-lock"
WORKFLOW = ROOT / ".github" / "workflows" / "update-policy-lock.yml"
BRANCH = "feat/hard-review-repair-policy"


def run(*command: str, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


run("npm", "install", "--package-lock-only", "--ignore-scripts")

# Transportdateien vor Tests und Commit entfernen.
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

env = dict(os.environ)
env["REMARK_BASE_SHA"] = "origin/main"
env["REMARK_HEAD_SHA"] = "HEAD"
run("npm", "run", "lint:markdown:changed", env=env)
run("python", "scripts/validate_links.py")
run("python", "scripts/build_graph.py")
run("python", "scripts/validate_graph.py")
run("python", "scripts/build_docs.py")
run("mkdocs", "build", "--strict")

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", "-A")
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
    print("Keine Lockfile- oder Policyänderungen zu committen")
    raise SystemExit(0)
run("git", "commit", "-m", "build: finalize audited review-policy dependencies")
run("git", "push", "origin", f"HEAD:{BRANCH}")
