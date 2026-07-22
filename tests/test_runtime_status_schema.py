"""Regression tests for the runtime status contract."""

import json
from pathlib import Path

from scripts.automation_run_status import PHASES, start_run, validate_status


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "automation" / "schema" / "run-status.schema.json"


def test_runtime_status_schema_exists():
    """The runtime contract must be shipped with the project."""
    assert SCHEMA.exists()


def test_runtime_status_schema_is_valid_json():
    """The schema itself must stay parseable."""
    data = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert data["type"] == "object"
    assert "properties" in data
    assert "status" in data["properties"]


def test_required_runtime_fields_are_documented():
    """Required fields prevent incomplete recovery records."""
    data = json.loads(SCHEMA.read_text(encoding="utf-8"))
    required = set(data.get("required", []))
    assert {
        "run_id",
        "workflow",
        "git_sha",
        "status",
        "phase",
        "started_at",
        "ended_at",
        "duration_seconds",
        "metrics",
        "artifacts",
        "error_class",
        "error_message",
        "recovery_action",
    }.issubset(required)


def test_schema_documents_every_real_generator_phase():
    data = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert set(data["properties"]["phase"]["enum"]) == PHASES


def test_new_status_matches_dependency_free_contract(tmp_path):
    payload = start_run(
        tmp_path / "status.json",
        "pytest",
        run_id="schema-test",
        git_sha="0123456789abcdef",
    )
    assert validate_status(payload) == []
