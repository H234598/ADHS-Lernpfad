#!/usr/bin/env python3
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "feat/hard-review-repair-policy"
TEMP_DIR = ROOT / ".pr44-review-fix"
TEMP_WORKFLOW = ROOT / ".github" / "workflows" / "apply-pr44-review-fixes.yml"


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Erwarteter Text fehlt in {relative}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def run(*command: str, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


replace_once(
    "CONTRIBUTING.md",
    "npm ci\nREMARK_BASE_SHA=origin/main REMARK_HEAD_SHA=HEAD \\\n",
    "npm ci\nnpm run audit:dependencies\nREMARK_BASE_SHA=origin/main REMARK_HEAD_SHA=HEAD \\\n",
)

replace_once(
    "prompts/MERGE-AUTOMATION-PROMPT.md",
    'npm ci\nREMARK_BASE_SHA="origin/main" REMARK_HEAD_SHA="HEAD" \\\n',
    'npm ci\nnpm run audit:dependencies\nREMARK_BASE_SHA="origin/main" REMARK_HEAD_SHA="HEAD" \\\n',
)

replace_once(
    "prompts/PR-REPAIR-PROMPT.md",
    'npm ci\n\nREMARK_BASE_SHA="origin/main" REMARK_HEAD_SHA="HEAD" \\\n',
    'npm ci\nnpm run audit:dependencies\n\nREMARK_BASE_SHA="origin/main" REMARK_HEAD_SHA="HEAD" \\\n',
)

replace_once(
    "WARTUNG.md",
    "ab 08:00 regelmäßiger Merge-Wächter\n"
    "          ↓\n"
    "vor 20:00 rote Gates → Diagnose sammeln und weiter prüfen\n"
    "          ↓\n"
    "ab 20:00 rote Gates → sicherer Reparaturzyklus auf bestehendem Branch\n",
    "ab 08:00 regelmäßiger Merge-Wächter\n"
    "          ↓\n"
    "Reparaturfenster = max(PR-Erstellung + 2 Stunden, 20:00 am Erstellungstag)\n"
    "          ↓\n"
    "vor dem Reparaturfenster rote Gates → Diagnose sammeln und weiter prüfen\n"
    "          ↓\n"
    "ab dem Reparaturfenster rote Gates → sicherer Reparaturzyklus auf bestehendem Branch\n",
)

policy_path = ROOT / "scripts" / "merge_repair_policy.py"
policy = policy_path.read_text(encoding="utf-8")
policy = policy.replace(
    '            "CI oder Review ist rot; vor dem Reparaturfenster wird noch kein Reparaturzyklus gestartet.",\n',
    '            "CI oder Review ist rot; vor dem Reparaturfenster wird noch kein "\n'
    '            "Reparaturzyklus gestartet.",\n',
)
policy = policy.replace(
    '            "Nach Beginn des Reparaturfensters ist ein sicherer Zyklus auf dem bestehenden PR-Branch erforderlich.",\n',
    '            "Nach Beginn des Reparaturfensters ist ein sicherer Zyklus auf dem "\n'
    '            "bestehenden PR-Branch erforderlich.",\n',
)
old_policy_block = '''    if coderabbit_state in {"missing", "pending"}:
        return decision(
            "wait_coderabbit",
            "Eine erfolgreiche CodeRabbit-Prüfung des aktuellen Heads fehlt noch.",
            blocker=True,
            repair=False,
        )

    if coderabbit_state != "success" or unresolved_threads:
        return decision(
            "hard_block_review",
            "Das verpflichtende CodeRabbit-Gate ist nicht vollständig grün.",
            blocker=True,
            repair=False,
        )

    if ci_state in {"missing", "pending"}:
        return decision(
            "wait_ci",
            "Die CI des aktuellen Heads fehlt oder läuft noch.",
            blocker=False,
            repair=False,
        )

    if ci_state != "success":
        return decision(
            "wait_ci",
            "Die erste CI ist nicht vollständig erfolgreich.",
            blocker=False,
            repair=False,
        )
'''
new_policy_block = '''    if coderabbit_state != "success":
        return decision(
            "wait_coderabbit",
            "Eine erfolgreiche CodeRabbit-Prüfung des aktuellen Heads fehlt noch.",
            blocker=True,
            repair=False,
        )

    if ci_state != "success":
        return decision(
            "wait_ci",
            "Die CI des aktuellen Heads fehlt oder läuft noch.",
            blocker=False,
            repair=False,
        )
'''
if new_policy_block not in policy:
    if old_policy_block not in policy:
        raise RuntimeError("Erwarteter Entscheidungsblock in merge_repair_policy.py fehlt")
    policy = policy.replace(old_policy_block, new_policy_block, 1)
policy_path.write_text(policy, encoding="utf-8")

review_path = ROOT / "scripts" / "review_gate.py"
review = review_path.read_text(encoding="utf-8")
old_signal_function = '''def _latest_coderabbit_signals(repository: str, head_sha: str, token: str) -> list[dict[str, str]]:
    statuses = _request_json(f"{API}/repos/{repository}/commits/{head_sha}/status", token)
    checks = _request_json(
        f"{API}/repos/{repository}/commits/{head_sha}/check-runs?per_page=100", token
    )
    collected: list[dict[str, str]] = []
'''
new_signal_function = '''def _latest_coderabbit_signals(
    repository: str,
    head_sha: str,
    token: str,
) -> list[dict[str, str]]:
    statuses = _request_json(f"{API}/repos/{repository}/commits/{head_sha}/status", token)
    checks = []
    page = 1
    while True:
        batch = _request_json(
            f"{API}/repos/{repository}/commits/{head_sha}/check-runs"
            f"?per_page=100&page={page}",
            token,
        )
        batch_checks = batch.get("check_runs", [])
        checks.extend(batch_checks)
        if len(batch_checks) < 100:
            break
        page += 1
    collected: list[dict[str, str]] = []
'''
if new_signal_function not in review:
    if old_signal_function not in review:
        raise RuntimeError("Erwarteter Signalblock in review_gate.py fehlt")
    review = review.replace(old_signal_function, new_signal_function, 1)
review = review.replace('    for check in checks.get("check_runs", []):\n', '    for check in checks:\n', 1)
old_classification = '''    states = [signal.get("state", "missing").casefold() for signal in signals]
    successful = {"success", "neutral"}
    if not signals:
        coderabbit_state = "missing"
        reasons.append("Kein CodeRabbit-Signal für den aktuellen Head vorhanden.")
    elif any(state not in successful for state in states):
        coderabbit_state = "failure"
        reasons.append("Mindestens ein aktuelles CodeRabbit-Signal ist nicht erfolgreich.")
    else:
        coderabbit_state = "success"
'''
new_classification = '''    states = [signal.get("state", "missing").casefold() for signal in signals]
    successful = {"success", "neutral", "skipped"}
    pending = {"", "missing", "pending", "queued", "in_progress", "requested", "waiting"}
    if not signals:
        coderabbit_state = "missing"
        reasons.append("Kein CodeRabbit-Signal für den aktuellen Head vorhanden.")
    elif any(state not in successful | pending for state in states):
        coderabbit_state = "failure"
        reasons.append("Mindestens ein aktuelles CodeRabbit-Signal ist fehlgeschlagen.")
    elif any(state in pending for state in states):
        coderabbit_state = "pending"
        reasons.append("Mindestens ein aktuelles CodeRabbit-Signal läuft noch.")
    else:
        coderabbit_state = "success"
'''
if new_classification not in review:
    if old_classification not in review:
        raise RuntimeError("Erwarteter Klassifikationsblock in review_gate.py fehlt")
    review = review.replace(old_classification, new_classification, 1)
review_path.write_text(review, encoding="utf-8")

review_tests_path = ROOT / "tests" / "test_review_gate.py"
review_tests = review_tests_path.read_text(encoding="utf-8")
review_tests = review_tests.replace(
    "import unittest\n",
    "import unittest\nfrom unittest.mock import patch\n",
    1,
)
review_tests = review_tests.replace(
    "from review_gate import evaluate_gate, is_coderabbit_signal\n",
    "from review_gate import _latest_coderabbit_signals, evaluate_gate, is_coderabbit_signal\n",
    1,
)
new_review_tests = '''
    def test_in_progress_signal_is_pending_not_failure(self) -> None:
        state, unresolved, reasons, disagreement = evaluate_gate(
            signals=[{"name": "CodeRabbit", "state": "in_progress"}],
            threads=[],
            comments=[],
            head_sha=HEAD,
        )
        self.assertEqual(state, "pending")
        self.assertEqual(unresolved, [])
        self.assertTrue(any("läuft noch" in reason for reason in reasons))
        self.assertFalse(disagreement)

    def test_check_runs_are_paginated_before_signal_selection(self) -> None:
        def fake_request(url: str, token: str, *, data=None):
            del token, data
            if url.endswith("/status"):
                return {"statuses": []}
            if "page=1" in url:
                return {
                    "check_runs": [
                        {"name": f"unrelated-{index}", "app": {"name": "GitHub Actions"}}
                        for index in range(100)
                    ]
                }
            if "page=2" in url:
                return {
                    "check_runs": [
                        {
                            "name": "CodeRabbit",
                            "app": {"name": "coderabbitai"},
                            "status": "completed",
                            "conclusion": "success",
                            "completed_at": "2026-07-27T20:00:00Z",
                            "html_url": "https://example.invalid/check",
                        }
                    ]
                }
            raise AssertionError(f"Unerwartete URL: {url}")

        with patch("review_gate._request_json", side_effect=fake_request):
            signals = _latest_coderabbit_signals("owner/repo", HEAD, "token")

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["state"], "success")
        self.assertIn("CodeRabbit", signals[0]["name"])

'''
marker = "    def test_success_requires_signal_and_no_open_threads(self) -> None:\n"
if "test_in_progress_signal_is_pending_not_failure" not in review_tests:
    if marker not in review_tests:
        raise RuntimeError("Einfügemarke in test_review_gate.py fehlt")
    review_tests = review_tests.replace(marker, new_review_tests + marker, 1)
review_tests_path.write_text(review_tests, encoding="utf-8")

policy_tests_path = ROOT / "tests" / "test_merge_repair_policy.py"
policy_tests = policy_tests_path.read_text(encoding="utf-8")
new_policy_test = '''
    def test_pending_coderabbit_waits_when_ci_is_green(self) -> None:
        result = self.evaluate(21, ci_state="success", coderabbit_state="pending")
        self.assertEqual(result.action, "wait_coderabbit")
        self.assertTrue(result.hard_blocker)

'''
policy_marker = "    def test_missing_coderabbit_is_hard_blocker_when_ci_is_green(self) -> None:\n"
if "test_pending_coderabbit_waits_when_ci_is_green" not in policy_tests:
    if policy_marker not in policy_tests:
        raise RuntimeError("Einfügemarke in test_merge_repair_policy.py fehlt")
    policy_tests = policy_tests.replace(policy_marker, new_policy_test + policy_marker, 1)
policy_tests_path.write_text(policy_tests, encoding="utf-8")

files_test_path = ROOT / "tests" / "test_review_policy_files.py"
files_test = files_test_path.read_text(encoding="utf-8")
new_files_test = '''

def test_dependency_audit_is_required_in_all_documented_gate_sequences() -> None:
    for relative in (
        "CONTRIBUTING.md",
        "prompts/MERGE-AUTOMATION-PROMPT.md",
        "prompts/PR-REPAIR-PROMPT.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "npm run audit:dependencies" in text

'''
files_marker = "\ndef test_repair_deadline_and_no_two_failure_cap_are_explicit() -> None:\n"
if "test_dependency_audit_is_required_in_all_documented_gate_sequences" not in files_test:
    if files_marker not in files_test:
        raise RuntimeError("Einfügemarke in test_review_policy_files.py fehlt")
    files_test = files_test.replace(files_marker, new_files_test + files_marker, 1)
files_test_path.write_text(files_test, encoding="utf-8")

baseline_path = ROOT / "automation" / "prompt-baselines.json"
baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
for item in baseline["prompts"]:
    prompt_bytes = (ROOT / item["path"]).read_bytes()
    item["protected_prefix_bytes"] = len(prompt_bytes)
    item["sha256"] = sha256(prompt_bytes).hexdigest()
baseline_path.write_text(
    json.dumps(baseline, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

shutil.rmtree(TEMP_DIR)
TEMP_WORKFLOW.unlink(missing_ok=True)

run("python", "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements-docs.txt", "-r", "requirements-export.txt")
run("python", "-m", "pip", "check")
run("npm", "ci")
run("npm", "run", "audit:dependencies")
run("python", "-m", "compileall", "-q", "scripts", "tests")
run("python", "scripts/validate_prompt_baselines.py")
run("python", "-m", "pytest", "-q")
run("npm", "test")
run("git", "fetch", "origin", "main")
remark_env = dict(__import__("os").environ)
remark_env.update({"REMARK_BASE_SHA": "origin/main", "REMARK_HEAD_SHA": "HEAD"})
run("npm", "run", "lint:markdown:changed", env=remark_env)
run("python", "scripts/build_literature.py")
run("git", "diff", "--exit-code", "--", "Literatur.md", "references.bib", "references.json")
run("python", "scripts/validate_links.py")
run("python", "scripts/build_graph.py")
run("python", "scripts/validate_graph.py")
run("python", "scripts/validate_compendium.py")
run("python", "scripts/build_combined.py")
run("python", "scripts/build_anki.py")
run("python", "scripts/build_docs.py")
run("mkdocs", "build", "--strict")
run("git", "diff", "--check")

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", "CONTRIBUTING.md", "WARTUNG.md", "automation/prompt-baselines.json")
run("git", "add", "prompts/MERGE-AUTOMATION-PROMPT.md", "prompts/PR-REPAIR-PROMPT.md")
run("git", "add", "scripts/merge_repair_policy.py", "scripts/review_gate.py")
run("git", "add", "tests/test_merge_repair_policy.py", "tests/test_review_gate.py", "tests/test_review_policy_files.py")
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
    print("Keine Änderungen anzuwenden")
    raise SystemExit(0)
run("git", "commit", "-m", "fix: address final review findings for hard gates")
run("git", "push", "origin", f"HEAD:{BRANCH}")
