#!/usr/bin/env python3
"""Atomare, driftgeschützte Migration und Rollback des Main-Rulesets."""

from __future__ import annotations

from dataclasses import asdict
import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ruleset_contract import (
    NEW_CONTEXT,
    OLD_CONTEXTS,
    PRESERVED_CONTEXTS,
    TransitionSummary,
    canonical_digest,
    load_json,
    required_checks,
    ruleset_payload,
    validate_rollback,
    validate_transition,
)

__all__ = [
    "NEW_CONTEXT",
    "OLD_CONTEXTS",
    "PRESERVED_CONTEXTS",
    "TransitionSummary",
    "canonical_digest",
    "load_json",
    "required_checks",
    "ruleset_payload",
    "validate_rollback",
    "validate_transition",
]

API = "https://api.github.com"


def _request_json(
    url: str,
    token: str | None,
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request = Request(
        url,
        data=None if data is None else json.dumps(data).encode("utf-8"),
        method=method,
    )
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", "ADHS-Lernpfad-ruleset-migration")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        hint = " Mit GITHUB_TOKEN erneut ausführen." if not token else ""
        raise RuntimeError(
            f"GitHub API {exc.code} für {url}: {detail[:500]}.{hint}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError("GitHub lieferte kein Ruleset-Objekt")
    return payload


def _write_report(
    output_dir: Path,
    *,
    summary: TransitionSummary,
    applied: bool,
    live_before: dict[str, Any],
    live_after: dict[str, Any] | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "ruleset-before.json").write_text(
        json.dumps(live_before, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if live_after is not None:
        (output_dir / "ruleset-after.json").write_text(
            json.dumps(live_after, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    (output_dir / "ruleset-migration-report.json").write_text(
        json.dumps(
            {"applied": applied, "summary": asdict(summary)},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--ruleset-id", type=int, default=20499620)
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument(
        "--before",
        type=Path,
        default=Path("automation/rulesets/main-required-gates.before.json"),
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path("automation/rulesets/main-required-gates.target.json"),
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("build/ruleset-migration")
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args()
    if not args.repository:
        parser.error("repository ist erforderlich")
    if args.apply and not args.token:
        parser.error("--apply benötigt GITHUB_TOKEN mit Administration:write")

    before = load_json(args.before)
    target = load_json(args.target)
    expected, desired = (target, before) if args.rollback else (before, target)
    validator = validate_rollback if args.rollback else validate_transition
    url = f"{API}/repos/{args.repository}/rulesets/{args.ruleset_id}"
    live = _request_json(url, args.token)
    if canonical_digest(live) != canonical_digest(expected):
        raise RuntimeError(
            "Live-Ruleset weicht vom geprüften Ausgangssnapshot ab; "
            "Transition abgebrochen."
        )
    summary = validator(live, desired)

    after: dict[str, Any] | None = None
    if args.apply:
        _request_json(url, args.token, method="PUT", data=ruleset_payload(desired))
        after = _request_json(url, args.token)
        if canonical_digest(after) != canonical_digest(desired):
            raise RuntimeError(
                "GitHub-Ruleset entspricht nach PUT nicht dem Zielvertrag"
            )

    _write_report(
        args.output_dir,
        summary=summary,
        applied=args.apply,
        live_before=live,
        live_after=after,
    )
    print(
        json.dumps(
            {"applied": args.apply, **asdict(summary)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
