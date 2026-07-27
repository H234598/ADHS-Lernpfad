from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from review_gate import evaluate_gate, is_coderabbit_signal

HEAD = "a" * 40


class ReviewGateTests(unittest.TestCase):
    def success_signal(self):
        return [{"name": "CodeRabbit", "state": "success", "updated_at": "2026-07-27T12:00:00Z"}]

    def thread(self, *, resolved: bool, outdated: bool = False, author: str = "coderabbitai"):
        return {
            "id": "thread-1",
            "isResolved": resolved,
            "isOutdated": outdated,
            "comments": {"nodes": [{"author": {"login": author}, "body": "Hinweis"}]},
        }

    def comment(self, body: str, created_at: str):
        return {"body": body, "created_at": created_at}

    def test_real_coderabbit_signal_is_detected(self) -> None:
        self.assertTrue(is_coderabbit_signal("CodeRabbit"))
        self.assertTrue(is_coderabbit_signal("Review", "coderabbitai"))

    def test_hard_gate_does_not_count_itself_as_coderabbit(self) -> None:
        self.assertFalse(is_coderabbit_signal("CodeRabbit review gate (blocking)"))
        self.assertFalse(
            is_coderabbit_signal("CodeRabbit review gate (blocking)", "GitHub Actions")
        )

    def test_success_requires_signal_and_no_open_threads(self) -> None:
        state, unresolved, reasons, disagreement = evaluate_gate(
            signals=self.success_signal(), threads=[], comments=[], head_sha=HEAD
        )
        self.assertEqual(state, "success")
        self.assertEqual(unresolved, [])
        self.assertEqual(reasons, [])
        self.assertFalse(disagreement)

    def test_missing_signal_blocks(self) -> None:
        state, unresolved, reasons, disagreement = evaluate_gate(
            signals=[], threads=[], comments=[], head_sha=HEAD
        )
        self.assertEqual(state, "missing")
        self.assertTrue(reasons)
        self.assertFalse(disagreement)

    def test_unresolved_outdated_coderabbit_thread_still_blocks(self) -> None:
        state, unresolved, reasons, disagreement = evaluate_gate(
            signals=self.success_signal(),
            threads=[self.thread(resolved=False, outdated=True)],
            comments=[],
            head_sha=HEAD,
        )
        self.assertEqual(state, "success")
        self.assertEqual(unresolved, ["thread-1"])
        self.assertTrue(any("veraltete Threads" in reason for reason in reasons))
        self.assertFalse(disagreement)

    def test_non_coderabbit_thread_does_not_block_gate(self) -> None:
        state, unresolved, reasons, disagreement = evaluate_gate(
            signals=self.success_signal(),
            threads=[self.thread(resolved=False, author="human-reviewer")],
            comments=[],
            head_sha=HEAD,
        )
        self.assertEqual(state, "success")
        self.assertEqual(unresolved, [])
        self.assertFalse(disagreement)

    def test_open_disagreement_blocks(self) -> None:
        state, unresolved, reasons, disagreement = evaluate_gate(
            signals=self.success_signal(),
            threads=[],
            comments=[
                self.comment(
                    f"<!-- coderabbit-disagreement head={HEAD} -->",
                    "2026-07-27T12:00:00Z",
                )
            ],
            head_sha=HEAD,
        )
        self.assertTrue(disagreement)
        self.assertTrue(any("Konflikt" in reason for reason in reasons))

    def test_resolved_disagreement_no_longer_blocks(self) -> None:
        state, unresolved, reasons, disagreement = evaluate_gate(
            signals=self.success_signal(),
            threads=[],
            comments=[
                self.comment(
                    f"<!-- coderabbit-disagreement head={HEAD} -->",
                    "2026-07-27T12:00:00Z",
                ),
                self.comment(
                    f"<!-- coderabbit-disagreement-resolved head={HEAD} -->",
                    "2026-07-27T13:00:00Z",
                ),
            ],
            head_sha=HEAD,
        )
        self.assertFalse(disagreement)
        self.assertEqual(reasons, [])


if __name__ == "__main__":
    unittest.main()
