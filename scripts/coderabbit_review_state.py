#!/usr/bin/env python3
"""Blockiert grünen Status bei aktivem CodeRabbit-Changes-Requested-Review."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import re
from typing import Any

from github_api import request_json

API = "https://api.github.com"
AUTHOR_RE = re.compile(r"^coderabbitai(?:\[bot\])?$", re.IGNORECASE)
FORMAL_STATES = {"approved", "changes_requested", "dismissed"}


@dataclass(frozen=True)
class ReviewStateReport:
    """Daten für den persistierten formellen CodeRabbit-Reviewzustand."""

    repository: str
    number: int
    head_sha: str
    state: str
    reasons: tuple[str, ...]


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _items(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def evaluate_coderabbit_review_state(
    reviews: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    """Den letzten formellen CodeRabbit-Reviewzustand bestimmen."""

    candidates: list[dict[str, Any]] = []
    for review in reviews:
        if not isinstance(review, dict):
            continue
        author = str(_mapping(review.get("user")).get("login") or "")
        if AUTHOR_RE.fullmatch(author.strip()):
            candidates.append(review)
    if not candidates:
        return "none", []

    ordered = sorted(
        candidates,
        key=lambda item: (
            str(item.get("submitted_at") or item.get("created_at") or ""),
            int(item.get("id") or 0),
        ),
    )
    normalized = [
        str(item.get("state") or "none").strip().casefold() for item in ordered
    ]
    formal = [state for state in normalized if state in FORMAL_STATES]
    state = formal[-1] if formal else normalized[-1]
    if state == "changes_requested":
        return state, [
            "CodeRabbit hat Änderungen angefordert; semantische Pre-Merge-Checks "
            "dürfen nicht durch ein separates grünes Statussignal überstimmt werden."
        ]
    return state, []


def _request_json(url: str, token: str) -> Any:
    """GitHub-JSON über den zentralen hostgebundenen API-Client abrufen."""

    return request_json(
        url,
        token,
        user_agent="ADHS-Lernpfad-coderabbit-review-state",
    )


def _reviews(repository: str, number: int, token: str) -> list[dict[str, Any]]:
    """Alle PR-Reviews paginiert laden."""

    result: list[dict[str, Any]] = []
    page = 1
    while True:
        batch = _items(
            _request_json(
                f"{API}/repos/{repository}/pulls/{number}/reviews"
                f"?per_page=100&page={page}",
                token,
            )
        )
        result.extend(item for item in batch if isinstance(item, dict))
        if len(batch) < 100:
            return result
        page += 1


def _write_report(output_dir: Path, report: ReviewStateReport) -> None:
    """JSON- und Markdownbericht für den formellen Reviewzustand schreiben."""

    output_dir.mkdir(parents=True, exist_ok=True)
    passed = report.state != "changes_requested"
    payload = {
        "repository": report.repository,
        "pull_request": report.number,
        "head_sha": report.head_sha,
        "state": report.state,
        "passed": passed,
        "reasons": list(report.reasons),
        "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    (output_dir / "coderabbit-review-state.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# CodeRabbit review state",
        "",
        f"- Repository: `{report.repository}`",
        f"- Pull Request: `#{report.number}`",
        f"- Head: `{report.head_sha}`",
        f"- Reviewzustand: **{report.state}**",
        f"- Ergebnis: **{'bestanden' if passed else 'blockiert'}**",
        "",
        "## Begründung",
        "",
        *(f"- {reason}" for reason in report.reasons),
    ]
    if not report.reasons:
        lines.append(
            "- Kein aktiver CodeRabbit-Changes-Requested-Review blockiert den PR."
        )
    (output_dir / "coderabbit-review-state.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> int:
    """Aktuellen PR-Head und formellen CodeRabbit-Reviewzustand prüfen."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--output-dir", type=Path, default=Path("build/review-gate"))
    args = parser.parse_args()
    if not args.repository or not args.token or not args.pr_number:
        parser.error("repository, token und pr-number sind erforderlich")

    pull = _mapping(
        _request_json(
            f"{API}/repos/{args.repository}/pulls/{args.pr_number}", args.token
        )
    )
    if pull.get("state") != "open":
        print(f"PR #{args.pr_number} ist nicht offen; Reviewzustand wird übersprungen.")
        return 0
    head_sha = str(_mapping(pull.get("head")).get("sha") or "")
    if not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        raise RuntimeError("Aktueller PR-Head konnte nicht bestimmt werden")

    state, reasons = evaluate_coderabbit_review_state(
        _reviews(args.repository, args.pr_number, args.token)
    )
    _write_report(
        args.output_dir,
        ReviewStateReport(
            repository=args.repository,
            number=args.pr_number,
            head_sha=head_sha,
            state=state,
            reasons=tuple(reasons),
        ),
    )
    print((args.output_dir / "coderabbit-review-state.md").read_text(encoding="utf-8"))
    return 1 if state == "changes_requested" else 0


if __name__ == "__main__":
    raise SystemExit(main())
