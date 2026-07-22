#!/usr/bin/env python3
"""Build stable downloadable artifacts for GitHub Pages and CI archives."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
from typing import Final
from zipfile import ZIP_DEFLATED, ZipFile

ROOT: Final = Path(__file__).resolve().parents[1]
BUILD: Final = ROOT / "build"
ARTIFACTS: Final = BUILD / "artifacts"
COMBINED: Final = BUILD / "ADHS-Lernpfad-Gesamtdokument.md"

ARTIFACT_METADATA: Final[dict[str, tuple[str, str]]] = {
    "ADHS-Lernpfad.pdf": ("PDF", "application/pdf"),
    "ADHS-Lernpfad.epub": ("EPUB 3", "application/epub+zip"),
    "ADHS-Lernpfad.html": ("Offline-HTML", "text/html"),
    "ADHS-Lernpfad.tex": ("LaTeX", "application/x-tex"),
    "ADHS-Lernpfad-Gesamtdokument.md": ("Markdown", "text/markdown"),
    "ADHS-Lernpfad-Obsidian-Vault.zip": ("Obsidian Vault", "application/zip"),
    "ADHS-Lernpfad.apkg": ("Anki", "application/octet-stream"),
    "references.bib": ("BibTeX", "application/x-bibtex"),
    "references.json": ("CSL JSON", "application/json"),
}

VAULT_ROOT_FILES: Final = (
    "README.md",
    "00-Einfuehrung.md",
    "Glossar.md",
    "Literatur.md",
    "ROADMAP.md",
    "DOWNLOADS.md",
    "references.bib",
    "references.json",
)
VAULT_DIRECTORIES: Final = (
    "01-Grundlagen",
    "02-Vertiefung",
    "references",
    "knowledge-graph",
    "cards",
    "figures",
    "assets",
)


def run(command: list[str]) -> None:
    """Run one external build command and fail immediately on errors."""

    subprocess.run(command, cwd=ROOT, check=True)


def require_file(path: Path) -> Path:
    """Return an expected build input or raise a useful error."""

    if not path.is_file():
        raise FileNotFoundError(f"Erwartete Datei fehlt: {path.relative_to(ROOT)}")
    return path


def common_pandoc_args() -> list[str]:
    """Return arguments shared by EPUB, HTML, LaTeX and PDF exports."""

    return [
        str(require_file(COMBINED)),
        "--standalone",
        "--toc",
        "--citeproc",
        f"--bibliography={require_file(ROOT / 'references.bib')}",
        "--metadata=title:ADHS-Lernpfad",
        "--metadata=lang:de-DE",
        "--resource-path=.:figures:assets",
    ]


def build_document_exports() -> None:
    """Create EPUB 3, embedded HTML, LaTeX and PDF reading formats."""

    common = common_pandoc_args()
    run(["pandoc", *common, "--to=epub3", "--output", str(ARTIFACTS / "ADHS-Lernpfad.epub")])
    run(
        [
            "pandoc",
            *common,
            "--to=html5",
            "--embed-resources",
            "--output",
            str(ARTIFACTS / "ADHS-Lernpfad.html"),
        ]
    )
    run(["pandoc", *common, "--output", str(ARTIFACTS / "ADHS-Lernpfad.tex")])
    run(
        [
            "pandoc",
            *common,
            "--pdf-engine=lualatex",
            "--variable=mainfont:DejaVu Serif",
            "--variable=sansfont:DejaVu Sans",
            "--variable=monofont:DejaVu Sans Mono",
            "--output",
            str(ARTIFACTS / "ADHS-Lernpfad.pdf"),
        ]
    )


def copy_generated_sources() -> None:
    """Copy text, bibliography and Anki outputs into the public bundle."""

    sources = {
        COMBINED: ARTIFACTS / "ADHS-Lernpfad-Gesamtdokument.md",
        ROOT / "references.bib": ARTIFACTS / "references.bib",
        ROOT / "references.json": ARTIFACTS / "references.json",
        BUILD / "ADHS-Lernpfad.apkg": ARTIFACTS / "ADHS-Lernpfad.apkg",
    }
    for source, destination in sources.items():
        shutil.copy2(require_file(source), destination)


def vault_files() -> list[Path]:
    """Collect the learning-facing files included in the Obsidian archive."""

    selected: list[Path] = []
    for relative in VAULT_ROOT_FILES:
        path = ROOT / relative
        if path.is_file():
            selected.append(path)
    for relative in VAULT_DIRECTORIES:
        directory = ROOT / relative
        if directory.is_dir():
            selected.extend(path for path in directory.rglob("*") if path.is_file())
    return sorted(set(selected))


def build_vault_zip() -> None:
    """Create a clean Obsidian-oriented ZIP without project infrastructure."""

    destination = ARTIFACTS / "ADHS-Lernpfad-Obsidian-Vault.zip"
    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for source in vault_files():
            archive.write(source, Path("ADHS-Lernpfad") / source.relative_to(ROOT))


def digest(path: Path) -> str:
    """Calculate the SHA-256 digest of one artifact."""

    checksum = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def write_manifest() -> None:
    """Write a JSON manifest and conventional SHA256SUMS file."""

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    entries: list[dict[str, object]] = []
    checksum_lines: list[str] = []
    for filename, (label, media_type) in ARTIFACT_METADATA.items():
        path = require_file(ARTIFACTS / filename)
        checksum = digest(path)
        entries.append(
            {
                "filename": filename,
                "label": label,
                "media_type": media_type,
                "size_bytes": path.stat().st_size,
                "sha256": checksum,
                "url": f"https://ADHS.telacore.org/artifacts/{filename}",
            }
        )
        checksum_lines.append(f"{checksum}  {filename}")

    manifest = {
        "project": "ADHS-Lernpfad",
        "generated_at": generated_at,
        "artifacts": entries,
    }
    (ARTIFACTS / "downloads.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (ARTIFACTS / "SHA256SUMS.txt").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    """Build every public download and its integrity metadata."""

    if ARTIFACTS.exists():
        shutil.rmtree(ARTIFACTS)
    ARTIFACTS.mkdir(parents=True)
    build_document_exports()
    copy_generated_sources()
    build_vault_zip()
    write_manifest()
    print(f"Downloads: {len(ARTIFACT_METADATA)} Artefakte plus Manifest und Prüfsummen")


if __name__ == "__main__":
    main()
