#!/usr/bin/env python3
"""Build the export-ready combined Markdown document with runtime telemetry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from automation_run_status import (
    DEFAULT_STATUS_PATH, finish_run, start_run, status_is_managed, update_status,
)
from content_links import convert_for_combined

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("build/ADHS-Lernpfad-Gesamtdokument.md")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status-file", type=Path, default=ROOT / DEFAULT_STATUS_PATH)
    parser.add_argument("--workflow", default="combined-document")
    return parser.parse_args(argv)


def _load_paths(root: Path) -> tuple[list[Path], dict[str, int]]:
    index_path = root / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    chapters = index.get("chapters")
    if not isinstance(chapters, list):
        raise ValueError("index.json: chapters muss eine Liste sein")
    paths = [root / "00-Einfuehrung.md"]
    for position, item in enumerate(chapters):
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError(f"index.json: chapters[{position}].path fehlt")
        paths.append(root / item["path"])
    paths.extend([root / "Glossar.md", root / "Literatur.md"])
    missing = [path for path in paths if not path.is_file()]
    if missing:
        relative = ", ".join(path.relative_to(root).as_posix() for path in missing)
        raise FileNotFoundError(f"Eingabedokumente fehlen: {relative}")
    references = root / "references"
    source_count = sum(
        path.is_file() and path.name != "README.md"
        for path in references.glob("*.md")
    ) if references.is_dir() else 0
    return paths, {
        "documents": len(paths), "chapters": len(chapters), "sources": source_count,
    }


def build_combined(root: Path = ROOT) -> tuple[Path, dict[str, int]]:
    """Create the combined document and return output plus content metrics."""

    paths, metrics = _load_paths(root)
    included_paths = {path.resolve() for path in paths}
    parts = [
        "---\n"
        "title: ADHS-Lernpfad – Gesamtdokument\n"
        "lang: de\n"
        "bibliography: references.bib\n"
        "link-citations: true\n"
        "---\n"
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
        text = convert_for_combined(text, path, root, included_paths)
        parts.extend([text.strip(), "\n---\n"])
    output = root / OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    return output, metrics


def run_build(
    *, root: Path = ROOT, status_file: Path | None = None,
    workflow: str = "combined-document",
) -> int:
    target = status_file or root / DEFAULT_STATUS_PATH
    managed = status_is_managed()
    if not managed:
        start_run(target, workflow)
    phase = "load_content"
    try:
        update_status(
            target, status="running", phase=phase,
            workflow=None if managed else workflow,
        )
        _paths, metrics = _load_paths(root)
        update_status(target, metrics=metrics)

        phase = "export"
        update_status(target, status="running", phase=phase)
        # Reuse the checked inputs in the public builder. A second read is
        # intentional: conversion sees the exact bytes written by producers.
        output, metrics = build_combined(root)
        artifact = output.relative_to(root).as_posix()
        update_status(target, metrics=metrics, artifacts=[artifact])
        if not managed:
            finish_run(
                target, success=True, phase="success", metrics=metrics,
                artifacts=[artifact],
            )
        return 0
    except Exception as exc:
        error_class = "content_error" if phase == "load_content" else "export_error"
        recovery = "fix_content_and_retry" if phase == "load_content" else "retry_combined_export"
        message = (str(exc) or type(exc).__name__).replace(str(root), ".")[:2000]
        try:
            finish_run(
                target, success=False, phase=phase, error_class=error_class,
                error_message=message, recovery_action=recovery,
            )
        except Exception as status_exc:
            print(f"Runtime-Status konnte nicht finalisiert werden: {status_exc}", file=sys.stderr)
        print(f"Gesamtdokument fehlgeschlagen ({phase}): {message}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    exit_code = run_build(
        root=ROOT, status_file=args.status_file, workflow=args.workflow,
    )
    if exit_code == 0:
        print("Gesamtdokument mit exportfähigen internen Links erstellt")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
