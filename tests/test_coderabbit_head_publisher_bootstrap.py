from __future__ import annotations

import scripts.publish_review_gate_check as publisher
from scripts.publish_review_gate_check import (
    GATE_CHECK_NAME,
    protect_against_head_change,
    publish_gate_check,
)
from scripts.review_gate import GateResult

HEAD = "a" * 40


def _result(*, passed: bool = True) -> GateResult:
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


def test_publisher_posts_required_check_on_explicit_pr_head(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []

    def fake_request(
        url: str,
        token: str,
        *,
        user_agent: str,
        method: str = "GET",
        data=None,
    ):
        calls.append((url, method, data or {}))
        return {}

    monkeypatch.setattr(publisher, "request_json", fake_request)

    publish_gate_check("H234598/ADHS-Lernpfad", "token", _result())

    assert len(calls) == 1
    url, method, payload = calls[0]
    assert url.endswith("/repos/H234598/ADHS-Lernpfad/check-runs")
    assert method == "POST"
    assert payload["name"] == GATE_CHECK_NAME == "CodeRabbit review gate (blocking)"
    assert payload["head_sha"] == HEAD
    assert payload["status"] == "completed"
    assert payload["conclusion"] == "success"


def test_publisher_rejects_stale_success_after_head_change() -> None:
    protected = protect_against_head_change(
        _result(passed=True),
        {"state": "open", "head": {"sha": "b" * 40}},
        enforcement_outcome="success",
    )

    assert protected.passed is False
    assert protected.head_sha == "b" * 40
    assert any(
        "während der Auswertung geändert" in reason
        for reason in protected.reasons
    )
