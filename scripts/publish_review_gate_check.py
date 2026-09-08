"""Publish the final CodeRabbit gate explicitly on the evaluated PR head."""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import re
from typing import Any

from github_api import request_json
from review_gate import GateResult

API = "https://api.github.com"
GATE_CHECK_NAME = "CodeRabbit review gate (blocking)"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_result(
    path: Path,
    *,
    repository: str,
    pr_number: int,
    fresh_pull: dict[str, Any],
) -> GateResult:
    """Load the evaluated gate or synthesize a fail-closed missing result."""

    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise RuntimeError("CodeRabbit-Gatebericht muss ein JSON-Objekt sein")
        return GateResult(
            repository=str(raw.get("repository") or repository),
            pull_request=int(raw.get("pull_request") or pr_number),
            head_sha=str(raw.get("head_sha") or ""),
            coderabbit_state=str(raw.get("coderabbit_state") or "missing"),
            coderabbit_signals=[
                {str(key): str(value) for key, value in item.items()}
                for item in raw.get("coderabbit_signals", [])
                if isinstance(item, dict)
            ],
            unresolved_thread_ids=[
                str(item) for item in raw.get("unresolved_thread_ids", [])
            ],
            disagreement_open=bool(raw.get("disagreement_open")),
            passed=bool(raw.get("passed")),
            reasons=[str(item) for item in raw.get("reasons", [])],
            checked_at=str(raw.get("checked_at") or ""),
        )

    fresh_head = str(_mapping(fresh_pull.get("head")).get("sha") or "")
    return GateResult(
        repository=repository,
        pull_request=pr_number,
        head_sha=fresh_head,
        coderabbit_state="missing",
        coderabbit_signals=[],
        unresolved_thread_ids=[],
        disagreement_open=False,
        passed=False,
        reasons=["CodeRabbit-Gatebericht fehlt; fail-closed publiziert."],
        checked_at="",
    )


def protect_against_head_change(
    result: GateResult,
    fresh_pull: dict[str, Any],
    *,
    enforcement_outcome: str,
) -> GateResult:
    """Bind a positive gate to a fresh PR snapshot and formal review result."""

    fresh_head = str(_mapping(fresh_pull.get("head")).get("sha") or "")
    target_head = fresh_head if SHA_RE.fullmatch(fresh_head) else result.head_sha
    reasons = list(result.reasons)
    passed = bool(result.passed)

    head_changed = target_head != result.head_sha
    if str(fresh_pull.get("state") or "") != "open" or head_changed:
        passed = False
        reasons.append(
            "Der Pull Request wurde während der Auswertung geändert oder "
            "geschlossen; "
            f"Ausgangs-Head: {result.head_sha}; aktueller Head: "
            f"{fresh_head or '<unbekannt>'}."
        )

    if enforcement_outcome != "success":
        passed = False
        reasons.append(
            "Der formelle CodeRabbit-Reviewzustand wurde nicht erfolgreich "
            "durchgesetzt "
            f"(Workflow-Ergebnis: {enforcement_outcome or 'missing'})."
        )

    return replace(
        result,
        head_sha=target_head,
        passed=passed,
        reasons=reasons,
    )


def publish_gate_check(repository: str, token: str, result: GateResult) -> None:
    """Publish one completed Required Check on the explicit PR-head SHA."""

    if not SHA_RE.fullmatch(result.head_sha):
        raise RuntimeError(
            "CodeRabbit-Head-Check benötigt einen vollständigen Git-SHA"
        )
    if result.passed:
        summary = (
            "CodeRabbit ist für den aktuellen Head erfolgreich; alle Threads "
            "und formellen Reviewzustände sind geklärt."
        )
    else:
        summary = "; ".join(result.reasons) or (
            "CodeRabbit review gate ist blockiert."
        )
    request_json(
        f"{API}/repos/{repository}/check-runs",
        token,
        user_agent="ADHS-Lernpfad-coderabbit-head-check",
        method="POST",
        data={
            "name": GATE_CHECK_NAME,
            "head_sha": result.head_sha,
            "status": "completed",
            "conclusion": "success" if result.passed else "failure",
            "output": {
                "title": GATE_CHECK_NAME,
                "summary": summary[:65535],
            },
        },
    )


def _parse_args() -> argparse.Namespace:
    """Parse arguments for explicit PR-head check publication."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("build/review-gate/review-gate.json"),
    )
    parser.add_argument("--enforcement-outcome", default="")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/review-gate/published-head-check.json"),
    )
    args = parser.parse_args()
    if not args.repository or not args.pr_number or not args.token:
        parser.error("repository, pr-number und token sind erforderlich")
    return args


def main() -> int:
    """Publish the final formal+semantic CodeRabbit result."""

    args = _parse_args()
    fresh_pull = _mapping(
        request_json(
            f"{API}/repos/{args.repository}/pulls/{args.pr_number}",
            args.token,
            user_agent="ADHS-Lernpfad-coderabbit-head-check",
        )
    )
    result = _load_result(
        args.report,
        repository=args.repository,
        pr_number=args.pr_number,
        fresh_pull=fresh_pull,
    )
    protected = protect_against_head_change(
        result,
        fresh_pull,
        enforcement_outcome=args.enforcement_outcome,
    )
    publish_gate_check(args.repository, args.token, protected)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(asdict(protected), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asdict(protected), ensure_ascii=False, indent=2))
    return 0 if protected.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
