#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
from pathlib import Path
import shutil
import subprocess
import tarfile
from io import BytesIO

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / ".graph-bootstrap"
EXPECTED_CHUNKS = 5
WORKFLOW = ROOT / ".github" / "workflows" / "apply-graph-phase.yml"

chunks = sorted(BOOTSTRAP.glob("payload-*.txt"))
if len(chunks) != EXPECTED_CHUNKS:
    print(f"Payload noch unvollständig: {len(chunks)}/{EXPECTED_CHUNKS} Chunks")
    raise SystemExit(0)

encoded = "".join(path.read_text(encoding="utf-8").strip() for path in chunks)
archive_bytes = gzip.decompress(base64.b64decode(encoded, validate=True))
with tarfile.open(fileobj=BytesIO(archive_bytes), mode="r:") as archive:
    for member in archive.getmembers():
        destination = (ROOT / member.name).resolve()
        destination.relative_to(ROOT.resolve())
    archive.extractall(ROOT, filter="data")

shutil.rmtree(BOOTSTRAP)
WORKFLOW.unlink(missing_ok=True)
subprocess.run(["git", "config", "user.name", "github-actions[bot]"], cwd=ROOT, check=True)
subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], cwd=ROOT, check=True)
subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
    print("Keine Änderungen anzuwenden")
    raise SystemExit(0)
subprocess.run(["git", "commit", "-m", "Fix Wissensgraph-Kernmodell"], cwd=ROOT, check=True)
subprocess.run(["git", "push", "origin", "HEAD"], cwd=ROOT, check=True)
