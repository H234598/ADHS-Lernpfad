#!/usr/bin/env python3
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / ".policy-bootstrap"
WORKFLOW = ROOT / ".github" / "workflows" / "apply-hard-review-policy.yml"
BRANCH = "feat/hard-review-repair-policy"


def run(*command: str, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Erwarteter Text fehlt in {path.relative_to(ROOT)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(path: Path, marker: str, addition: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    path.write_text(text.rstrip() + "\n\n" + addition.strip() + "\n", encoding="utf-8")


# Wartungsseite an die neue Gate- und Zeitpolicy angleichen.
wartung = ROOT / "WARTUNG.md"
replace_once(wartung, "last_reviewed: 2026-07-22", "last_reviewed: 2026-07-27")
replace_once(
    wartung,
    """```text
06:00  neue Einheit recherchieren und erstellen
          ↓
        lokale Pflichtprüfungen
          ↓
        Branch, Push und Draft-Pull-Request
          ↓
        mindestens zwei Stunden Prüfzeit
          ↓
ab 08:00 stündlicher Prüf-, Reparatur- und Merge-Wächter
          ↓
        erste CI grün → Ready for review
          ↓
        zweite CI grün → Squash-Merge nach main
```

CodeRabbit bekommt während der zweistündigen Draft-Phase Gelegenheit zur Prüfung. Eine fehlende Prüfung oder ein ausgeschöpftes Kontingent ist nach Ablauf der Frist kein harter Blocker. Nachvollziehbare kritische Hinweise werden dennoch berücksichtigt.

Fehlgeschlagene CI wird nicht einfach liegen gelassen: Der Wächter führt auf dem bestehenden Einheiten-Branch genau einen sicheren Reparaturzyklus aus und wartet anschließend auf die neu gestartete CI. Nicht sicher automatisch lösbare Fehler bleiben offen und werden gemeldet.
""",
    """```text
06:00  neue Einheit recherchieren und erstellen
          ↓
        lokale Pflichtprüfungen einschließlich Remark-lint
          ↓
        Branch, Push und Draft-Pull-Request
          ↓
        mindestens zwei Stunden Reviewfrist
          ↓
ab 08:00 regelmäßiger Merge-Wächter
          ↓
vor 20:00 rote Gates → Diagnose sammeln und weiter prüfen
          ↓
ab 20:00 rote Gates → sicherer Reparaturzyklus auf bestehendem Branch
          ↓
        erste CI + Remark-lint + CodeRabbit grün → Ready for review
          ↓
        zweite CI + Remark-lint + CodeRabbit grün → Squash-Merge
```

CodeRabbit ist ein verpflichtendes hartes Gate. Für den aktuellen Head müssen ein erfolgreicher CodeRabbit-Status, vollständig gelöste Review-Threads und der erfolgreiche Check `CodeRabbit review gate (blocking)` vorliegen. Schweigen, Limiterschöpfung oder ein ungeklärter Dissens gelten nicht als Zustimmung.

Der Reparaturzyklus startet frühestens zu `max(PR-Erstellung + 2 Stunden, 20:00 Uhr Europe/Berlin am Erstellungstag)`. Bis dahin bleibt der Wächter aktiv, sammelt Diagnosen und prüft weiter. Es gibt keinen Abbruch nach dem zweiten roten CI-Lauf. Ab dem Reparaturfenster ist pro Wächterlauf genau ein sicherer, idempotenter Zyklus zulässig; neue Ursachen können in späteren Läufen erneut repariert werden.

Die vollständige technische Policy steht unter [[automation/MERGE-REPAIR-POLICY|Merge- und Reparaturpolicy]].
""",
)
replace_once(
    wartung,
    "- Python-Syntax und Whitespace,\n",
    "- Python-Syntax und Whitespace,\n- reproduzierbares Remark-lint für geänderte Markdown-Dateien,\n- verpflichtendes CodeRabbit-Gate mit Thread- und Dissensprüfung,\n",
)
replace_once(
    wartung,
    "Normale neue Lerneinheiten dürfen nach zwei grünen CI-Phasen automatisch gemergt werden.",
    "Normale neue Lerneinheiten dürfen nur nach zwei grünen CI-Phasen, grünem Remark-lint und vollständig grünem CodeRabbit-Gate automatisch gemergt werden.",
)

# Automations- und Beitragsdokumentation ergänzen.
append_once(
    ROOT / "automation" / "README.md",
    "## Hartes Review-Gate und verzögertes Reparaturfenster",
    """## Hartes Review-Gate und verzögertes Reparaturfenster

Die verbindliche Merge- und Reparaturpolicy ist unter [[automation/MERGE-REPAIR-POLICY|Merge- und Reparaturpolicy]] dokumentiert. `scripts/merge_repair_policy.py` berechnet die Fristen in `Europe/Berlin`; `scripts/review_gate.py` prüft das CodeRabbit-Signal des aktuellen Heads, ungelöste Threads und dokumentierte Dissense.

Review- und Lintberichte werden als strukturierte Artefakte registriert. Ein fehlendes CodeRabbit-Signal, ein ungelöster Thread, ein offener Dissens oder ein roter Remark-lint-Check blockiert die Statusphasen `ready_for_review` und `merge`.
""",
)
append_once(
    ROOT / "CONTRIBUTING.md",
    "## Verbindliche Markdown- und Review-Gates",
    """## Verbindliche Markdown- und Review-Gates

Vor einem Inhalts-PR beziehungsweise nach einer Reparatur müssen die geänderten Markdown-Dateien reproduzierbar geprüft werden:

```bash
npm ci
REMARK_BASE_SHA=origin/main REMARK_HEAD_SHA=HEAD \\
  npm run lint:markdown:changed
```

Jede Remark-lint-Warnung ist blockierend. CodeRabbit ist für automatische Einheiten ebenfalls ein hartes Gate: Alle Threads werden behoben oder mit überprüfbarer Begründung abgeschlossen. Ein fachlicher oder technischer Dissens wird nicht einseitig aufgelöst, sondern als manueller Blocker dokumentiert.
""",
)

# Changelogeintrag direkt nach der Hauptüberschrift einsetzen.
changelog = ROOT / "CHANGELOG.md"
changelog_text = changelog.read_text(encoding="utf-8")
entry = """## 0.18.0 – 2026-07-27

- CodeRabbit für automatische Einheiten zum verpflichtenden harten Gate gemacht
- ungelöste und auch veraltete CodeRabbit-Threads sowie dokumentierte Dissense als Mergeblocker verankert
- Reparaturfenster auf frühestens 20:00 Uhr Europe/Berlin am PR-Erstellungstag verschoben und starre Zwei-Fehler-Grenze entfernt
- deterministische Zeit- und Reparaturentscheidung samt Regressionstests ergänzt
- reproduzierbares, gepinntes Remark-lint für geänderte Markdown-Dateien als blockierenden CI-Check eingeführt
- Reparaturprompt um aktuelle Evidenzrecherche, Thread-Matrix, sichere Stagingregeln und inkrementelle Re-Reviews gehärtet

"""
if "## 0.18.0 – 2026-07-27" not in changelog_text:
    first_newline = changelog_text.find("\n") + 1
    changelog.write_text(
        changelog_text[:first_newline] + "\n" + entry + changelog_text[first_newline:].lstrip("\n"),
        encoding="utf-8",
    )

# Bewusst geänderte vollständige Policy-Prompts als neue kryptografische Baseline schützen.
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
    "description": "Vollständige geschützte Automationsprompts nach Einführung von CodeRabbit-Hard-Gate, Remark-lint und verzögertem Reparaturfenster.",
    "prompts": records,
}
(ROOT / "automation" / "prompt-baselines.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

# Reproduzierbares npm-Lockfile für die exakt gepinnten Remark-Abhängigkeiten.
run("npm", "install", "--package-lock-only", "--ignore-scripts")

# Transportdateien dürfen den finalen PR-Diff nicht erreichen.
shutil.rmtree(BOOTSTRAP)
WORKFLOW.unlink(missing_ok=True)

# Vollständige Prüfung der Policy- und Infrastrukturänderungen.
run("python", "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements-docs.txt", "-r", "requirements-export.txt")
run("python", "-m", "pip", "check")
run("npm", "ci")
run("git", "diff", "--check")
run("python", "-m", "compileall", "-q", "scripts", "tests")
run("python", "scripts/validate_prompt_baselines.py")
run("python", "-m", "pytest", "-q")
run("npm", "test")

# Bereits committed Markdownänderungen plus die in diesem Lauf geänderte Dokumentation linten.
env = dict(__import__("os").environ)
env["REMARK_BASE_SHA"] = "origin/main"
env["REMARK_HEAD_SHA"] = "HEAD"
run("npm", "run", "lint:markdown:changed", env=env)
remark_bin = ROOT / "node_modules" / ".bin" / "remark"
run(
    str(remark_bin),
    "--frail",
    "--no-stdout",
    "WARTUNG.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "automation/README.md",
)

# Der Infrastruktur-PR verändert keine Lerninhalte, trotzdem müssen zentrale Validatoren laufen.
run("python", "scripts/validate_links.py")
run("python", "scripts/build_graph.py")
run("python", "scripts/validate_graph.py")
run("python", "scripts/build_docs.py")
run("mkdocs", "build", "--strict")

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", "-A")
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
    print("Keine finalen Policyänderungen zu committen")
    raise SystemExit(0)
run("git", "commit", "-m", "policy: enforce hard review and delayed repair gates")
run("git", "push", "origin", f"HEAD:{BRANCH}")
print("Hard-Review- und Repair-Policy vollständig materialisiert und geprüft")
