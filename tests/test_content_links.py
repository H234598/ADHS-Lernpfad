from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from content_links import (
    LinkOccurrence,
    analyze_all,
    convert_for_web,
    resolve_occurrence,
    scan_wikilinks,
)
from content_model import build_content_index


class ContentLinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "01-Grundlagen").mkdir()
        (self.root / "other").mkdir()
        (self.root / "knowledge-graph").mkdir()
        (self.root / "README.md").write_text("# Startseite\n", encoding="utf-8")
        (self.root / "Glossar.md").write_text(
            "# Glossar\n\n## Begriff\n", encoding="utf-8",
        )
        (self.root / "01-Grundlagen" / "01-A.md").write_text(
            "---\ntitle: Alpha\naliases: [Erstes Kapitel, Gemeinsam]\n"
            "level: Grundlagen\n---\n\n# Alpha\n\n## Abschnitt\nText\n",
            encoding="utf-8",
        )
        (self.root / "01-Grundlagen" / "02-B.md").write_text(
            "---\ntitle: Beta\nlevel: Grundlagen\nprerequisites: [Alpha]\n"
            "---\n\n# Beta\n",
            encoding="utf-8",
        )
        (self.root / "other" / "01-A.md").write_text(
            "---\ntitle: Doppel\naliases: [Gemeinsam]\n---\n\n# Doppel\n",
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
            "    scope: learning\n",
            encoding="utf-8",
        )
        self.index = build_content_index(self.root)
        self.source = self.root / "01-Grundlagen" / "02-B.md"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def occurrence(
        self, target: str, heading: str | None = None,
    ) -> LinkOccurrence:
        return LinkOccurrence(
            source=self.source,
            raw=f"[[{target}{'#' + heading if heading else ''}]]",
            target=target,
            heading=heading,
            label=heading or Path(target).stem or target,
            embed=False,
            line=1,
            column=1,
            start=0,
            end=0,
        )

    def test_scanner_ignores_frontmatter_code_comments_and_inline_code(self) -> None:
        text = (
            "---\nexample: '[[Frontmatter]]'\n---\n"
            "[[Alpha]]\n"
            "`[[Inline]]`\n"
            "<!-- [[Kommentar]] -->\n"
            "```md\n[[Code]]\n```\n"
            "![[Bild.png|Bild]]\n"
        )
        found = scan_wikilinks(text, self.source)
        self.assertEqual([item.target for item in found], ["Alpha", "Bild.png"])
        self.assertEqual([item.embed for item in found], [False, True])

    def test_title_alias_heading_and_planned_resolution(self) -> None:
        title = resolve_occurrence(self.index, self.occurrence("Alpha"))
        alias = resolve_occurrence(self.index, self.occurrence("Erstes Kapitel"))
        heading = resolve_occurrence(
            self.index, self.occurrence("Alpha", "Abschnitt"),
        )
        planned = resolve_occurrence(
            self.index, self.occurrence("01-Grundlagen/03-C"),
        )
        self.assertEqual(title.target_id, "doc:01-Grundlagen/01-A")
        self.assertEqual(alias.target_id, title.target_id)
        self.assertEqual(heading.status, "ok")
        self.assertTrue(heading.target_id.startswith("section:"))
        self.assertEqual(planned.status, "planned")

    def test_ambiguous_missing_heading_and_path_escape(self) -> None:
        ambiguous = resolve_occurrence(self.index, self.occurrence("Gemeinsam"))
        missing_heading = resolve_occurrence(
            self.index, self.occurrence("Alpha", "Fehlt"),
        )
        escaped = resolve_occurrence(
            self.index, self.occurrence("../../../secret"),
        )
        self.assertEqual(ambiguous.status, "ambiguous")
        self.assertEqual(missing_heading.status, "missing-heading")
        self.assertEqual(escaped.status, "malformed")

    def test_web_conversion_uses_relative_markdown_link(self) -> None:
        converted = convert_for_web(
            "Siehe [[Alpha#Abschnitt|hier]].\n",
            self.source,
            self.root,
            index=self.index,
        )
        self.assertEqual(converted, "Siehe [hier](01-A.md#abschnitt).\n")

    def test_analyze_all_returns_all_issues(self) -> None:
        self.source.write_text(
            "# Beta\n\n[[Fehlt]] und [[Alpha#Fehlt]]\n", encoding="utf-8",
        )
        _, issues = analyze_all(self.root)
        codes = [issue.code for issue in issues]
        self.assertIn("missing-document", codes)
        self.assertIn("missing-heading", codes)


if __name__ == "__main__":
    unittest.main()
