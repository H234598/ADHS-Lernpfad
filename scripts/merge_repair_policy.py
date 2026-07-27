#!/usr/bin/env python3
"""Deterministische Zeit-, Review- und Reparaturentscheidung für Einheiten-PRs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
import argparse
import json
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
REVIEW_DELAY = timedelta(hours=2)
REPAIR_HOUR = 20
CI_STATES = {"success", "failure", "pending", "missing"}
REVIEW_STATES = {"success", "failure", "pending", "missing"}


@dataclass(frozen=True)
class PolicyDecision:
    """Maschinenlesbare Entscheidung des Merge-Wächters."""

    action: str
    reason: str
    review_eligible_at: str
    repair_eligible_at: str
    hard_blocker: bool
    repair_allowed: bool


def parse_timestamp(value: str) -> datetime:
    """RFC-3339-Zeitstempel einlesen und nach Europe/Berlin umrechnen."""

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Zeitstempel benötigt eine Zeitzone")
    return parsed.astimezone(BERLIN)


def policy_deadlines(created_at: datetime) -> tuple[datetime, datetime]:
    """Review- und Reparaturfrist für den Erstellungstag bestimmen."""

    local_created = created_at.astimezone(BERLIN)
    review_eligible = local_created + REVIEW_DELAY
    same_day_20 = datetime.combine(local_created.date(), time(REPAIR_HOUR), BERLIN)
    repair_eligible = max(review_eligible, same_day_20)
    return review_eligible, repair_eligible


def evaluate_policy(
    *,
    created_at: datetime,
    now: datetime,
    ci_state: str,
    coderabbit_state: str,
    unresolved_threads: int,
    disagreement: bool,
    draft: bool,
    second_ci_state: str = "missing",
) -> PolicyDecision:
    """Aus aktuellem PR-Zustand genau eine sichere Aktion ableiten."""

    if ci_state not in CI_STATES:
        raise ValueError(f"Unbekannter CI-Zustand: {ci_state}")
    if coderabbit_state not in REVIEW_STATES:
        raise ValueError(f"Unbekannter CodeRabbit-Zustand: {coderabbit_state}")
    if second_ci_state not in CI_STATES:
        raise ValueError(f"Unbekannter Zweit-CI-Zustand: {second_ci_state}")
    if unresolved_threads < 0:
        raise ValueError("unresolved_threads darf nicht negativ sein")

    local_now = now.astimezone(BERLIN)
    review_at, repair_at = policy_deadlines(created_at)

    def decision(action: str, reason: str, *, blocker: bool, repair: bool) -> PolicyDecision:
        return PolicyDecision(
            action=action,
            reason=reason,
            review_eligible_at=review_at.isoformat(),
            repair_eligible_at=repair_at.isoformat(),
            hard_blocker=blocker,
            repair_allowed=repair,
        )

    if local_now < review_at:
        return decision(
            "wait_initial_review",
            "Die verbindliche zweistündige Reviewfrist ist noch nicht abgelaufen.",
            blocker=False,
            repair=False,
        )

    if disagreement:
        return decision(
            "manual_intervention",
            "Agent und CodeRabbit sind fachlich oder technisch nicht zu einer belastbaren Einigung gekommen.",
            blocker=True,
            repair=False,
        )

    review_failed = coderabbit_state == "failure" or unresolved_threads > 0
    first_ci_failed = ci_state == "failure"
    second_ci_failed = not draft and second_ci_state == "failure"
    repairable_failure = first_ci_failed or second_ci_failed or review_failed

    # Eine rote CI oder ein konkreter Reviewbefund bleibt reparierbar, auch wenn
    # CodeRabbit für denselben Head noch läuft. Das fehlende Review verhindert
    # Ready/Merge, darf aber eine nach 20:00 nötige CI-Reparatur nicht blockieren.
    if repairable_failure and local_now < repair_at:
        return decision(
            "wait_until_repair_window",
            "CI oder Review ist rot; vor dem Reparaturfenster wird noch kein Reparaturzyklus gestartet.",
            blocker=review_failed,
            repair=False,
        )

    if repairable_failure:
        return decision(
            "repair_existing_branch",
            "Nach Beginn des Reparaturfensters ist ein sicherer Zyklus auf dem bestehenden PR-Branch erforderlich.",
            blocker=review_failed,
            repair=True,
        )

    if coderabbit_state in {"missing", "pending"}:
        return decision(
            "wait_coderabbit",
            "Eine erfolgreiche CodeRabbit-Prüfung des aktuellen Heads fehlt noch.",
            blocker=True,
            repair=False,
        )

    if coderabbit_state != "success" or unresolved_threads:
        return decision(
            "hard_block_review",
            "Das verpflichtende CodeRabbit-Gate ist nicht vollständig grün.",
            blocker=True,
            repair=False,
        )

    if ci_state in {"missing", "pending"}:
        return decision(
            "wait_ci",
            "Die CI des aktuellen Heads fehlt oder läuft noch.",
            blocker=False,
            repair=False,
        )

    if ci_state != "success":
        return decision(
            "wait_ci",
            "Die erste CI ist nicht vollständig erfolgreich.",
            blocker=False,
            repair=False,
        )

    if draft:
        return decision(
            "ready_for_review",
            "Erste CI und CodeRabbit-Gate sind grün; der Draft darf umgewandelt, aber noch nicht gemergt werden.",
            blocker=False,
            repair=False,
        )

    if second_ci_state in {"missing", "pending"}:
        return decision(
            "wait_second_ci",
            "Die nach Ready for review gestartete zweite CI fehlt oder läuft noch.",
            blocker=False,
            repair=False,
        )

    return decision(
        "merge",
        "Zweite CI, Remark-lint und verpflichtendes CodeRabbit-Gate sind vollständig grün.",
        blocker=False,
        repair=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--now")
    parser.add_argument("--ci-state", required=True, choices=sorted(CI_STATES))
    parser.add_argument("--coderabbit-state", required=True, choices=sorted(REVIEW_STATES))
    parser.add_argument("--unresolved-threads", type=int, default=0)
    parser.add_argument("--disagreement", action="store_true")
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--second-ci-state", default="missing", choices=sorted(CI_STATES))
    args = parser.parse_args()

    created_at = parse_timestamp(args.created_at)
    now = parse_timestamp(args.now) if args.now else datetime.now(BERLIN)
    result = evaluate_policy(
        created_at=created_at,
        now=now,
        ci_state=args.ci_state,
        coderabbit_state=args.coderabbit_state,
        unresolved_threads=args.unresolved_threads,
        disagreement=args.disagreement,
        draft=args.draft,
        second_ci_state=args.second_ci_state,
    )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if not result.hard_blocker else 20


if __name__ == "__main__":
    raise SystemExit(main())
