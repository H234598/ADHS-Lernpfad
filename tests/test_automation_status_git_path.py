"""Regression tests for safe Git executable resolution in automation status."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scripts import automation_status


def test_git_sha_fallback_executes_an_absolute_git_path(monkeypatch) -> None:
    """Fallback Git execution must not rely on PATH resolution inside subprocess."""

    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.setattr(automation_status.shutil, "which", lambda _name: "/opt/test/bin/git")
    observed: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        """Capture the resolved command without starting a process."""

        observed["command"] = command
        observed["kwargs"] = kwargs
        return SimpleNamespace(stdout=("a" * 40) + "\n")

    monkeypatch.setattr(automation_status.subprocess, "run", fake_run)

    assert automation_status._git_sha() == "a" * 40  # nosec B101 -- pytest assertion
    command = observed["command"]
    assert isinstance(command, list)  # nosec B101 -- pytest assertion
    assert Path(command[0]).is_absolute()  # nosec B101 -- pytest assertion
    assert command[0] == "/opt/test/bin/git"  # nosec B101 -- pytest assertion
    assert command[1:] == ["rev-parse", "HEAD"]  # nosec B101 -- pytest assertion


def test_git_sha_fallback_returns_none_without_git(monkeypatch) -> None:
    """Missing Git must fail closed without attempting a subprocess."""

    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.setattr(automation_status.shutil, "which", lambda _name: None)

    def unexpected_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        """Fail the test if the subprocess boundary is reached unexpectedly."""

        raise AssertionError("subprocess.run must not be called when Git is unavailable")

    monkeypatch.setattr(automation_status.subprocess, "run", unexpected_run)

    assert automation_status._git_sha() is None  # nosec B101 -- pytest assertion
