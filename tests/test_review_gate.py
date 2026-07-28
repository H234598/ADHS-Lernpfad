from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from review_gate import (
    _latest_coderabbit_signals,
    evaluate_gate,
    is_coderabbit_author,
    is_coderabbit_signal,
    is_trusted_resolution_author,
)

HEAD = "a" * 40
OLD_HEAD = "b" * 40
OWNER = "H234598"


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

    def comment(self, body: str, created_at: str, author: str = OWNER):
        return {"body": body, "created_at": created_at, "user": {"login": author}}

    def evaluate(self, **kwargs):
        return evaluate_gate(
            trusted_resolution_authors={OWNER},
            **kwargs,
        )

    def test_real_coderabbit_signal_is_detected(self) -> None:
        self.assertTrue(is_coderabbit_signal("CodeRabbit"))
        self.assertTrue(is_coderabbit_signal("Review", "coderabbitai"))

    def test_hard_gate_does_not_count_itself_as_coderabbit(self) -> None:
        self.assertFalse(is_coderabbit_signal("CodeRabbit review gate (blocking)"))
        self.assertFalse(
            is_coderabbit_signal("CodeRabbit review gate (blocking)", "GitHub Actions")
        )

    def test_coderabbit_commenter_allowlist_is_strict(self) -> None:
        self.assertTrue(is_coderabbit_author("coderabbitai"))
        self.assertTrue(is_coderabbit_author("coderabbitai[bot]"))
        self.assertFalse(is_coderabbit_author("not-coderabbit"))
        self.assertFalse(is_coderabbit_author("coderabbit-helper"))

    def test_trusted_resolvers_include_owner_and_coderabbit(self) -> None:
        trusted = {OWNER}
        self.assertTrue(is_trusted_resolution_author(OWNER, trusted))
        self.assertTrue(is_trusted_resolution_author("coderabbitai[bot]", trusted))
        self.assertFalse(is_trusted_resolution_author("external-reviewer", trusted))

    def test_in_progress_signal_is_pending_not_failure(self) -> None:
        state, unresolved, reasons, disagreement = self.evaluate(
            signals=[{"name": "CodeRabbit", "state": "in_progress"}],
            threads=[],
            comments=[],
            head_sha=HEAD,
        )
        self.assertEqual(state, "pending")
        self.assertEqual(unresolved, [])
        self.assertTrue(any("läuft noch" in reason for reason in reasons))
        self.assertFalse(disagreement)

    def test_neutral_and_skipped_signals_do_not_pass(self) -> None:
        for signal_state in ("neutral", "skipped"):
            with self.subTest(state=signal_state):
                state, unresolved, reasons, disagreement = self.evaluate(
                    signals=[{"name": "CodeRabbit", "state": signal_state}],
                    threads=[],
                    comments=[],
                    head_sha=HEAD,
                )
                self.assertEqual(state, "pending")
                self.assertEqual(unresolved, [])
                self.assertTrue(any("läuft noch" in reason for reason in reasons))
                self.assertFalse(disagreement)

    def test_failure_takes_precedence_over_pending_signal(self) -> None:
        state, unresolved, reasons, disagreement = self.evaluate(
            signals=[
                {"name": "CodeRabbit", "state": "queued"},
                {"name": "CodeRabbit review", "state": "failure"},
            ],
            threads=[],
            comments=[],
            head_sha=HEAD,
        )
        self.assertEqual(state, "failure")
        self.assertEqual(unresolved, [])
        self.assertTrue(any("fehlgeschlagen" in reason for reason in reasons))
        self.assertFalse(disagreement)

    def test_check_runs_are_paginated_before_signal_selection(self) -> None:
        def fake_request(url: str, token: str, *, data=None):
            del token, data
            if url.endswith("/status"):
                return {"statuses": []}
            if "&page=1" in url:
                return {
                    "check_runs": [
                        {
                            "name": f"unrelated-{index}",
                            "app": {"name": "GitHub Actions"},
                        }
                        for index in range(100)
                    ]
                }
            if "&page=2" in url:
                return {
                    "check_runs": [
                        {
                            "name": "CodeRabbit",
                            "app": {"name": "coderabbitai"},
                            "status": "completed",
                            "conclusion": "success",
                            "completed_at": "2026-07-27T20:00:00Z",
                            "html_url": "https://example.invalid/check",
                        }
                    ]
                }
            raise AssertionError(f"Unerwartete URL: {url}")

        with patch("review_gate._request_json", side_effect=fake_request):
            signals = _latest_coderabbit_signals("owner/repo", HEAD, "token")

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["state"], "success")
        self.assertIn("CodeRabbit", signals[0]["name"])

    def test_success_requires_signal_and_no_open_threads(self) -> None:
        state, unresolved, reasons, disagreement = self.evaluate(
            signals=self.success_signal(), threads=[], comments=[], head_sha=HEAD
        )
        self.assertEqual(state, "success")
        self.assertEqual(unresolved, [])
        self.assertEqual(reasons, [])
        self.assertFalse(disagreement)

    def test_missing_signal_blocks(self) -> None:
        state, unresolved, reasons, disagreement = self.evaluate(
            signals=[], threads=[], comments=[], head_sha=HEAD
        )
        self.assertEqual(state, "missing")
        self.assertTrue(reasons)
        self.assertFalse(disagreement)

    def test_unresolved_outdated_coderabbit_thread_still_blocks(self) -> None:
        state, unresolved, reasons, disagreement = self.evaluate(
            signals=self.success_signal(),
            threads=[self.thread(resolved=False, outdated=True)],
            comments=[],
            head_sha=HEAD,
        )
        self.assertEqual(state, "success")
        self.assertEqual(unresolved, ["thread-1"])
        self.assertTrue(any("veraltete Threads" in reason for reason in reasons))
        self.assertFalse(disagreement)

    def test_similarly_named_untrusted_thread_does_not_block(self) -> None:
        state, unresolved, reasons, disagreement = self.evaluate(
            signals=self.success_signal(),
            threads=[self.thread(resolved=False, author="coderabbit-helper")],
            comments=[],
            head_sha=HEAD,
        )
        self.assertEqual(state, "success")
        self.assertEqual(unresolved, [])
        self.assertFalse(disagreement)

    def test_non_coderabbit_thread_does_not_block_gate(self) -> None:
        state, unresolved, reasons, disagreement = self.evaluate(
            signals=self.success_signal(),
            threads=[self.thread(resolved=False, author="human-reviewer")],
            comments=[],
            head_sha=HEAD,
        )
        self.assertEqual(state, "success")
        self.assertEqual(unresolved, [])
        self.assertFalse(disagreement)

    def test_open_disagreement_blocks(self) -> None:
        state, unresolved, reasons, disagreement = self.evaluate(
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

    def test_open_disagreement_from_prior_head_survives_new_commit(self) -> None:
        state, unresolved, reasons, disagreement = self.evaluate(
            signals=self.success_signal(),
            threads=[],
            comments=[
                self.comment(
                    f"<!-- coderabbit-disagreement head={OLD_HEAD} -->",
                    "2026-07-27T12:00:00Z",
                )
            ],
            head_sha=HEAD,
        )
        self.assertTrue(disagreement)
        self.assertTrue(any(OLD_HEAD in reason for reason in reasons))

    def test_repository_owner_can_resolve_disagreement(self) -> None:
        state, unresolved, reasons, disagreement = self.evaluate(
            signals=self.success_signal(),
            threads=[],
            comments=[
                self.comment(
                    f"<!-- coderabbit-disagreement head={HEAD} -->",
                    "2026-07-27T12:00:00Z",
                    author="agent-reporter",
                ),
                self.comment(
                    f"<!-- coderabbit-disagreement-resolved head={HEAD} -->",
                    "2026-07-27T13:00:00Z",
                    author=OWNER,
                ),
            ],
            head_sha=HEAD,
        )
        self.assertFalse(disagreement)
        self.assertEqual(reasons, [])

    def test_coderabbit_can_resolve_disagreement(self) -> None:
        state, unresolved, reasons, disagreement = self.evaluate(
            signals=self.success_signal(),
            threads=[],
            comments=[
                self.comment(
                    f"<!-- coderabbit-disagreement head={HEAD} -->",
                    "2026-07-27T12:00:00Z",
                    author="agent-reporter",
                ),
                self.comment(
                    f"<!-- coderabbit-disagreement-resolved head={HEAD} -->",
                    "2026-07-27T13:00:00Z",
                    author="coderabbitai[bot]",
                ),
            ],
            head_sha=HEAD,
        )
        self.assertFalse(disagreement)
        self.assertEqual(reasons, [])

    def test_untrusted_commenter_cannot_resolve_disagreement(self) -> None:
        state, unresolved, reasons, disagreement = self.evaluate(
            signals=self.success_signal(),
            threads=[],
            comments=[
                self.comment(
                    f"<!-- coderabbit-disagreement head={HEAD} -->",
                    "2026-07-27T12:00:00Z",
                    author="agent-reporter",
                ),
                self.comment(
                    f"<!-- coderabbit-disagreement-resolved head={HEAD} -->",
                    "2026-07-27T13:00:00Z",
                    author="external-reviewer",
                ),
            ],
            head_sha=HEAD,
        )
        self.assertTrue(disagreement)
        self.assertTrue(any("Nicht vertrauenswürdige" in reason for reason in reasons))
        self.assertTrue(any("Konflikt" in reason for reason in reasons))


if __name__ == "__main__":
    unittest.main()
