#!/usr/bin/env python3
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
edges = set()
pattern = re.compile(r"\[\[([^\]|#]+)")
for path in ROOT.rglob("*.md"):
    if any(part in {"build", "site"} for part in path.parts):
        continue
    source = str(path.relative_to(ROOT).with_suffix(""))
    for target in pattern.findall(path.read_text(encoding="utf-8")):
        edges.add((source, target))

out = ROOT / "build"
out.mkdir(exist_ok=True)
(out / "knowledge-graph.json").write_text(
    json.dumps({"edges": [{"source": a, "target": b} for a, b in sorted(edges)]}, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
lines = ["flowchart LR"]
for i, (source, target) in enumerate(sorted(edges)):
    lines.append(f'  A{i}["{source}"] --> B{i}["{target}"]')
(out / "knowledge-graph.mmd").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wissensgraph: {len(edges)} Kanten")
