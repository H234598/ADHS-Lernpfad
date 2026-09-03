"""Driftgeschützter Vertrag für die Main-Ruleset-Transition."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

OLD_CONTEXTS = {"content-scope", "claim-source-entailment", "complete-build"}
NEW_CONTEXT = "Learning card policy (blocking)"
PRESERVED_CONTEXTS = {
    "Validate and build",
    "Build all download formats",
    "Remark lint (blocking)",
    "CodeRabbit review gate (blocking)",
}
READ_ONLY_KEYS = {
    "id",
    "node_id",
    "source_type",
    "source",
    "created_at",
    "updated_at",
    "current_user_can_bypass",
    "_links",
}


@dataclass(frozen=True)
class TransitionSummary:
    """Maschinenlesbare Zusammenfassung einer erlaubten Transition."""

    direction: str
    current_digest: str
    target_digest: str
    removed_contexts: tuple[str, ...]
    added_contexts: tuple[str, ...]
    bypass_actors_preserved: bool


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def load_json(path: Path) -> dict[str, Any]:
    """Ein versioniertes Ruleset-Snapshot laden."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} muss ein JSON-Objekt enthalten")
    return value


def ruleset_payload(document: dict[str, Any]) -> dict[str, Any]:
    """Nur von GitHubs Update-API akzeptierte Felder behalten."""

    accepted = {"name", "target", "enforcement", "bypass_actors", "conditions", "rules"}
    payload = {
        key: value
        for key, value in document.items()
        if key in accepted and key not in READ_ONLY_KEYS
    }
    missing = sorted(
        {"name", "target", "enforcement", "conditions", "rules"} - payload.keys()
    )
    if missing:
        raise ValueError("Ruleset-Payload unvollständig: " + ", ".join(missing))
    payload.setdefault("bypass_actors", [])
    return payload


def canonical_digest(document: dict[str, Any]) -> str:
    """Den schreibbaren Rulesetvertrag kanonisch hashen."""

    canonical = json.dumps(
        ruleset_payload(document),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _status_rule(document: dict[str, Any]) -> dict[str, Any]:
    matches = [
        rule
        for rule in document.get("rules", [])
        if isinstance(rule, dict) and rule.get("type") == "required_status_checks"
    ]
    if len(matches) != 1:
        raise ValueError("Ruleset benötigt genau eine required_status_checks-Regel")
    return matches[0]


def required_checks(document: dict[str, Any]) -> dict[str, int | None]:
    """Required-Check-Kontexte samt optionaler App-Bindung lesen."""

    raw_checks = _mapping(_status_rule(document).get("parameters")).get(
        "required_status_checks", []
    )
    result: dict[str, int | None] = {}
    for raw in raw_checks:
        check = _mapping(raw)
        context = str(check.get("context") or "")
        if not context or context in result:
            raise ValueError(f"Leerer oder doppelter Required-Check-Kontext: {context}")
        integration = check.get("integration_id")
        result[context] = int(integration) if integration is not None else None
    return result


def _rules_without_status(document: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        rule
        for rule in document.get("rules", [])
        if isinstance(rule, dict) and rule.get("type") != "required_status_checks"
    ]


def _status_parameters_without_checks(document: dict[str, Any]) -> dict[str, Any]:
    """Nicht-Kontext-Parameter der Required-Checks driftgeschützt vergleichen."""

    parameters = dict(_mapping(_status_rule(document).get("parameters")))
    parameters.pop("required_status_checks", None)
    return parameters


def _validate_common(current: dict[str, Any], target: dict[str, Any]) -> None:
    for key in ("name", "target", "enforcement", "conditions"):
        if current.get(key) != target.get(key):
            raise ValueError(f"Unzulässiger Ruleset-Drift in {key}")
    if current.get("bypass_actors", []) != target.get("bypass_actors", []):
        raise ValueError(
            "Bypass-Akteure oder Bypass-Modi dürfen nicht verändert werden"
        )
    if _rules_without_status(current) != _rules_without_status(target):
        raise ValueError("Regeln außerhalb required_status_checks dürfen nicht driften")
    if _status_parameters_without_checks(current) != _status_parameters_without_checks(
        target
    ):
        raise ValueError(
            "Parameter von required_status_checks außerhalb der Kontextliste dürfen "
            "nicht driften"
        )


def _transition(
    current: dict[str, Any],
    target: dict[str, Any],
    *,
    direction: str,
    expected_current: set[str],
    expected_target: set[str],
) -> TransitionSummary:
    current_payload = ruleset_payload(current)
    target_payload = ruleset_payload(target)
    _validate_common(current_payload, target_payload)
    current_checks = required_checks(current_payload)
    target_checks = required_checks(target_payload)
    if set(current_checks) != expected_current:
        raise ValueError("Unerwarteter Ausgangsvertrag")
    if set(target_checks) != expected_target:
        raise ValueError("Unerwarteter Zielvertrag")
    for context in PRESERVED_CONTEXTS:
        if current_checks[context] != target_checks[context]:
            raise ValueError(
                f"Providerbindung von {context} darf nicht geändert werden"
            )
    if NEW_CONTEXT in target_checks and target_checks[NEW_CONTEXT] != 15368:
        raise ValueError("Learning card policy muss von GitHub Actions stammen")
    if NEW_CONTEXT in current_checks and current_checks[NEW_CONTEXT] != 15368:
        raise ValueError("Ausgangs-Aggregator stammt nicht von GitHub Actions")
    return TransitionSummary(
        direction=direction,
        current_digest=canonical_digest(current_payload),
        target_digest=canonical_digest(target_payload),
        removed_contexts=tuple(sorted(set(current_checks) - set(target_checks))),
        added_contexts=tuple(sorted(set(target_checks) - set(current_checks))),
        bypass_actors_preserved=True,
    )


def validate_transition(
    current: dict[str, Any], target: dict[str, Any]
) -> TransitionSummary:
    """Nur den Austausch der drei Rohkontexte gegen den Aggregator erlauben."""

    return _transition(
        current,
        target,
        direction="forward",
        expected_current=PRESERVED_CONTEXTS | OLD_CONTEXTS,
        expected_target=PRESERVED_CONTEXTS | {NEW_CONTEXT},
    )


def validate_rollback(
    current: dict[str, Any], target: dict[str, Any]
) -> TransitionSummary:
    """Nur den exakten Rücktausch gegen die drei Rohkontexte erlauben."""

    return _transition(
        current,
        target,
        direction="rollback",
        expected_current=PRESERVED_CONTEXTS | {NEW_CONTEXT},
        expected_target=PRESERVED_CONTEXTS | OLD_CONTEXTS,
    )
