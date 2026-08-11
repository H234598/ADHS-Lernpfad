from __future__ import annotations

from pathlib import Path
import json

import yaml

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


def test_generator_runs_remark_lint_before_draft_creation() -> None:
    generator = (ROOT / "prompts/AUTOMATION-PROMPT.md").read_text(encoding="utf-8")
    lint_position = generator.index("npm run lint:markdown:changed")
    branch_position = generator.index("## 8. Git-Arbeitsweise")
    assert "npm run audit:dependencies" in generator
    assert lint_position < branch_position
    assert "Eine Remark-lint-Meldung darf nicht" in generator


def test_dependency_audit_is_required_in_all_documented_gate_sequences() -> None:
    for relative in (
        "CONTRIBUTING.md",
        "prompts/MERGE-AUTOMATION-PROMPT.md",
        "prompts/PR-REPAIR-PROMPT.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "npm run audit:dependencies" in text


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


def test_codacy_delegates_only_remark_markdown_analysis() -> None:
    config = (ROOT / ".codacy.yml").read_text(encoding="utf-8")
    assert "engines:" in config
    assert "remark-lint:" in config
    assert '- "**.md"' in config
    assert '- "**/*.md"' in config
    assert "bandit:" not in config
    assert "prospector:" not in config
    assert "pylint" not in config


def test_codacy_workflow_preserves_explicit_fail_closed_analyzer_coverage() -> None:
    """Keep the local Codacy matrix explicit, bounded, isolated, and fail closed."""

    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/codacy.yml").read_text(encoding="utf-8")
    )
    jobs = workflow["jobs"]
    analysis = jobs["codacy-analysis"]
    gate = jobs["codacy-security-scan"]

    expected_timeouts = {
        "bandit": "10minutes",
        "prospector": "10minutes",
        "pylintpython3": "10minutes",
        "ruff": "10minutes",
        "shellcheck": "10minutes",
        "psscriptanalyzer": "10minutes",
        "eslint-9": "10minutes",
        "biome": "10minutes",
        "stylelint": "10minutes",
    }
    matrix = analysis["strategy"]["matrix"]["include"]
    tool_names = [entry["tool"] for entry in matrix]
    actual_timeouts = {
        entry["tool"]: entry["tool_timeout"]
        for entry in matrix
    }

    checkout = next(
        step for step in analysis["steps"] if step.get("name") == "Checkout code"
    )
    codacy = next(
        step
        for step in analysis["steps"]
        if str(step.get("uses", "")).startswith("codacy/codacy-analysis-cli-action@")
    )
    upload = next(
        step
        for step in analysis["steps"]
        if str(step.get("uses", "")).startswith("github/codeql-action/upload-sarif@")
    )
    enforcement = next(
        step
        for step in gate["steps"]
        if step.get("name") == "Enforce complete analyzer matrix"
    )
    enforcement_run = enforcement.get("run", "")

    checks = {
        "permissions": analysis["permissions"]
        == {"contents": "read", "security-events": "write"},
        "no-actions-read": "actions" not in analysis["permissions"],
        "job-timeout": analysis["timeout-minutes"] == 20,
        "fail-fast": analysis["strategy"]["fail-fast"] is False,
        "max-parallel": analysis["strategy"]["max-parallel"] == 4,
        "matrix-size": len(matrix) == len(expected_timeouts),
        "matrix-unique": len(set(tool_names)) == len(tool_names),
        "matrix": actual_timeouts == expected_timeouts,
        "opengrep-excluded": "opengrep" not in actual_timeouts,
        "checkout-credentials": checkout["with"]["persist-credentials"] is False,
        "tool-selection": codacy["with"]["tool"] == "${{ matrix.tool }}",
        "tool-timeout": codacy["with"]["tool-timeout"] == "${{ matrix.tool_timeout }}",
        "fail-if-incomplete": codacy["with"]["fail-if-incomplete"] is True,
        "finding-policy": codacy["with"]["max-allowed-issues"] == 2147483647,
        "sarif-after-failure": upload.get("if")
        == "${{ !cancelled() && hashFiles('results.sarif') != '' }}",
        "sarif-category": upload["with"]["category"] == "codacy-${{ matrix.tool }}",
        "aggregate-name": gate["name"] == "Codacy Security Scan",
        "aggregate-needs": gate["needs"] == "codacy-analysis",
        "aggregate-always": gate.get("if") == "${{ always() }}",
        "aggregate-timeout": gate["timeout-minutes"] == 5,
        "aggregate-result-env": enforcement.get("env", {}).get("ANALYZER_RESULT")
        == "${{ needs.codacy-analysis.result }}",
        "aggregate-rejects-non-success": (
            '[[ "$ANALYZER_RESULT" != "success" ]]' in enforcement_run
            and "exit 1" in enforcement_run
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise AssertionError("Codacy workflow policy mismatch: " + ", ".join(failed))


def test_remark_lint_sanitizes_project_specific_obsidian_syntax() -> None:
    script = (ROOT / "scripts/remark_lint.mjs").read_text(encoding="utf-8")
    assert "const WIKILINK_RE = /\\[\\[([\\s\\S]*?)\\]\\]/g" in script
    assert "const EMBED_RE = /!\\[\\[([\\s\\S]*?)\\]\\]/g" in script
    assert "sanitizeObsidianMarkdown" in script
    assert "remarkPresetLintRecommended" in script
    assert "--files" in script


def test_gate_workflows_are_valid_yaml_and_read_only() -> None:
    for relative in (
        ".github/workflows/remark-lint.yml",
        ".github/workflows/coderabbit-hard-gate.yml",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        parsed = yaml.safe_load(text)
        assert isinstance(parsed, dict)
        assert "jobs" in parsed
        assert "write" not in text


def test_coderabbit_gate_uses_trusted_main_checkout() -> None:
    workflow = (ROOT / ".github/workflows/coderabbit-hard-gate.yml").read_text(
        encoding="utf-8"
    )
    assert "CodeRabbit review gate (blocking)" in workflow
    assert "ref: main" in workflow
    assert "persist-credentials: false" in workflow
    assert "pull_request_target" in workflow
