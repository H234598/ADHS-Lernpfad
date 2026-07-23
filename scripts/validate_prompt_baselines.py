#!/usr/bin/env python3
"""Ensure recovery additions never shorten or rewrite protected prompts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "automation" / "prompt-baselines.json"
BASELINE_SCHEMA_VERSION = "1.0.0"
EXPECTED_PROMPTS = (
    "prompts/AUTOMATION-PROMPT.md",
    "prompts/PR-REPAIR-PROMPT.md",
    "prompts/MERGE-AUTOMATION-PROMPT.md",
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def validate_baselines(
    root: Path = ROOT,
    manifest_path: Path = BASELINES,
) -> list[str]:
    try:
        manifest: Any = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"Prompt-Baseline-Manifest ist ungültig: {exc}"]
    if not isinstance(manifest, dict):
        return ["Prompt-Baseline-Manifest muss ein JSON-Objekt sein"]

    errors: list[str] = []
    expected_manifest_fields = {"schema_version", "description", "prompts"}
    if set(manifest) != expected_manifest_fields:
        errors.append(
            "Prompt-Baseline-Manifest benötigt exakt die Felder "
            "description, prompts und schema_version"
        )
    if manifest.get("schema_version") != BASELINE_SCHEMA_VERSION:
        errors.append(
            f"Prompt-Baseline-Manifest benötigt schema_version "
            f"{BASELINE_SCHEMA_VERSION}"
        )
    if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
        errors.append("Prompt-Baseline-Manifest benötigt eine Beschreibung")

    records = manifest.get("prompts")
    if not isinstance(records, list):
        errors.append("Prompt-Baseline-Manifest benötigt eine prompts-Liste")
        return errors

    seen: set[str] = set()
    accepted: list[tuple[str, int, str]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"prompts[{index}] muss ein Objekt sein")
            continue
        if set(record) != {"path", "protected_prefix_bytes", "sha256"}:
            errors.append(
                f"prompts[{index}] benötigt exakt path, "
                "protected_prefix_bytes und sha256"
            )
        relative = record.get("path")
        length = record.get("protected_prefix_bytes")
        expected = record.get("sha256")
        if not isinstance(relative, str):
            errors.append(f"prompts[{index}] besitzt ungültige Felder")
            continue
        pure_path = PurePosixPath(relative)
        if (
            pure_path.is_absolute()
            or ".." in pure_path.parts
            or "\\" in relative
            or relative != pure_path.as_posix()
        ):
            errors.append(f"prompts[{index}].path ist nicht repository-relativ")
            continue
        if relative in seen:
            errors.append(f"Prompt-Baseline ist doppelt: {relative}")
            continue
        seen.add(relative)
        if relative not in EXPECTED_PROMPTS:
            errors.append(f"Unerwarteter geschützter Prompt: {relative}")
            continue
        if (
            not isinstance(length, int)
            or isinstance(length, bool)
            or length < 1
            or not isinstance(expected, str)
            or not _SHA256_RE.fullmatch(expected)
        ):
            errors.append(f"prompts[{index}] besitzt ungültige Felder")
            continue
        accepted.append((relative, length, expected))

    missing = sorted(set(EXPECTED_PROMPTS) - seen)
    if missing:
        errors.append("Geschützte Prompts fehlen: " + ", ".join(missing))
    if len(records) != len(EXPECTED_PROMPTS):
        errors.append(
            f"Prompt-Baseline-Manifest benötigt exakt {len(EXPECTED_PROMPTS)} Einträge"
        )

    resolved_root = root.resolve()
    for relative, length, expected in accepted:
        path = (root / relative).resolve()
        if not path.is_relative_to(resolved_root):
            errors.append(f"{relative} verlässt das Repository")
            continue
        try:
            content = path.read_bytes()
        except OSError as exc:
            errors.append(f"{relative} ist nicht lesbar: {exc}")
            continue
        if len(content) < length:
            errors.append(
                f"{relative} wurde verkürzt: {len(content)} < {length} Byte"
            )
            continue
        actual = hashlib.sha256(content[:length]).hexdigest()
        if actual != expected:
            errors.append(
                f"{relative}: geschützter Prompt-Präfix wurde verändert"
            )
    return errors


def main() -> int:
    errors = validate_baselines()
    if errors:
        for error in errors:
            print(f"Prompt-Schutzfehler: {error}")
        return 1
    print("Geschützte Automationsprompts sind vollständig und unverändert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
