#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "agent/einheit-12-komorbiditaet-depression-suizidalitaet"
BOOTSTRAP = ROOT / ".unit12-finalize"
WORKFLOW = ROOT / ".github" / "workflows" / "finalize-unit-12.yml"
CHAPTER = ROOT / "01-Grundlagen" / "12-Komorbiditaet-Depression-und-Suizidalitaet.md"


def run(*command: str) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


# Link the previous chapter to the new unit.
previous = ROOT / "01-Grundlagen" / "11-Schlaf-Bewegung-und-koerperliche-Gesundheit.md"
previous_text = previous.read_text(encoding="utf-8")
old_next = "- Weiter: [[README|Übersicht]]"
new_next = "- Weiter: [[01-Grundlagen/12-Komorbiditaet-Depression-und-Suizidalitaet|Komorbidität, Depression und Suizidalität]]"
if new_next not in previous_text:
    if old_next not in previous_text:
        raise RuntimeError("Erwarteter Weiter-Link in Einheit 11 fehlt")
    previous.write_text(previous_text.replace(old_next, new_next, 1), encoding="utf-8")

# Remove the fulfilled planned-node entry while preserving the remaining roadmap nodes.
planned_path = ROOT / "knowledge-graph" / "planned-nodes.yaml"
planned = yaml.safe_load(planned_path.read_text(encoding="utf-8"))
if not isinstance(planned, dict) or not isinstance(planned.get("nodes"), list):
    raise RuntimeError("planned-nodes.yaml besitzt nicht das erwartete Schema")
fulfilled = "01-Grundlagen/12-Komorbiditaet-Depression-und-Suizidalitaet"
planned["nodes"] = [
    node for node in planned["nodes"]
    if not isinstance(node, dict) or str(node.get("path")) != fulfilled
]
planned_path.write_text(
    "# Bewusst geplante, noch nicht vorhandene Seiten.\n"
    "# Nur hier registrierte fehlende Ziele dürfen als \"planned\" veröffentlicht werden.\n"
    + yaml.safe_dump(planned, allow_unicode=True, sort_keys=False),
    encoding="utf-8",
)

# Record the content release without touching infrastructure documentation.
changelog = ROOT / "CHANGELOG.md"
changelog_text = changelog.read_text(encoding="utf-8")
entry = (
    "## 0.11.0 – 2026-07-21\n\n"
    "- Einheit 12 „Komorbidität, Depression und Suizidalität“ ergänzt\n"
    "- depressive Komorbidität, Symptomüberlappung und diagnostisches Überschatten differenziert eingeordnet\n"
    "- aktuelle longitudinale und systematische Evidenz zu Suizidalität bei ADHS zusammengefasst\n"
    "- klare Krisen- und Notfallhinweise für Deutschland sowie Grenzen individueller Risikovorhersage ergänzt\n"
    "- vier aktuelle Studienkarten, Glossarbegriffe, Anki-Karte und Wissensgraph-Verknüpfungen ergänzt\n\n"
)
if "## 0.11.0 – 2026-07-21" not in changelog_text:
    first_newline = changelog_text.find("\n")
    changelog.write_text(
        changelog_text[: first_newline + 1] + "\n" + entry + changelog_text[first_newline + 1 :].lstrip("\n"),
        encoding="utf-8",
    )

# Generate literature once, stage it, and prove that a second generation is byte-stable.
run("python", "scripts/build_literature.py")
run("git", "add", "Literatur.md", "references.bib", "references.json")
run("python", "scripts/build_literature.py")
run("git", "diff", "--exit-code", "--", "Literatur.md", "references.bib", "references.json")

# Required project checks plus the existing unit suite.
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

# Report the validator-equivalent prose word count in the workflow log.
chapter_text = CHAPTER.read_text(encoding="utf-8")
prose = re.sub(r"\A---\n.*?\n---\n", "", chapter_text, flags=re.S)
prose = re.sub(r"```.*?```", "", prose, flags=re.S)
prose = re.sub(r"</?(?:details|summary)>", "", prose)
prose = re.sub(r"## Navigation.*\Z", "", prose, flags=re.S)
prose = re.sub(
    r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]",
    lambda match: match.group(2) or match.group(1),
    prose,
)
words = len(re.findall(r"\b[\wÄÖÜäöüß]+(?:[-’'][\wÄÖÜäöüß]+)*\b", prose))
print(json.dumps({"unit": 12, "prose_words": words}, ensure_ascii=False))
if not 800 <= words <= 2500:
    raise RuntimeError(f"Einheit 12 liegt mit {words} Wörtern außerhalb der erlaubten Grenzen")

# The transport files must not appear in the final pull-request diff.
shutil.rmtree(BOOTSTRAP)
WORKFLOW.unlink(missing_ok=True)

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", "-A")
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
    raise RuntimeError("Keine finalen Änderungen zum Committen vorhanden")
run("git", "commit", "-m", "Einheit 12: Komorbidität, Depression und Suizidalität")
run("git", "push", "origin", f"HEAD:{BRANCH}")
print("Einheit 12 vollständig geprüft und finalisiert")
