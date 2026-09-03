"""Characterization tests for the validate_status contract before S3776 refactoring."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from scripts.automation_status import make_artifact, start_run, validate_status


def _running_status(tmp_path: Path) -> dict:
    return start_run(
        tmp_path / "status.json",
        "manual",
        run_id="validate-status-characterization",
        git_sha="0123456789abcdef",
    )


def test_validate_status_rejects_boolean_revision_even_though_bool_is_int_subclass(
    tmp_path: Path,
) -> None:
    payload = _running_status(tmp_path)
    payload["revision"] = True

    assert (  # nosec B101 -- pytest assertion
        "revision muss eine positive Ganzzahl sein" in validate_status(payload)
    )


def test_validate_status_rejects_updated_at_before_created_at(tmp_path: Path) -> None:
    payload = _running_status(tmp_path)
    payload["created_at"] = "2026-09-04T02:00:00.000Z"
    payload["updated_at"] = "2026-09-04T01:59:59.999Z"
    payload["retention_until"] = "2026-10-04T02:00:00.000Z"

    assert (  # nosec B101 -- pytest assertion
        "updated_at darf nicht vor created_at liegen" in validate_status(payload)
    )


def test_validate_status_rejects_end_fields_on_non_final_status(tmp_path: Path) -> None:
    payload = _running_status(tmp_path)
    payload["ended_at"] = payload["updated_at"]
    payload["duration_seconds"] = 0.0

    assert (  # nosec B101 -- pytest assertion
        "Nicht finaler Status darf keine Endzeit oder Laufzeit besitzen"
        in validate_status(payload)
    )


def test_validate_status_rejects_non_json_metric_values(tmp_path: Path) -> None:
    payload = _running_status(tmp_path)
    payload["metrics"] = {"not_json": float("nan")}

    assert (  # nosec B101 -- pytest assertion
        "metrics enthält keine reinen JSON-Werte" in validate_status(payload)
    )


def test_validate_status_rejects_duplicate_artifact_identity(tmp_path: Path) -> None:
    payload = _running_status(tmp_path)
    artifact = make_artifact(
        "report",
        "build/report.md",
        path="build/report.md",
        recorded_at=payload["updated_at"],
    )
    payload["artifacts"] = [artifact, deepcopy(artifact)]

    assert (  # nosec B101 -- pytest assertion
        "artifacts enthält doppelte Typ/Wert-Kombinationen" in validate_status(payload)
    )


def test_validate_status_rejects_unknown_top_level_field(tmp_path: Path) -> None:
    payload = _running_status(tmp_path)
    payload["future_contract_field"] = "must-not-be-silently-accepted"

    assert (  # nosec B101 -- pytest assertion
        "Status: unbekannte Felder: future_contract_field" in validate_status(payload)
    )
