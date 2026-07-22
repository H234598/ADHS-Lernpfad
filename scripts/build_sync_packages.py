#!/usr/bin/env python3
"""Build reproducible ZIP packages for each synchronization platform."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Final
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT: Final = Path(__file__).resolve().parents[1]
SYNC: Final = ROOT / "Sync"
PACKAGE_ROOT: Final = Path("ADHS-Lernpfad-Sync")
FIXED_TIMESTAMP: Final = (2026, 1, 1, 0, 0, 0)

SHARED_FILES: Final = (
    SYNC / "README.md",
    SYNC / "PLAN.md",
    SYNC / "MODES.md",
    SYNC / "CONFIGURATION.md",
    SYNC / "TROUBLESHOOTING.md",
)

PLATFORMS: Final[dict[str, tuple[Path, ...]]] = {
    "Linux": (SYNC / "Linux", SYNC / "Common"),
    "Android": (SYNC / "Android", SYNC / "Common"),
    "Windows": (SYNC / "Windows",),
    "macOS": (SYNC / "macOS", SYNC / "Common"),
    "iOS": (SYNC / "iOS", SYNC / "Common"),
    "BSD": (SYNC / "BSD", SYNC / "Common"),
}


def collect_files(entries: tuple[Path, ...]) -> list[Path]:
    """Collect regular source files from files and directories."""

    selected: set[Path] = set(SHARED_FILES)
    for entry in entries:
        if entry.is_file():
            selected.add(entry)
        elif entry.is_dir():
            selected.update(path for path in entry.rglob("*") if path.is_file())
        else:
            raise FileNotFoundError(f"Sync-Paketquelle fehlt: {entry.relative_to(ROOT)}")
    missing = [path for path in selected if not path.is_file()]
    if missing:
        names = ", ".join(str(path.relative_to(ROOT)) for path in missing)
        raise FileNotFoundError(f"Sync-Paketdateien fehlen: {names}")
    return sorted(selected)


def archive_mode(path: Path) -> int:
    """Return a useful POSIX mode stored in the ZIP metadata."""

    if path.suffix.lower() == ".sh":
        return 0o755
    return 0o644


def write_file(archive: ZipFile, source: Path) -> None:
    """Write one source file with deterministic timestamp and permissions."""

    relative = source.relative_to(ROOT)
    destination = (PACKAGE_ROOT / relative).as_posix()
    info = ZipInfo(destination, date_time=FIXED_TIMESTAMP)
    info.compress_type = ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (archive_mode(source) & 0xFFFF) << 16
    archive.writestr(info, source.read_bytes())


def build_sync_packages(output_dir: Path) -> list[Path]:
    """Build all platform archives and return their paths."""

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    packages: list[Path] = []
    for platform, entries in PLATFORMS.items():
        destination = output_dir / f"ADHS-Lernpfad-Sync-{platform}.zip"
        with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for source in collect_files(entries):
                write_file(archive, source)
        packages.append(destination)
    return packages


def main() -> None:
    """Build packages under build/sync-packages for local and CI use."""

    packages = build_sync_packages(ROOT / "build" / "sync-packages")
    for package in packages:
        print(package.relative_to(ROOT))


if __name__ == "__main__":
    main()
