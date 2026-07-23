#!/usr/bin/env python3
"""Prepare a validated status snapshot for the ``automation-status`` branch.

This script never performs Git operations.  The trusted ``workflow_run``
workflow validates an untrusted diagnostic artifact with this script, then
copies only the resulting status JSON and redacted Markdown report into an
orphan, append-oriented branch.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
from typing import Any

try:
    from .automation_status import (
        AutomationStatusError,
        read_status,
        render_diagnostic,
        validate_status,
    )
    from .validate_runtime_status import validate_file
except ImportError:  # pragma: no cover - direct command-line use
    from automation_status import (
        AutomationStatusError,
        read_status,
        render_diagnostic,
        validate_status,
    )
    from validate_runtime_status import validate_file


MAX_STATUS_BYTES = 1_048_576
STATUS_BRANCH_README = """# Persistente Automationsstatus

Dieser orphan Branch wird ausschließlich durch den vertrauenswürdigen
`Persist automation status`-Workflow aktualisiert. Er enthält keine Lerninhalte
und keinen ausführbaren Code.

Kanonische Pfade:

```text
automation/status/<workflow>/<run_id>.json
automation/status/<workflow>/<run_id>.md
automation/status/<workflow>/latest.json
automation/status/<workflow>/latest.md
```

Statusdateien werden vor dem Commit gegen `automation/run-status.schema.json`
und die semantischen Invarianten validiert. Erfolgreiche Läufe werden 30 Tage,
fehlgeschlagene oder blockierte Läufe 90 Tage aufbewahrt; `latest.*` bleibt
dauerhaft erhalten.
"""


def discover_status(input_root: Path) -> Path:
    """Find exactly one regular runtime status below a downloaded artifact."""

    root = Path(input_root)
    candidates = sorted(
        path
        for path in root.rglob("runtime-status.json")
        if path.is_file() and not path.is_symlink()
    )
    if len(candidates) != 1:
        raise ValueError(
            f"Genau eine runtime-status.json erwartet, gefunden: {len(candidates)}"
        )
    return candidates[0]


def _safe_output_path(root: Path, workflow: str, filename: str) -> Path:
    destination = root / "automation" / "status" / workflow / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def prepare_snapshot(
    source: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Validate and copy one run plus its human diagnosis."""

    source = Path(source)
    output_root = Path(output_root)
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"Statusquelle ist keine reguläre Datei: {source}")
    if source.stat().st_size > MAX_STATUS_BYTES:
        raise ValueError(
            f"Statusquelle überschreitet {MAX_STATUS_BYTES} Byte: {source}"
        )
    errors = validate_file(source)
    if errors:
        raise ValueError("Statusquelle ist ungültig: " + "; ".join(errors))
    status = read_status(source)
    semantic_errors = validate_status(status)
    if semantic_errors:
        raise ValueError("Statusquelle verletzt Invarianten: " + "; ".join(semantic_errors))

    workflow = status["workflow"]
    run_id = status["run_id"]
    payload = json.dumps(
        status,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    diagnosis = render_diagnostic(status)
    for filename, content in (
        (f"{run_id}.json", payload),
        (f"{run_id}.md", diagnosis),
        ("latest.json", payload),
        ("latest.md", diagnosis),
    ):
        _safe_output_path(output_root, workflow, filename).write_text(
            content,
            encoding="utf-8",
        )
    (output_root / "README.md").write_text(
        STATUS_BRANCH_README,
        encoding="utf-8",
    )
    (output_root / ".nojekyll").touch()
    return status


def _status_order(
    status: dict[str, Any],
) -> tuple[datetime, datetime, int, str]:
    """Return a stable order for independent ``workflow_run`` deliveries."""

    return (
        datetime.fromisoformat(status["created_at"].replace("Z", "+00:00")),
        datetime.fromisoformat(status["updated_at"].replace("Z", "+00:00")),
        status["revision"],
        status["run_id"],
    )


def _write_status_pair(
    status: dict[str, Any],
    json_path: Path,
    markdown_path: Path,
) -> None:
    payload = json.dumps(
        status,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    json_path.write_text(payload, encoding="utf-8")
    markdown_path.write_text(render_diagnostic(status), encoding="utf-8")


def merge_snapshot(
    snapshot_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Merge one validated snapshot without regressing run or latest revisions."""

    snapshot_root = Path(snapshot_root)
    output_root = Path(output_root)
    run_files = sorted(
        path
        for path in (snapshot_root / "automation" / "status").glob("*/*.json")
        if path.name != "latest.json" and path.is_file() and not path.is_symlink()
    )
    if len(run_files) != 1:
        raise ValueError(
            f"Genau eine Laufstatusdatei im Snapshot erwartet, gefunden: {len(run_files)}"
        )
    incoming = read_status(run_files[0])
    workflow = incoming["workflow"]
    run_id = incoming["run_id"]
    destination = output_root / "automation" / "status" / workflow
    destination.mkdir(parents=True, exist_ok=True)

    run_json = destination / f"{run_id}.json"
    selected_run = incoming
    if run_json.exists():
        existing_run = read_status(run_json)
        if existing_run["run_id"] != run_id or existing_run["workflow"] != workflow:
            raise ValueError(f"Kollidierende Laufstatusdatei: {run_json}")
        if existing_run["revision"] > incoming["revision"]:
            selected_run = existing_run
    _write_status_pair(
        selected_run,
        run_json,
        destination / f"{run_id}.md",
    )

    latest_json = destination / "latest.json"
    selected_latest = incoming
    if latest_json.exists():
        existing_latest = read_status(latest_json)
        if _status_order(existing_latest) > _status_order(incoming):
            selected_latest = existing_latest
    _write_status_pair(
        selected_latest,
        latest_json,
        destination / "latest.md",
    )

    (output_root / "README.md").write_text(
        STATUS_BRANCH_README,
        encoding="utf-8",
    )
    (output_root / ".nojekyll").touch()
    return incoming


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path)
    source.add_argument("--input-root", type=Path)
    source.add_argument("--snapshot-root", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--clean-output",
        action="store_true",
        help="vorherigen temporären Snapshot vollständig ersetzen",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.snapshot_root is not None:
        if args.clean_output:
            print("Statuspersistenz abgewiesen: --clean-output ist beim Merge unzulässig")
            return 1
        try:
            status = merge_snapshot(args.snapshot_root, args.output_root)
        except (AutomationStatusError, OSError, ValueError) as exc:
            print(f"Statuspersistenz abgewiesen: {exc}")
            return 1
        print(render_diagnostic(status), end="")
        return 0

    source = args.input or discover_status(args.input_root)
    if args.clean_output and args.output_root.exists():
        shutil.rmtree(args.output_root)
    try:
        status = prepare_snapshot(source, args.output_root)
    except (AutomationStatusError, OSError, ValueError) as exc:
        print(f"Statuspersistenz abgewiesen: {exc}")
        return 1
    print(render_diagnostic(status), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
