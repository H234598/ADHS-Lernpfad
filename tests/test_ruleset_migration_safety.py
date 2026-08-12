from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ruleset_migration import (
    exclusive_ruleset_lock,
    load_json,
    validate_transition,
)


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
    def test_competing_local_migration_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            lock_path = Path(directory) / "ruleset.lock"
            with exclusive_ruleset_lock(lock_path):
                with self.assertRaisesRegex(RuntimeError, "gesperrt"):
                    with exclusive_ruleset_lock(lock_path):
                        self.fail("Ein zweiter Ruleset-Lock darf nicht gelingen")

    def test_migration_entrypoint_holds_lock_around_live_transition(self) -> None:
        source = (ROOT / "scripts/ruleset_migration.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("with exclusive_ruleset_lock", source)
        self.assertIn("fresh_live = _request_json", source)
        self.assertIn(
            "canonical_digest(fresh_live) != canonical_digest(live)",
            source,
        )


if __name__ == "__main__":
    unittest.main()
