#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
from io import BytesIO
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / ".graph-web-bootstrap"
WORKFLOW = ROOT / ".github" / "workflows" / "apply-graph-web-phase.yml"
EXPECTED_CHUNKS = 3

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

vendor_tmp = ROOT / "build" / "vendor-cytoscape"
if vendor_tmp.exists():
    shutil.rmtree(vendor_tmp)
vendor_tmp.mkdir(parents=True)
package_name = subprocess.run(
    ["npm", "pack", "cytoscape@3.34.0", "--silent"],
    cwd=vendor_tmp,
    check=True,
    capture_output=True,
    text=True,
).stdout.strip().splitlines()[-1]
with tarfile.open(vendor_tmp / package_name, mode="r:gz") as archive:
    archive.extractall(vendor_tmp, filter="data")
package = vendor_tmp / "package"
subprocess.run(
    ["node", "-e", "const p=require('./package/package.json'); if(p.version!=='3.34.0') process.exit(1)"],
    cwd=vendor_tmp,
    check=True,
)
vendor = ROOT / "assets" / "vendor" / "cytoscape"
vendor.mkdir(parents=True, exist_ok=True)
shutil.copy2(package / "dist" / "cytoscape.min.js", vendor / "cytoscape.min.js")
shutil.copy2(package / "LICENSE", vendor / "LICENSE")
(vendor / "VERSION.txt").write_text("3.34.0\n", encoding="utf-8")
checksum = subprocess.run(
    ["sha256sum", "cytoscape.min.js", "LICENSE", "VERSION.txt"],
    cwd=vendor,
    check=True,
    capture_output=True,
    text=True,
).stdout
(vendor / "SHA256SUMS.txt").write_text(checksum, encoding="utf-8")
shutil.rmtree(vendor_tmp)

subprocess.run(["npm", "install", "--package-lock-only", "--ignore-scripts"], cwd=ROOT, check=True)

# Bootstrap files are deliberately absent from the final commit.
shutil.rmtree(BOOTSTRAP)
WORKFLOW.unlink(missing_ok=True)

print("Phase-2-Dateien, Vendor-Abhängigkeit und Lockfile vorbereitet")
