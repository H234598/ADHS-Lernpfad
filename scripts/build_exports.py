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
import subprocess  # nosec B404 -- subprocess is restricted to the resolved pandoc executable
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
GRAPH_BUILD: Final = BUILD / "knowledge-graph"

ARTIFACT_FILENAMES: Final[dict[str, str]] = {
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

MEDIA_TYPE_ZIP: Final = "application/zip"
MEDIA_TYPE_JSON: Final = "application/json"
MEDIA_TYPE_MARKDOWN: Final = "text/markdown"

COMBINED: Final = BUILD / ARTIFACT_FILENAMES["combined_markdown"]
RUNTIME_STATUS: Final = BUILD / ARTIFACT_FILENAMES["runtime_status"]

ARTIFACT_METADATA: Final[dict[str, tuple[str, str]]] = {
    ARTIFACT_FILENAMES["pdf"]: ("PDF", "application/pdf"),
    ARTIFACT_FILENAMES["epub"]: ("EPUB 3", "application/epub+zip"),
    ARTIFACT_FILENAMES["html"]: ("Offline-HTML", "text/html"),
    ARTIFACT_FILENAMES["latex"]: ("LaTeX", "application/x-tex"),
    ARTIFACT_FILENAMES["combined_markdown"]: ("Markdown", MEDIA_TYPE_MARKDOWN),
    ARTIFACT_FILENAMES["obsidian_vault"]: ("Obsidian Vault", MEDIA_TYPE_ZIP),
    ARTIFACT_FILENAMES["anki"]: ("Anki", "application/octet-stream"),
    ARTIFACT_FILENAMES["references_bib"]: ("BibTeX", "application/x-bibtex"),
    ARTIFACT_FILENAMES["references_json"]: ("CSL JSON", MEDIA_TYPE_JSON),
    ARTIFACT_FILENAMES["sync_linux"]: ("Sync-Paket Linux", MEDIA_TYPE_ZIP),
    ARTIFACT_FILENAMES["sync_android"]: ("Sync-Paket Android", MEDIA_TYPE_ZIP),
    ARTIFACT_FILENAMES["sync_windows"]: ("Sync-Paket Windows", MEDIA_TYPE_ZIP),
    ARTIFACT_FILENAMES["sync_macos"]: ("Sync-Paket macOS", MEDIA_TYPE_ZIP),
    ARTIFACT_FILENAMES["sync_ios"]: ("Sync-Paket iOS/iPadOS", MEDIA_TYPE_ZIP),
    ARTIFACT_FILENAMES["sync_bsd"]: ("Sync-Paket BSD", MEDIA_TYPE_ZIP),
    ARTIFACT_FILENAMES["knowledge_graph_json"]: (
        "Wissensgraph JSON",
        MEDIA_TYPE_JSON,
    ),
    ARTIFACT_FILENAMES["knowledge_graph_graphml"]: (
        "Wissensgraph GraphML",
        "application/graphml+xml",
    ),
    ARTIFACT_FILENAMES["knowledge_graph_mermaid"]: (
        "Wissensgraph Mermaid",
        "text/plain",
    ),
    ARTIFACT_FILENAMES["graph_report_markdown"]: (
        "Graphbericht Markdown",
        MEDIA_TYPE_MARKDOWN,
    ),
    ARTIFACT_FILENAMES["graph_report_json"]: (
        "Graphbericht JSON",
        MEDIA_TYPE_JSON,
    ),
    ARTIFACT_FILENAMES["runtime_status"]: (
        "Generator-Laufstatus",
        MEDIA_TYPE_JSON,
    ),
}

ARTIFACT_DESCRIPTIONS: Final[dict[str, str]] = {
    ARTIFACT_FILENAMES["pdf"]: "Gesetzte Lesefassung des vollständigen Lernpfads.",
    ARTIFACT_FILENAMES["epub"]: "Anpassbare EPUB-3-Fassung für E-Reader.",
    ARTIFACT_FILENAMES["html"]: "Eigenständige Offline-HTML-Fassung.",
    ARTIFACT_FILENAMES["latex"]: "Von Pandoc erzeugter LaTeX-Quelltext.",
    ARTIFACT_FILENAMES["combined_markdown"]: (
        "Zusammengeführte Markdown-Fassung aller Kapitel."
    ),
    ARTIFACT_FILENAMES["obsidian_vault"]: "Reproduzierbares Obsidian-Vault-Archiv.",
    ARTIFACT_FILENAMES["anki"]: "Anki-Lernkartendeck.",
    ARTIFACT_FILENAMES["references_bib"]: "Bibliografie im BibTeX-Format.",
    ARTIFACT_FILENAMES["references_json"]: "Bibliografie im CSL-JSON-Format.",
    ARTIFACT_FILENAMES["sync_linux"]: "Installations- und Sync-Paket für Linux.",
    ARTIFACT_FILENAMES["sync_android"]: (
        "Installations- und Sync-Paket für Android/Termux."
    ),
    ARTIFACT_FILENAMES["sync_windows"]: (
        "Installations- und Sync-Paket für Windows."
    ),
    ARTIFACT_FILENAMES["sync_macos"]: "Installations- und Sync-Paket für macOS.",
    ARTIFACT_FILENAMES["sync_ios"]: (
        "Installations- und Sync-Paket für iOS/iPadOS mit iSH."
    ),
    ARTIFACT_FILENAMES["sync_bsd"]: (
        "Installations- und Sync-Paket für BSD/TrueNAS."
    ),
    ARTIFACT_FILENAMES["knowledge_graph_json"]: (
        "Kanonischer, typisierter Wissensgraph mit Qualitätsdaten."
    ),
    ARTIFACT_FILENAMES["knowledge_graph_graphml"]: (
        "GraphML-Austauschdatei für Graphwerkzeuge."
    ),
    ARTIFACT_FILENAMES["knowledge_graph_mermaid"]: (
        "Mermaid-Diagnoseansicht des Wissensgraphen."
    ),
    ARTIFACT_FILENAMES["graph_report_markdown"]: (
        "Menschenlesbarer Wissensgraph-Qualitätsbericht."
    ),
    ARTIFACT_FILENAMES["graph_report_json"]: (
        "Maschinenlesbarer Wissensgraph-Qualitätsbericht."
    ),
    ARTIFACT_FILENAMES["runtime_status"]: (
        "Finaler schema-validierter Status des Generatorlaufs."
    ),
}

VAULT_ROOT_FILES: Final = (
    "README.md",
    "00-Einfuehrung.md",
    "Glossar.md",
    "Literatur.md",
    "ROADMAP.md",
    "DOWNLOADS.md",
    ARTIFACT_FILENAMES["references_bib"],
    ARTIFACT_FILENAMES["references_json"],
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
    """Run the one explicitly supported external exporter with fixed argv semantics."""

    if not command or command[0] != "pandoc":
        raise ValueError("Nur der interne Pandoc-Export ist als Subprozess erlaubt")
    executable = shutil.which("pandoc")
    if executable is None:
        raise FileNotFoundError("pandoc wurde im kontrollierten PATH nicht gefunden")
    subprocess.run(  # nosec B603 -- executable is allowlisted and resolved; shell is never used
        [executable, *command[1:]], cwd=ROOT, check=True
    )


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
        str(require_file(COMBINED)),
        "--standalone",
        "--toc",
        "--citeproc",
        f"--bibliography={require_file(ROOT / ARTIFACT_FILENAMES['references_bib'])}",
        "--metadata=title:ADHS-Lernpfad",
        "--metadata=lang:de-DE",
        "--resource-path=.:figures:assets",
    ]


def build_document_exports() -> None:
    common = common_pandoc_args()
    run(
        [
            "pandoc",
            *common,
            "--to=epub3",
            "--output",
            str(ARTIFACTS / ARTIFACT_FILENAMES["epub"]),
        ]
    )
    run(
        [
            "pandoc",
            *common,
            "--to=html5",
            "--embed-resources",
            "--output",
            str(ARTIFACTS / ARTIFACT_FILENAMES["html"]),
        ]
    )
    run(
        [
            "pandoc",
            *common,
            "--output",
            str(ARTIFACTS / ARTIFACT_FILENAMES["latex"]),
        ]
    )
    run(
        [
            "pandoc",
            *common,
            "--pdf-engine=lualatex",
            "--variable=mainfont:DejaVu Serif",
            "--variable=sansfont:DejaVu Sans",
            "--variable=monofont:DejaVu Sans Mono",
            "--output",
            str(ARTIFACTS / ARTIFACT_FILENAMES["pdf"]),
        ]
    )


def copy_generated_sources() -> None:
    sources = {
        COMBINED: ARTIFACTS / ARTIFACT_FILENAMES["combined_markdown"],
        ROOT / ARTIFACT_FILENAMES["references_bib"]: (
            ARTIFACTS / ARTIFACT_FILENAMES["references_bib"]
        ),
        ROOT / ARTIFACT_FILENAMES["references_json"]: (
            ARTIFACTS / ARTIFACT_FILENAMES["references_json"]
        ),
        BUILD / ARTIFACT_FILENAMES["anki"]: ARTIFACTS / ARTIFACT_FILENAMES["anki"],
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
    destination = ARTIFACTS / ARTIFACT_FILENAMES["obsidian_vault"]
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
        ARTIFACT_FILENAMES["knowledge_graph_json"]: (
            GRAPH_BUILD / ARTIFACT_FILENAMES["knowledge_graph_json"]
        ),
        ARTIFACT_FILENAMES["knowledge_graph_graphml"]: (
            GRAPH_BUILD / ARTIFACT_FILENAMES["knowledge_graph_graphml"]
        ),
        ARTIFACT_FILENAMES["knowledge_graph_mermaid"]: (
            GRAPH_BUILD / ARTIFACT_FILENAMES["knowledge_graph_mermaid"]
        ),
        ARTIFACT_FILENAMES["graph_report_markdown"]: (
            GRAPH_BUILD / ARTIFACT_FILENAMES["graph_report_markdown"]
        ),
        ARTIFACT_FILENAMES["graph_report_json"]: (
            GRAPH_BUILD / ARTIFACT_FILENAMES["graph_report_json"]
        ),
    }
    if include_runtime:
        sources[ARTIFACT_FILENAMES["runtime_status"]] = runtime_source
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
        entries.append(
            {
                "name": label,
                "filename": filename,
                "type": media_type,
                "label": label,
                "media_type": media_type,
                "description": ARTIFACT_DESCRIPTIONS[filename],
                "size_bytes": path.stat().st_size,
                "sha256": checksum,
                "generated_at": timestamp,
                "url": f"https://ADHS.telacore.org/artifacts/{filename}",
            }
        )
        checksum_lines.append(f"{checksum}  {filename}")
    (ARTIFACTS / "downloads.json").write_text(
        json.dumps(
            {
                "project": "ADHS-Lernpfad",
                "generated_at": timestamp,
                "artifacts": entries,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (ARTIFACTS / "SHA256SUMS.txt").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )


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
                phase="complete",
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
        print(
            f"Manifest-Aktualisierung fehlgeschlagen: {_safe_error_message(exc)}",
            file=sys.stderr,
        )
        return 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.refresh_manifest:
        return refresh_manifest(args.status_file)
    return run_build(status_file=args.status_file, workflow=args.workflow)


if __name__ == "__main__":
    raise SystemExit(main())
