from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_prompt_baselines import validate_baselines


ROOT = Path(__file__).resolve().parents[1]


def test_protected_prompt_prefixes_are_unchanged_and_not_shortened() -> None:
    assert validate_baselines() == []


def test_validator_detects_shortening_and_rewriting(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text("geschützter Text\nZusatz\n", encoding="utf-8")
    protected = "geschützter Text\n".encode()
    import hashlib

    manifest = tmp_path / "baselines.json"
    manifest.write_text(
        json.dumps(
            {
                "prompts": [
                    {
                        "path": "prompt.md",
                        "protected_prefix_bytes": len(protected),
                        "sha256": hashlib.sha256(protected).hexdigest(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert validate_baselines(tmp_path, manifest) == []
    prompt.write_text("veränderter Text\n", encoding="utf-8")
    assert validate_baselines(tmp_path, manifest)
