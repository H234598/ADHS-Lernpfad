#!/usr/bin/env python3
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SELF_DIR = ROOT / ".generator-lint-policy"
WORKFLOW = ROOT / ".github" / "workflows" / "apply-generator-lint-policy.yml"
BRANCH = "feat/hard-review-repair-policy"


def run(*command: str, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


prompt = ROOT / "prompts" / "AUTOMATION-PROMPT.md"
text = prompt.read_text(encoding="utf-8")
old_block = """```bash
python3 scripts/build_literature.py
git diff --exit-code -- Literatur.md references.bib references.json
python3 scripts/validate_links.py
python3 scripts/build_graph.py
python3 scripts/validate_compendium.py
python3 scripts/build_combined.py
python3 scripts/build_anki.py
python3 scripts/build_docs.py
mkdocs build --strict
```

Alle Prüfungen müssen erfolgreich beendet sein. Die Validierung muss insbesondere Mindest- und Maximallänge, Pflichtabschnitte, Quellen, Obsidian-Wikilinks, Bibliografiekonsistenz und fortlaufende Nummerierung prüfen.
"""
new_block = """```bash
python -m pip install --disable-pip-version-check \\
  -r requirements-docs.txt -r requirements-export.txt
python -m pip check
npm ci
npm run audit:dependencies
REMARK_BASE_SHA=origin/main REMARK_HEAD_SHA=HEAD \\
  npm run lint:markdown:changed

python3 scripts/build_literature.py
git diff --exit-code -- Literatur.md references.bib references.json
python3 scripts/validate_links.py
python3 scripts/build_graph.py
python3 scripts/validate_graph.py
python3 scripts/validate_compendium.py
python3 scripts/build_combined.py
python3 scripts/build_anki.py
python3 scripts/build_docs.py
mkdocs build --strict
```

Alle Prüfungen müssen erfolgreich beendet sein. Die Validierung muss insbesondere Remark-lint, npm-Abhängigkeitsaudit, Mindest- und Maximallänge, Pflichtabschnitte, Quellen, Obsidian-Wikilinks, Bibliografiekonsistenz, Wissensgraph und fortlaufende Nummerierung prüfen. Eine Remark-lint-Meldung darf nicht bis zum späteren Reparaturfenster verschleppt werden, wenn sie bereits vor dem ersten Commit reproduzierbar erkennbar ist.
"""
if new_block not in text:
    if old_block not in text:
        raise RuntimeError("Pflichtprüfungsblock im Erzeugungsprompt wurde nicht gefunden")
    prompt.write_text(text.replace(old_block, new_block, 1), encoding="utf-8")

# Vollständige Policy-Prompts nach bewusster Änderung neu baselinen.
prompt_paths = (
    "prompts/AUTOMATION-PROMPT.md",
    "prompts/PR-REPAIR-PROMPT.md",
    "prompts/MERGE-AUTOMATION-PROMPT.md",
)
records = []
for relative in prompt_paths:
    content = (ROOT / relative).read_bytes()
    records.append(
        {
            "path": relative,
            "protected_prefix_bytes": len(content),
            "sha256": sha256(content).hexdigest(),
        }
    )
manifest = {
    "schema_version": "1.0.0",
    "description": "Vollständige geschützte Automationsprompts mit generatorseitigem Remark-lint, CodeRabbit-Hard-Gate und verzögertem Reparaturfenster.",
    "prompts": records,
}
(ROOT / "automation" / "prompt-baselines.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

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
run("git", "add", "prompts/AUTOMATION-PROMPT.md", "automation/prompt-baselines.json")
run("git", "add", "-u", ".generator-lint-policy", ".github/workflows/apply-generator-lint-policy.yml")
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
    print("Keine Generatorpolicy-Änderung zu committen")
    raise SystemExit(0)
run("git", "commit", "-m", "policy: run blocking Remark lint before draft creation")
run("git", "push", "origin", f"HEAD:{BRANCH}")
