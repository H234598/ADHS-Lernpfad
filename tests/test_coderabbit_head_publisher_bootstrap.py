"""Bootstrap contract tests for the explicit CodeRabbit head-check publisher."""

from __future__ import annotations

import unittest

import scripts.publish_review_gate_check as publisher
from scripts.publish_review_gate_check import (
    GATE_CHECK_NAME,
    protect_against_head_change,
    publish_gate_check,
)
from scripts.review_gate import GateResult

HEAD = "a" * 40


def _result(*, passed: bool = True) -> GateResult:
    """Build the smallest representative CodeRabbit gate result."""
    return GateResult(
        repository="H234598/ADHS-Lernpfad",
        pull_request=67,
        head_sha=HEAD,
        coderabbit_state="success" if passed else "failure",
        coderabbit_signals=[],
        unresolved_thread_ids=[],
        disagreement_open=False,
        passed=passed,
        reasons=[] if passed else ["gate failed"],
        checked_at="2026-09-23T00:00:00Z",
    )


class HeadPublisherBootstrapTests(unittest.TestCase):
    """Protect the publisher behavior needed to bootstrap PR #67."""

    def test_publisher_posts_required_check_on_explicit_pr_head(self) -> None:
        """Publish exactly one successful required check on the evaluated head."""
        calls: list[tuple[str, str, dict]] = []

        def fake_request(url: str, _token: str, **kwargs):
            calls.append((url, str(kwargs.get("method", "GET")), kwargs.get("data") or {}))
            return {}

        original = publisher.request_json
        publisher.request_json = fake_request
        try:
            publish_gate_check("H234598/ADHS-Lernpfad", "token", _result())
        finally:
            publisher.request_json = original

        self.assertEqual(len(calls), 1)
        url, method, payload = calls[0]
        self.assertTrue(url.endswith("/repos/H234598/ADHS-Lernpfad/check-runs"))
        self.assertEqual(method, "POST")
        self.assertEqual(
            payload["name"],
            GATE_CHECK_NAME,
        )
        self.assertEqual(GATE_CHECK_NAME, "CodeRabbit review gate (blocking)")
        self.assertEqual(payload["head_sha"], HEAD)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["conclusion"], "success")

    def test_publisher_rejects_stale_success_after_head_change(self) -> None:
        """Fail closed when the pull-request head changes during evaluation."""
        protected = protect_against_head_change(
            _result(passed=True),
            {"state": "open", "head": {"sha": "b" * 40}},
            enforcement_outcome="success",
        )

        self.assertFalse(protected.passed)
        self.assertEqual(protected.head_sha, "b" * 40)
        self.assertTrue(
            any(
                "während der Auswertung geändert" in reason
                for reason in protected.reasons
            )
        )


if __name__ == "__main__":
    unittest.main()
