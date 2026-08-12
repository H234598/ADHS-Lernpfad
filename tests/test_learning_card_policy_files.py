from __future__ import annotations

from pathlib import Path
import json
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class LearningCardPolicyFileTests(unittest.TestCase):
    def test_policy_workflow_is_always_reporting_and_read_only(self) -> None:
        path = ROOT / ".github/workflows/learning-card-policy.yml"
        text = path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(text)
        self.assertIsInstance(parsed, dict)
        self.assertIn("Learning card policy (blocking)", text)
        self.assertIn("pull_request_target", text)
        self.assertIn("workflow_run", text)
        self.assertIn('"CodeRabbit hard gate"', text)
        self.assertIn("ref: main", text)
        self.assertIn("persist-credentials: false", text)
        self.assertNotIn("paths:", text)
        self.assertNotIn("write", text)

    def test_coderabbit_config_enforces_two_semantic_error_checks(self) -> None:
        config = yaml.safe_load((ROOT / ".coderabbit.yaml").read_text(encoding="utf-8"))
        reviews = config["reviews"]
        self.assertTrue(reviews["request_changes_workflow"])
        pre_merge = reviews["pre_merge_checks"]
        self.assertTrue(pre_merge["override_requested_reviewers_only"])
        checks = {check["name"]: check for check in pre_merge["custom_checks"]}
        self.assertEqual(set(checks), {"content-scope", "claim-source-entailment"})
        self.assertTrue(all(check["mode"] == "error" for check in checks.values()))
        self.assertIn("association", checks["content-scope"]["instructions"])
        self.assertIn("population", checks["claim-source-entailment"]["instructions"])

    def test_hard_gate_enforces_coderabbit_review_state(self) -> None:
        text = (ROOT / ".github/workflows/coderabbit-hard-gate.yml").read_text(encoding="utf-8")
        self.assertIn("coderabbit_review_state.py", text)
        self.assertIn("Enforce current CodeRabbit review state", text)

    def test_policy_document_separates_router_semantics_and_build(self) -> None:
        text = (ROOT / "automation/LEARNING-CARD-POLICY.md").read_text(encoding="utf-8")
        self.assertIn(
            "Der deterministische Router beantwortet ausschließlich die erste Frage",
            text,
        )
        self.assertIn("content-scope", text)
        self.assertIn("claim-source-entailment", text)
        self.assertIn("complete-build", text)
        self.assertIn("Workflow- oder Gatecode ohne Lernkarte", text)

    def test_ruleset_target_is_valid_json_and_requires_aggregator(self) -> None:
        target = json.loads(
            (ROOT / "automation/rulesets/main-required-gates.target.json").read_text(
                encoding="utf-8"
            )
        )
        status_rule = next(
            rule for rule in target["rules"] if rule["type"] == "required_status_checks"
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
