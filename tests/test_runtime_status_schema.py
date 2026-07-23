"""Regression tests for the strict automation recovery schema."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from scripts.automation_status import (
    ERROR_CLASSES,
    PHASES,
    RECOVERY_LEVELS,
    SCHEMA_VERSION,
    STATUSES,
    WORKFLOWS,
    start_run,
    validate_status,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "automation" / "run-status.schema.json"


def _schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_runtime_status_schema_is_valid_draft_2020_12_json() -> None:
    schema = _schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema["type"] == "object"
    assert schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION


def test_schema_and_dependency_free_enumerations_are_identical() -> None:
    schema = _schema()
    assert set(schema["$defs"]["status"]["enum"]) == STATUSES
    assert set(schema["$defs"]["phase"]["enum"]) == PHASES
    assert set(schema["properties"]["workflow"]["enum"]) == WORKFLOWS
    assert set(schema["$defs"]["error"]["properties"]["class"]["enum"]) == ERROR_CLASSES
    assert (
        set(schema["$defs"]["recovery"]["properties"]["level"]["enum"])
        == RECOVERY_LEVELS
    )


def test_every_controlled_object_rejects_unknown_properties() -> None:
    schema = _schema()
    assert schema["additionalProperties"] is False
    for definition in ("context", "workflowRun", "artifact", "error", "recovery"):
        assert schema["$defs"][definition]["additionalProperties"] is False


def test_new_status_matches_schema_and_dependency_free_contract(tmp_path: Path) -> None:
    target = tmp_path / "status.json"
    payload = start_run(
        target,
        "knowledge-graph",
        run_id="schema-test",
        git_sha="0123456789abcdef",
    )
    assert validate_status(payload) == []
    jsonschema.Draft202012Validator(
        _schema(),
        format_checker=jsonschema.FormatChecker(),
    ).validate(payload)


def test_schema_rejects_unknown_top_level_fields(tmp_path: Path) -> None:
    payload = start_run(
        tmp_path / "status.json",
        "manual",
        run_id="unknown-field-test",
    )
    payload["secret_surprise"] = "must not pass"
    errors = sorted(
        jsonschema.Draft202012Validator(_schema()).iter_errors(payload),
        key=lambda error: list(error.absolute_path),
    )
    assert errors
    assert any("Additional properties" in error.message for error in errors)


def test_schema_and_runtime_require_explicit_utc_timestamps(tmp_path: Path) -> None:
    payload = start_run(
        tmp_path / "status.json",
        "manual",
        run_id="utc-test",
    )
    payload["updated_at"] = payload["updated_at"].replace("Z", "+02:00")
    errors = list(
        jsonschema.Draft202012Validator(
            _schema(),
            format_checker=jsonschema.FormatChecker(),
        ).iter_errors(payload)
    )
    assert errors
    assert any("pattern" in error.schema_path for error in errors)
    assert any("updated_at muss ein ISO-8601-UTC-Zeitstempel sein" in error
               for error in validate_status(payload))
