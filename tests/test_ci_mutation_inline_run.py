"""Regression tests for inline GitHub Actions ``run:`` mutation parsing."""

import tempfile
from pathlib import Path

from scripts.validate_ci_mutation_safety import validate_repository


def _write_workflow(root: Path, content: str) -> None:
    """Write one synthetic workflow into a temporary repository."""
    path = root / ".github" / "workflows" / "inline.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_inline_run_git_writer_is_rejected() -> None:
    """Detect a mutation embedded directly in a list-item ``run:`` mapping."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _write_workflow(
            root,
            """name: Inline writer
on: workflow_dispatch
jobs:
  write:
    runs-on: ubuntu-24.04
    steps:
      - run: git commit -m inline
""",
        )

        codes = {issue.code for issue in validate_repository(root)}

        assert {"CIW001", "CIW002", "CIW003"}.issubset(codes)  # nosec B101


def test_block_run_git_writer_remains_rejected() -> None:
    """Preserve mutation detection for the ordinary block ``run:`` form."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _write_workflow(
            root,
            """name: Block writer
on: workflow_dispatch
jobs:
  write:
    runs-on: ubuntu-24.04
    steps:
      - run: |
          git commit -m block
""",
        )

        codes = {issue.code for issue in validate_repository(root)}

        assert {"CIW001", "CIW002", "CIW003"}.issubset(codes)  # nosec B101


def test_inline_run_outside_steps_hits_ciw011_fallback() -> None:
    """Detect inline mutation text outside an analyzable ``steps`` block."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _write_workflow(
            root,
            """name: Outside writer
on: workflow_dispatch
jobs:
  write:
    runs-on: ubuntu-24.04
    run: git push origin HEAD:unsafe
""",
        )

        codes = {issue.code for issue in validate_repository(root)}

        assert "CIW011" in codes  # nosec B101
