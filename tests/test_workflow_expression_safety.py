from __future__ import annotations

from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = (
    ".github/workflows/coderabbit-hard-gate.yml",
    ".github/workflows/learning-card-policy.yml",
)


class WorkflowExpressionSafetyTests(unittest.TestCase):
    def test_pr_number_is_not_interpolated_directly_into_shell(self) -> None:
        for relative_path in WORKFLOWS:
            with self.subTest(workflow=relative_path):
                workflow = yaml.safe_load(
                    (ROOT / relative_path).read_text(encoding="utf-8")
                )
                shell_steps = [
                    step
                    for job in workflow["jobs"].values()
                    for step in job.get("steps", [])
                    if "run" in step
                ]
                target_steps = [
                    step
                    for step in shell_steps
                    if "--pr-number" in str(step.get("run") or "")
                ]
                self.assertTrue(target_steps)
                for step in target_steps:
                    run = str(step["run"])
                    self.assertNotIn("${{ steps.pr.outputs.number }}", run)
                    self.assertIn('"$TARGET_PR"', run)
                    self.assertEqual(
                        step.get("env", {}).get("TARGET_PR"),
                        "${{ steps.pr.outputs.number }}",
                    )


if __name__ == "__main__":
    unittest.main()
