from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from graph_web import (
    annotate_special_wikilinks,
    copy_graph_outputs,
    inject_fallback,
    render_fallback_markdown,
    render_runtime_markdown,
)
from content_links import convert_for_web


class GraphWebTests(unittest.TestCase):
    def graph(self) -> dict[str, object]:
        return {
            "nodes": [
                {"id": "doc:vorhanden", "label": "Vorhanden", "type": "chapter", "exists": True, "planned": False, "lifecycle_status": "published", "path": "Vorhanden.md"},
                {"id": "planned:spaeter", "label": "Später", "type": "planned", "planned": True, "exists": False, "lifecycle_status": "in_progress", "path": "Spaeter.md"},
                {"id": "placeholder:fehlt", "label": "Fehlt", "type": "placeholder", "planned": False, "exists": False, "issue_code": "missing-document", "scope": "issue"},
            ],
            "edges": [
                {
                    "id": "e1", "source": "doc:vorhanden", "target": "planned:spaeter",
                    "type": "wikilink", "status": "planned",
                    "occurrences": [
                        {"path": "Kapitel.md", "raw": "[[Spaeter|spätere Einheit]]"},
                        {"path": "Kapitel.md", "raw": "[[Spaeter]]"},
                        {"path": "Kapitel.md", "raw": "![[Spaeter]]"},
                    ],
                },
                {
                    "id": "e2", "source": "doc:quelle", "target": "doc:vorhanden",
                    "type": "wikilink", "status": "missing-heading",
                    "occurrences": [{"path": "Quelle.md", "raw": "[[Vorhanden#Fehlt|Abschnitt]]"}],
                },
                {
                    "id": "e3", "source": "doc:quelle", "target": "placeholder:fehlt",
                    "type": "wikilink", "status": "missing-document",
                    "occurrences": [{"path": "Quelle.md", "raw": "[[Fehlt]]"}],
                },
            ],
            "issues": [{
                "code": "missing-heading",
                "requested_target": "Vorhanden",
                "raw": "[[Vorhanden#Fehlt|Abschnitt]]",
                "path": "Quelle.md",
                "line": 3,
            }],
        }

    def write_graph(self, root: Path) -> None:
        destination = root / "build" / "knowledge-graph"
        destination.mkdir(parents=True)
        (destination / "knowledge-graph.json").write_text(json.dumps(self.graph()), encoding="utf-8")

    def test_planned_link_becomes_marked_graph_link(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_graph(root)
            source = root / "Kapitel.md"
            converted = annotate_special_wikilinks("Siehe [[Spaeter|spätere Einheit]].\n", source, root)
            self.assertIn('kg-link--planned', converted)
            self.assertIn('data-kg-status="planned"', converted)
            self.assertIn('node=planned%3Aspaeter', converted)

    def test_missing_heading_becomes_non_navigating_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_graph(root)
            converted = annotate_special_wikilinks("[[Vorhanden#Fehlt|Abschnitt]]", root / "Quelle.md", root)
            self.assertIn('role="note"', converted)
            self.assertIn("Abschnitt fehlt", converted)
            self.assertNotIn("href=", converted)

    def test_missing_link_can_continue_through_diagnostic_web_conversion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_graph(root)
            source = root / "Quelle.md"
            annotated = annotate_special_wikilinks("[[Fehlt]]\n", source, root)
            self.assertIn('data-kg-status="missing-document"', annotated)
            self.assertNotIn("[[Fehlt]]", annotated)
            self.assertEqual(convert_for_web(annotated, source, root), annotated)

    def test_existing_link_is_left_for_normal_link_conversion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_graph(root)
            text = "Siehe [[Vorhanden|vorhandene Einheit]].\n"
            self.assertEqual(
                text,
                annotate_special_wikilinks(text, root / "Quelle.md", root),
            )
            other_heading = "[[Vorhanden#Existiert|anderer Abschnitt]]\n"
            self.assertEqual(
                other_heading,
                annotate_special_wikilinks(other_heading, root / "Quelle.md", root),
            )

    def test_code_fence_is_not_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_graph(root)
            text = "```markdown\n[[Spaeter]]\n```\n"
            self.assertEqual(text, annotate_special_wikilinks(text, root / "Quelle.md", root))

    def test_inline_code_comments_and_indented_code_are_not_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_graph(root)
            text = (
                "`[[Spaeter]]`\n"
                "<!-- [[Spaeter]] -->\n"
                "    [[Spaeter]]\n"
            )
            self.assertEqual(
                text,
                annotate_special_wikilinks(text, root / "Kapitel.md", root),
            )
            self.assertEqual(
                text,
                convert_for_web(
                    annotate_special_wikilinks(text, root / "Kapitel.md", root),
                    root / "Kapitel.md",
                    root,
                ),
            )

    def test_planned_embed_becomes_accessible_graph_link(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_graph(root)
            converted = annotate_special_wikilinks(
                "![[Spaeter]]\n", root / "Kapitel.md", root,
            )
            self.assertNotIn("![[Spaeter]]", converted)
            self.assertIn("Einbettung:", converted)
            self.assertIn('data-kg-status="planned"', converted)

    def test_fallback_contains_nodes_and_issues(self) -> None:
        fallback = render_fallback_markdown(self.graph())
        self.assertIn("3 Knoten", fallback)
        self.assertIn("Später", fallback)
        self.assertIn("Abschnitt fehlt", fallback)
        self.assertIn("in Arbeit", fallback)
        self.assertIn("data-kg-node-row", fallback)
        self.assertIn("data-kg-edge-table", fallback)
        self.assertIn("### Beziehungen", fallback)

    def test_fallback_injection_preserves_markers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_graph(root)
            (root / "build" / "runtime-status.json").write_text(
                json.dumps({"status": "success", "phase": "complete", "updated_at": "2026-07-22T10:45:00Z"}),
                encoding="utf-8",
            )
            source = (
                "A\n<!-- knowledge-graph-runtime:start -->\naltstatus\n<!-- knowledge-graph-runtime:end -->\n"
                "<!-- knowledge-graph-fallback:start -->\nalt\n<!-- knowledge-graph-fallback:end -->\nB\n"
            )
            rendered = inject_fallback(source, root)
            self.assertIn("Semantische Graphansicht", rendered)
            self.assertIn("Wissensgraph: OK", rendered)
            self.assertNotIn("\nalt\n", rendered)

    def test_failed_runtime_status_contains_recovery_details(self) -> None:
        rendered = render_runtime_markdown({
            "status": "failed",
            "phase": "validate_graph",
            "error_class": "schema_error",
            "error_message": "Schema ungültig",
            "recovery_action": "Validierung erneut ausführen",
        })
        self.assertIn("fehlgeschlagen", rendered)
        self.assertIn("schema_error", rendered)
        self.assertIn("Validierung erneut", rendered)

    def test_runtime_uses_canonical_schema_fields_and_metrics(self) -> None:
        rendered = render_runtime_markdown({
            "status": "success",
            "phase": "success",
            "git_sha": "abc1234",
            "ended_at": "2026-07-22T10:45:00Z",
            "duration_seconds": 0,
            "metrics": {"nodes": 170, "edges": 492, "errors": 0, "warnings": 0},
        })
        self.assertIn("`abc1234`", rendered)
        self.assertIn("| Laufzeit | 0 s |", rendered)
        self.assertIn("| Knoten | 170 |", rendered)
        self.assertIn("| Kanten | 492 |", rendered)
        self.assertIn(
            "22.07.2026, 08:45:00 UTC",
            render_runtime_markdown({
                "status": "success",
                "updated_at": "2026-07-22T10:45:00+02:00",
            }),
        )

    def test_fallback_rejects_external_node_urls_and_escapes_runtime_timestamp(self) -> None:
        graph = self.graph()
        graph["nodes"][0]["url"] = "javascript:alert(1)"
        fallback = render_fallback_markdown(graph)
        self.assertNotIn('href="javascript:', fallback)
        rendered = render_runtime_markdown({
            "status": "success",
            "updated_at": "<img src=x onerror=alert(1)>",
        })
        self.assertNotIn("<img", rendered)
        self.assertIn("&lt;img", rendered)

    def test_issue_table_cannot_be_broken_by_markdown_metacharacters(self) -> None:
        graph = self.graph()
        graph["issues"][0].update({
            "requested_target": "x|[click](javascript:alert(1))`",
            "message": "bad | `cell` <script>alert(1)</script>",
        })
        fallback = render_fallback_markdown(graph)
        self.assertIn('<table class="knowledge-graph-issues">', fallback)
        self.assertIn("x|[click](javascript:alert(1))`", fallback)
        self.assertNotIn("<script>", fallback)
        self.assertIn("&lt;script&gt;", fallback)

    def test_copy_graph_outputs_includes_runtime_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_graph(root)
            (root / "build" / "runtime-status.json").write_text(
                '{"status":"success"}\n', encoding="utf-8"
            )
            docs = root / "docs"
            copied = copy_graph_outputs(root, docs)
            self.assertIn("runtime-status.json", copied)
            self.assertTrue((docs / "knowledge-graph" / "data" / "runtime-status.json").is_file())

    def test_assets_are_locally_referenced(self) -> None:
        mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        self.assertIn("assets/vendor/cytoscape/cytoscape.min.js", mkdocs)
        self.assertNotIn("cdn.jsdelivr.net/npm/cytoscape", mkdocs)


if __name__ == "__main__":
    unittest.main()
