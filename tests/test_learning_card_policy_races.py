from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import learning_card_policy
from learning_card_policy import (
    build_pull_snapshot,
    select_latest_check_runs,
)

HEAD = "a" * 40


def run(
    *,
    status: str,
    conclusion: str | None,
    created_at: str,
    started_at: str,
    completed_at: str | None,
    run_id: int,
) -> dict[str, object]:
    return {
        "id": run_id,
        "name": "Validate and build",
        "head_sha": HEAD,
        "status": status,
        "conclusion": conclusion,
        "created_at": created_at,
        "started_at": started_at,
        "completed_at": completed_at,
    }


def policy_run(
    name: str,
    *,
    status: str = "completed",
    conclusion: str | None = "success",
    created_at: str = "2026-08-12T10:00:00Z",
    run_id: int,
) -> dict[str, object]:
    return {
        "id": run_id,
        "name": name,
        "head_sha": HEAD,
        "status": status,
        "conclusion": conclusion,
        "created_at": created_at,
        "started_at": created_at,
        "completed_at": created_at if status == "completed" else None,
        "html_url": f"https://example.invalid/check/{run_id}",
    }


class CheckOrderingTests(unittest.TestCase):
    def test_newer_pending_run_wins_over_later_completed_older_run(self) -> None:
        older_success = run(
            status="completed",
            conclusion="success",
            created_at="2026-08-12T10:00:00Z",
            started_at="2026-08-12T10:01:00Z",
            completed_at="2026-08-12T12:00:00Z",
            run_id=100,
        )
        newer_pending = run(
            status="in_progress",
            conclusion=None,
            created_at="2026-08-12T11:00:00Z",
            started_at="2026-08-12T11:30:00Z",
            completed_at=None,
            run_id=200,
        )

        selected = select_latest_check_runs(
            [older_success, newer_pending],
            head_sha=HEAD,
            names={"Validate and build"},
        )

        self.assertEqual(selected["Validate and build"]["id"], 200)
        self.assertEqual(
            selected["Validate and build"]["status"],
            "in_progress",
        )


class PullSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pull = {
            "state": "open",
            "head": {"sha": HEAD, "ref": "feature/card"},
            "body": "initial body",
        }
        self.files = [
            {
                "filename": "01-Grundlagen/01-Was-ist-ADHS.md",
                "status": "modified",
            }
        ]
        self.baseline = build_pull_snapshot(self.pull, self.files)

    def test_head_change_invalidates_snapshot(self) -> None:
        changed_pull = {
            **self.pull,
            "head": {"sha": "b" * 40, "ref": "feature/card"},
        }
        self.assertNotEqual(
            build_pull_snapshot(changed_pull, self.files),
            self.baseline,
        )

    def test_body_change_invalidates_snapshot(self) -> None:
        changed_pull = {**self.pull, "body": "changed body"}
        self.assertNotEqual(
            build_pull_snapshot(changed_pull, self.files),
            self.baseline,
        )

    def test_file_scope_change_invalidates_snapshot(self) -> None:
        changed_files = [
            *self.files,
            {
                "filename": "references/Faraone2021.md",
                "status": "added",
            },
        ]
        self.assertNotEqual(
            build_pull_snapshot(self.pull, changed_files),
            self.baseline,
        )

    def test_file_order_does_not_invalidate_snapshot(self) -> None:
        more_files = [
            *self.files,
            {
                "filename": "Glossar.md",
                "status": "modified",
            },
        ]
        self.assertEqual(
            build_pull_snapshot(self.pull, more_files),
            build_pull_snapshot(self.pull, list(reversed(more_files))),
        )

    def test_main_revalidates_snapshot_before_reporting(self) -> None:
        initial_pull = {
            "state": "open",
            "head": {"sha": HEAD, "ref": "feature/docs"},
            "body": "initial body",
        }
        changed_pull = {**initial_pull, "body": "changed body"}
        files = [{"filename": "README.md", "status": "modified"}]

        with TemporaryDirectory() as directory:
            output_dir = Path(directory)
            argv = [
                "learning_card_policy.py",
                "--repository",
                "H234598/ADHS-Lernpfad",
                "--pr-number",
                "53",
                "--token",
                "test-token",
                "--output-dir",
                str(output_dir),
            ]
            with (
                patch.object(
                    learning_card_policy,
                    "_request_json",
                    side_effect=[initial_pull, changed_pull],
                ),
                patch.object(
                    learning_card_policy,
                    "_paginated",
                    side_effect=[files, files],
                ),
                patch.object(sys, "argv", argv),
            ):
                result = learning_card_policy.main()

            report = json.loads(
                (output_dir / "learning-card-policy.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result, 1)
        self.assertFalse(report["decision"]["passed"])
        self.assertTrue(
            any(
                "während der Auswertung geändert" in reason
                for reason in report["decision"]["reasons"]
            )
        )

    def test_main_reloads_check_runs_after_stable_snapshot(self) -> None:
        pull = {
            "state": "open",
            "head": {"sha": HEAD, "ref": "agent/einheit-21-test"},
            "body": "<!-- adhs-daily-unit -->",
        }
        files = [
            {
                "filename": "01-Grundlagen/01-Was-ist-ADHS.md",
                "status": "modified",
            }
        ]
        initial_runs = [
            policy_run("Validate and build", run_id=1),
            policy_run("Build all download formats", run_id=2),
            policy_run("CodeRabbit review gate (blocking)", run_id=3),
        ]
        final_runs = [
            *initial_runs,
            policy_run(
                "Validate and build",
                status="in_progress",
                conclusion=None,
                created_at="2026-08-12T11:00:00Z",
                run_id=4,
            ),
        ]

        with TemporaryDirectory() as directory:
            output_dir = Path(directory)
            argv = [
                "learning_card_policy.py",
                "--repository",
                "H234598/ADHS-Lernpfad",
                "--pr-number",
                "53",
                "--token",
                "test-token",
                "--output-dir",
                str(output_dir),
            ]
            with (
                patch.object(
                    learning_card_policy,
                    "_request_json",
                    side_effect=[pull, pull],
                ),
                patch.object(
                    learning_card_policy,
                    "_paginated",
                    side_effect=[files, initial_runs, files, final_runs],
                ),
                patch.object(sys, "argv", argv),
            ):
                result = learning_card_policy.main()

            report = json.loads(
                (output_dir / "learning-card-policy.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result, 1)
        self.assertFalse(report["decision"]["passed"])
        self.assertEqual(report["decision"]["subgates"]["complete_build"], "pending")
        self.assertEqual(
            report["decision"]["required_checks"]["Validate and build"]["state"],
            "pending",
        )


if __name__ == "__main__":
    unittest.main()
