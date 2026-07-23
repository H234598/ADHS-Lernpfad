#!/usr/bin/env python3
"""Ensure recovery additions never shorten or rewrite protected prompts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "automation" / "prompt-baselines.json"


def validate_baselines(
    root: Path = ROOT,
    manifest_path: Path = BASELINES,
) -> list[str]:
    try:
        manifest: dict[str, Any] = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"Prompt-Baseline-Manifest ist ungültig: {exc}"]
    records = manifest.get("prompts")
    if not isinstance(records, list):
        return ["Prompt-Baseline-Manifest benötigt eine prompts-Liste"]
    errors: list[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"prompts[{index}] muss ein Objekt sein")
            continue
        relative = record.get("path")
        length = record.get("protected_prefix_bytes")
        expected = record.get("sha256")
        if (
            not isinstance(relative, str)
            or not isinstance(length, int)
            or isinstance(length, bool)
            or length < 1
            or not isinstance(expected, str)
        ):
            errors.append(f"prompts[{index}] besitzt ungültige Felder")
            continue
        path = root / relative
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
