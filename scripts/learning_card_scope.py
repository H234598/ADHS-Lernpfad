"""Deterministische Anwendbarkeit der Lernkarten-Policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

LEARNING_MARKER = "<!-- adhs-daily-unit -->"
MANUAL_MERGE_MARKER = "<!-- manual-merge-required -->"
LEARNING_PREFIXES = ("01-Grundlagen/", "02-Vertiefung/")
SCIENTIFIC_SUPPORT_EXACT = {
    "Glossar.md",
    "Literatur.md",
    "cards/cards.yaml",
    "references.bib",
    "references.json",
}
AUTOMATION_PREFIXES = (".github/", "automation/", "prompts/", "scripts/")
AUTOMATION_EXACT = {
    ".coderabbit.yaml",
    ".codacy.yml",
    "package.json",
    "package-lock.json",
    "requirements-docs.txt",
    "requirements-export.txt",
}


@dataclass(frozen=True)
class ScopeDecision:
    """Dateibasierte Schutzklasse ohne wissenschaftliche Inhaltsbewertung."""

    classification: str
    requires_semantic_review: bool
    manual_merge_required: bool
    learning_provenance: bool
    manual_merge_marker: bool
    learning_paths: tuple[str, ...]
    scientific_support_paths: tuple[str, ...]
    automation_paths: tuple[str, ...]
    reasons: tuple[str, ...]


def _normalize_path(value: Any) -> str:
    path = str(value or "").strip()
    while path.startswith("./"):
        path = path[2:]
    return path


def _candidate_paths(raw_file: dict[str, Any]) -> tuple[str, ...]:
    paths = {
        _normalize_path(raw_file.get("filename")),
        _normalize_path(raw_file.get("previous_filename")),
    }
    paths.discard("")
    return tuple(sorted(paths))


def _is_learning_path(path: str) -> bool:
    return path.endswith(".md") and path.startswith(LEARNING_PREFIXES)


def _is_scientific_support_path(path: str) -> bool:
    return path in SCIENTIFIC_SUPPORT_EXACT or (
        path.startswith("references/")
        and path.endswith(".md")
        and path != "references/README.md"
    )


def _is_automation_path(path: str) -> bool:
    return path in AUTOMATION_EXACT or path.startswith(AUTOMATION_PREFIXES)


def classify_pull_request(
    *,
    files: list[dict[str, Any]],
    head_ref: str,
    body: str,
) -> ScopeDecision:
    """Anwendbarkeit, Provenienz und sensible Dateiklassen bestimmen."""

    learning: set[str] = set()
    scientific: set[str] = set()
    automation: set[str] = set()
    for raw_file in files:
        if not isinstance(raw_file, dict):
            continue
        for path in _candidate_paths(raw_file):
            if _is_learning_path(path):
                learning.add(path)
            if _is_scientific_support_path(path):
                scientific.add(path)
            if _is_automation_path(path):
                automation.add(path)

    provenance = head_ref.startswith("agent/einheit-") or LEARNING_MARKER in body
    manual_marker = MANUAL_MERGE_MARKER in body
    semantic = bool(learning or scientific)
    manual = bool(automation)

    if semantic and manual:
        classification = "learning_card_sensitive"
    elif learning:
        classification = "learning_card"
    elif scientific:
        classification = "scientific_support"
    elif manual:
        classification = "automation_only"
    else:
        classification = "not_applicable"

    reasons: list[str] = []
    if learning:
        reasons.append(f"{len(learning)} Lernkartendatei(en) betroffen.")
    if scientific:
        reasons.append(f"{len(scientific)} wissenschaftliche Begleitdatei(en) betroffen.")
    if automation:
        reasons.append(
            f"{len(automation)} automations- oder sicherheitssensitive Datei(en) betroffen."
        )
    if semantic and not provenance:
        reasons.append(
            "Wissenschaftlicher Scope ohne Einheiten-Provenienz; die semantische "
            "Prüfung bleibt fail-closed anwendbar."
        )
    if provenance and not semantic:
        reasons.append(
            "Einheiten-Provenienz ohne wissenschaftliche Dateiänderung aktiviert "
            "keine semantische Prüfung."
        )
    if manual and not manual_marker:
        reasons.append(
            "Sensible Automation benötigt den Marker manual-merge-required und "
            "eine bewusste Infrastrukturprüfung."
        )
    if not reasons:
        reasons.append("Keine Lernkarte oder wissenschaftliche Begleitdatei betroffen.")

    return ScopeDecision(
        classification=classification,
        requires_semantic_review=semantic,
        manual_merge_required=manual,
        learning_provenance=provenance,
        manual_merge_marker=manual_marker,
        learning_paths=tuple(sorted(learning)),
        scientific_support_paths=tuple(sorted(scientific)),
        automation_paths=tuple(sorted(automation)),
        reasons=tuple(reasons),
    )
