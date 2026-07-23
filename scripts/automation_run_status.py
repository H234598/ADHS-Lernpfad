#!/usr/bin/env python3
"""Backward-compatible imports for the canonical automation status module.

New scheduler integrations use ``scripts/automation_status.py`` directly.
Graph and export builders keep importing this module so existing call sites do
not need a flag-day migration.
"""

from __future__ import annotations

try:
    from .automation_status import (  # noqa: F401
        DEFAULT_STATUS_PATH,
        FINAL_STATUSES,
        PHASES,
        STATUSES,
        _read_status,
        finish_run,
        restore_status_file,
        start_run,
        status_is_managed,
        update_status,
        utc_now,
        validate_status,
        write_status,
    )
except ImportError:  # pragma: no cover - direct script execution
    from automation_status import (  # type: ignore[no-redef]  # noqa: F401
        DEFAULT_STATUS_PATH,
        FINAL_STATUSES,
        PHASES,
        STATUSES,
        _read_status,
        finish_run,
        restore_status_file,
        start_run,
        status_is_managed,
        update_status,
        utc_now,
        validate_status,
        write_status,
    )


__all__ = [
    "DEFAULT_STATUS_PATH",
    "FINAL_STATUSES",
    "PHASES",
    "STATUSES",
    "finish_run",
    "restore_status_file",
    "start_run",
    "status_is_managed",
    "update_status",
    "utc_now",
    "validate_status",
    "write_status",
]


if __name__ == "__main__":
    status = start_run(DEFAULT_STATUS_PATH, "manual", run_id="manual")
    print(status["run_id"])
