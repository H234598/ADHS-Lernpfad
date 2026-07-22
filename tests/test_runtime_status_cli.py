"""Regression tests for runtime status helper interfaces.

These tests intentionally verify the contract of the runtime status layer without
requiring a full GitHub Actions environment.
"""

from pathlib import Path
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_status_schema_exists():
    schema = ROOT / "automation" / "schema" / "run-status.schema.json"
    assert schema.exists()
    data = json.loads(schema.read_text(encoding="utf-8"))
    assert data["type"] == "object"


def test_runtime_status_tools_exist():
    expected = [
        ROOT / "scripts" / "automation_run_status.py",
        ROOT / "scripts" / "runtime_status_cli.py",
        ROOT / "scripts" / "validate_runtime_status.py",
    ]
    assert all(path.exists() for path in expected)


def test_runtime_status_cli_help():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "runtime_status_cli.py"), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "status" in result.stdout.lower()
