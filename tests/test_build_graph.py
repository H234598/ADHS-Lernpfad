from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from build_graph import GraphBuilder, render_graphml, render_mermaid, render_report
from content_model import build_content_index


class GraphBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "01-Grundlagen").mkdir()
        (self.root / "references").mkdir()
        (self.root / "knowledge-graph").mkdir()
        (self.root / "README.md").write_text("# Start\n", encoding="utf-8")
        (self.root / "ROADMAP.md").write_text(
            "# Roadmap\n\n## Grundlagen\n", encoding="utf-8",
        )
        (self.root / "Glossar.md").write_text(
            "---\ntitle: Glossar\n---\n\n# Glossar\n\n## ADHS\n\n## Genetik\n",
            encoding="utf-8",
        )
        (self.root / "01-Grundlagen" / "01-A.md").write_text(
            "---\n"
            "title: Alpha\n"
            "level: Grundlagen\n"
            "difficulty: 1\n"
            "prerequisites: []\n"
            "tags: [ADHS]\n"
            "references: [Ref2026]\n"
            "---\n\n"
            "# Alpha\n\nSiehe [[Glossar#ADHS|ADHS]].\n",
            encoding="utf-8",
        )
        (self.root / "01-Grundlagen" / "02-B.md").write_text(
            "---\n"
            "title: Beta\n"
            "level: Grundlagen\n"
            "difficulty: 2\n"
            "prerequisites: [Alpha]\n"
            "tags: [Genetik, Neuer Begriff]\n"
            "references: [Ref2026]\n"
            "---\n\n"
            "# Beta\n\n[[Alpha]] und [[01-Grundlagen/03-C|Gamma]].\n",
            encoding="utf-8",
        )
        (self.root / "references" / "Ref2026.md").write_text(
            "---\n"
            "reference_id: Ref2026\n"
            "title: Studie\n"
            "evidence_type: review\n"
            "evidence_grade: high\n"
            "---\n\n# Studie\n",
            encoding="utf-8",
        )
        (self.root / "index.json").write_text(
            json.dumps({"chapters": [
                {"number": 1, "path": "01-Grundlagen/01-A.md"},
                {"number": 2, "path": "01-Grundlagen/02-B.md"},
            ]}),
            encoding="utf-8",
        )
        (self.root / "knowledge-graph" / "planned-nodes.yaml").write_text(
            "nodes:\n"
            "  - path: 01-Grundlagen/03-C\n"
            "    title: Gamma\n"
            "    type: chapter\n"
            "    scope: learning\n"
            "    roadmap: ROADMAP.md#grundlagen\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def build(self) -> dict:
        return GraphBuilder(build_content_index(self.root)).build()

    def test_graph_contains_documents_yaml_relations_and_planned_nodes(self) -> None:
        graph = self.build()
        node_ids = {node["id"] for node in graph["nodes"]}
        edge_keys = {
            (edge["type"], edge["source"], edge["target"], edge["status"])
            for edge in graph["edges"]
        }
        self.assertIn("doc:01-Grundlagen/02-B", node_ids)
        self.assertIn("ref:Ref2026", node_ids)
        self.assertIn("planned:01-Grundlagen/03-C", node_ids)
        self.assertIn((
            "prerequisite",
            "doc:01-Grundlagen/01-A",
            "doc:01-Grundlagen/02-B",
            "ok",
        ), edge_keys)
        self.assertIn((
            "cites", "doc:01-Grundlagen/02-B", "ref:Ref2026", "ok",
        ), edge_keys)
        self.assertIn((
            "sequence",
            "doc:01-Grundlagen/01-A",
            "doc:01-Grundlagen/02-B",
            "ok",
        ), edge_keys)
        self.assertTrue(any(
            edge["type"] == "wikilink" and edge["status"] == "planned"
            for edge in graph["edges"]
        ))
        self.assertTrue(any(
            node["type"] == "concept" and node["label"] == "Neuer Begriff"
            for node in graph["nodes"]
        ))

    def test_every_edge_endpoint_exists_and_ids_are_unique(self) -> None:
        graph = self.build()
        node_ids = [node["id"] for node in graph["nodes"]]
        self.assertEqual(len(node_ids), len(set(node_ids)))
        node_set = set(node_ids)
        for edge in graph["edges"]:
            self.assertIn(edge["source"], node_set)
            self.assertIn(edge["target"], node_set)

    def test_output_is_deterministic(self) -> None:
        first = json.dumps(self.build(), ensure_ascii=False, sort_keys=True)
        second = json.dumps(self.build(), ensure_ascii=False, sort_keys=True)
        self.assertEqual(first, second)

    def test_mermaid_defines_each_node_once_and_graphml_report_render(self) -> None:
        graph = self.build()
        mermaid = render_mermaid(graph, scope="all")
        graphml = render_graphml(graph)
        report = render_report(graph)
        alpha_lines = [line for line in mermaid.splitlines() if '"Alpha"' in line]
        self.assertEqual(len(alpha_lines), 1)
        self.assertIn("<graphml", graphml)
        self.assertIn("# Wissensgraph-Bericht", report)


if __name__ == "__main__":
    unittest.main()
