from __future__ import annotations

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_prompts_define_coderabbit_as_hard_gate() -> None:
    merge = (ROOT / "prompts/MERGE-AUTOMATION-PROMPT.md").read_text(encoding="utf-8")
    repair = (ROOT / "prompts/PR-REPAIR-PROMPT.md").read_text(encoding="utf-8")
    assert "CodeRabbit ist ein verpflichtendes hartes Gate" in merge
    assert "CodeRabbit ist ein verpflichtendes hartes Gate" in repair
    assert "CodeRabbit ist dennoch kein Pflicht-Gate" not in merge
    assert "CodeRabbit ist **kein Pflicht-Gate**" not in repair
    assert "coderabbit-disagreement" in merge
    assert "coderabbit-disagreement" in repair


def test_repair_deadline_and_no_two_failure_cap_are_explicit() -> None:
    merge = (ROOT / "prompts/MERGE-AUTOMATION-PROMPT.md").read_text(encoding="utf-8")
    repair = (ROOT / "prompts/PR-REPAIR-PROMPT.md").read_text(encoding="utf-8")
    assert "20:00 Uhr Europe/Berlin" in merge
    assert "keinen Abbruch nach dem zweiten roten CI-Lauf" in merge
    assert "keine starre Grenze von zwei roten CI-Läufen" in repair


def test_remark_lint_is_pinned_audited_and_blocking() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    dependencies = package["devDependencies"]
    assert dependencies["remark"] == "15.0.1"
    assert "remark-cli" not in dependencies
    assert dependencies["remark-preset-lint-recommended"] == "7.0.1"
    assert package["scripts"]["audit:dependencies"] == "npm audit --audit-level=high"
    assert package["scripts"]["lint:markdown:changed"]
    workflow = (ROOT / ".github/workflows/remark-lint.yml").read_text(encoding="utf-8")
    assert "Remark lint (blocking)" in workflow
    assert "npm ci" in workflow
    assert "npm run audit:dependencies" in workflow
    assert "npm run lint:markdown:changed" in workflow


def test_remark_lint_sanitizes_project_specific_obsidian_syntax() -> None:
    script = (ROOT / "scripts/remark_lint.mjs").read_text(encoding="utf-8")
    assert "const WIKILINK_RE = /\\[\\[([\\s\\S]*?)\\]\\]/g" in script
    assert "const EMBED_RE = /!\\[\\[([\\s\\S]*?)\\]\\]/g" in script
    assert "sanitizeObsidianMarkdown" in script
    assert "remarkPresetLintRecommended" in script
    assert "--files" in script


def test_coderabbit_gate_uses_trusted_main_checkout() -> None:
    workflow = (ROOT / ".github/workflows/coderabbit-hard-gate.yml").read_text(
        encoding="utf-8"
    )
    assert "CodeRabbit review gate (blocking)" in workflow
    assert "ref: main" in workflow
    assert "persist-credentials: false" in workflow
    assert "pull_request_target" in workflow
