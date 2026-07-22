"""Regression tests for the runtime status contract."""

import json
from pathlib import Path


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
    assert {"run_id", "workflow", "status"}.issubset(required)
