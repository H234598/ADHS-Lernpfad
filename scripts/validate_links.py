#!/usr/bin/env python3
"""Obsidian-Wikilinks einschließlich Aliasen, Unterordnern und Ankern prüfen."""

from pathlib import Path

from content_links import validate_all

ROOT = Path(__file__).resolve().parents[1]
errors = validate_all(ROOT)

if errors:
    print("Linkvalidierung fehlgeschlagen:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("Linkvalidierung erfolgreich: alle Obsidian-Wikilinks sind eindeutig auflösbar")
