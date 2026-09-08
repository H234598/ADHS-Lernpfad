from __future__ import annotations

from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from learning_card_policy import classify_pull_request, evaluate_policy
from learning_card_checks import REQUIRED_POLICY_CHECKS

HEAD = "a" * 40


def _check(name: str, *, conclusion: str = "success") -> dict[str, object]:
    return {
        "name": name,
        "status": "completed",
        "conclusion": conclusion,
        "head_sha": HEAD,
        "created_at": "2026-09-08T10:00:00Z",
        "completed_at": "2026-09-08T10:01:00Z",
        "html_url": f"https://example.invalid/{name}",
    }


def _scope():
    return classify_pull_request(
        files=[{"filename": "02-Vertiefung/09-Beispiel.md", "status": "modified"}],
        head_ref="agent/einheit-99-beispiel",
        body="<!-- adhs-daily-unit -->",
    )


def test_cancelled_review_gate_is_reported_as_transport_block_not_two_scientific_failures() -> None:
    runs = [
        _check(
            name,
            conclusion=(
                "cancelled"
                if name == "CodeRabbit review gate (blocking)"
                else "success"
            ),
        )
        for name in REQUIRED_POLICY_CHECKS
    ]

    decision = evaluate_policy(scope=_scope(), check_runs=runs, head_sha=HEAD)

    assert decision.passed is False
    assert decision.review_gate_state == "failure"
    assert decision.subgates["content_scope"] == "failure"
    assert decision.subgates["claim_source_entailment"] == "failure"
    joined = " ".join(decision.reasons)
    assert "durch das CodeRabbit-Review-Gate blockiert" in joined
    assert "nicht als eigenständige fachliche Fehler bewertet" in joined
    assert "Subgate content_scope ist failure" not in joined
    assert "Subgate claim_source_entailment ist failure" not in joined


def test_green_review_gate_remains_semantically_green() -> None:
    decision = evaluate_policy(
        scope=_scope(),
        check_runs=[_check(name) for name in REQUIRED_POLICY_CHECKS],
        head_sha=HEAD,
    )

    assert decision.passed is True
    assert decision.review_gate_state == "success"
    assert decision.subgates["content_scope"] == "success"
    assert decision.subgates["claim_source_entailment"] == "success"


def test_learning_card_workflow_serializes_pr_events_instead_of_cancelling_required_checks() -> None:
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/learning-card-policy.yml").read_text(encoding="utf-8")
    )

    assert workflow["concurrency"]["cancel-in-progress"] is False
