from __future__ import annotations

from copy import deepcopy
import multiprocessing
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ruleset_migration
from ruleset_migration import (
    exclusive_ruleset_lock,
    load_json,
    validate_transition,
)


def _try_lock_in_child(lock_path: str) -> None:
    """In einem getrennten Prozess denselben Lock anfordern."""

    try:
        with exclusive_ruleset_lock(Path(lock_path)):
            pass
    except RuntimeError:
        raise SystemExit(23) from None
    raise SystemExit(0)


class RulesetParameterDriftTests(unittest.TestCase):
    def setUp(self) -> None:
        rulesets = ROOT / "automation/rulesets"
        self.current = load_json(
            rulesets / "main-required-gates.before.json"
        )
        self.target = load_json(
            rulesets / "main-required-gates.target.json"
        )

    def status_parameters(self, document: dict[str, object]) -> dict[str, object]:
        rule = next(
            item
            for item in document["rules"]
            if item["type"] == "required_status_checks"
        )
        return rule["parameters"]

    def test_strict_required_status_policy_drift_is_rejected(self) -> None:
        drifted = deepcopy(self.target)
        self.status_parameters(drifted)[
            "strict_required_status_checks_policy"
        ] = True
        with self.assertRaisesRegex(ValueError, "Parameter"):
            validate_transition(self.current, drifted)

    def test_enforce_on_create_drift_is_rejected(self) -> None:
        drifted = deepcopy(self.target)
        self.status_parameters(drifted)["do_not_enforce_on_create"] = True
        with self.assertRaisesRegex(ValueError, "Parameter"):
            validate_transition(self.current, drifted)


class RulesetLockTests(unittest.TestCase):
    def setUp(self) -> None:
        rulesets = ROOT / "automation/rulesets"
        self.current = load_json(
            rulesets / "main-required-gates.before.json"
        )
        self.target = load_json(
            rulesets / "main-required-gates.target.json"
        )

    def test_competing_process_migration_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            lock_path = Path(directory) / "ruleset.lock"
            context = multiprocessing.get_context("spawn")
            with exclusive_ruleset_lock(lock_path):
                child = context.Process(
                    target=_try_lock_in_child,
                    args=(str(lock_path),),
                )
                child.start()
                child.join(timeout=20)
                self.assertFalse(child.is_alive())
                self.assertEqual(child.exitcode, 23)

    def test_migration_entrypoint_holds_lock_around_live_transition(self) -> None:
        with TemporaryDirectory() as directory:
            directory_path = Path(directory)
            lock_path = directory_path / "ruleset.lock"
            output_dir = directory_path / "report"
            calls: list[str] = []
            get_count = 0

            def fake_request(
                url: str,
                token: str | None,
                *,
                method: str = "GET",
                data: dict[str, object] | None = None,
            ) -> dict[str, object]:
                nonlocal get_count
                with self.assertRaisesRegex(RuntimeError, "gesperrt"):
                    with exclusive_ruleset_lock(lock_path):
                        self.fail("Der Live-Übergang muss den Lock halten")
                calls.append(method)
                if method == "PUT":
                    return deepcopy(self.target)
                get_count += 1
                return deepcopy(
                    self.current if get_count <= 2 else self.target
                )

            argv = [
                "ruleset_migration.py",
                "--repository",
                "H234598/ADHS-Lernpfad",
                "--token",
                "test-token",
                "--before",
                str(
                    ROOT
                    / "automation/rulesets/main-required-gates.before.json"
                ),
                "--target",
                str(
                    ROOT
                    / "automation/rulesets/main-required-gates.target.json"
                ),
                "--output-dir",
                str(output_dir),
                "--lock-path",
                str(lock_path),
                "--apply",
            ]

            with (
                patch.object(
                    ruleset_migration,
                    "_request_json",
                    side_effect=fake_request,
                ),
                patch.object(sys, "argv", argv),
            ):
                self.assertEqual(ruleset_migration.main(), 0)

            self.assertEqual(calls, ["GET", "GET", "PUT", "GET"])
            self.assertFalse(lock_path.exists())

    def test_drift_immediately_before_put_aborts_without_write(self) -> None:
        drifted = deepcopy(self.current)
        drifted["enforcement"] = "disabled"
        calls: list[str] = []

        with TemporaryDirectory() as directory:
            directory_path = Path(directory)
            argv = [
                "ruleset_migration.py",
                "--repository",
                "H234598/ADHS-Lernpfad",
                "--token",
                "test-token",
                "--before",
                str(
                    ROOT
                    / "automation/rulesets/main-required-gates.before.json"
                ),
                "--target",
                str(
                    ROOT
                    / "automation/rulesets/main-required-gates.target.json"
                ),
                "--output-dir",
                str(directory_path / "report"),
                "--lock-path",
                str(directory_path / "ruleset.lock"),
                "--apply",
            ]

            def fake_request(
                url: str,
                token: str | None,
                *,
                method: str = "GET",
                data: dict[str, object] | None = None,
            ) -> dict[str, object]:
                calls.append(method)
                if len(calls) == 1:
                    return deepcopy(self.current)
                if len(calls) == 2:
                    return deepcopy(drifted)
                self.fail("Nach erkanntem Drift darf kein weiterer API-Aufruf erfolgen")

            with (
                patch.object(
                    ruleset_migration,
                    "_request_json",
                    side_effect=fake_request,
                ),
                patch.object(sys, "argv", argv),
                self.assertRaisesRegex(RuntimeError, "während der Transition"),
            ):
                ruleset_migration.main()

        self.assertEqual(calls, ["GET", "GET"])


if __name__ == "__main__":
    unittest.main()
