"""Bootstrap contract tests for the explicit CodeRabbit head-check publisher."""

from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

publisher = importlib.import_module("publish_review_gate_check")
review_gate = importlib.import_module("review_gate")

GATE_CHECK_NAME = publisher.GATE_CHECK_NAME
load_result = publisher.load_result
protect_against_head_change = publisher.protect_against_head_change
publish_gate_check = publisher.publish_gate_check
GateResult = review_gate.GateResult

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

    def test_publisher_token_is_environment_only(self) -> None:
        """Do not expose GitHub tokens through a process-list-visible CLI option."""
        source = (
            ROOT / "scripts/publish_review_gate_check.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn('parser.add_argument("--token"', source)
        self.assertIn(
            'parser.set_defaults(token=os.getenv("GITHUB_TOKEN"))',
            source,
        )

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
        self.assertEqual(payload["name"], GATE_CHECK_NAME)
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

    def test_publisher_fails_closed_when_fresh_head_is_invalid(self) -> None:
        """Treat an unresolved current PR head as unknown, never unchanged."""
        protected = protect_against_head_change(
            _result(passed=True),
            {"state": "open", "head": {"sha": "not-a-sha"}},
            enforcement_outcome="success",
        )

        self.assertFalse(protected.passed)
        self.assertTrue(
            any(
                "während der Auswertung geändert" in reason
                for reason in protected.reasons
            )
        )

    def test_report_identity_must_match_requested_pull_request(self) -> None:
        """Reject a persisted gate report that belongs to another PR."""
        raw = {
            "repository": "H234598/ADHS-Lernpfad",
            "pull_request": 999,
            "head_sha": HEAD,
            "coderabbit_state": "success",
            "coderabbit_signals": [],
            "unresolved_thread_ids": [],
            "disagreement_open": False,
            "passed": True,
            "reasons": [],
            "checked_at": "2026-09-23T00:00:00Z",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review-gate.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "gehört nicht"):
                load_result(
                    path,
                    repository="H234598/ADHS-Lernpfad",
                    pr_number=67,
                    fresh_pull={"head": {"sha": HEAD}},
                )

    def test_report_pull_request_requires_exact_integer_type(self) -> None:
        """Reject booleans and floats masquerading as the requested PR number."""
        for invalid_pr in (True, 1.0):
            with self.subTest(pull_request=invalid_pr):
                raw = {
                    "repository": "H234598/ADHS-Lernpfad",
                    "pull_request": invalid_pr,
                    "head_sha": HEAD,
                    "coderabbit_state": "success",
                    "coderabbit_signals": [],
                    "unresolved_thread_ids": [],
                    "disagreement_open": False,
                    "passed": True,
                    "reasons": [],
                    "checked_at": "2026-09-23T00:00:00Z",
                }
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "review-gate.json"
                    path.write_text(json.dumps(raw), encoding="utf-8")
                    with self.assertRaisesRegex(RuntimeError, "gehört nicht"):
                        load_result(
                            path,
                            repository="H234598/ADHS-Lernpfad",
                            pr_number=1,
                            fresh_pull={"head": {"sha": HEAD}},
                        )

    def test_report_passed_accepts_only_json_boolean_true(self) -> None:
        """Never treat truthy strings in persisted trust data as success."""
        raw = {
            "repository": "H234598/ADHS-Lernpfad",
            "pull_request": 67,
            "head_sha": HEAD,
            "coderabbit_state": "success",
            "coderabbit_signals": [],
            "unresolved_thread_ids": [],
            "disagreement_open": False,
            "passed": "false",
            "reasons": [],
            "checked_at": "2026-09-23T00:00:00Z",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review-gate.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            loaded = load_result(
                path,
                repository="H234598/ADHS-Lernpfad",
                pr_number=67,
                fresh_pull={"head": {"sha": HEAD}},
            )

        self.assertFalse(loaded.passed)
        self.assertEqual(loaded.repository, "H234598/ADHS-Lernpfad")
        self.assertEqual(loaded.pull_request, 67)


if __name__ == "__main__":
    unittest.main()
