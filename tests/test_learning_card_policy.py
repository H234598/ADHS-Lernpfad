from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from learning_card_policy import (
    REQUIRED_POLICY_CHECKS,
    classify_pull_request,
    evaluate_policy,
    select_latest_check_runs,
)
from learning_card_scope import AUTOMATION_PREFIXES

HEAD = "a" * 40
OLD_HEAD = "b" * 40


def changed(
    filename: str,
    *,
    status: str = "modified",
    previous_filename: str | None = None,
) -> dict[str, str]:
    item = {"filename": filename, "status": status}
    if previous_filename is not None:
        item["previous_filename"] = previous_filename
    return item


def check(
    name: str,
    *,
    conclusion: str | None = "success",
    status: str = "completed",
    head_sha: str = HEAD,
    completed_at: str = "2026-08-12T12:00:00Z",
) -> dict[str, object]:
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "head_sha": head_sha,
        "completed_at": completed_at,
        "started_at": completed_at,
        "html_url": f"https://example.invalid/{name}",
    }


class ApplicabilityTests(unittest.TestCase):
    def classify(
        self,
        *files: dict[str, str],
        head_ref: str = "feature/ui",
        body: str = "",
    ):
        return classify_pull_request(
            files=list(files),
            head_ref=head_ref,
            body=body,
        )

    def test_ui_and_test_only_pull_request_is_not_applicable(self) -> None:
        result = self.classify(
            changed("mkdocs.yml"),
            changed("tests/web/navigation.spec.mjs"),
        )
        self.assertEqual(result.classification, "not_applicable")
        self.assertFalse(result.requires_semantic_review)
        self.assertFalse(result.manual_merge_required)
        self.assertEqual(result.learning_paths, ())
        self.assertEqual(result.scientific_support_paths, ())

    def test_direct_learning_card_change_requires_semantic_review(self) -> None:
        result = self.classify(changed("01-Grundlagen/01-Was-ist-ADHS.md"))
        self.assertEqual(result.classification, "learning_card")
        self.assertTrue(result.requires_semantic_review)
        self.assertEqual(
            result.learning_paths,
            ("01-Grundlagen/01-Was-ist-ADHS.md",),
        )

    def test_nested_advanced_learning_card_requires_semantic_review(self) -> None:
        result = self.classify(changed("02-Vertiefung/Unterordner/Karte.md"))
        self.assertEqual(result.classification, "learning_card")
        self.assertTrue(result.requires_semantic_review)

    def test_structured_source_card_requires_semantic_review(self) -> None:
        result = self.classify(changed("references/Faraone2021.md"))
        self.assertEqual(result.classification, "scientific_support")
        self.assertTrue(result.requires_semantic_review)
        self.assertEqual(
            result.scientific_support_paths,
            ("references/Faraone2021.md",),
        )

    def test_generated_scientific_outputs_require_semantic_review(self) -> None:
        for path in (
            "Literatur.md",
            "references.bib",
            "references.json",
            "Glossar.md",
            "cards/cards.yaml",
        ):
            with self.subTest(path=path):
                result = self.classify(changed(path))
                self.assertEqual(result.classification, "scientific_support")
                self.assertTrue(result.requires_semantic_review)

    def test_reference_readme_is_documentation_not_scientific_support(self) -> None:
        result = self.classify(changed("references/README.md"))
        self.assertEqual(result.classification, "not_applicable")
        self.assertFalse(result.requires_semantic_review)

    def test_learning_branch_or_marker_without_scientific_change_is_not_enough(
        self,
    ) -> None:
        for head_ref, body in (
            ("agent/einheit-21-beispiel", ""),
            ("feature/ui", "<!-- adhs-daily-unit -->"),
        ):
            with self.subTest(head_ref=head_ref, body=body):
                result = self.classify(
                    changed("assets/stylesheets/extra.css"),
                    head_ref=head_ref,
                    body=body,
                )
                self.assertEqual(result.classification, "not_applicable")
                self.assertFalse(result.requires_semantic_review)
                self.assertTrue(result.learning_provenance)

    def test_automation_changes_are_orthogonal_and_manual(self) -> None:
        canonical_paths = {
            ".github/": "workflows/validate.yml",
            "prompts/": "AUTOMATION-PROMPT.md",
            "scripts/": "review_gate.py",
        }
        self.assertTrue(set(canonical_paths).issubset(AUTOMATION_PREFIXES))

        for prefix, suffix in canonical_paths.items():
            path = f"{prefix}{suffix}"
            with self.subTest(path=path):
                result = self.classify(changed(path))
                self.assertEqual(result.classification, "automation_only")
                self.assertFalse(result.requires_semantic_review)
                self.assertTrue(result.manual_merge_required)
                self.assertEqual(result.automation_paths, (path,))

    def test_learning_card_plus_workflow_is_semantic_and_manual(self) -> None:
        result = self.classify(
            changed("02-Vertiefung/08-Beispiel.md", status="added"),
            changed(".github/workflows/validate.yml"),
            head_ref="agent/einheit-21-beispiel",
            body=(
                "<!-- adhs-daily-unit -->\n"
                "<!-- manual-merge-required -->"
            ),
        )
        self.assertEqual(result.classification, "learning_card_sensitive")
        self.assertTrue(result.requires_semantic_review)
        self.assertTrue(result.manual_merge_required)
        self.assertTrue(result.manual_merge_marker)

    def test_rename_out_of_learning_tree_still_requires_semantic_review(
        self,
    ) -> None:
        result = self.classify(
            changed(
                "archive/01-Was-ist-ADHS.md",
                status="renamed",
                previous_filename="01-Grundlagen/01-Was-ist-ADHS.md",
            )
        )
        self.assertEqual(result.classification, "learning_card")
        self.assertTrue(result.requires_semantic_review)
        self.assertIn(
            "01-Grundlagen/01-Was-ist-ADHS.md",
            result.learning_paths,
        )

    def test_deleting_learning_card_requires_semantic_review(self) -> None:
        result = self.classify(
            changed("02-Vertiefung/07-Beispiel.md", status="removed")
        )
        self.assertTrue(result.requires_semantic_review)
        self.assertEqual(result.classification, "learning_card")


class CheckSelectionTests(unittest.TestCase):
    def test_latest_check_run_per_exact_name_and_current_head_is_selected(
        self,
    ) -> None:
        selected = select_latest_check_runs(
            [
                check(
                    "Validate and build",
                    conclusion="failure",
                    completed_at="2026-08-12T11:00:00Z",
                ),
                check(
                    "Validate and build",
                    conclusion="success",
                    completed_at="2026-08-12T12:00:00Z",
                ),
                check("Build all download formats", head_sha=OLD_HEAD),
                check("unrelated"),
            ],
            head_sha=HEAD,
            names=set(REQUIRED_POLICY_CHECKS),
        )
        self.assertEqual(
            selected["Validate and build"]["conclusion"],
            "success",
        )
        self.assertNotIn("Build all download formats", selected)
        self.assertNotIn("unrelated", selected)


class PolicyEvaluationTests(unittest.TestCase):
    def scope(self, path: str = "01-Grundlagen/01-Was-ist-ADHS.md"):
        return classify_pull_request(
            files=[changed(path)],
            head_ref="feature/card",
            body="",
        )

    def successful_checks(self) -> list[dict[str, object]]:
        return [check(name) for name in REQUIRED_POLICY_CHECKS]

    def checks_with_state(
        self,
        target: str,
        *,
        status: str,
        conclusion: str | None,
    ) -> list[dict[str, object]]:
        return [
            check(
                name,
                status=status if name == target else "completed",
                conclusion=conclusion if name == target else "success",
            )
            for name in REQUIRED_POLICY_CHECKS
        ]

    def test_not_applicable_policy_succeeds_without_waiting_for_subgates(
        self,
    ) -> None:
        scope = classify_pull_request(
            files=[changed("assets/stylesheets/extra.css")],
            head_ref="feature/ui",
            body="",
        )
        result = evaluate_policy(
            scope=scope,
            check_runs=[],
            head_sha=HEAD,
        )
        self.assertTrue(result.passed)
        self.assertEqual(
            result.subgates["content_scope"],
            "not_applicable",
        )
        self.assertEqual(
            result.subgates["claim_source_entailment"],
            "not_applicable",
        )
        self.assertEqual(
            result.subgates["complete_build"],
            "not_applicable",
        )

    def test_applicable_policy_requires_all_three_real_checks(self) -> None:
        result = evaluate_policy(
            scope=self.scope(),
            check_runs=self.successful_checks(),
            head_sha=HEAD,
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.subgates["content_scope"], "success")
        self.assertEqual(
            result.subgates["claim_source_entailment"],
            "success",
        )
        self.assertEqual(result.subgates["complete_build"], "success")

    def test_coderabbit_hard_gate_drives_both_semantic_subgates(self) -> None:
        runs = self.checks_with_state(
            "CodeRabbit review gate (blocking)",
            status="completed",
            conclusion="failure",
        )
        result = evaluate_policy(
            scope=self.scope(),
            check_runs=runs,
            head_sha=HEAD,
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.subgates["content_scope"], "failure")
        self.assertEqual(
            result.subgates["claim_source_entailment"],
            "failure",
        )
        self.assertEqual(result.subgates["complete_build"], "success")

    def test_missing_coderabbit_hard_gate_fails_both_semantic_subgates(
        self,
    ) -> None:
        runs = [
            run
            for run in self.successful_checks()
            if run["name"] != "CodeRabbit review gate (blocking)"
        ]
        result = evaluate_policy(
            scope=self.scope(),
            check_runs=runs,
            head_sha=HEAD,
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.subgates["content_scope"], "missing")
        self.assertEqual(
            result.subgates["claim_source_entailment"],
            "missing",
        )
        self.assertEqual(result.subgates["complete_build"], "success")

    def test_non_success_coderabbit_never_passes_semantic_subgates(
        self,
    ) -> None:
        cases = (
            ("in_progress", None, "pending"),
            ("completed", "failure", "failure"),
            ("completed", "neutral", "pending"),
            ("completed", "skipped", "pending"),
            ("completed", "cancelled", "failure"),
            ("completed", "timed_out", "failure"),
        )
        target = "CodeRabbit review gate (blocking)"
        for status, conclusion, expected in cases:
            with self.subTest(status=status, conclusion=conclusion):
                result = evaluate_policy(
                    scope=self.scope(),
                    check_runs=self.checks_with_state(
                        target,
                        status=status,
                        conclusion=conclusion,
                    ),
                    head_sha=HEAD,
                )
                self.assertFalse(result.passed)
                self.assertEqual(
                    result.subgates["content_scope"],
                    expected,
                )
                self.assertEqual(
                    result.subgates["claim_source_entailment"],
                    expected,
                )
                self.assertEqual(
                    result.subgates["complete_build"],
                    "success",
                )

    def test_complete_build_requires_validation_and_export(self) -> None:
        for missing in (
            "Validate and build",
            "Build all download formats",
        ):
            with self.subTest(missing=missing):
                runs = [
                    run
                    for run in self.successful_checks()
                    if run["name"] != missing
                ]
                result = evaluate_policy(
                    scope=self.scope(),
                    check_runs=runs,
                    head_sha=HEAD,
                )
                self.assertFalse(result.passed)
                self.assertEqual(
                    result.subgates["complete_build"],
                    "missing",
                )

    def test_non_success_build_checks_never_pass_complete_build(self) -> None:
        cases = (
            ("in_progress", None, "pending"),
            ("completed", "failure", "failure"),
            ("completed", "neutral", "pending"),
            ("completed", "skipped", "pending"),
            ("completed", "cancelled", "failure"),
            ("completed", "timed_out", "failure"),
        )
        for target in (
            "Validate and build",
            "Build all download formats",
        ):
            for status, conclusion, expected in cases:
                with self.subTest(
                    target=target,
                    status=status,
                    conclusion=conclusion,
                ):
                    result = evaluate_policy(
                        scope=self.scope(),
                        check_runs=self.checks_with_state(
                            target,
                            status=status,
                            conclusion=conclusion,
                        ),
                        head_sha=HEAD,
                    )
                    self.assertFalse(result.passed)
                    self.assertEqual(
                        result.subgates["complete_build"],
                        expected,
                    )

    def test_old_head_successes_do_not_satisfy_current_policy(self) -> None:
        result = evaluate_policy(
            scope=self.scope(),
            check_runs=[
                check(name, head_sha=OLD_HEAD)
                for name in REQUIRED_POLICY_CHECKS
            ],
            head_sha=HEAD,
        )
        self.assertFalse(result.passed)
        self.assertIn("missing", result.subgates.values())


if __name__ == "__main__":
    unittest.main()
