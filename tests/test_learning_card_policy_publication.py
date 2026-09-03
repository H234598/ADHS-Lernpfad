from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import learning_card_policy
from learning_card_checks import PolicyDecision

HEAD = "a" * 40


class LearningCardPolicyPublicationTests(unittest.TestCase):
    def decision(self, *, passed: bool) -> PolicyDecision:
        return PolicyDecision(
            head_sha=HEAD,
            passed=passed,
            subgates={
                "content_scope": "success" if passed else "failure",
                "claim_source_entailment": "success" if passed else "failure",
                "complete_build": "success",
            },
            required_checks={},
            manual_merge_required=False,
            reasons=() if passed else ("Semantisches Subgate blockiert.",),
        )

    def test_success_is_published_as_check_run_on_pr_head(self) -> None:
        with patch.object(learning_card_policy, "request_json") as request:
            learning_card_policy._publish_check(
                "H234598/ADHS-Lernpfad",
                "token",
                self.decision(passed=True),
            )

        self.assertEqual(
            request.call_args.args[0],
            "https://api.github.com/repos/H234598/ADHS-Lernpfad/check-runs",
        )
        self.assertEqual(request.call_args.args[1], "token")
        self.assertEqual(request.call_args.kwargs["method"], "POST")
        payload = request.call_args.kwargs["data"]
        self.assertEqual(payload["name"], learning_card_policy.POLICY_CHECK_NAME)
        self.assertEqual(payload["head_sha"], HEAD)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["conclusion"], "success")

    def test_blocked_decision_publishes_failure(self) -> None:
        with patch.object(learning_card_policy, "request_json") as request:
            learning_card_policy._publish_check(
                "H234598/ADHS-Lernpfad",
                "token",
                self.decision(passed=False),
            )

        payload = request.call_args.kwargs["data"]
        self.assertEqual(payload["head_sha"], HEAD)
        self.assertEqual(payload["conclusion"], "failure")
        self.assertIn("Semantisches Subgate blockiert", payload["output"]["summary"])


if __name__ == "__main__":
    unittest.main()
