from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from word_count_policy import evaluate_word_count


class WordCountPolicyTests(unittest.TestCase):
    def classify(self, number: int, words: int) -> tuple[int, int]:
        errors, warnings = evaluate_word_count(number, words, "Einheit.md")
        return len(errors), len(warnings)

    def test_all_documented_boundaries(self) -> None:
        self.assertEqual(self.classify(11, 799), (1, 0))
        self.assertEqual(self.classify(11, 800), (0, 1))
        self.assertEqual(self.classify(11, 1199), (0, 1))
        self.assertEqual(self.classify(11, 1200), (0, 0))
        self.assertEqual(self.classify(11, 2500), (0, 0))
        self.assertEqual(self.classify(11, 2501), (0, 1))
        self.assertEqual(self.classify(11, 3000), (0, 1))
        self.assertEqual(self.classify(11, 3001), (1, 0))

    def test_legacy_units_skip_only_target_range_warning(self) -> None:
        self.assertEqual(self.classify(1, 900), (0, 0))
        self.assertEqual(self.classify(10, 2600), (0, 0))
        self.assertEqual(self.classify(1, 799), (1, 0))
        self.assertEqual(self.classify(10, 3001), (1, 0))


if __name__ == "__main__":
    unittest.main()
