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
        self.assertEqual(
            permissions,
            {
                "contents": "read",
                "pull-requests": "read",
                "issues": "read",
                "checks": "write",
                "statuses": "none",
            },
        )

        self.assertIn("Learning card policy (blocking)", text)
        self.assertIn("pull_request_target", text)
        self.assertIn("workflow_run", text)
        self.assertIn('"CodeRabbit hard gate"', text)
        self.assertIn("ref: main", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("--publish-check", text)
        self.assertNotIn("paths:", text)

    def test_pages_write_permissions_are_scoped_to_deploy_job(self) -> None:
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        )
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertNotIn("permissions", workflow["jobs"]["build"])
        self.assertEqual(
            workflow["jobs"]["deploy"]["permissions"],
            {"pages": "write", "id-token": "write"},
        )

    def test_dangerous_trigger_exceptions_are_narrow_and_security_guarded(self) -> None:
        hard_path = ROOT / ".github/workflows/coderabbit-hard-gate.yml"
        hard_text = hard_path.read_text(encoding="utf-8")
        hard = yaml.safe_load(hard_text)
        self.assertGreaterEqual(
            hard_text.count("zizmor: ignore[dangerous-triggers]"),
            2,
        )
        self.assertTrue(
            all(value in {"read", "none"} for value in hard["permissions"].values())
        )
        hard_checkout = next(
            step
            for step in hard["jobs"]["review-gate"]["steps"]
            if step.get("name") == "Checkout trusted gate implementation from main"
        )
        self.assertEqual(hard_checkout["with"]["ref"], "main")
        self.assertFalse(hard_checkout["with"]["persist-credentials"])

        persist_path = ROOT / ".github/workflows/persist-automation-status.yml"
        persist_text = persist_path.read_text(encoding="utf-8")
        persist = yaml.safe_load(persist_text)
        self.assertIn("zizmor: ignore[dangerous-triggers]", persist_text)
        persist_job = persist["jobs"]["persist"]
        self.assertEqual(
            persist_job["if"],
            "github.event.workflow_run.head_repository.full_name == github.repository",
        )
        persist_checkout = next(
            step
            for step in persist_job["steps"]
            if step.get("name") == "Check out trusted implementation from main"
        )
        self.assertEqual(persist_checkout["with"]["ref"], "main")
        self.assertIn("without executing them", persist_text)
        self.assertIn("persist_automation_status.py", persist_text)

    def test_manual_merge_authorization_is_explicit_trusted_dispatch_input(self) -> None:
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/learning-card-policy.yml").read_text(
                encoding="utf-8"
            )
        )
        dispatch = workflow[True]["workflow_dispatch"] if True in workflow else workflow["on"]["workflow_dispatch"]
        inputs = dispatch["inputs"]
        authorization = inputs["manual_merge_authorized"]
        self.assertEqual(authorization["type"], "boolean")
        self.assertFalse(authorization["default"])
        step = next(
            step
            for step in workflow["jobs"]["policy"]["steps"]
            if step.get("name") == "Evaluate and publish current-head learning-card policy"
        )
        self.assertEqual(
            step["env"]["MANUAL_MERGE_AUTHORIZED"],
            "${{ inputs.manual_merge_authorized }}",
        )
        run = str(step["run"])
        self.assertNotIn("inputs.manual_merge_authorized", run)
        self.assertIn("--manual-merge-authorized", run)

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
        self.assertIn("workflow_dispatch", text)
        self.assertIn("manual_merge_authorized", text)

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
