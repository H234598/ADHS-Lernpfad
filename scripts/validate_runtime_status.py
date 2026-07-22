#!/usr/bin/env python3
"""Validate runtime status against JSON Schema and semantic invariants."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:  # Support both ``python scripts/...`` and package imports in tests.
    from .automation_run_status import PHASES, STATUSES, validate_status
except ImportError:  # pragma: no cover - exercised by command-line use
    from automation_run_status import PHASES, STATUSES, validate_status


ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "build" / "runtime-status.json"
SCHEMA = ROOT / "automation" / "schema" / "run-status.schema.json"
REPORT_JSON = ROOT / "build" / "runtime-status-validation-report.json"
REPORT_MD = ROOT / "build" / "runtime-status-validation-report.md"


def _load_object(path: Path, label: str) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, [f"{label} fehlt: {path}"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {}, [f"{label} ist kein gültiges UTF-8-JSON: {exc}"]
    if not isinstance(value, dict):
        return {}, [f"{label} muss ein JSON-Objekt sein: {path}"]
    return value, []


def _schema_contract_errors(schema: dict[str, Any]) -> list[str]:
    """Check the essential schema shape even without the jsonschema package."""

    errors: list[str] = []
    properties = schema.get("properties")
    required = schema.get("required")
    if schema.get("type") != "object":
        errors.append("Runtime schema: root type must be object")
    if schema.get("additionalProperties") is not False:
        errors.append("Runtime schema: additionalProperties must be false")
    if not isinstance(properties, dict):
        return [*errors, "Runtime schema: properties must be an object"]
    if not isinstance(required, list) or any(not isinstance(item, str) for item in required):
        return [*errors, "Runtime schema: required must be a string array"]
    missing_properties = sorted(set(required) - set(properties))
    if missing_properties:
        errors.append(
            "Runtime schema: required fields lack properties: "
            + ", ".join(missing_properties)
        )
    phase_schema = properties.get("phase")
    phase_enum = phase_schema.get("enum") if isinstance(phase_schema, dict) else None
    if (
        not isinstance(phase_enum, list)
        or any(not isinstance(item, str) for item in phase_enum)
        or set(phase_enum) != PHASES
    ):
        errors.append("Runtime schema: phase enum differs from the runtime implementation")
    status_schema = properties.get("status")
    status_enum = status_schema.get("enum") if isinstance(status_schema, dict) else None
    if (
        not isinstance(status_enum, list)
        or any(not isinstance(item, str) for item in status_enum)
        or set(status_enum) != STATUSES
    ):
        errors.append("Runtime schema: status enum differs from the runtime implementation")
    return errors


def validate_file(status_path: Path, schema_path: Path = SCHEMA) -> list[str]:
    """Return all available schema and semantic validation errors."""

    status, status_errors = _load_object(status_path, "Runtime status")
    schema, schema_errors = _load_object(schema_path, "Runtime schema")
    errors = [*status_errors, *schema_errors]
    if status_errors or schema_errors:
        return errors

    errors.extend(_schema_contract_errors(schema))
    # Semantic checks are always required. JSON Schema cannot express time
    # ordering and Python's JSON parser accepts non-standard NaN values.
    errors.extend(validate_status(status))

    try:
        import jsonschema  # type: ignore[import-not-found]
    except ImportError:
        return list(dict.fromkeys(errors))

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
        )
        errors.extend(
            f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
            for error in sorted(
                validator.iter_errors(status),
                key=lambda item: tuple(str(part) for part in item.absolute_path),
            )
        )
    except jsonschema.SchemaError as exc:
        errors.append(f"Runtime schema ist ungültig: {exc.message}")
    return list(dict.fromkeys(errors))


def report_payload(
    status_path: Path, schema_path: Path, errors: list[str],
) -> dict[str, Any]:
    return {
        "valid": not errors,
        "status_file": str(status_path),
        "schema_file": str(schema_path),
        "error_count": len(errors),
        "errors": [{"message": error} for error in errors],
    }


def render_report(status_path: Path, schema_path: Path, errors: list[str]) -> str:
    lines = [
        "# Runtime-Status-Validierungsbericht",
        "",
        f"- Ergebnis: **{'gültig' if not errors else 'FEHLERHAFT'}**",
        f"- Statusdatei: `{status_path}`",
        f"- Schemadatei: `{schema_path}`",
        f"- Fehler: **{len(errors)}**",
        "",
        "## Befunde",
        "",
    ]
    lines.extend(f"- {error}" for error in errors)
    if not errors:
        lines.append("- keine")
    return "\n".join(lines) + "\n"


def write_reports(
    status_path: Path,
    schema_path: Path,
    errors: list[str],
    report_json: Path = REPORT_JSON,
    report_markdown: Path = REPORT_MD,
) -> None:
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_markdown.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(
        json.dumps(
            report_payload(status_path, schema_path, errors),
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    report_markdown.write_text(
        render_report(status_path, schema_path, errors),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an automation runtime status")
    parser.add_argument("status", nargs="?", type=Path, default=STATUS)
    parser.add_argument("--schema", type=Path, default=SCHEMA)
    parser.add_argument("--report-json", type=Path, default=REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=REPORT_MD)
    args = parser.parse_args(argv)

    errors = validate_file(args.status, args.schema)
    try:
        write_reports(
            args.status, args.schema, errors,
            report_json=args.report_json, report_markdown=args.report_md,
        )
    except OSError as exc:
        print(f"Runtime status ungültig: Validierungsbericht kann nicht geschrieben werden: {exc}")
        return 1
    if errors:
        for error in errors:
            print(f"Runtime status ungültig: {error}")
        return 1
    print(f"Runtime status valid: {args.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
