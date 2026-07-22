from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GraphPageScopeTests(unittest.TestCase):
    def test_public_page_is_limited_to_graph_legend_and_generated_fallback(self) -> None:
        page = (ROOT / "knowledge-graph" / "README.md").read_text(encoding="utf-8")
        headings = [line for line in page.splitlines() if line.startswith("## ")]
        self.assertEqual(headings, ["## Interaktive Ansicht", "## Legende"])
        self.assertIn("data-knowledge-graph", page)
        self.assertIn("knowledge-graph-runtime:start", page)
        self.assertIn("knowledge-graph-fallback:start", page)
        self.assertNotIn("Dokument- und Navigationsgraph", page)
        self.assertNotIn("## Datenquellen und Aktualisierung", page)
        self.assertNotIn("## Ausgabeformate", page)
        self.assertNotIn("## Lokal bauen und prüfen", page)

    def test_maintenance_contains_the_moved_graph_documentation(self) -> None:
        maintenance = (ROOT / "WARTUNG.md").read_text(encoding="utf-8")
        self.assertIn("## Wissensgraph", maintenance)
        self.assertIn("### Zweck und Abgrenzung", maintenance)
        self.assertIn("### Datenquellen und Aktualisierung", maintenance)
        self.assertIn("### Statusmodell und Webdarstellung", maintenance)
        self.assertIn("### Ausgabeformate", maintenance)
        self.assertIn("### Lokal bauen und prüfen", maintenance)
        self.assertIn("Dokument- und Navigationsgraph", maintenance)


if __name__ == "__main__":
    unittest.main()
