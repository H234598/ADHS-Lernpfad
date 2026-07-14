#!/usr/bin/env python3
"""Literatur.md, BibTeX und CSL JSON aus den Studienkarten erzeugen."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "references"
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.S)
CITATION_RE = re.compile(r"## Vollständige Zitation\n\n(.+?)(?:\n\n##|\Z)", re.S)


class ReferenceError(ValueError):
    pass


@dataclass(frozen=True)
class Reference:
    reference_id: str
    meta: dict[str, Any]
    citation: dict[str, Any]
    body_citation: str
    source: Path


def parse_reference(path: Path) -> Reference:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ReferenceError(f"Kein Frontmatter: {path.relative_to(ROOT)}")
    meta = yaml.safe_load(match.group(1))
    if not isinstance(meta, dict):
        raise ReferenceError(f"Frontmatter ist kein Mapping: {path.relative_to(ROOT)}")
    citation = meta.get("citation")
    if not isinstance(citation, dict):
        raise ReferenceError(f"Strukturierte citation fehlt: {path.relative_to(ROOT)}")
    citation_match = CITATION_RE.search(match.group(2))
    if not citation_match:
        raise ReferenceError(f"Abschnitt 'Vollständige Zitation' fehlt: {path.relative_to(ROOT)}")
    reference_id = str(meta.get("reference_id", "")).strip()
    if not reference_id or reference_id != path.stem:
        raise ReferenceError(
            f"reference_id muss dem Dateinamen entsprechen: {path.relative_to(ROOT)}"
        )
    return Reference(reference_id, meta, citation, citation_match.group(1).strip(), path)


def require(citation: dict[str, Any], field: str, source: Path) -> Any:
    value = citation.get(field)
    if value in (None, "", []):
        raise ReferenceError(f"citation.{field} fehlt: {source.relative_to(ROOT)}")
    return value


def author_text(citation: dict[str, Any], source: Path) -> str:
    authors = require(citation, "authors", source)
    if not isinstance(authors, list) or not all(
        isinstance(item, str) and item.strip() for item in authors
    ):
        raise ReferenceError(
            f"citation.authors muss eine Liste von Namen sein: {source.relative_to(ROOT)}"
        )
    names = [item.strip() for item in authors]
    if citation.get("et_al"):
        return ", ".join(names) + ", et al."
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} & {names[1]}"
    return ", ".join(names[:-1]) + f", & {names[-1]}"


def formatted_citation(reference: Reference) -> str:
    citation = reference.citation
    authors = author_text(citation, reference.source)
    year = require(citation, "year", reference.source)
    title = str(require(citation, "article_title", reference.source)).rstrip(".")
    journal = str(citation.get("journal", "")).strip()
    volume = str(citation.get("volume", "")).strip()
    issue = str(citation.get("issue", "")).strip()
    pages = str(citation.get("pages", "")).strip()
    article_number = str(citation.get("article_number", "")).strip()

    result = f"{authors} ({year}). {title}."
    if journal:
        journal_volume = journal + (f", {volume}" if volume else "")
        result += f" *{journal_volume}*"
        if issue:
            result += f"({issue})"
        locator = pages or article_number
        if locator:
            result += f", {locator}"
        result += "."
    return result


def bibtex_escape(value: Any) -> str:
    text = str(value)
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("{", r"\{")
        .replace("}", r"\}")
    )


def bibtex_entry(reference: Reference) -> str:
    citation = reference.citation
    entry_type = str(citation.get("entry_type", "article")).strip() or "article"
    authors = [str(item).strip() for item in citation["authors"]]
    if citation.get("et_al"):
        authors.append("others")
    fields: list[tuple[str, Any]] = [
        ("author", " and ".join(authors)),
        ("title", citation["article_title"]),
        ("year", citation["year"]),
    ]
    mappings = [
        ("journal", "journal"),
        ("volume", "volume"),
        ("issue", "number"),
        ("pages", "pages"),
        ("article_number", "eid"),
    ]
    for source_name, bib_name in mappings:
        if citation.get(source_name):
            value = citation[source_name]
            if bib_name == "pages":
                value = str(value).replace("–", "--").replace("—", "--")
            fields.append((bib_name, value))
    if reference.meta.get("doi"):
        fields.append(("doi", reference.meta["doi"]))
        fields.append(("url", f"https://doi.org/{reference.meta['doi']}"))
    elif reference.meta.get("pmid"):
        fields.append(("url", f"https://pubmed.ncbi.nlm.nih.gov/{reference.meta['pmid']}/"))
    if reference.meta.get("pmid"):
        fields.append(("pmid", reference.meta["pmid"]))
    lines = [f"@{entry_type}{{{reference.reference_id},"]
    for name, value in fields:
        lines.append(f"  {name} = {{{bibtex_escape(value)}}},")
    lines.append("}")
    return "\n".join(lines)


def csl_author(name: str) -> dict[str, str]:
    if "," in name:
        family, given = name.split(",", 1)
        return {"family": family.strip(), "given": given.strip()}
    return {"literal": name.strip()}


def csl_entry(reference: Reference) -> dict[str, Any]:
    citation = reference.citation
    entry: dict[str, Any] = {
        "id": reference.reference_id,
        "type": citation.get("csl_type", "article-journal"),
        "title": citation["article_title"],
        "author": [csl_author(str(name)) for name in citation["authors"]],
        "issued": {"date-parts": [[int(citation["year"])]]},
    }
    mapping = {
        "journal": "container-title",
        "volume": "volume",
        "issue": "issue",
        "pages": "page",
        "article_number": "number",
    }
    for source_name, csl_name in mapping.items():
        if citation.get(source_name):
            entry[csl_name] = str(citation[source_name])
    if reference.meta.get("doi"):
        entry["DOI"] = str(reference.meta["doi"])
        entry["URL"] = f"https://doi.org/{reference.meta['doi']}"
    elif reference.meta.get("pmid"):
        entry["URL"] = f"https://pubmed.ncbi.nlm.nih.gov/{reference.meta['pmid']}/"
    if reference.meta.get("pmid"):
        entry["PMID"] = str(reference.meta["pmid"])
    if citation.get("et_al"):
        entry["note"] = (
            "Die Studienkarte enthält eine ausdrücklich gekennzeichnete, "
            "abgekürzte Autorenliste."
        )
    return entry


def markdown_bibliography(references: list[Reference]) -> str:
    last_reviewed = max(str(ref.meta.get("last_checked", "")) for ref in references)
    lines = [
        "---",
        "title: Literatur",
        "generated: true",
        f"last_reviewed: {last_reviewed}",
        "---",
        "",
        "# Literatur",
        "",
        "> Automatisch aus `references/` erzeugt. Nicht manuell bearbeiten.",
        "",
        "[BibTeX herunterladen](references.bib) · "
        "[CSL JSON herunterladen](references.json)",
        "",
    ]
    for ref in references:
        lines.extend([f"## {ref.reference_id}", "", formatted_citation(ref), ""])
        if ref.meta.get("doi"):
            doi = ref.meta["doi"]
            lines.append(f"- DOI: [https://doi.org/{doi}](https://doi.org/{doi})")
        if ref.meta.get("pmid"):
            pmid = ref.meta["pmid"]
            lines.append(f"- PubMed: [PMID {pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")
        lines.extend(
            [
                f"- Evidenztyp: `{ref.meta.get('evidence_type')}` · "
                f"Evidenzgrad: `{ref.meta.get('evidence_grade')}` · "
                f"Status: `{ref.meta.get('status')}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    references = [
        parse_reference(path)
        for path in sorted(REFERENCE_DIR.glob("*.md"))
        if path.name != "README.md"
    ]
    if not references:
        raise ReferenceError("Keine Studienkarten gefunden")

    for reference in references:
        generated = formatted_citation(reference)
        if generated != reference.body_citation:
            raise ReferenceError(
                f"Zitation weicht von citation-Metadaten ab: "
                f"{reference.source.relative_to(ROOT)}\n"
                f"Erwartet: {generated}\n"
                f"Vorhanden: {reference.body_citation}"
            )

    (ROOT / "Literatur.md").write_text(
        markdown_bibliography(references), encoding="utf-8"
    )
    (ROOT / "references.bib").write_text(
        "\n\n".join(bibtex_entry(ref) for ref in references) + "\n",
        encoding="utf-8",
    )
    (ROOT / "references.json").write_text(
        json.dumps(
            [csl_entry(ref) for ref in references],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Literatur: {len(references)} Quellen; "
        "Literatur.md, references.bib und references.json erzeugt"
    )


if __name__ == "__main__":
    main()
