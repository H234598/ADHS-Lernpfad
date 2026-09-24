"""Bootstrap contracts for trusted CodeRabbit publication from main."""

from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

review_state = importlib.import_module("coderabbit_review_state")


class TrustedCodeRabbitPublisherBootstrapTests(unittest.TestCase):
    """Protect the default-branch trust boundary used by PR #67."""

    def test_review_state_supports_fail_closed_dismissed_recheck(self) -> None:
        """Trusted main must understand the final dismissed-review recheck."""
        self.assertTrue(hasattr(review_state, "review_state_blocks"))
        blocker = getattr(review_state, "review_state_blocks", None)
        self.assertIsNotNone(blocker)
        if blocker is None:
            return
        self.assertFalse(blocker("dismissed"))
        self.assertTrue(blocker("dismissed", block_dismissed=True))
        self.assertTrue(blocker("changes_requested", block_dismissed=True))
        self.assertFalse(blocker("approved", block_dismissed=True))

    def test_trusted_publisher_workflow_is_default_branch_only(self) -> None:
        """Only a main-defined workflow may hold checks:write."""
        path = ROOT / ".github/workflows/coderabbit-trusted-publisher.yml"
        self.assertTrue(path.exists(), "trusted publisher workflow fehlt")
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))

        self.assertEqual(
            workflow["permissions"],
            {
                "contents": "read",
                "pull-requests": "read",
                "checks": "write",
            },
        )
        trigger = workflow[True] if True in workflow else workflow["on"]
        self.assertEqual(
            trigger["workflow_run"]["workflows"],
            ["CodeRabbit hard gate"],
        )
        self.assertEqual(trigger["workflow_run"]["types"], ["completed"])

        job = workflow["jobs"]["publish"]
        checkout = next(
            step
            for step in job["steps"]
            if step.get("name") == "Checkout trusted implementation from main"
        )
        self.assertEqual(checkout["with"]["ref"], "main")
        self.assertFalse(checkout["with"]["persist-credentials"])

        run_text = "\n".join(
            str(step.get("run") or "") for step in job["steps"]
        )
        self.assertIn("review_gate.py", run_text)
        self.assertIn("coderabbit_review_state.py", run_text)
        self.assertIn("--block-dismissed", run_text)
        self.assertIn("publish_review_gate_check.py", run_text)


if __name__ == "__main__":
    unittest.main()
