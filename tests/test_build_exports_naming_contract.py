from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_exports


EXPECTED_ARTIFACT_FILENAMES = {
    "pdf": "ADHS-Lernpfad.pdf",
    "epub": "ADHS-Lernpfad.epub",
    "html": "ADHS-Lernpfad.html",
    "latex": "ADHS-Lernpfad.tex",
    "combined_markdown": "ADHS-Lernpfad-Gesamtdokument.md",
    "obsidian_vault": "ADHS-Lernpfad-Obsidian-Vault.zip",
    "anki": "ADHS-Lernpfad.apkg",
    "references_bib": "references.bib",
    "references_json": "references.json",
    "sync_linux": "ADHS-Lernpfad-Sync-Linux.zip",
    "sync_android": "ADHS-Lernpfad-Sync-Android.zip",
    "sync_windows": "ADHS-Lernpfad-Sync-Windows.zip",
    "sync_macos": "ADHS-Lernpfad-Sync-macOS.zip",
    "sync_ios": "ADHS-Lernpfad-Sync-iOS.zip",
    "sync_bsd": "ADHS-Lernpfad-Sync-BSD.zip",
    "knowledge_graph_json": "knowledge-graph.json",
    "knowledge_graph_graphml": "knowledge-graph.graphml",
    "knowledge_graph_mermaid": "knowledge-graph.mmd",
    "graph_report_markdown": "graph-report.md",
    "graph_report_json": "graph-report.json",
    "runtime_status": "runtime-status.json",
}


class ExportNamingContractTests(unittest.TestCase):
    def test_public_artifact_filenames_have_one_canonical_registry(self) -> None:
        self.assertEqual(build_exports.ARTIFACT_FILENAMES, EXPECTED_ARTIFACT_FILENAMES)
        self.assertEqual(
            set(build_exports.ARTIFACT_METADATA),
            set(EXPECTED_ARTIFACT_FILENAMES.values()),
        )
        self.assertEqual(
            set(build_exports.ARTIFACT_DESCRIPTIONS),
            set(EXPECTED_ARTIFACT_FILENAMES.values()),
        )

    def test_shared_media_types_have_canonical_constants(self) -> None:
        self.assertEqual(build_exports.MEDIA_TYPE_ZIP, "application/zip")
        self.assertEqual(build_exports.MEDIA_TYPE_JSON, "application/json")
        self.assertEqual(build_exports.MEDIA_TYPE_MARKDOWN, "text/markdown")


if __name__ == "__main__":
    unittest.main()
