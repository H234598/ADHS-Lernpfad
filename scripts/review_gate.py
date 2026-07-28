#!/usr/bin/env python3
"""Blockierendes CodeRabbit-Gate für den aktuellen Pull-Request-Head."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"
CODERABBIT_RE = re.compile(r"coderabbit", re.IGNORECASE)
CODERABBIT_AUTHOR_RE = re.compile(r"^coderabbitai(?:\[bot\])?$", re.IGNORECASE)
SELF_GATE_RE = re.compile(
    r"(?:coderabbit.*review\s*gate|review\s*gate.*coderabbit)", re.IGNORECASE
)
DISAGREEMENT_RE = re.compile(r"<!--\s*coderabbit-disagreement\s+head=([0-9a-f]{40})\s*-->")
DISAGREEMENT_RESOLVED_RE = re.compile(
    r"<!--\s*coderabbit-disagreement-resolved\s+head=([0-9a-f]{40})\s*-->"
)


@dataclass(frozen=True)
class GateResult:
    """Auswertbares Ergebnis des verpflichtenden Review-Gates."""

    repository: str
    pull_request: int
    head_sha: str
    coderabbit_state: str
    coderabbit_signals: list[dict[str, str]]
    unresolved_thread_ids: list[str]
    disagreement_open: bool
    passed: bool
    reasons: list[str]
    checked_at: str


def is_coderabbit_signal(name: str, app_name: str = "") -> bool:
    """Echte CodeRabbit-Signale erkennen, ohne das eigene Gate zu zählen."""

    combined = " ".join(part for part in (app_name, name) if part).strip()
    return bool(CODERABBIT_RE.search(combined)) and not bool(SELF_GATE_RE.search(combined))


def is_coderabbit_author(login: str) -> bool:
    """Nur die bekannten CodeRabbit-Kommentaridentitäten akzeptieren."""

    return bool(CODERABBIT_AUTHOR_RE.fullmatch(login.strip()))


def is_trusted_resolution_author(login: str, trusted_authors: set[str]) -> bool:
    """Dissensauflösungen nur CodeRabbit oder explizit vertrauten Menschen erlauben."""

    normalized = login.strip().casefold()
    trusted = {author.strip().casefold() for author in trusted_authors if author.strip()}
    return is_coderabbit_author(login) or normalized in trusted


def _mapping(value: Any) -> dict[str, Any]:
    """Ungeprüfte API-Werte defensiv als Mapping behandeln."""

    return value if isinstance(value, dict) else {}


def _items(value: Any) -> list[Any]:
    """Ungeprüfte API-Werte defensiv als Liste behandeln."""

    return value if isinstance(value, list) else []


def _request_json(url: str, token: str, *, data: dict[str, Any] | None = None) -> Any:
    body = None if data is None else json.dumps(data).encode("utf-8")
    request = Request(url, data=body)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("User-Agent", "ADHS-Lernpfad-review-gate")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code} für {url}: {detail[:500]}") from exc


def _latest_coderabbit_signals(
    repository: str,
    head_sha: str,
    token: str,
) -> list[dict[str, str]]:
    """Alle aktuellen CodeRabbit-Status- und Check-Signale des Heads lesen."""

    statuses = _mapping(
        _request_json(f"{API}/repos/{repository}/commits/{head_sha}/status", token)
    )
    checks: list[Any] = []
    page = 1
    while True:
        batch = _mapping(
            _request_json(
                f"{API}/repos/{repository}/commits/{head_sha}/check-runs"
                f"?per_page=100&page={page}",
                token,
            )
        )
        batch_checks = _items(batch.get("check_runs"))
        checks.extend(batch_checks)
        if len(batch_checks) < 100:
            break
        page += 1

    collected: list[dict[str, str]] = []
    for raw_status in _items(statuses.get("statuses")):
        status = _mapping(raw_status)
        context = str(status.get("context") or "")
        if is_coderabbit_signal(context):
            collected.append(
                {
                    "key": f"status:{context.casefold()}",
                    "name": context,
                    "state": str(status.get("state") or "missing"),
                    "updated_at": str(
                        status.get("updated_at") or status.get("created_at") or ""
                    ),
                    "url": str(status.get("target_url") or ""),
                }
            )

    for raw_check in checks:
        check = _mapping(raw_check)
        name = str(check.get("name") or "")
        app_name = str(_mapping(check.get("app")).get("name") or "")
        if is_coderabbit_signal(name, app_name):
            state = str(check.get("conclusion") or check.get("status") or "missing")
            collected.append(
                {
                    "key": f"check:{app_name.casefold()}:{name.casefold()}",
                    "name": f"{app_name}: {name}".strip(": "),
                    "state": state,
                    "updated_at": str(
                        check.get("completed_at") or check.get("started_at") or ""
                    ),
                    "url": str(check.get("html_url") or ""),
                }
            )

    latest: dict[str, dict[str, str]] = {}
    for signal in collected:
        current = latest.get(signal["key"])
        if current is None or signal["updated_at"] >= current["updated_at"]:
            latest[signal["key"]] = signal
    return sorted(latest.values(), key=lambda item: (item["name"], item["updated_at"]))


def _review_threads(repository: str, number: int, token: str) -> list[dict[str, Any]]:
    owner, name = repository.split("/", 1)
    query = """
    query($owner: String!, $name: String!, $number: Int!, $after: String) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $number) {
          reviewThreads(first: 100, after: $after) {
            nodes {
              id
              isResolved
              isOutdated
              comments(first: 100) {
                nodes { author { login } body url createdAt }
              }
            }
            pageInfo { hasNextPage endCursor }
          }
        }
      }
    }
    """
    after: str | None = None
    result: list[dict[str, Any]] = []
    while True:
        payload = _mapping(
            _request_json(
                GRAPHQL,
                token,
                data={
                    "query": query,
                    "variables": {
                        "owner": owner,
                        "name": name,
                        "number": number,
                        "after": after,
                    },
                },
            )
        )
        if payload.get("errors"):
            raise RuntimeError(f"GitHub GraphQL: {payload['errors']}")
        data = _mapping(payload.get("data"))
        repository_data = _mapping(data.get("repository"))
        pull = repository_data.get("pullRequest")
        if not isinstance(pull, dict):
            raise RuntimeError(f"Pull Request #{number} wurde nicht gefunden")
        connection = _mapping(pull.get("reviewThreads"))
        result.extend(
            item for item in _items(connection.get("nodes")) if isinstance(item, dict)
        )
        page_info = _mapping(connection.get("pageInfo"))
        if not page_info.get("hasNextPage"):
            return result
        after = str(page_info.get("endCursor") or "") or None


def _issue_comments(repository: str, number: int, token: str) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    page = 1
    while True:
        batch = _items(
            _request_json(
                f"{API}/repos/{repository}/issues/{number}/comments"
                f"?per_page=100&page={page}",
                token,
            )
        )
        comments.extend(item for item in batch if isinstance(item, dict))
        if len(batch) < 100:
            return comments
        page += 1


def evaluate_gate(
    *,
    signals: list[dict[str, str]],
    threads: list[dict[str, Any]],
    comments: list[dict[str, Any]],
    head_sha: str,
    trusted_resolution_authors: set[str] | None = None,
) -> tuple[str, list[str], list[str], bool]:
    """GitHub-Rohdaten ohne Seiteneffekte zu einer Gateentscheidung verdichten."""

    trusted_authors = trusted_resolution_authors or set()
    reasons: list[str] = []
    states = [signal.get("state", "missing").casefold() for signal in signals]
    successful = {"success"}
    pending = {
        "",
        "missing",
        "pending",
        "queued",
        "in_progress",
        "requested",
        "waiting",
        "neutral",
        "skipped",
    }
    if not signals:
        coderabbit_state = "missing"
        reasons.append("Kein CodeRabbit-Signal für den aktuellen Head vorhanden.")
    elif any(state not in successful | pending for state in states):
        coderabbit_state = "failure"
        reasons.append("Mindestens ein aktuelles CodeRabbit-Signal ist fehlgeschlagen.")
    elif any(state in pending for state in states):
        coderabbit_state = "pending"
        reasons.append("Mindestens ein aktuelles CodeRabbit-Signal läuft noch.")
    else:
        coderabbit_state = "success"

    unresolved: list[str] = []
    for thread in threads:
        if thread.get("isResolved"):
            continue
        thread_comments = _mapping(thread.get("comments"))
        authors = [
            str(_mapping(_mapping(comment).get("author")).get("login") or "")
            for comment in _items(thread_comments.get("nodes"))
        ]
        if any(is_coderabbit_author(author) for author in authors):
            unresolved.append(str(thread.get("id")))
    if unresolved:
        reasons.append(
            f"{len(unresolved)} CodeRabbit-Review-Thread(s) sind ungelöst; auch "
            "veraltete Threads müssen begründet abgeschlossen werden."
        )

    disagreements: dict[str, datetime] = {}
    resolutions: dict[str, datetime] = {}
    ignored_resolution_authors: set[str] = set()
    for raw_comment in comments:
        comment = _mapping(raw_comment)
        body = str(comment.get("body") or "")
        raw_created = str(comment.get("created_at") or "")
        if not raw_created:
            continue
        created = datetime.fromisoformat(raw_created.replace("Z", "+00:00"))
        for marked_head in DISAGREEMENT_RE.findall(body):
            disagreements[marked_head] = max(disagreements.get(marked_head, created), created)

        resolution_heads = DISAGREEMENT_RESOLVED_RE.findall(body)
        if not resolution_heads:
            continue
        author = str(_mapping(comment.get("user")).get("login") or "")
        if not is_trusted_resolution_author(author, trusted_authors):
            ignored_resolution_authors.add(author or "<unbekannt>")
            continue
        for marked_head in resolution_heads:
            resolutions[marked_head] = max(resolutions.get(marked_head, created), created)

    if ignored_resolution_authors:
        reasons.append(
            "Nicht vertrauenswürdige Dissensauflösung ignoriert von: "
            + ", ".join(sorted(ignored_resolution_authors))
        )

    open_disagreement_heads = sorted(
        marked_head
        for marked_head, marked_at in disagreements.items()
        if marked_head not in resolutions or marked_at > resolutions[marked_head]
    )
    disagreement_open = bool(open_disagreement_heads)
    if disagreement_open:
        scope = "aktuellen Head" if head_sha in open_disagreement_heads else "aktuellen oder früheren Head"
        reasons.append(
            f"Ein dokumentierter Agent-CodeRabbit-Konflikt für den {scope} ist "
            "ungeklärt: " + ", ".join(open_disagreement_heads)
        )

    return coderabbit_state, unresolved, reasons, disagreement_open


def _write_report(result: GateResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "review-gate.json").write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# CodeRabbit hard gate",
        "",
        f"- Repository: `{result.repository}`",
        f"- Pull Request: `#{result.pull_request}`",
        f"- Head: `{result.head_sha}`",
        f"- CodeRabbit: **{result.coderabbit_state}**",
        f"- ungelöste Threads: **{len(result.unresolved_thread_ids)}**",
        f"- ungeklärter Dissens: **{'ja' if result.disagreement_open else 'nein'}**",
        f"- Gate: **{'bestanden' if result.passed else 'blockiert'}**",
        "",
        "## Begründung",
        "",
    ]
    lines.extend(f"- {reason}" for reason in result.reasons)
    if not result.reasons:
        lines.append("- CodeRabbit ist für den aktuellen Head erfolgreich und alle Threads sind gelöst.")
    (output_dir / "review-gate.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--output-dir", type=Path, default=Path("build/review-gate"))
    parser.add_argument(
        "--trusted-resolver",
        action="append",
        default=[],
        help="Zusätzlicher GitHub-Login, der einen Dissens ausdrücklich auflösen darf.",
    )
    args = parser.parse_args()
    if not args.repository or not args.token or not args.pr_number:
        parser.error("repository, token und pr-number sind erforderlich")

    pull = _mapping(
        _request_json(
            f"{API}/repos/{args.repository}/pulls/{args.pr_number}", args.token
        )
    )
    if pull.get("state") != "open":
        print(f"PR #{args.pr_number} ist nicht offen; Gate wird übersprungen.")
        return 0
    head_sha = str(_mapping(pull.get("head")).get("sha") or "")
    if not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        raise RuntimeError("Aktueller PR-Head konnte nicht bestimmt werden")

    signals = _latest_coderabbit_signals(args.repository, head_sha, args.token)
    threads = _review_threads(args.repository, args.pr_number, args.token)
    comments = _issue_comments(args.repository, args.pr_number, args.token)
    repository_owner = args.repository.split("/", 1)[0]
    trusted_resolution_authors = {repository_owner, *args.trusted_resolver}
    state, unresolved, reasons, disagreement = evaluate_gate(
        signals=signals,
        threads=threads,
        comments=comments,
        head_sha=head_sha,
        trusted_resolution_authors=trusted_resolution_authors,
    )
    passed = state == "success" and not unresolved and not disagreement
    result = GateResult(
        repository=args.repository,
        pull_request=args.pr_number,
        head_sha=head_sha,
        coderabbit_state=state,
        coderabbit_signals=signals,
        unresolved_thread_ids=unresolved,
        disagreement_open=disagreement,
        passed=passed,
        reasons=reasons,
        checked_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    _write_report(result, args.output_dir)
    print((args.output_dir / "review-gate.md").read_text(encoding="utf-8"))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
