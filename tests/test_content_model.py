from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from content_model import build_content_index, document_anchor, slugify


class ContentModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "01-Grundlagen").mkdir()
        (self.root / "references").mkdir()
        (self.root / "knowledge-graph").mkdir()
        (self.root / "README.md").write_text("# Start\n", encoding="utf-8")
        (self.root / "Glossar.md").write_text(
            "---\ntitle: Glossar\ntags: [ADHS, Glossar]\n---\n\n"
            "# Glossar\n\n## Arbeitsgedächtnis\nText\n",
            encoding="utf-8",
        )
        (self.root / "01-Grundlagen" / "01-Start.md").write_text(
            "---\n"
            "title: Start\n"
            "aliases: [Einstieg]\n"
            "level: Grundlagen\n"
            "difficulty: 1\n"
            "last_reviewed: 2026-07-16\n"
            "tags: [ADHS]\n"
            "references: [Ref2026]\n"
            "prerequisites: []\n"
            "---\n\n"
            "# Einheit 1 – Start\n\n## Überblick {#ueberblick}\nText\n",
            encoding="utf-8",
        )
        (self.root / "references" / "Ref2026.md").write_text(
            "---\nreference_id: Ref2026\ntitle: Beispielstudie\n---\n\n"
            "# Beispielstudie\n",
            encoding="utf-8",
        )
        (self.root / "index.json").write_text(
            json.dumps({"chapters": [{
                "number": 1,
                "path": "01-Grundlagen/01-Start.md",
                "title": "Start",
            }]}),
            encoding="utf-8",
        )
        (self.root / "knowledge-graph" / "planned-nodes.yaml").write_text(
            "nodes:\n"
            "  - path: 01-Grundlagen/02-Fortsetzung\n"
            "    title: Fortsetzung\n"
            "    type: chapter\n"
            "    scope: learning\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_index_builds_stable_ids_and_metadata(self) -> None:
        index = build_content_index(self.root)
        chapter = index.documents["doc:01-Grundlagen/01-Start"]
        self.assertEqual(chapter.title, "Start")
        self.assertEqual(chapter.aliases, ("Einstieg",))
        self.assertEqual(chapter.type, "chapter")
        self.assertEqual(chapter.metadata["last_reviewed"], "2026-07-16")
        self.assertEqual(chapter.url, "/01-Grundlagen/01-Start/")
        self.assertEqual(chapter.headings[1].anchor, "ueberblick")
        self.assertEqual(index.chapter_ids, [chapter.id])
        self.assertIn("planned:01-Grundlagen/02-Fortsetzung", index.planned_nodes)
        self.assertEqual(index.lookup_documents("Einstieg"), [chapter])

    def test_glossary_section_and_reference_lookup(self) -> None:
        index = build_content_index(self.root)
        glossary, heading = index.glossary_section("Arbeitsgedächtnis")
        self.assertEqual(glossary.id, "doc:Glossar")
        self.assertEqual(heading.anchor, "arbeitsgedachtnis")
        self.assertEqual(
            [item.id for item in index.lookup_documents("Ref2026")],
            ["ref:Ref2026"],
        )

    def test_duplicate_heading_anchor_is_reported(self) -> None:
        path = self.root / "README.md"
        path.write_text("# Start\n\n## Ähnlich\n\n## Ahnlich\n", encoding="utf-8")
        index = build_content_index(self.root)
        self.assertIn(
            "duplicate-heading-anchor",
            [issue.code for issue in index.model_issues],
        )

    def test_slug_and_document_anchor_remain_compatible(self) -> None:
        self.assertEqual(slugify("Arbeitsgedächtnis"), "arbeitsgedachtnis")
        self.assertEqual(
            document_anchor(Path("01-Grundlagen/01-Start.md")),
            "doc-01-grundlagen-01-start",
        )

    def test_generated_cache_markdown_is_excluded(self) -> None:
        cache = self.root / ".pytest_cache"
        cache.mkdir()
        (cache / "README.md").write_text("# Pytest cache\n", encoding="utf-8")

        index = build_content_index(self.root)

        self.assertNotIn("doc:.pytest_cache/README", index.documents)

    def test_technical_roadmap_is_classified_as_technical(self) -> None:
        (self.root / "TECHNISCHE_ROADMAP.md").write_text(
            "---\ntitle: Technische Roadmap\n---\n\n# Technische Roadmap\n",
            encoding="utf-8",
        )

        document = build_content_index(self.root).documents[
            "doc:TECHNISCHE_ROADMAP"
        ]

        self.assertEqual((document.type, document.scope), ("technical", "technical"))


if __name__ == "__main__":
    unittest.main()
