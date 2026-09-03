from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class LearningCardPolicyFileTests(unittest.TestCase):
    def test_policy_workflow_uses_least_privilege_and_can_publish_check(self) -> None:
        path = ROOT / ".github/workflows/learning-card-policy.yml"
        text = path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(text)
        self.assertIsInstance(parsed, dict)
        permissions = parsed.get("permissions")
        self.assertIsInstance(permissions, dict)
        self.assertEqual(permissions.get("contents"), "read")
        self.assertEqual(permissions.get("pull-requests"), "read")
        self.assertEqual(permissions.get("issues"), "read")
        self.assertEqual(permissions.get("checks"), "write")
        self.assertEqual(permissions.get("statuses"), "none")
        self.assertEqual(
            {key for key, value in permissions.items() if value == "write"},
            {"checks"},
        )

        self.assertIn("Learning card policy (blocking)", text)
        self.assertIn("pull_request_target", text)
        self.assertIn("workflow_run", text)
        self.assertIn('"CodeRabbit hard gate"', text)
        self.assertIn("ref: main", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("--publish-check", text)
        self.assertNotIn("paths:", text)

    def test_coderabbit_config_enforces_scoped_semantic_error_checks(self) -> None:
        config = yaml.safe_load(
            (ROOT / ".coderabbit.yaml").read_text(encoding="utf-8")
        )
        reviews = config["reviews"]
        self.assertTrue(reviews["request_changes_workflow"])
        pre_merge = reviews["pre_merge_checks"]
        self.assertTrue(pre_merge["override_requested_reviewers_only"])
        checks = {
            check["name"]: check for check in pre_merge["custom_checks"]
        }
        self.assertEqual(
            set(checks),
            {"content-scope", "claim-source-entailment"},
        )
        self.assertTrue(
            all(check["mode"] == "error" for check in checks.values())
        )
        self.assertIn("association", checks["content-scope"]["instructions"])
        self.assertIn("population", checks["claim-source-entailment"]["instructions"])
        for check in checks.values():
            instructions = check["instructions"]
            self.assertIn("current pull request diff", instructions)
            self.assertIn("current base branch", instructions)
            self.assertIn("Ignore historical commits", instructions)
            self.assertIn("Pass immediately as not applicable", instructions)

    def test_hard_gate_enforces_coderabbit_review_state(self) -> None:
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/coderabbit-hard-gate.yml").read_text(
                encoding="utf-8"
            )
        )
        job = workflow["jobs"]["review-gate"]
        steps = job["steps"]
        enforcement = [
            step
            for step in steps
            if step.get("name") == "Enforce current CodeRabbit review state"
        ]
        self.assertEqual(len(enforcement), 1)
        step = enforcement[0]
        self.assertEqual(step.get("if"), "steps.pr.outputs.skip != 'true'")
        self.assertIsNot(step.get("continue-on-error"), True)
        run = str(step.get("run") or "")
        self.assertIn("python scripts/coderabbit_review_state.py", run)
        self.assertIn("--repository", run)
        self.assertIn("--pr-number", run)

    def test_policy_document_separates_router_semantics_and_build(self) -> None:
        text = (ROOT / "automation/LEARNING-CARD-POLICY.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "Der deterministische Router beantwortet ausschließlich die erste Frage",
            text,
        )
        self.assertIn("content-scope", text)
        self.assertIn("claim-source-entailment", text)
        self.assertIn("complete-build", text)
        self.assertIn("Workflow- oder Gatecode ohne Lernkarte", text)
        self.assertIn("checks: write", text)
        self.assertIn("PR-Head", text)

    def test_ruleset_target_is_valid_json_and_requires_aggregator(self) -> None:
        target = json.loads(
            (
                ROOT / "automation/rulesets/main-required-gates.target.json"
            ).read_text(encoding="utf-8")
        )
        status_rule = next(
            rule
            for rule in target["rules"]
            if rule["type"] == "required_status_checks"
        )
        names = {
            check["context"]
            for check in status_rule["parameters"]["required_status_checks"]
        }
        self.assertIn("Learning card policy (blocking)", names)
        self.assertNotIn("content-scope", names)
        self.assertNotIn("claim-source-entailment", names)
        self.assertNotIn("complete-build", names)


if __name__ == "__main__":
    unittest.main()
