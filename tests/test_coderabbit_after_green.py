"""Tests for the cost-aware CodeRabbit after-green gate."""

from scripts.coderabbit_after_green import evaluate_green_state


def _check(name: str, *, status: str = "completed", conclusion: str = "success", ident: int = 1) -> dict:
    """Build one synthetic check run."""

    return {"id": ident, "name": name, "status": status, "conclusion": conclusion}


def _status(context: str, *, state: str = "success", ident: int = 1) -> dict:
    """Build one synthetic commit status."""

    return {"id": ident, "context": context, "state": state}


def _required_checks() -> list[dict]:
    """Return a complete successful set of repository prerequisite checks."""

    return [
        _check("Validate and build"),
        _check("Build all download formats"),
        _check("Remark lint (blocking)"),
        _check("Learning card policy (blocking)"),
        _check("Codacy Security Scan"),
    ]


def test_all_non_coderabbit_gates_green_allows_request() -> None:
    """Allow CodeRabbit only after every configured prerequisite is green."""

    checks = _required_checks() + [_check("Codacy analyzer (ruff)")]
    statuses = [_status("qlty check")]

    assert evaluate_green_state(checks, statuses) == []  # nosec B101 -- pytest assertion


def test_pending_non_coderabbit_check_blocks_request() -> None:
    """Block while any ordinary check on the current head is still running."""

    checks = _required_checks() + [
        _check("Additional safety check", status="in_progress", conclusion="")
    ]

    reasons = evaluate_green_state(checks, [_status("qlty check")])

    assert "Check läuft noch: Additional safety check" in reasons  # nosec B101


def test_failed_non_coderabbit_status_blocks_request() -> None:
    """Block when an external non-CodeRabbit status is not green."""

    reasons = evaluate_green_state(
        _required_checks(),
        [_status("qlty check"), _status("external quality", state="failure")],
    )

    assert "Status nicht grün: external quality=failure" in reasons  # nosec B101


def test_coderabbit_pending_state_is_ignored_before_request() -> None:
    """Do not create a chicken-and-egg dependency on CodeRabbit itself."""

    checks = _required_checks() + [
        _check("CodeRabbit review gate (blocking)", conclusion="failure"),
        _check("content-scope", status="in_progress", conclusion=""),
    ]
    statuses = [_status("qlty check"), _status("CodeRabbit", state="pending")]

    assert evaluate_green_state(checks, statuses) == []  # nosec B101 -- pytest assertion


def test_latest_check_result_wins_over_stale_success() -> None:
    """Reject a newer failure even if an earlier run on the same SHA succeeded."""

    checks = _required_checks()
    checks.extend(
        [
            _check("Additional safety check", ident=10),
            _check("Additional safety check", conclusion="failure", ident=11),
        ]
    )

    reasons = evaluate_green_state(checks, [_status("qlty check")])

    assert "Check nicht grün: Additional safety check=failure" in reasons  # nosec B101


def test_missing_required_gate_blocks_request() -> None:
    """Never infer green from an absent mandatory check."""

    checks = [check for check in _required_checks() if check["name"] != "Remark lint (blocking)"]

    reasons = evaluate_green_state(checks, [_status("qlty check")])

    assert "Pflichtcheck fehlt: Remark lint (blocking)" in reasons  # nosec B101
