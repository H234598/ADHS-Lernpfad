from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from coderabbit_review_state import evaluate_coderabbit_review_state


def review(
    state: str,
    *,
    submitted_at: str,
    author: str = "coderabbitai[bot]",
    review_id: int = 1,
) -> dict[str, object]:
    return {
        "id": review_id,
        "state": state,
        "submitted_at": submitted_at,
        "user": {"login": author},
    }


class CodeRabbitReviewStateTests(unittest.TestCase):
    def test_changes_requested_blocks_even_when_status_signal_is_green(self) -> None:
        state, reasons = evaluate_coderabbit_review_state(
            [
                review(
                    "CHANGES_REQUESTED",
                    submitted_at="2026-08-12T12:00:00Z",
                )
            ]
        )
        self.assertEqual(state, "changes_requested")
        self.assertTrue(
            any("Änderungen angefordert" in reason for reason in reasons)
        )

    def test_later_comment_does_not_clear_changes_request(self) -> None:
        state, reasons = evaluate_coderabbit_review_state(
            [
                review(
                    "CHANGES_REQUESTED",
                    submitted_at="2026-08-12T11:00:00Z",
                    review_id=1,
                ),
                review(
                    "COMMENTED",
                    submitted_at="2026-08-12T12:00:00Z",
                    review_id=2,
                ),
            ]
        )
        self.assertEqual(state, "changes_requested")
        self.assertTrue(reasons)

    def test_later_approval_clears_earlier_changes_request(self) -> None:
        state, reasons = evaluate_coderabbit_review_state(
            [
                review(
                    "CHANGES_REQUESTED",
                    submitted_at="2026-08-12T11:00:00Z",
                    review_id=1,
                ),
                review(
                    "APPROVED",
                    submitted_at="2026-08-12T12:00:00Z",
                    review_id=2,
                ),
            ]
        )
        self.assertEqual(state, "approved")
        self.assertEqual(reasons, [])

    def test_non_coderabbit_reviews_cannot_satisfy_or_block_gate(self) -> None:
        state, reasons = evaluate_coderabbit_review_state(
            [
                review(
                    "CHANGES_REQUESTED",
                    submitted_at="2026-08-12T12:00:00Z",
                    author="external-reviewer",
                )
            ]
        )
        self.assertEqual(state, "none")
        self.assertEqual(reasons, [])

    def test_commented_or_missing_review_does_not_replace_status_gate(self) -> None:
        for reviews, expected in (
            ([], "none"),
            (
                [
                    review(
                        "COMMENTED",
                        submitted_at="2026-08-12T12:00:00Z",
                    )
                ],
                "commented",
            ),
        ):
            with self.subTest(reviews=reviews):
                state, reasons = evaluate_coderabbit_review_state(reviews)
                self.assertEqual(state, expected)
                self.assertEqual(reasons, [])

    def test_dismissed_review_does_not_keep_obsolete_request_changes(self) -> None:
        state, reasons = evaluate_coderabbit_review_state(
            [
                review(
                    "DISMISSED",
                    submitted_at="2026-08-12T12:00:00Z",
                    review_id=1,
                )
            ]
        )
        self.assertEqual(state, "dismissed")
        self.assertEqual(reasons, [])


if __name__ == "__main__":
    unittest.main()
