from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from learning_card_policy import classify_pull_request, evaluate_policy

HEAD = "a" * 40


def changed(filename: str) -> dict[str, str]:
    return {"filename": filename, "status": "modified"}


class ManualAutomationPolicyTests(unittest.TestCase):
    def test_sensitive_automation_without_marker_blocks_policy(self) -> None:
        scope = classify_pull_request(
            files=[changed(".github/workflows/validate.yml")],
            head_ref="feature/ci",
            body="",
        )
        result = evaluate_policy(scope=scope, check_runs=[], head_sha=HEAD)
        self.assertFalse(result.passed)
        self.assertTrue(result.manual_merge_required)
        self.assertTrue(
            any(
                "Marker manual-merge-required fehlt" in reason
                for reason in result.reasons
            )
        )

    def test_sensitive_automation_with_marker_is_explicitly_manual_but_not_semantic(self) -> None:
        scope = classify_pull_request(
            files=[changed(".github/workflows/validate.yml")],
            head_ref="feature/ci",
            body="<!-- manual-merge-required -->",
        )
        result = evaluate_policy(scope=scope, check_runs=[], head_sha=HEAD)
        self.assertTrue(result.passed)
        self.assertTrue(result.manual_merge_required)
        self.assertEqual(result.subgates["content_scope"], "not_applicable")


if __name__ == "__main__":
    unittest.main()
