#!/usr/bin/env python3
"""Single executable source for the documented learning-unit word limits."""

from __future__ import annotations

MIN_WORDS = 800
TARGET_MIN_WORDS = 1200
TARGET_MAX_WORDS = 2500
MAX_WORDS = 3000
LEGACY_TARGET_WARNING_EXEMPTIONS = frozenset(range(1, 11))


def evaluate_word_count(number: int, words: int, path: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if words < MIN_WORDS:
        errors.append(f"{path}: nur {words} Fließtextwörter; mindestens {MIN_WORDS} erforderlich")
    if words > MAX_WORDS:
        errors.append(f"{path}: {words} Fließtextwörter; Maximum sind {MAX_WORDS}")
    if number not in LEGACY_TARGET_WARNING_EXEMPTIONS and not errors:
        if words < TARGET_MIN_WORDS:
            warnings.append(
                f"{path}: {words} Wörter; unter dem Zielbereich von {TARGET_MIN_WORDS} Wörtern"
            )
        elif words > TARGET_MAX_WORDS:
            warnings.append(
                f"{path}: {words} Wörter; über dem Zielbereich von {TARGET_MAX_WORDS} Wörtern"
            )
    return errors, warnings
