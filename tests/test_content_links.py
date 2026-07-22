from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from content_links import (
    LinkOccurrence,
    analyze_all,
    convert_for_combined,
    convert_for_web,
    resolve_occurrence,
    scan_wikilinks,
)
from callouts import convert_obsidian_callouts_for_web
from content_index import parse_headings
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

    def test_scanner_ignores_indented_code(self) -> None:
        text = "    [[Fehlt]]\n\t![[Bild.png]]\n\n[[Alpha]]\n"
        found = scan_wikilinks(text, self.source)
        self.assertEqual([item.raw for item in found], ["[[Alpha]]"])

    def test_indented_comment_close_does_not_hide_following_link(self) -> None:
        text = "<!--\n    Kommentar -->\n[[Alpha]]\n"
        found = scan_wikilinks(text, self.source)
        self.assertEqual([item.raw for item in found], ["[[Alpha]]"])

    def test_comment_opener_inside_indented_code_is_literal(self) -> None:
        text = "    <!-- literal code\n[[Alpha]]\n"
        found = scan_wikilinks(text, self.source)
        self.assertEqual([item.raw for item in found], ["[[Alpha]]"])

    def test_fence_marker_inside_comment_does_not_open_fence(self) -> None:
        text = "<!--\n```\n-->\n[[Alpha]]\n"
        found = scan_wikilinks(text, self.source)
        self.assertEqual([item.raw for item in found], ["[[Alpha]]"])

    def test_fence_closer_must_match_character_length_indent_and_tail(self) -> None:
        text = (
            "````md\n"
            "[[Hidden1]]\n"
            "```\n"
            "[[Hidden2]]\n"
            "    ````\n"
            "```not-a-close\n"
            "[[Hidden3]]\n"
            "````\n"
            "[[Alpha]]\n"
        )
        found = scan_wikilinks(text, self.source)
        self.assertEqual([item.raw for item in found], ["[[Alpha]]"])

    def test_multiline_code_spans_hide_links_and_match_delimiter_length(self) -> None:
        text = (
            "`one\n[[Hidden1]]\ntwo`\n"
            "``one\n[[Hidden2]]\ntwo``\n"
            "`unmatched literal\n"
            "[[Alpha]]\n"
        )
        found = scan_wikilinks(text, self.source)
        self.assertEqual([item.raw for item in found], ["[[Alpha]]"])

    def test_inline_code_lookahead_stops_at_markdown_block_boundaries(self) -> None:
        text = (
            "Start `\n"
            "[[BeforeBlank]]\n"
            "\n"
            "Next ` literal\n"
            "[[AfterBlank]]\n"
            "\n"
            "Start `\n"
            "[[BeforeHeading]]\n"
            "# Heading `\n"
            "[[AfterHeading]]\n"
            "\n"
            "Start `\n"
            "[[BeforeFence]]\n"
            "```text\n"
            "` and [[HiddenInFence]]\n"
            "```\n"
            "[[AfterFence]]\n"
        )
        found = scan_wikilinks(text, self.source)
        self.assertEqual(
            [item.raw for item in found],
            [
                "[[BeforeBlank]]", "[[AfterBlank]]",
                "[[BeforeHeading]]", "[[AfterHeading]]",
                "[[BeforeFence]]", "[[AfterFence]]",
            ],
        )

    def test_shared_fence_state_protects_headings_combined_and_callouts(self) -> None:
        markdown = (
            "````md\n"
            "# Fake one\n"
            "```\n"
            "# Fake two\n"
            "    ````\n"
            "```not-a-close\n"
            "# Fake three\n"
            "````\n"
            "# Real\n"
        )
        headings, issues = parse_headings(markdown, 1)
        self.assertEqual(issues, [])
        self.assertEqual([heading.title for heading in headings], ["Real"])

        combined = convert_for_combined(
            markdown,
            self.source,
            self.root,
            {self.source.resolve()},
            index=self.index,
        )
        self.assertNotIn("Fake two {#", combined)
        self.assertNotIn("Fake three {#", combined)
        self.assertIn("# Real {#doc-01-grundlagen-02-b--real}", combined)

        callouts = convert_obsidian_callouts_for_web(
            "````md\n"
            "> [!note] Versteckt\n"
            "```\n"
            "> bleibt Code\n"
            "````\n"
            "> [!note] Sichtbar\n"
            "> Inhalt\n"
        )
        self.assertIn("> [!note] Versteckt", callouts)
        self.assertIn("> bleibt Code", callouts)
        self.assertIn('!!! note "Sichtbar"', callouts)

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
