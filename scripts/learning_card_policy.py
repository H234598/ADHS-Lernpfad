#!/usr/bin/env python3
"""Immer berichtendes, scopeabhängiges Lernkarten-Gate."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import re
import time
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from learning_card_checks import (
    PolicyDecision,
    REQUIRED_POLICY_CHECKS,
    evaluate_policy,
    select_latest_check_runs,
)
from learning_card_scope import ScopeDecision, classify_pull_request

__all__ = [
    "PolicyDecision",
    "PullSnapshot",
    "REQUIRED_POLICY_CHECKS",
    "ScopeDecision",
    "build_pull_snapshot",
    "classify_pull_request",
    "evaluate_policy",
    "select_latest_check_runs",
]

API = "https://api.github.com"


@dataclass(frozen=True)
class PullSnapshot:
    """PR-Zustand, der vor einem positiven Bericht unverändert sein muss."""

    state: str
    head_sha: str
    head_ref: str
    body: str
    files: tuple[tuple[str, str, str], ...]


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _items(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def build_pull_snapshot(
    pull: dict[str, Any],
    files: list[dict[str, Any]],
) -> PullSnapshot:
    """Head, Body und vollständigen geänderten Dateiscope kanonisieren."""

    head = _mapping(pull.get("head"))
    file_scope = tuple(
        sorted(
            (
                str(item.get("filename") or ""),
                str(item.get("previous_filename") or ""),
                str(item.get("status") or ""),
            )
            for item in files
            if isinstance(item, dict)
        )
    )
    return PullSnapshot(
        state=str(pull.get("state") or ""),
        head_sha=str(head.get("sha") or ""),
        head_ref=str(head.get("ref") or ""),
        body=str(pull.get("body") or ""),
        files=file_scope,
    )


def _request_json(url: str, token: str) -> Any:
    request = Request(url)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("User-Agent", "ADHS-Lernpfad-learning-card-policy")
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API {exc.code} für {url}: {detail[:500]}"
        ) from exc


def _paginated(
    url: str,
    token: str,
    *,
    key: str | None = None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    page = 1
    while True:
        separator = "&" if "?" in url else "?"
        payload = _request_json(
            f"{url}{separator}per_page=100&page={page}",
            token,
        )
        batch = (
            _items(_mapping(payload).get(key)) if key else _items(payload)
        )
        result.extend(item for item in batch if isinstance(item, dict))
        if len(batch) < 100:
            return result
        page += 1


def _write_report(
    repository: str,
    number: int,
    scope: ScopeDecision,
    decision: PolicyDecision,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "repository": repository,
        "pull_request": number,
        "checked_at": (
            datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "scope": asdict(scope),
        "decision": asdict(decision),
    }
    (output_dir / "learning-card-policy.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Learning card policy",
        "",
        f"- Repository: `{repository}`",
        f"- Pull Request: `#{number}`",
        f"- Head: `{decision.head_sha}`",
        f"- Klassifikation: **{scope.classification}**",
        (
            "- Semantische Prüfung: **"
            f"{'ja' if scope.requires_semantic_review else 'nein'}**"
        ),
        (
            "- Manueller Merge: **"
            f"{'ja' if scope.manual_merge_required else 'nein'}**"
        ),
        (
            "- Ergebnis: **"
            f"{'bestanden' if decision.passed else 'blockiert'}**"
        ),
        "",
        "## Subgates",
        "",
        *(
            f"- `{name}`: **{state}**"
            for name, state in decision.subgates.items()
        ),
        "",
        "## Begründung",
        "",
        *(f"- {reason}" for reason in decision.reasons),
    ]
    (output_dir / "learning-card-policy.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repository",
        default=os.getenv("GITHUB_REPOSITORY"),
    )
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/learning-card-policy"),
    )
    parser.add_argument("--max-wait-seconds", type=int, default=480)
    parser.add_argument("--poll-interval-seconds", type=int, default=10)
    args = parser.parse_args()
    if not args.repository or not args.token or not args.pr_number:
        parser.error("repository, token und pr-number sind erforderlich")
    if args.max_wait_seconds < 0 or args.poll_interval_seconds < 1:
        parser.error(
            "Wartezeiten müssen nichtnegativ beziehungsweise positiv sein"
        )

    pull_url = f"{API}/repos/{args.repository}/pulls/{args.pr_number}"
    files_url = f"{pull_url}/files"
    pull = _mapping(_request_json(pull_url, args.token))
    if pull.get("state") != "open":
        print(
            f"PR #{args.pr_number} ist nicht offen; Policy wird übersprungen."
        )
        return 0
    files = _paginated(files_url, args.token)
    initial_snapshot = build_pull_snapshot(pull, files)
    head_sha = initial_snapshot.head_sha
    if not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        raise RuntimeError("Aktueller PR-Head konnte nicht bestimmt werden")

    scope = classify_pull_request(
        files=files,
        head_ref=initial_snapshot.head_ref,
        body=initial_snapshot.body,
    )
    decision = evaluate_policy(
        scope=scope,
        check_runs=[],
        head_sha=head_sha,
    )
    started = time.monotonic()
    while scope.requires_semantic_review:
        runs = _paginated(
            f"{API}/repos/{args.repository}/commits/{head_sha}/check-runs",
            args.token,
            key="check_runs",
        )
        decision = evaluate_policy(
            scope=scope,
            check_runs=runs,
            head_sha=head_sha,
        )
        if decision.passed or "failure" in decision.subgates.values():
            break
        if scope.manual_merge_required and not scope.manual_merge_marker:
            break
        if time.monotonic() - started >= args.max_wait_seconds:
            break
        time.sleep(args.poll_interval_seconds)

    fresh_pull = _mapping(_request_json(pull_url, args.token))
    fresh_files = _paginated(files_url, args.token)
    fresh_snapshot = build_pull_snapshot(fresh_pull, fresh_files)
    if fresh_snapshot != initial_snapshot:
        decision = replace(
            decision,
            passed=False,
            reasons=(
                *decision.reasons,
                "Der Pull Request wurde während der Auswertung geändert; "
                "Head, Body oder Dateiscope sind nicht mehr identisch. "
                f"Ausgangs-Head: {initial_snapshot.head_sha}; "
                f"aktueller Head: {fresh_snapshot.head_sha}.",
            ),
        )

    _write_report(
        args.repository,
        args.pr_number,
        scope,
        decision,
        args.output_dir,
    )
    print(
        (args.output_dir / "learning-card-policy.md").read_text(
            encoding="utf-8"
        )
    )
    return 0 if decision.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
