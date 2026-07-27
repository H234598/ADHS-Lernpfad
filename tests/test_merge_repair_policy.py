from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from merge_repair_policy import evaluate_policy, policy_deadlines

BERLIN = ZoneInfo("Europe/Berlin")


class MergeRepairPolicyTests(unittest.TestCase):
    def created(self) -> datetime:
        return datetime(2026, 7, 27, 6, 0, tzinfo=BERLIN)

    def evaluate(self, hour: int, **overrides):
        values = {
            "created_at": self.created(),
            "now": datetime(2026, 7, 27, hour, 0, tzinfo=BERLIN),
            "ci_state": "failure",
            "coderabbit_state": "success",
            "unresolved_threads": 0,
            "disagreement": False,
            "draft": True,
            "second_ci_state": "missing",
        }
        values.update(overrides)
        return evaluate_policy(**values)

    def test_deadline_is_same_day_at_20_berlin(self) -> None:
        review_at, repair_at = policy_deadlines(self.created())
        self.assertEqual(review_at.hour, 8)
        self.assertEqual(repair_at.hour, 20)
        self.assertEqual(repair_at.date(), self.created().date())

    def test_late_pr_still_gets_two_full_hours(self) -> None:
        created = datetime(2026, 7, 27, 21, 15, tzinfo=BERLIN)
        review_at, repair_at = policy_deadlines(created)
        self.assertEqual(review_at.hour, 23)
        self.assertEqual(review_at.minute, 15)
        self.assertEqual(repair_at, review_at)

    def test_red_ci_before_20_waits_without_repair(self) -> None:
        result = self.evaluate(12)
        self.assertEqual(result.action, "wait_until_repair_window")
        self.assertFalse(result.repair_allowed)

    def test_red_ci_at_20_starts_repair(self) -> None:
        result = self.evaluate(20)
        self.assertEqual(result.action, "repair_existing_branch")
        self.assertTrue(result.repair_allowed)

    def test_red_ci_after_deadline_repairs_even_if_coderabbit_is_pending(self) -> None:
        result = self.evaluate(21, coderabbit_state="pending")
        self.assertEqual(result.action, "repair_existing_branch")
        self.assertTrue(result.repair_allowed)

    def test_pending_coderabbit_waits_when_ci_is_green(self) -> None:
        result = self.evaluate(21, ci_state="success", coderabbit_state="pending")
        self.assertEqual(result.action, "wait_coderabbit")
        self.assertTrue(result.hard_blocker)

    def test_missing_coderabbit_is_hard_blocker_when_ci_is_green(self) -> None:
        result = self.evaluate(21, ci_state="success", coderabbit_state="missing")
        self.assertEqual(result.action, "wait_coderabbit")
        self.assertTrue(result.hard_blocker)

    def test_unresolved_thread_repairs_only_after_deadline(self) -> None:
        early = self.evaluate(12, ci_state="success", unresolved_threads=2)
        late = self.evaluate(20, ci_state="success", unresolved_threads=2)
        self.assertEqual(early.action, "wait_until_repair_window")
        self.assertFalse(early.repair_allowed)
        self.assertEqual(late.action, "repair_existing_branch")
        self.assertTrue(late.repair_allowed)

    def test_red_second_ci_repairs_after_deadline_despite_pending_review(self) -> None:
        result = self.evaluate(
            21,
            ci_state="success",
            coderabbit_state="pending",
            draft=False,
            second_ci_state="failure",
        )
        self.assertEqual(result.action, "repair_existing_branch")
        self.assertTrue(result.repair_allowed)

    def test_disagreement_is_manual_hard_blocker(self) -> None:
        result = self.evaluate(21, ci_state="success", disagreement=True)
        self.assertEqual(result.action, "manual_intervention")
        self.assertTrue(result.hard_blocker)
        self.assertFalse(result.repair_allowed)

    def test_green_draft_can_become_ready(self) -> None:
        result = self.evaluate(12, ci_state="success", coderabbit_state="success")
        self.assertEqual(result.action, "ready_for_review")

    def test_green_second_ci_can_merge(self) -> None:
        result = self.evaluate(
            21,
            ci_state="success",
            coderabbit_state="success",
            draft=False,
            second_ci_state="success",
        )
        self.assertEqual(result.action, "merge")


if __name__ == "__main__":
    unittest.main()
