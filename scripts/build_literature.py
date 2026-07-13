#!/usr/bin/env python3
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
items = []
for path in sorted((ROOT / "references").glob("*.md")):
    if path.name == "README.md":
        continue
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not match:
        raise ValueError(f"Kein Frontmatter: {path}")
    meta = yaml.safe_load(match.group(1))
    body = match.group(2)
    citation_match = re.search(
        r"## Vollständige Zitation\n\n(.+?)(?:\n\n##|\Z)", body, re.S
    )
    if not citation_match:
        raise ValueError(f"Keine Zitation: {path}")
    items.append((meta["reference_id"], meta, citation_match.group(1).strip()))

lines = [
    "---", "title: Literatur", "generated: true", "last_reviewed: 2026-07-13", "---", "",
    "# Literatur", "", "> Automatisch aus `references/` erzeugt. Nicht manuell bearbeiten.", ""
]
for ref_id, meta, citation in items:
    lines.extend([f"## {ref_id}", "", citation, ""])
    if meta.get("doi"):
        doi = meta["doi"]
        lines.append(f"- DOI: [https://doi.org/{doi}](https://doi.org/{doi})")
    if meta.get("pmid"):
        pmid = meta["pmid"]
        lines.append(f"- PubMed: [PMID {pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")
    lines.extend([
        f"- Evidenztyp: `{meta.get('evidence_type')}` · Evidenzgrad: `{meta.get('evidence_grade')}` · Status: `{meta.get('status')}`",
        "",
    ])

(ROOT / "Literatur.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Literatur: {len(items)} Quellen")
