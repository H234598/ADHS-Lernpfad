"""Tests for the cost-aware CodeRabbit after-green gate."""

from pathlib import Path

from scripts import coderabbit_after_green as after_green


ROOT = Path(__file__).resolve().parents[1]


def _check(
    name: str,
    *,
    status: str = "completed",
    conclusion: str = "success",
    ident: int = 1,
) -> dict:
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

    assert after_green.evaluate_green_state(checks, statuses) == []  # nosec B101


def test_pending_non_coderabbit_check_blocks_request() -> None:
    """Block while any ordinary check on the current head is still running."""
    checks = _required_checks() + [
        _check("Additional safety check", status="in_progress", conclusion="")
    ]

    reasons = after_green.evaluate_green_state(checks, [_status("qlty check")])

    assert "Check läuft noch: Additional safety check" in reasons  # nosec B101


def test_failed_non_coderabbit_status_blocks_request() -> None:
    """Block when an external non-CodeRabbit status is not green."""
    reasons = after_green.evaluate_green_state(
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

    assert after_green.evaluate_green_state(checks, statuses) == []  # nosec B101


def test_latest_check_result_wins_over_stale_success() -> None:
    """Reject a newer failure even if an earlier run on the same SHA succeeded."""
    checks = _required_checks()
    checks.extend(
        [
            _check("Additional safety check", ident=10),
            _check("Additional safety check", conclusion="failure", ident=11),
        ]
    )

    reasons = after_green.evaluate_green_state(checks, [_status("qlty check")])

    assert "Check nicht grün: Additional safety check=failure" in reasons  # nosec B101


def test_missing_required_gate_blocks_request() -> None:
    """Never infer green from an absent mandatory check."""
    checks = [
        check
        for check in _required_checks()
        if check["name"] != "Remark lint (blocking)"
    ]

    reasons = after_green.evaluate_green_state(checks, [_status("qlty check")])

    assert "Pflichtcheck fehlt: Remark lint (blocking)" in reasons  # nosec B101


def test_workflow_run_without_pr_can_scan_open_same_repo_prs(monkeypatch) -> None:
    """Scan eligible same-repository PRs when a workflow_run has no PR number."""
    pulls = [
        {
            "number": 65,
            "state": "open",
            "head": {"repo": {"full_name": "H234598/ADHS-Lernpfad"}},
        },
        {
            "number": 66,
            "state": "open",
            "head": {"repo": {"full_name": "someone/fork"}},
        },
    ]
    seen: list[int] = []

    def fake_paged(repository, suffix, token, key=None):
        del repository, token, key
        assert suffix.startswith("pulls?state=open")  # nosec B101 -- pytest assertion
        return pulls

    def fake_request(repository, pr_number, token):
        del repository, token
        seen.append(pr_number)
        return True

    monkeypatch.setattr(after_green, "_paged", fake_paged)
    monkeypatch.setattr(after_green, "request_if_green", fake_request)
    scanner = getattr(after_green, "request_all_green", None)

    assert scanner is not None, "workflow_run fallback scanner fehlt"  # nosec B101
    assert scanner("H234598/ADHS-Lernpfad", "token") == 1  # nosec B101
    assert seen == [65]  # nosec B101


def test_untrusted_request_marker_does_not_suppress_request(monkeypatch) -> None:
    """Trust deduplication markers only when GitHub Actions authored them."""
    head_sha = "head-a"
    posted: list[str] = []
    marker = f"{after_green.MARKER_PREFIX}{head_sha} -->"

    monkeypatch.setattr(
        after_green,
        "_current_same_repo_head",
        lambda repository, pr_number, token: head_sha,
    )
    monkeypatch.setattr(after_green, "_gate_reasons", lambda *args: [])
    monkeypatch.setattr(
        after_green,
        "_has_current_coderabbit_review",
        lambda *args: False,
    )

    def fake_paged(repository, suffix, token, key=None):
        del repository, token, key
        assert suffix.startswith("issues/65/comments")  # nosec B101
        return [
            {
                "body": marker,
                "user": {"login": "untrusted-user"},
            }
        ]

    def fake_post(repository, pr_number, current_head, token):
        del repository, pr_number, token
        posted.append(current_head)

    monkeypatch.setattr(after_green, "_paged", fake_paged)
    monkeypatch.setattr(after_green, "_post_review_request", fake_post)

    assert after_green.request_if_green("H234598/ADHS-Lernpfad", 65, "token")  # nosec B101
    assert posted == [head_sha]  # nosec B101


def test_head_change_after_gate_validation_aborts_request(monkeypatch) -> None:
    """Re-check the PR head immediately before posting the paid review request."""
    heads = iter(["validated-head", "new-head"])
    posted: list[str] = []

    monkeypatch.setattr(
        after_green,
        "_current_same_repo_head",
        lambda repository, pr_number, token: next(heads),
    )
    monkeypatch.setattr(after_green, "_gate_reasons", lambda *args: [])
    monkeypatch.setattr(
        after_green,
        "_has_current_coderabbit_review",
        lambda *args: False,
    )
    monkeypatch.setattr(after_green, "_already_requested", lambda *args: False)
    monkeypatch.setattr(
        after_green,
        "_post_review_request",
        lambda repository, pr_number, head_sha, token: posted.append(head_sha),
    )

    assert not after_green.request_if_green(  # nosec B101
        "H234598/ADHS-Lernpfad",
        65,
        "token",
    )
    assert posted == []  # nosec B101


def test_after_green_workflow_serializes_all_request_paths() -> None:
    """Serialize fallback scans and PR-specific requests in one non-cancelling group."""
    workflow = (ROOT / ".github/workflows/coderabbit-after-green.yml").read_text(
        encoding="utf-8"
    )

    assert "group: coderabbit-after-green\n" in workflow  # nosec B101
    assert "cancel-in-progress: false" in workflow  # nosec B101
