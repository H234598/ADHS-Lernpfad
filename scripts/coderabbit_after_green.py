"""Request one CodeRabbit review only after every non-CodeRabbit gate is green."""

from __future__ import annotations

import argparse
import os
from collections.abc import Iterable
from typing import Any

try:
    from .github_api import request_json
except ImportError:  # pragma: no cover - direct script execution
    from github_api import request_json

API_ROOT = "https://api.github.com"
USER_AGENT = "ADHS-Lernpfad-coderabbit-after-green"
MARKER_PREFIX = "<!-- coderabbit-after-green:"

REQUIRED_CHECK_RUNS = (
    "Validate and build",
    "Build all download formats",
    "Remark lint (blocking)",
    "Learning card policy (blocking)",
    "Codacy Security Scan",
)
REQUIRED_STATUSES = ("qlty check",)
ALLOWED_NONBLOCKING_CONCLUSIONS = {"success", "neutral", "skipped"}


def _is_coderabbit_context(name: str) -> bool:
    """Return whether a check/status belongs to CodeRabbit or this requester."""
    normalized = name.casefold()
    return (
        "coderabbit" in normalized
        or normalized in {"content-scope", "claim-source-entailment"}
        or normalized == "request coderabbit after green"
    )


def _latest_by_name(items: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Keep the newest GitHub object for every check/status context name."""
    latest: dict[str, dict[str, Any]] = {}
    for item in items:
        name = str(item.get("name") or item.get("context") or "")
        if not name:
            continue
        current = latest.get(name)
        if current is None or int(item.get("id") or 0) > int(current.get("id") or 0):
            latest[name] = item
    return latest


def evaluate_green_state(
    check_runs: Iterable[dict[str, Any]],
    statuses: Iterable[dict[str, Any]],
) -> list[str]:
    """Return reasons why CodeRabbit must not be requested yet."""
    reasons: list[str] = []
    latest_checks = _latest_by_name(check_runs)
    latest_statuses = _latest_by_name(statuses)

    for name in REQUIRED_CHECK_RUNS:
        check = latest_checks.get(name)
        if check is None:
            reasons.append(f"Pflichtcheck fehlt: {name}")
            continue
        if check.get("status") != "completed" or check.get("conclusion") != "success":
            reasons.append(
                f"Pflichtcheck nicht grün: {name}="
                f"{check.get('status')}/{check.get('conclusion')}"
            )

    for name in REQUIRED_STATUSES:
        status = latest_statuses.get(name)
        if status is None:
            reasons.append(f"Pflichtstatus fehlt: {name}")
            continue
        if status.get("state") != "success":
            reasons.append(f"Pflichtstatus nicht grün: {name}={status.get('state')}")

    for name, check in latest_checks.items():
        if _is_coderabbit_context(name):
            continue
        if check.get("status") != "completed":
            reasons.append(f"Check läuft noch: {name}")
            continue
        conclusion = str(check.get("conclusion") or "")
        if conclusion not in ALLOWED_NONBLOCKING_CONCLUSIONS:
            reasons.append(f"Check nicht grün: {name}={conclusion or 'ohne Ergebnis'}")

    for name, status in latest_statuses.items():
        if _is_coderabbit_context(name):
            continue
        if status.get("state") != "success":
            reasons.append(f"Status nicht grün: {name}={status.get('state')}")

    return sorted(set(reasons))


def _get(repository: str, suffix: str, token: str) -> Any:
    """Fetch one GitHub REST resource."""
    return request_json(
        f"{API_ROOT}/repos/{repository}/{suffix}",
        token,
        user_agent=USER_AGENT,
    )


def _paged(
    repository: str,
    suffix: str,
    token: str,
    key: str | None = None,
) -> list[Any]:
    """Fetch up to ten pages of one list endpoint."""
    collected: list[Any] = []
    separator = "&" if "?" in suffix else "?"
    for page in range(1, 11):
        payload = _get(
            repository,
            f"{suffix}{separator}per_page=100&page={page}",
            token,
        )
        items = payload.get(key, []) if key else payload
        if not isinstance(items, list):
            raise TypeError(f"Unerwartete GitHub-Antwort für {suffix}")
        collected.extend(items)
        if len(items) < 100:
            break
    return collected


def _current_same_repo_head(repository: str, pr_number: int, token: str) -> str | None:
    """Return the current head SHA for an open same-repository PR."""
    pull = _get(repository, f"pulls/{pr_number}", token)
    if pull.get("state") != "open":
        print("PR ist nicht offen; kein CodeRabbit-Request.")
        return None

    head = pull.get("head") or {}
    head_sha = str(head.get("sha") or "")
    if not head_sha:
        raise RuntimeError("PR besitzt keinen Head-SHA")
    if ((head.get("repo") or {}).get("full_name")) != repository:
        print("Fork-PR: bezahlter CodeRabbit-Request bleibt manuell.")
        return None
    return head_sha


def _gate_reasons(repository: str, head_sha: str, token: str) -> list[str]:
    """Return all non-CodeRabbit reasons blocking a paid review request."""
    check_runs = _paged(
        repository,
        f"commits/{head_sha}/check-runs?filter=latest",
        token,
        key="check_runs",
    )
    combined_status = _get(repository, f"commits/{head_sha}/status?per_page=100", token)
    statuses = combined_status.get("statuses", [])
    if not isinstance(statuses, list):
        raise TypeError("GitHub lieferte keine Statusliste")
    return evaluate_green_state(check_runs, statuses)


def _has_current_coderabbit_review(
    repository: str,
    pr_number: int,
    head_sha: str,
    token: str,
) -> bool:
    """Return whether CodeRabbit has already reviewed this exact head."""
    reviews = _paged(repository, f"pulls/{pr_number}/reviews", token)
    for review in reviews:
        login = str(((review.get("user") or {}).get("login")) or "").casefold()
        if login.startswith("coderabbitai") and review.get("commit_id") == head_sha:
            return True
    return False


def _already_requested(
    repository: str,
    pr_number: int,
    head_sha: str,
    token: str,
) -> bool:
    """Return whether trusted GitHub Actions already requested this exact head."""
    marker = f"{MARKER_PREFIX}{head_sha} -->"
    comments = _paged(repository, f"issues/{pr_number}/comments", token)
    for comment in comments:
        login = str(((comment.get("user") or {}).get("login")) or "").casefold()
        if login != "github-actions[bot]":
            continue
        if marker in str(comment.get("body") or ""):
            return True
    return False


def _post_review_request(
    repository: str,
    pr_number: int,
    head_sha: str,
    token: str,
) -> None:
    """Post the single explicit CodeRabbit request for one PR head."""
    marker = f"{MARKER_PREFIX}{head_sha} -->"
    body = (
        f"{marker}\n"
        "@coderabbitai review\n\n"
        "Automatisch angefordert, nachdem alle Non-CodeRabbit-Checks und "
        "Statuskontexte des aktuellen Heads grün waren."
    )
    request_json(
        f"{API_ROOT}/repos/{repository}/issues/{pr_number}/comments",
        token,
        user_agent=USER_AGENT,
        method="POST",
        data={"body": body},
    )


def request_if_green(repository: str, pr_number: int, token: str) -> bool:
    """Request CodeRabbit exactly once when the current same-repo head is ready."""
    head_sha = _current_same_repo_head(repository, pr_number, token)
    if head_sha is None:
        return False

    reasons = _gate_reasons(repository, head_sha, token)
    if reasons:
        print(f"PR #{pr_number}: CodeRabbit wird noch nicht angefordert:")
        for reason in reasons:
            print(f"- {reason}")
        return False

    if _has_current_coderabbit_review(repository, pr_number, head_sha, token):
        print(f"PR #{pr_number}: CodeRabbit hat den aktuellen Head bereits reviewed.")
        return False
    if _already_requested(repository, pr_number, head_sha, token):
        print(f"PR #{pr_number}: CodeRabbit wurde für diesen Head bereits angefordert.")
        return False

    current_head = _current_same_repo_head(repository, pr_number, token)
    if current_head != head_sha:
        print(
            f"PR #{pr_number}: Head wechselte nach Gate-Prüfung "
            f"von {head_sha} auf {current_head or 'nicht verfügbar'}; kein Request."
        )
        return False

    _post_review_request(repository, pr_number, head_sha, token)
    print(f"CodeRabbit für PR #{pr_number} Head {head_sha} angefordert.")
    return True


def request_all_green(repository: str, token: str) -> int:
    """Evaluate every open same-repository PR when no event PR is available."""
    pulls = _paged(repository, "pulls?state=open&sort=updated&direction=desc", token)
    requested = 0
    for pull in pulls:
        if pull.get("state") != "open":
            continue
        head_repo = (((pull.get("head") or {}).get("repo") or {}).get("full_name"))
        pr_number = pull.get("number")
        if head_repo != repository or not isinstance(pr_number, int):
            continue
        if request_if_green(repository, pr_number, token):
            requested += 1
    print(f"After-Green-Scan abgeschlossen: {requested} Review-Request(s) ausgelöst.")
    return requested


def main() -> int:
    """CLI entry point for the after-green CodeRabbit requester."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr-number", type=int)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError("GITHUB_TOKEN fehlt")
    if args.pr_number is None:
        request_all_green(args.repository, token)
    else:
        request_if_green(args.repository, args.pr_number, token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
