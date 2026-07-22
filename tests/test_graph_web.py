from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from graph_web import copy_graph_data, inject_graph_page, load_graph, render_graph_shell


class GraphWebTests(unittest.TestCase):
    def graph(self) -> dict[str, object]:
        return {
            "stats": {
                "node_count": 2,
                "edge_count": 1,
                "issue_count": 0,
                "error_count": 0,
                "warning_count": 0,
                "nodes_by_type": {"chapter": 1, "planned": 1},
                "edges_by_type": {"prerequisite": 1},
                "issues_by_code": {},
            },
            "nodes": [
                {
                    "id": "doc:vorhanden",
                    "label": "Vorhanden",
                    "type": "chapter",
                    "scope": "learning",
                    "exists": True,
                    "planned": False,
                },
                {
                    "id": "planned:spaeter",
                    "label": "Später",
                    "type": "planned",
                    "scope": "learning",
                    "exists": False,
                    "planned": True,
                },
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "doc:vorhanden",
                    "target": "planned:spaeter",
                    "type": "prerequisite",
                    "status": "planned",
                    "count": 1,
                    "occurrences": [],
                }
            ],
            "issues": [],
        }

    def write_graph(self, root: Path) -> Path:
        destination = root / "build" / "knowledge-graph" / "knowledge-graph.json"
        destination.parent.mkdir(parents=True)
        destination.write_text(json.dumps(self.graph()), encoding="utf-8")
        return destination

    def test_shell_contains_only_graph_ui_and_legend(self) -> None:
        rendered = render_graph_shell(self.graph())
        self.assertIn("data-knowledge-graph", rendered)
        self.assertIn("data-kg-canvas", rendered)
        self.assertIn("data-kg-legend", rendered)
        self.assertNotIn("Datenquellen", rendered)
        self.assertNotIn("Ausgabeformate", rendered)
        self.assertNotIn("Knotenliste", rendered)

    def test_injection_requires_exactly_one_marker(self) -> None:
        source = "# Wissensgraph\n\n<!-- knowledge-graph-app -->\n"
        rendered = inject_graph_page(source, self.graph())
        self.assertNotIn("<!-- knowledge-graph-app -->", rendered)
        self.assertIn("data-knowledge-graph", rendered)
        with self.assertRaises(ValueError):
            inject_graph_page("# Wissensgraph\n", self.graph())

    def test_load_and_copy_use_canonical_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.write_graph(root)
            self.assertEqual(load_graph(root)["nodes"], self.graph()["nodes"])
            docs = root / "build" / "docs"
            copied = copy_graph_data(root, docs)
            self.assertTrue(copied.is_file())
            self.assertEqual(copied.read_bytes(), source.read_bytes())

    def test_repository_wires_assets_and_keeps_source_page_lean(self) -> None:
        mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        self.assertIn("assets/stylesheets/knowledge-graph.css", mkdocs)
        self.assertIn("cytoscape@3.34.0/dist/cytoscape.min.js", mkdocs)
        self.assertIn("assets/javascripts/knowledge-graph.js", mkdocs)

        graph_page = (ROOT / "knowledge-graph" / "README.md").read_text(encoding="utf-8")
        self.assertEqual(graph_page.count("<!-- knowledge-graph-app -->"), 1)
        self.assertNotIn("## Datenquellen", graph_page)
        self.assertNotIn("## Ausgabe", graph_page)

        maintenance = (ROOT / "WARTUNG.md").read_text(encoding="utf-8")
        self.assertIn("## Wissensgraph", maintenance)
        self.assertIn("### Datenquellen", maintenance)
        self.assertIn("### Erzeugte Dateien", maintenance)

    def test_missing_graph_has_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(FileNotFoundError, "build_graph.py"):
                load_graph(Path(temp))


if __name__ == "__main__":
    unittest.main()
