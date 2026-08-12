from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ruleset_migration import (
    NEW_CONTEXT,
    OLD_CONTEXTS,
    canonical_digest,
    load_json,
    required_checks,
    ruleset_payload,
    validate_rollback,
    validate_transition,
)


class RulesetMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        rulesets = ROOT / "automation/rulesets"
        self.current = load_json(rulesets / "main-required-gates.before.json")
        self.target = load_json(rulesets / "main-required-gates.target.json")

    def test_target_replaces_only_raw_learning_contexts(self) -> None:
        summary = validate_transition(self.current, self.target)
        self.assertEqual(set(summary.removed_contexts), OLD_CONTEXTS)
        self.assertEqual(summary.added_contexts, (NEW_CONTEXT,))
        self.assertTrue(summary.bypass_actors_preserved)

    def test_target_preserves_pull_request_bypass_actors(self) -> None:
        self.assertEqual(
            ruleset_payload(self.current)["bypass_actors"],
            ruleset_payload(self.target)["bypass_actors"],
        )
        self.assertTrue(
            all(
                actor["bypass_mode"] == "pull_request"
                for actor in ruleset_payload(self.target)["bypass_actors"]
            )
        )

    def test_target_uses_github_actions_policy_provider(self) -> None:
        checks = required_checks(self.target)
        self.assertEqual(checks[NEW_CONTEXT], 15368)
        self.assertTrue(OLD_CONTEXTS.isdisjoint(checks))


    def test_rollback_restores_only_raw_learning_contexts(self) -> None:
        summary = validate_rollback(self.target, self.current)
        self.assertEqual(summary.direction, "rollback")
        self.assertEqual(summary.removed_contexts, (NEW_CONTEXT,))
        self.assertEqual(set(summary.added_contexts), OLD_CONTEXTS)
        self.assertTrue(summary.bypass_actors_preserved)

    def test_unrelated_rule_drift_is_rejected(self) -> None:
        drifted = deepcopy(self.target)
        drifted["rules"][1]["parameters"]["required_approving_review_count"] = 1
        with self.assertRaisesRegex(ValueError, "außerhalb"):
            validate_transition(self.current, drifted)

    def test_bypass_drift_is_rejected(self) -> None:
        drifted = deepcopy(self.target)
        drifted["bypass_actors"] = []
        with self.assertRaisesRegex(ValueError, "Bypass"):
            validate_transition(self.current, drifted)

    def test_read_only_api_fields_do_not_affect_digest_or_payload(self) -> None:
        enriched = deepcopy(self.current)
        enriched.update(
            {
                "node_id": "node",
                "source": "H234598/ADHS-Lernpfad",
                "created_at": "2026-08-12T00:00:00Z",
                "current_user_can_bypass": "pull_requests_only",
            }
        )
        self.assertEqual(canonical_digest(enriched), canonical_digest(self.current))
        payload = ruleset_payload(enriched)
        self.assertNotIn("id", payload)
        self.assertNotIn("node_id", payload)
        self.assertNotIn("source", payload)


if __name__ == "__main__":
    unittest.main()
