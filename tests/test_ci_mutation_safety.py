from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_ci_mutation_safety import validate_repository


SAFE_WRITER = """name: Safe writer
on: workflow_dispatch
permissions:
  contents: write
jobs:
  publish:
    runs-on: ubuntu-24.04
    steps:
      - name: Apply verified payload
        run: |
          expected_payload_checksum='abc123'
          actual_payload_checksum="$(sha256sum "$RUNNER_TEMP/payload.b64" | cut -d' ' -f1)"
          printf 'Computed payload checksum: %s\\n' "$actual_payload_checksum"
          printf 'Expected payload checksum: %s\\n' "$expected_payload_checksum"
          for fragment in .automation-repair/unit.payload.*; do
            printf '%s bytes  ' "$(wc -c < "$fragment")"
            sha256sum "$fragment"
          done
          if [[ "$actual_payload_checksum" != "$expected_payload_checksum" ]]; then
            tar -tzf "$RUNNER_TEMP/payload.tar.gz" || true
            exit 1
          fi
          npm run audit:dependencies
          git add generated/
          git status --short
          git diff --cached --name-status
          git diff --cached --stat
          if git diff --cached --quiet; then exit 0; fi
          git commit -m publish
          git push origin HEAD:generated
"""


def write_workflow(root: Path, content: str, name: str = "writer.yml") -> None:
    """Write one synthetic workflow into a temporary repository."""

    path = root / ".github" / "workflows" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class MutationSafetyTests(unittest.TestCase):
    """Exercise positive, negative, and adversarial Variant-B contracts."""

    def test_repository_workflows_follow_variant_b(self) -> None:
        """Require every real workflow in this repository to pass."""

        self.assertEqual(validate_repository(ROOT), [])

    def test_safe_writer_passes(self) -> None:
        """Accept a writer with complete diagnostics and enforced checksums."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_workflow(root, SAFE_WRITER)
            self.assertEqual(validate_repository(root), [])

    def test_read_only_workflow_needs_no_writer_guard(self) -> None:
        """Avoid imposing writer requirements on a read-only workflow."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_workflow(
                root,
                "name: Read only\non: workflow_dispatch\npermissions:\n  contents: read\n",
            )
            self.assertEqual(validate_repository(root), [])

    def test_unguarded_writer_is_rejected(self) -> None:
        """Reject a writer lacking a guard, status, and staged diagnostics."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_workflow(root, """name: Unsafe
on: workflow_dispatch
jobs:
  write:
    runs-on: ubuntu-24.04
    steps:
      - run: |
          git add generated/
          git commit -m publish
          git push origin HEAD:generated
""")
            codes = {issue.code for issue in validate_repository(root)}
            self.assertTrue({"CIW001", "CIW002", "CIW003"}.issubset(codes))

    def test_each_writer_step_requires_its_own_guard_and_diagnostics(self) -> None:
        """Prevent a safe writer from masking an unsafe sibling step."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            second_writer = """      - name: Unsafe second writer
        run: |
          git add other/
          git commit -m unsafe
          git push origin HEAD:other
"""
            write_workflow(root, SAFE_WRITER + second_writer)
            issues = validate_repository(root)
            codes = [issue.code for issue in issues]
            self.assertIn("CIW001", codes)
            self.assertIn("CIW002", codes)
            self.assertIn("CIW003", codes)
            self.assertTrue(all(issue.line >= 31 for issue in issues))

    def test_opaque_payload_checksum_is_rejected(self) -> None:
        """Reject an opaque checksum assertion without useful diagnostics."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            start = SAFE_WRITER.index("          expected_payload_checksum")
            end = SAFE_WRITER.index("          npm run audit:dependencies")
            opaque = "          test \"$(sha256sum payload.b64)\" = abc123\n"
            write_workflow(root, SAFE_WRITER[:start] + opaque + SAFE_WRITER[end:])
            codes = {issue.code for issue in validate_repository(root)}
            self.assertTrue(
                {"CIW004", "CIW005", "CIW006", "CIW007", "CIW010"}.issubset(codes)
            )

    def test_printed_checksums_without_enforced_comparison_are_rejected(self) -> None:
        """Reject checksums that are merely printed but never enforced."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            comparison = """          if [[ "$actual_payload_checksum" != "$expected_payload_checksum" ]]; then
            tar -tzf "$RUNNER_TEMP/payload.tar.gz" || true
            exit 1
          fi
"""
            write_workflow(
                root,
                SAFE_WRITER.replace(
                    comparison,
                    "          tar -tzf \"$RUNNER_TEMP/payload.tar.gz\" || true\n",
                ),
            )
            codes = {issue.code for issue in validate_repository(root)}
            self.assertIn("CIW010", codes)

    def test_audit_bypasses_are_rejected(self) -> None:
        """Reject shell and workflow-level attempts to soften audit failures."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_workflow(
                root,
                SAFE_WRITER.replace(
                    "npm run audit:dependencies", "npm run audit:dependencies || true"
                ),
                "shell.yml",
            )
            write_workflow(
                root,
                SAFE_WRITER.replace(
                    "      - name: Apply verified payload\n",
                    "      - name: Apply verified payload\n        continue-on-error: true\n",
                ),
                "step.yml",
            )
            write_workflow(
                root,
                SAFE_WRITER.replace(
                    "npm run audit:dependencies",
                    "npm run audit:dependencies \\\n            || true",
                ),
                "multiline.yml",
            )
            codes = [issue.code for issue in validate_repository(root)]
            self.assertGreaterEqual(codes.count("CIW008"), 2)
            self.assertIn("CIW009", codes)


if __name__ == "__main__":
    unittest.main()
