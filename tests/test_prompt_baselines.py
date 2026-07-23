from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.validate_prompt_baselines import EXPECTED_PROMPTS, validate_baselines


ROOT = Path(__file__).resolve().parents[1]


def test_protected_prompt_prefixes_are_unchanged_and_not_shortened() -> None:
    assert validate_baselines() == []


def _write_valid_fixture(tmp_path: Path) -> tuple[Path, dict]:
    records = []
    for index, relative in enumerate(EXPECTED_PROMPTS):
        content = f"geschützter Text {index}\n".encode()
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content + b"additiver Zusatz\n")
        records.append(
            {
                "path": relative,
                "protected_prefix_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    manifest_data = {
        "schema_version": "1.0.0",
        "description": "Testmanifest",
        "prompts": records,
    }
    manifest = tmp_path / "baselines.json"
    manifest.write_text(
        json.dumps(manifest_data),
        encoding="utf-8",
    )
    return manifest, manifest_data


def test_validator_detects_shortening_and_rewriting(tmp_path: Path) -> None:
    manifest, _manifest_data = _write_valid_fixture(tmp_path)
    assert validate_baselines(tmp_path, manifest) == []
    prompt = tmp_path / EXPECTED_PROMPTS[0]
    prompt.write_text("veränderter Text\n", encoding="utf-8")
    assert validate_baselines(tmp_path, manifest)


@pytest.mark.parametrize(
    "tampering",
    (
        "non_object",
        "empty",
        "missing",
        "duplicate",
        "renamed",
        "absolute",
        "traversal",
        "wrong_version",
    ),
)
def test_validator_rejects_manifest_tampering(
    tmp_path: Path,
    tampering: str,
) -> None:
    manifest, data = _write_valid_fixture(tmp_path)
    payload: object = data
    if tampering == "non_object":
        payload = []
    elif tampering == "empty":
        data["prompts"] = []
    elif tampering == "missing":
        data["prompts"].pop()
    elif tampering == "duplicate":
        data["prompts"].append(dict(data["prompts"][0]))
    elif tampering == "renamed":
        data["prompts"][0]["path"] = "prompts/RENAMED.md"
    elif tampering == "absolute":
        data["prompts"][0]["path"] = "/tmp/AUTOMATION-PROMPT.md"
    elif tampering == "traversal":
        data["prompts"][0]["path"] = "../AUTOMATION-PROMPT.md"
    elif tampering == "wrong_version":
        data["schema_version"] = "999.0.0"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    assert validate_baselines(tmp_path, manifest)
