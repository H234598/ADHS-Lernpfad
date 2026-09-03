"""Regression tests for safe Git executable resolution in repository fallbacks."""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

from scripts import automation_status

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import graph_relations  # noqa: E402


def test_git_sha_fallback_executes_an_absolute_git_path(monkeypatch) -> None:
    """Automation-status Git execution must use an absolute executable path."""

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


def test_graph_source_revision_executes_an_absolute_git_path(monkeypatch, tmp_path) -> None:
    """Graph revision discovery must not pass a relative Git executable to subprocess."""

    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.setattr(graph_relations.shutil, "which", lambda _name: "tools/git")
    observed: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        """Capture graph Git execution without spawning a process."""

        observed["command"] = command
        observed["kwargs"] = kwargs
        return SimpleNamespace(stdout=("b" * 40) + "\n")

    monkeypatch.setattr(graph_relations.subprocess, "run", fake_run)

    assert graph_relations._source_revision(tmp_path) == "b" * 40  # nosec B101 -- pytest assertion
    command = observed["command"]
    assert isinstance(command, list)  # nosec B101 -- pytest assertion
    assert Path(command[0]).is_absolute()  # nosec B101 -- pytest assertion
    assert command[1:] == ["rev-parse", "HEAD"]  # nosec B101 -- pytest assertion
