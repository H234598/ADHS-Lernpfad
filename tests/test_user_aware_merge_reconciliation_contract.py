from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_merge_watcher_reconciles_nonfinal_canonical_run_before_no_open_pr_exit() -> None:
    text = _read("prompts/MERGE-AUTOMATION-PROMPT.md")
    folded = text.casefold()

    assert "unit_pr_reconciliation.py" in text
    assert "Out-of-band" in text or "Nutzereingriff" in text
    assert "geschlossenen" in text
    assert "verify_second_ci" in text
    assert "cleanup" in text
    assert "complete" in text
    assert "bevor" in folded and "kein geeigneter pr" in folded


def test_generator_reconciles_closed_predecessor_and_does_not_generate_new_content_same_recovery_run() -> None:
    text = _read("prompts/AUTOMATION-PROMPT.md")

    assert "unit_pr_reconciliation.py" in text
    assert "geschlossenen Vorgänger" in text
    assert "success / complete" in text
    assert "keine neue Einheit" in text
    assert "folgenden normalen Generatorlauf" in text


def test_technical_policy_defines_user_and_out_of_band_reconciliation() -> None:
    text = _read("automation/MERGE-REPAIR-POLICY.md")

    assert "Nutzereingriff" in text
    assert "Out-of-band" in text
    assert "closed" in text
    assert "merged" in text
    assert "CAS" in text
    assert "blockiert" in text


def test_documented_run_advancement_means_full_existing_state_machine() -> None:
    merge = _read("prompts/MERGE-AUTOMATION-PROMPT.md")
    generator = _read("prompts/AUTOMATION-PROMPT.md")

    phrase = "Lauf vorziehen"
    assert phrase in merge
    assert phrase in generator
    assert "keinen einzelnen sichtbaren GitHub-Schritt" in merge
    assert "bestehende Zustandsmaschine" in generator
