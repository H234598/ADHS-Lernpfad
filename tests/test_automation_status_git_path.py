"""Regression tests for safe Git executable resolution in automation status."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import scripts.automation_status as automation_status


def test_git_sha_fallback_executes_an_absolute_git_path(monkeypatch) -> None:
    """Fallback Git execution must not rely on PATH resolution inside subprocess."""

    monkeypatch.delenv("GITHUB_SHA", raising=False)
    observed: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        observed["command"] = command
        observed["kwargs"] = kwargs
        return SimpleNamespace(stdout=("a" * 40) + "\n")

    monkeypatch.setattr(automation_status.subprocess, "run", fake_run)

    assert automation_status._git_sha() == "a" * 40
    command = observed["command"]
    assert isinstance(command, list)
    assert Path(command[0]).is_absolute()
    assert command[1:] == ["rev-parse", "HEAD"]
