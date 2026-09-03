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
    def scope(self, *, marker: bool):
        return classify_pull_request(
            files=[changed(".github/workflows/validate.yml")],
            head_ref="feature/ci",
            body="<!-- manual-merge-required -->" if marker else "",
        )

    def test_sensitive_automation_without_marker_blocks_policy(self) -> None:
        result = evaluate_policy(
            scope=self.scope(marker=False),
            check_runs=[],
            head_sha=HEAD,
        )
        self.assertFalse(result.passed)
        self.assertTrue(result.manual_merge_required)
        self.assertTrue(
            any(
                "Marker manual-merge-required fehlt" in reason
                for reason in result.reasons
            )
        )

    def test_marker_alone_is_not_trusted_manual_authorization(self) -> None:
        result = evaluate_policy(
            scope=self.scope(marker=True),
            check_runs=[],
            head_sha=HEAD,
        )
        self.assertFalse(result.passed)
        self.assertTrue(result.manual_merge_required)
        self.assertTrue(
            any(
                "vertrauenswürdige Human-Freigabe" in reason
                for reason in result.reasons
            )
        )
        self.assertEqual(result.subgates["content_scope"], "not_applicable")

    def test_dispatch_authorization_plus_marker_allows_automation_only_policy(self) -> None:
        result = evaluate_policy(
            scope=self.scope(marker=True),
            check_runs=[],
            head_sha=HEAD,
            manual_merge_authorized=True,
        )
        self.assertTrue(result.passed)
        self.assertTrue(result.manual_merge_required)
        self.assertEqual(result.subgates["content_scope"], "not_applicable")

    def test_trusted_authorization_without_declaration_marker_still_blocks(self) -> None:
        result = evaluate_policy(
            scope=self.scope(marker=False),
            check_runs=[],
            head_sha=HEAD,
            manual_merge_authorized=True,
        )
        self.assertFalse(result.passed)
        self.assertTrue(
            any(
                "Marker manual-merge-required fehlt" in reason
                for reason in result.reasons
            )
        )


if __name__ == "__main__":
    unittest.main()
