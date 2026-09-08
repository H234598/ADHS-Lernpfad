from __future__ import annotations

from pathlib import Path

import yaml

import scripts.publish_review_gate_check as publisher
from scripts.publish_review_gate_check import GATE_CHECK_NAME, protect_against_head_change, publish_gate_check
from scripts.review_gate import GateResult

ROOT = Path(__file__).resolve().parents[1]
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
        checked_at="2026-09-08T11:00:00Z",
    )


def test_gate_check_is_explicitly_published_on_evaluated_pr_head(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []

    def fake_request(url: str, token: str, *, user_agent: str, method="GET", data=None):
        calls.append((url, token, data or {}))
        return {}

    monkeypatch.setattr(publisher, "request_json", fake_request)
    publish_gate_check("H234598/ADHS-Lernpfad", "token", _result())

    assert len(calls) == 1
    url, _token, payload = calls[0]
    assert url.endswith("/repos/H234598/ADHS-Lernpfad/check-runs")
    assert payload["name"] == GATE_CHECK_NAME == "CodeRabbit review gate (blocking)"
    assert payload["head_sha"] == HEAD
    assert payload["status"] == "completed"
    assert payload["conclusion"] == "success"


def test_coderabbit_workflow_serializes_pr_events_and_can_publish_head_check() -> None:
    path = ROOT / ".github/workflows/coderabbit-hard-gate.yml"
    text = path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)

    assert workflow["permissions"] == {
        "contents": "read",
        "pull-requests": "read",
        "issues": "read",
        "checks": "write",
        "statuses": "read",
    }
    assert workflow["concurrency"]["cancel-in-progress"] is False
    assert "publish_review_gate_check.py" in text
    assert "steps.enforce.outcome" in text


def test_gate_rejects_stale_success_when_pr_head_changes() -> None:
    stale = _result(passed=True)
    fresh_pull = {"state": "open", "head": {"sha": "b" * 40}}

    protected = protect_against_head_change(stale, fresh_pull, enforcement_outcome="success")

    assert protected.passed is False
    assert protected.head_sha == "b" * 40
    assert any("während der Auswertung geändert" in reason for reason in protected.reasons)


def test_formal_review_enforcement_failure_forces_published_failure() -> None:
    protected = protect_against_head_change(
        _result(passed=True),
        {"state": "open", "head": {"sha": HEAD}},
        enforcement_outcome="failure",
    )

    assert protected.passed is False
    assert any("formelle CodeRabbit-Reviewzustand" in reason for reason in protected.reasons)
