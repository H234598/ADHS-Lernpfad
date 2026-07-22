from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_exports


class GraphArtifactManifestTests(unittest.TestCase):
    GRAPH_NAMES = (
        "knowledge-graph.json",
        "knowledge-graph.graphml",
        "knowledge-graph.mmd",
        "graph-report.md",
        "graph-report.json",
        "runtime-status.json",
    )

    def test_all_phase3_artifacts_are_declared(self) -> None:
        self.assertTrue(set(self.GRAPH_NAMES).issubset(build_exports.ARTIFACT_METADATA))
        self.assertTrue(set(self.GRAPH_NAMES).issubset(build_exports.ARTIFACT_DESCRIPTIONS))

    def test_manifest_and_checksum_file_match_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artifacts = Path(temp)
            metadata = {
                name: build_exports.ARTIFACT_METADATA[name]
                for name in self.GRAPH_NAMES
            }
            for index, name in enumerate(self.GRAPH_NAMES):
                (artifacts / name).write_bytes(f"artifact-{index}\n".encode())
            with (
                patch.object(build_exports, "ARTIFACTS", artifacts),
                patch.object(build_exports, "ARTIFACT_METADATA", metadata),
                patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "1784700000"}),
            ):
                build_exports.write_manifest()

            manifest = json.loads((artifacts / "downloads.json").read_text(encoding="utf-8"))
            self.assertEqual([item["filename"] for item in manifest["artifacts"]], list(self.GRAPH_NAMES))
            for item in manifest["artifacts"]:
                content = (artifacts / item["filename"]).read_bytes()
                self.assertEqual(item["sha256"], sha256(content).hexdigest())
                self.assertTrue(item["description"])
                self.assertTrue(item["generated_at"].endswith("Z"))
                self.assertEqual(item["type"], item["media_type"])
            checksum_lines = (artifacts / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(checksum_lines), len(self.GRAPH_NAMES))
            self.assertTrue(all(line.split("  ", 1)[1] in self.GRAPH_NAMES for line in checksum_lines))

    def test_copy_graph_artifacts_includes_final_runtime_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            graph = root / "graph"
            artifacts = root / "artifacts"
            graph.mkdir()
            artifacts.mkdir()
            for name in self.GRAPH_NAMES[:-1]:
                (graph / name).write_text(f"{name}\n", encoding="utf-8")
            runtime = root / "runtime-status.json"
            runtime.write_text('{"status":"success"}\n', encoding="utf-8")
            with (
                patch.object(build_exports, "GRAPH_BUILD", graph),
                patch.object(build_exports, "ARTIFACTS", artifacts),
            ):
                build_exports.copy_graph_artifacts(runtime_source=runtime)
            self.assertEqual(
                {path.name for path in artifacts.iterdir()},
                set(self.GRAPH_NAMES),
            )
            self.assertEqual(
                (artifacts / "runtime-status.json").read_bytes(),
                runtime.read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
