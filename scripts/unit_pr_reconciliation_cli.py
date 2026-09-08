"""Trusted GitHub/StatusStore adapter for automated unit-PR reconciliation."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess  # nosec B404 -- fixed git executable/arguments, no shell
from typing import Any

from automation_status import RevisionConflict, StatusStore, read_status
from github_api import request_json
from unit_pr_reconciliation import (
    ReconciliationDecision,
    evaluate_closed_unit_pr,
    finalize_reconciliation,
    prepare_reconciliation,
)

API = "https://api.github.com"


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _request(url: str, token: str) -> Any:
    return request_json(
        url,
        token,
        user_agent="ADHS-Lernpfad-unit-pr-reconciliation",
    )


def _paginated_check_runs(
    repository: str,
    head_sha: str,
    token: str,
) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = _mapping(
            _request(
                f"{API}/repos/{repository}/commits/{head_sha}/check-runs"
                f"?per_page=100&page={page}",
                token,
            )
        )
        batch = [
            item
            for item in payload.get("check_runs", [])
            if isinstance(item, dict)
        ]
        runs.extend(batch)
        if len(batch) < 100:
            return runs
        page += 1


def _main_proof(
    repository: str,
    merge_sha: str | None,
    token: str,
) -> tuple[str, bool]:
    branch = _mapping(_request(f"{API}/repos/{repository}/branches/main", token))
    main_sha = str(_mapping(branch.get("commit")).get("sha") or "")
    if not merge_sha:
        return main_sha, False
    if main_sha == merge_sha:
        return main_sha, True
    comparison = _mapping(
        _request(f"{API}/repos/{repository}/compare/{merge_sha}...main", token)
    )
    contains_merge = str(comparison.get("status") or "").casefold() in {
        "ahead",
        "identical",
    }
    return main_sha, contains_merge


def _load_latest(store: StatusStore) -> dict[str, Any]:
    return read_status(store.latest_path("generator"))


def evaluate_snapshot(
    *,
    repository: str,
    pr_number: int,
    token: str,
    store: StatusStore,
) -> dict[str, Any]:
    """Read GitHub and canonical status without mutating either source."""

    status = _load_latest(store)
    pull = _mapping(
        _request(f"{API}/repos/{repository}/pulls/{pr_number}", token)
    )
    head_sha = str(_mapping(status.get("context")).get("commit_sha") or "")
    checks = _paginated_check_runs(repository, head_sha, token)
    decision = evaluate_closed_unit_pr(status, pull, checks)
    main_sha, main_contains_merge = _main_proof(
        repository,
        decision.merge_sha,
        token,
    )

    if decision.action == "complete_merged_run" and not main_contains_merge:
        decision = ReconciliationDecision(
            action="block_merged_outside_policy",
            passed=False,
            code="merged_content_not_on_main",
            merge_sha=decision.merge_sha,
            required_checks=decision.required_checks,
            reasons=(
                *decision.reasons,
                (
                    "Der Merge-Commit ist nicht als Bestandteil des aktuellen main "
                    "nachgewiesen."
                ),
            ),
        )

    return {
        "schema_version": "1.0.0",
        "repository": repository,
        "pr_number": pr_number,
        "run_id": str(status["run_id"]),
        "expected_revision": int(status["revision"]),
        "head_ref": str(_mapping(pull.get("head")).get("ref") or ""),
        "main_sha": main_sha,
        "main_contains_merge": main_contains_merge,
        "decision": asdict(decision),
    }


def _decision(payload: Mapping[str, Any]) -> ReconciliationDecision:
    raw = _mapping(payload.get("decision"))
    required = raw.get("required_checks")
    return ReconciliationDecision(
        action=str(raw.get("action") or "ignore"),
        passed=bool(raw.get("passed")),
        code=str(raw.get("code") or "invalid_decision"),
        merge_sha=str(raw.get("merge_sha")) if raw.get("merge_sha") else None,
        required_checks={
            str(name): {
                str(key): str(value)
                for key, value in _mapping(summary).items()
            }
            for name, summary in _mapping(required).items()
        },
        reasons=tuple(
            str(item)
            for item in raw.get("reasons", [])
            if isinstance(item, str)
        ),
    )


def _branch_exists(head_ref: str) -> bool:
    """Return whether the validated unit branch still exists on origin."""

    if not head_ref.startswith("agent/einheit-"):
        return False
    result = subprocess.run(  # nosec B603 -- fixed command + validated ref prefix
        [
            "git",
            "ls-remote",
            "--exit-code",
            "--heads",
            "origin",
            f"refs/heads/{head_ref}",
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def prepare_snapshot(
    *,
    snapshot: Mapping[str, Any],
    store: StatusStore,
) -> dict[str, Any]:
    """Advance the canonical run only through its persisted cleanup phase."""

    decision = _decision(snapshot)
    head_ref = str(snapshot.get("head_ref") or "")
    branch_exists = _branch_exists(head_ref)
    return prepare_reconciliation(
        store,
        workflow="generator",
        run_id=str(snapshot["run_id"]),
        decision=decision,
        expected_revision=int(snapshot["expected_revision"]),
        repository=str(snapshot["repository"]),
        pr_number=int(snapshot["pr_number"]),
        main_sha=str(snapshot.get("main_sha") or "") or None,
        main_contains_merge=bool(snapshot.get("main_contains_merge")),
        branch_exists=branch_exists,
    )


def finalize_snapshot(
    *,
    prepared: Mapping[str, Any],
    store: StatusStore,
    branch_exists: bool,
) -> dict[str, Any]:
    """Finalize a cleanup phase already persisted to the remote status branch."""

    result_status = _mapping(prepared.get("result_status"))
    if not result_status:
        raise RuntimeError("Vorbereiteter Reconciliation-Bericht enthält keinen Status")
    return finalize_reconciliation(
        store,
        workflow="generator",
        run_id=str(prepared["run_id"]),
        expected_revision=int(result_status["revision"]),
        branch_exists=branch_exists,
    )


def _bool(value: str) -> bool:
    normalized = value.casefold()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise argparse.ArgumentTypeError("boolean muss true oder false sein")


def _parse_args() -> argparse.Namespace:
    """Parse the trusted workflow adapter command line."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--status-root", type=Path, required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--evaluate", action="store_true")
    modes.add_argument("--prepare-decision", type=Path)
    modes.add_argument("--finalize-cleanup", type=Path)
    parser.add_argument("--branch-exists", type=_bool)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/unit-pr-reconciliation.json"),
    )
    args = parser.parse_args()
    if args.evaluate and (
        not args.repository or not args.pr_number or not args.token
    ):
        parser.error("--evaluate benötigt repository, pr-number und token")
    if args.finalize_cleanup and args.branch_exists is None:
        parser.error("--finalize-cleanup benötigt --branch-exists")
    return args


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Reconciliation-Snapshot muss ein JSON-Objekt sein")
    return payload


def main() -> int:
    """Evaluate, prepare, or finalize one reconciliation snapshot."""

    try:
        args = _parse_args()
        store = StatusStore(args.status_root)
        if args.evaluate:
            payload = evaluate_snapshot(
                repository=args.repository,
                pr_number=args.pr_number,
                token=args.token,
                store=store,
            )
        elif args.prepare_decision:
            payload = _load_object(args.prepare_decision)
            status = prepare_snapshot(snapshot=payload, store=store)
            payload = {**payload, "result_status": status}
        else:
            payload = _load_object(args.finalize_cleanup)
            status = finalize_snapshot(
                prepared=payload,
                store=store,
                branch_exists=args.branch_exists,
            )
            payload = {**payload, "result_status": status}

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except RevisionConflict as exc:
        print(f"CAS-Konflikt: {exc}")
        return 20
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
