#!/usr/bin/env python3
"""Build stable downloadable artifacts for GitHub Pages and CI archives."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Final
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from automation_run_status import (
    finish_run,
    start_run,
    status_is_managed,
    update_status,
)
from build_sync_packages import build_sync_packages

ROOT: Final = Path(__file__).resolve().parents[1]
BUILD: Final = ROOT / "build"
ARTIFACTS: Final = BUILD / "artifacts"
COMBINED: Final = BUILD / "ADHS-Lernpfad-Gesamtdokument.md"
RUNTIME_STATUS: Final = BUILD / "runtime-status.json"
GRAPH_BUILD: Final = BUILD / "knowledge-graph"

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
    "ADHS-Lernpfad-Sync-Linux.zip": ("Sync-Paket Linux", "application/zip"),
    "ADHS-Lernpfad-Sync-Android.zip": ("Sync-Paket Android", "application/zip"),
    "ADHS-Lernpfad-Sync-Windows.zip": ("Sync-Paket Windows", "application/zip"),
    "ADHS-Lernpfad-Sync-macOS.zip": ("Sync-Paket macOS", "application/zip"),
    "ADHS-Lernpfad-Sync-iOS.zip": ("Sync-Paket iOS/iPadOS", "application/zip"),
    "ADHS-Lernpfad-Sync-BSD.zip": ("Sync-Paket BSD", "application/zip"),
    "knowledge-graph.json": ("Wissensgraph JSON", "application/json"),
    "knowledge-graph.graphml": ("Wissensgraph GraphML", "application/graphml+xml"),
    "knowledge-graph.mmd": ("Wissensgraph Mermaid", "text/plain"),
    "graph-report.md": ("Graphbericht Markdown", "text/markdown"),
    "graph-report.json": ("Graphbericht JSON", "application/json"),
    "runtime-status.json": ("Generator-Laufstatus", "application/json"),
}

ARTIFACT_DESCRIPTIONS: Final[dict[str, str]] = {
    "ADHS-Lernpfad.pdf": "Gesetzte Lesefassung des vollständigen Lernpfads.",
    "ADHS-Lernpfad.epub": "Anpassbare EPUB-3-Fassung für E-Reader.",
    "ADHS-Lernpfad.html": "Eigenständige Offline-HTML-Fassung.",
    "ADHS-Lernpfad.tex": "Von Pandoc erzeugter LaTeX-Quelltext.",
    "ADHS-Lernpfad-Gesamtdokument.md": "Zusammengeführte Markdown-Fassung aller Kapitel.",
    "ADHS-Lernpfad-Obsidian-Vault.zip": "Reproduzierbares Obsidian-Vault-Archiv.",
    "ADHS-Lernpfad.apkg": "Anki-Lernkartendeck.",
    "references.bib": "Bibliografie im BibTeX-Format.",
    "references.json": "Bibliografie im CSL-JSON-Format.",
    "ADHS-Lernpfad-Sync-Linux.zip": "Installations- und Sync-Paket für Linux.",
    "ADHS-Lernpfad-Sync-Android.zip": "Installations- und Sync-Paket für Android/Termux.",
    "ADHS-Lernpfad-Sync-Windows.zip": "Installations- und Sync-Paket für Windows.",
    "ADHS-Lernpfad-Sync-macOS.zip": "Installations- und Sync-Paket für macOS.",
    "ADHS-Lernpfad-Sync-iOS.zip": "Installations- und Sync-Paket für iOS/iPadOS mit iSH.",
    "ADHS-Lernpfad-Sync-BSD.zip": "Installations- und Sync-Paket für BSD/TrueNAS.",
    "knowledge-graph.json": "Kanonischer, typisierter Wissensgraph mit Qualitätsdaten.",
    "knowledge-graph.graphml": "GraphML-Austauschdatei für Graphwerkzeuge.",
    "knowledge-graph.mmd": "Mermaid-Diagnoseansicht des Wissensgraphen.",
    "graph-report.md": "Menschenlesbarer Wissensgraph-Qualitätsbericht.",
    "graph-report.json": "Maschinenlesbarer Wissensgraph-Qualitätsbericht.",
    "runtime-status.json": "Finaler schema-validierter Status des Generatorlaufs.",
}

VAULT_ROOT_FILES: Final = (
    "README.md", "00-Einfuehrung.md", "Glossar.md", "Literatur.md",
    "ROADMAP.md", "DOWNLOADS.md", "references.bib", "references.json",
)
VAULT_DIRECTORIES: Final = (
    "01-Grundlagen", "02-Vertiefung", "references", "knowledge-graph",
    "cards", "figures", "assets",
)


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def require_file(path: Path) -> Path:
    if not path.is_file():
        try:
            shown = path.resolve().relative_to(ROOT.resolve()).as_posix()
        except ValueError:
            shown = str(path)
        raise FileNotFoundError(f"Erwartete Datei fehlt: {shown}")
    return path


def common_pandoc_args() -> list[str]:
    return [
        str(require_file(COMBINED)), "--standalone", "--toc", "--citeproc",
        f"--bibliography={require_file(ROOT / 'references.bib')}",
        "--metadata=title:ADHS-Lernpfad", "--metadata=lang:de-DE",
        "--resource-path=.:figures:assets",
    ]


def build_document_exports() -> None:
    common = common_pandoc_args()
    run(["pandoc", *common, "--to=epub3", "--output", str(ARTIFACTS / "ADHS-Lernpfad.epub")])
    run(["pandoc", *common, "--to=html5", "--embed-resources", "--output", str(ARTIFACTS / "ADHS-Lernpfad.html")])
    run(["pandoc", *common, "--output", str(ARTIFACTS / "ADHS-Lernpfad.tex")])
    run([
        "pandoc", *common, "--pdf-engine=lualatex",
        "--variable=mainfont:DejaVu Serif", "--variable=sansfont:DejaVu Sans",
        "--variable=monofont:DejaVu Sans Mono", "--output",
        str(ARTIFACTS / "ADHS-Lernpfad.pdf"),
    ])


def copy_generated_sources() -> None:
    sources = {
        COMBINED: ARTIFACTS / "ADHS-Lernpfad-Gesamtdokument.md",
        ROOT / "references.bib": ARTIFACTS / "references.bib",
        ROOT / "references.json": ARTIFACTS / "references.json",
        BUILD / "ADHS-Lernpfad.apkg": ARTIFACTS / "ADHS-Lernpfad.apkg",
    }
    for source, destination in sources.items():
        shutil.copy2(require_file(source), destination)


def build_public_sync_packages() -> None:
    package_dir = BUILD / "sync-packages"
    for package in build_sync_packages(package_dir):
        shutil.copy2(package, ARTIFACTS / package.name)


def vault_files() -> list[Path]:
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
    destination = ARTIFACTS / "ADHS-Lernpfad-Obsidian-Vault.zip"
    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for source in vault_files():
            archive_path = (Path("ADHS-Lernpfad") / source.relative_to(ROOT)).as_posix()
            info = ZipInfo(archive_path, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o644 & 0xFFFF) << 16
            archive.writestr(info, source.read_bytes())


def copy_graph_artifacts(
    *, include_runtime: bool = True, runtime_source: Path = RUNTIME_STATUS,
) -> None:
    sources = {
        "knowledge-graph.json": GRAPH_BUILD / "knowledge-graph.json",
        "knowledge-graph.graphml": GRAPH_BUILD / "knowledge-graph.graphml",
        "knowledge-graph.mmd": GRAPH_BUILD / "knowledge-graph.mmd",
        "graph-report.md": GRAPH_BUILD / "graph-report.md",
        "graph-report.json": GRAPH_BUILD / "graph-report.json",
    }
    if include_runtime:
        sources["runtime-status.json"] = runtime_source
    for filename, source in sources.items():
        shutil.copy2(require_file(source), ARTIFACTS / filename)


def digest(path: Path) -> str:
    checksum = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def generated_at() -> str:
    raw_epoch = os.getenv("SOURCE_DATE_EPOCH")
    if raw_epoch:
        moment = datetime.fromtimestamp(int(raw_epoch), timezone.utc)
    else:
        moment = datetime.now(timezone.utc)
    return moment.isoformat().replace("+00:00", "Z")


def write_manifest() -> None:
    timestamp = generated_at()
    entries: list[dict[str, object]] = []
    checksum_lines: list[str] = []
    for filename, (label, media_type) in ARTIFACT_METADATA.items():
        path = require_file(ARTIFACTS / filename)
        checksum = digest(path)
        entries.append({
            "name": label, "filename": filename, "type": media_type,
            "label": label, "media_type": media_type,
            "description": ARTIFACT_DESCRIPTIONS[filename],
            "size_bytes": path.stat().st_size, "sha256": checksum,
            "generated_at": timestamp,
            "url": f"https://ADHS.telacore.org/artifacts/{filename}",
        })
        checksum_lines.append(f"{checksum}  {filename}")
    (ARTIFACTS / "downloads.json").write_text(
        json.dumps({"project": "ADHS-Lernpfad", "generated_at": timestamp, "artifacts": entries}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (ARTIFACTS / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-manifest",
        action="store_true",
        help="finalen Runtime-Status erneut kopieren und Manifest aktualisieren",
    )
    parser.add_argument("--status-file", type=Path, default=RUNTIME_STATUS)
    parser.add_argument("--workflow", default="download-exports")
    return parser.parse_args(argv)


def _published_artifacts() -> list[str]:
    names = [*ARTIFACT_METADATA, "downloads.json", "SHA256SUMS.txt"]
    return [
        f"build/artifacts/{name}"
        for name in names
        if (ARTIFACTS / name).is_file()
    ]


def _status_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _safe_error_message(exc: BaseException) -> str:
    return (str(exc) or type(exc).__name__).replace(str(ROOT), ".")[:2000]


def run_build(
    *, status_file: Path = RUNTIME_STATUS, workflow: str = "download-exports",
) -> int:
    status_file = _status_path(status_file)
    managed = status_is_managed()
    if not managed:
        start_run(status_file, workflow, phase="export")
    try:
        update_status(
            status_file,
            status="running",
            phase="export",
            workflow=None if managed else workflow,
        )
        if ARTIFACTS.exists():
            shutil.rmtree(ARTIFACTS)
        ARTIFACTS.mkdir(parents=True)
        build_document_exports()
        copy_generated_sources()
        build_vault_zip()
        build_public_sync_packages()
        copy_graph_artifacts(include_runtime=False)

        copy_graph_artifacts(include_runtime=True, runtime_source=status_file)
        write_manifest()
        artifacts = _published_artifacts()
        if managed:
            update_status(status_file, phase="export", artifacts=artifacts)
        else:
            finish_run(
                status_file,
                success=True,
                phase="success",
                artifacts=artifacts,
            )
        # The status now contains the truthful, existing artifact list. Freeze
        # that final payload into the bundle and recalculate its checksum.
        copy_graph_artifacts(include_runtime=True, runtime_source=status_file)
        write_manifest()
        print(
            f"Downloads: {len(ARTIFACT_METADATA)} Artefakte plus Manifest und Prüfsummen"
        )
        return 0
    except Exception as exc:
        message = _safe_error_message(exc)
        try:
            finish_run(
                status_file,
                success=False,
                phase="export",
                error_class="export_error",
                error_message=message,
                recovery_action="reuse_valid_inputs_and_retry_export",
            )
        except Exception as status_exc:
            print(
                f"Runtime-Status konnte nicht finalisiert werden: {status_exc}",
                file=sys.stderr,
            )
        print(f"Downloadexport fehlgeschlagen: {message}", file=sys.stderr)
        return 1


def refresh_manifest(status_file: Path = RUNTIME_STATUS) -> int:
    status_file = _status_path(status_file)
    try:
        copy_graph_artifacts(include_runtime=True, runtime_source=status_file)
        write_manifest()
        print("Downloadmanifest mit finalem Runtime-Status aktualisiert")
        return 0
    except Exception as exc:
        print(f"Manifest-Aktualisierung fehlgeschlagen: {_safe_error_message(exc)}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.refresh_manifest:
        return refresh_manifest(args.status_file)
    return run_build(status_file=args.status_file, workflow=args.workflow)


if __name__ == "__main__":
    raise SystemExit(main())
