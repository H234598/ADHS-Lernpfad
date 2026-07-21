#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "agent/einheit-12-komorbiditaet-depression-suizidalitaet"
RUN_DIR = ROOT / ".unit12-run"
WORKFLOW = ROOT / ".github" / "workflows" / "unit12-run.yml"
CHAPTER = ROOT / "01-Grundlagen" / "12-Komorbiditaet-Depression-und-Suizidalitaet.md"


def run(*command: str) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


# Record the content release.
changelog = ROOT / "CHANGELOG.md"
text = changelog.read_text(encoding="utf-8")
if "## 0.11.0 – 2026-07-21" not in text:
    entry = (
        "## 0.11.0 – 2026-07-21\n\n"
        "- Einheit 12 „Komorbidität, Depression und Suizidalität“ ergänzt\n"
        "- depressive Komorbidität, Symptomüberlappung und diagnostisches Überschatten differenziert eingeordnet\n"
        "- aktuelle longitudinale und systematische Evidenz zu Suizidalität bei ADHS zusammengefasst\n"
        "- klare Krisen- und Notfallhinweise für Deutschland sowie Grenzen individueller Risikovorhersage ergänzt\n"
        "- vier aktuelle Studienkarten, Glossarbegriffe, Anki-Karte und Wissensgraph-Verknüpfungen ergänzt\n\n"
    )
    split = text.find("\n") + 1
    changelog.write_text(text[:split] + "\n" + entry + text[split:].lstrip("\n"), encoding="utf-8")

# Generate all three bibliography representations and prove a second run is byte-stable.
run("python", "scripts/build_literature.py")
run("git", "add", "Literatur.md", "references.bib", "references.json")
run("python", "scripts/build_literature.py")
run("git", "diff", "--exit-code", "--", "Literatur.md", "references.bib", "references.json")

# Full project checks required by the automation prompt.
run("git", "diff", "--check")
run("python", "-m", "compileall", "-q", "scripts", "tests")
if (ROOT / "tests").is_dir():
    run("python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py")
run("python", "scripts/validate_links.py")
run("python", "scripts/build_graph.py")
run("python", "scripts/validate_compendium.py")
run("python", "scripts/build_combined.py")
run("python", "scripts/build_anki.py")
run("python", "scripts/build_docs.py")
run("mkdocs", "build", "--strict")
run("python", "-m", "pip", "check")

# Emit the same prose-word metric as the repository validator.
chapter_text = CHAPTER.read_text(encoding="utf-8")
prose = re.sub(r"\A---\n.*?\n---\n", "", chapter_text, flags=re.S)
prose = re.sub(r"```.*?```", "", prose, flags=re.S)
prose = re.sub(r"</?(?:details|summary)>", "", prose)
prose = re.sub(r"## Navigation.*\Z", "", prose, flags=re.S)
prose = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda match: match.group(2) or match.group(1), prose)
words = len(re.findall(r"\b[\wÄÖÜäöüß]+(?:[-’'][\wÄÖÜäöüß]+)*\b", prose))
print(json.dumps({"unit": 12, "prose_words": words}, ensure_ascii=False))
if not 800 <= words <= 2500:
    raise RuntimeError(f"Einheit 12 liegt mit {words} Wörtern außerhalb der erlaubten Grenzen")

# Remove the temporary transport before the final commit.
shutil.rmtree(RUN_DIR)
WORKFLOW.unlink(missing_ok=True)

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", "-A")
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
    raise RuntimeError("Keine finalen Änderungen vorhanden")
run("git", "commit", "-m", "Einheit 12: Komorbidität, Depression und Suizidalität")
run("git", "push", "origin", f"HEAD:{BRANCH}")
print(f"UNIT12_RESULT branch={BRANCH} words={words} checks=success")
