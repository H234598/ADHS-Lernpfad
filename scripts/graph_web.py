#!/usr/bin/env python3
"""Webaufbereitung und barrierearme Fallbackansicht des Wissensgraphen."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit

from content_links import scan_wikilinks

GRAPH_RELATIVE_CANDIDATES = (
    Path("build/knowledge-graph/knowledge-graph.json"),
    Path("build/knowledge-graph.json"),
)
RUNTIME_STATUS_CANDIDATES = (
    Path("build/runtime-status.json"),
    Path("automation/runtime-status.json"),
)
FALLBACK_START = "<!-- knowledge-graph-fallback:start -->"
FALLBACK_END = "<!-- knowledge-graph-fallback:end -->"
RUNTIME_START = "<!-- knowledge-graph-runtime:start -->"
RUNTIME_END = "<!-- knowledge-graph-runtime:end -->"

STATUS_LABELS = {
    "ok": "vorhanden",
    "planned": "geplant",
    "missing": "Ziel fehlt",
    "missing-document": "Ziel fehlt",
    "missing-heading": "Abschnitt fehlt",
    "missing-reference": "Quelle fehlt",
    "ambiguous": "mehrdeutig",
    "malformed": "ungültig",
    "excluded-target": "nicht in der Webfassung",
}
LIFECYCLE_LABELS = {
    "planned": "geplant",
    "in_progress": "in Arbeit",
    "published": "veröffentlicht",
    "not_applicable": "nicht anwendbar",
}
RUN_STATUS_LABELS = {
    "created": "angelegt",
    "running": "läuft",
    "success": "OK",
    "failed": "fehlgeschlagen",
    "blocked": "blockiert",
    "recovering": "Wiederherstellung läuft",
    "recovered": "wiederhergestellt",
    "unknown": "unbekannt",
}


def graph_json_path(root: Path) -> Path | None:
    for relative in GRAPH_RELATIVE_CANDIDATES:
        candidate = root / relative
        if candidate.is_file():
            return candidate
    return None


def load_graph(root: Path) -> dict[str, object]:
    path = graph_json_path(root)
    if path is None:
        return {"nodes": [], "edges": [], "issues": [], "stats": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {"nodes": [], "edges": [], "issues": []}


def load_runtime_status(root: Path) -> dict[str, object]:
    for relative in RUNTIME_STATUS_CANDIDATES:
        candidate = root / relative
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"status": "unknown", "phase": "unreadable"}
        return data if isinstance(data, dict) else {"status": "unknown", "phase": "invalid"}
    return {"status": "unknown", "phase": "not_available"}


def _as_list(value: object) -> list[dict[str, object]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _node_status(node: dict[str, object]) -> str:
    status = str(node.get("graph_status") or node.get("link_status") or "ok")
    if node.get("planned") is True or (
        node.get("exists") is False and str(node.get("type")) == "planned"
    ):
        return "planned"
    if str(node.get("type")) == "placeholder":
        return str(node.get("issue_code") or "missing-document")
    return status


def _lifecycle_status(node: dict[str, object]) -> str:
    if str(node.get("type")) == "placeholder":
        return "not_applicable"
    value = str(node.get("lifecycle_status") or "")
    if value in LIFECYCLE_LABELS:
        return value
    return "planned" if node.get("planned") is True else "published"


def _format_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value:
        return "nicht verfügbar"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    zone_label = ""
    if parsed.utcoffset() is not None:
        parsed = parsed.astimezone(timezone.utc)
        zone_label = " UTC"
    return parsed.strftime("%d.%m.%Y, %H:%M:%S") + zone_label


def _special_occurrences(
    data: dict[str, object],
) -> dict[tuple[str, str], tuple[str, str]]:
    """Index non-OK links by their exact source occurrence.

    Exact `(path, raw)` matching avoids collisions between equal filenames in
    different directories and prevents a broken heading from poisoning every
    otherwise valid link to the same document.
    """

    result: dict[tuple[str, str], tuple[str, str]] = {}
    for edge in _as_list(data.get("edges")):
        status = str(edge.get("status") or "ok")
        if status == "ok" or status not in STATUS_LABELS:
            continue
        target_id = str(edge.get("target") or "")
        for occurrence in _as_list(edge.get("occurrences")):
            path = str(occurrence.get("path") or "").replace("\\", "/")
            raw = str(occurrence.get("raw") or "")
            if path and raw:
                result[(path, raw)] = (status, target_id)
    return result


def annotate_special_wikilinks(text: str, source: Path, root: Path) -> str:
    """Geplante oder defekte Wikilinks vor der normalen Konvertierung sichtbar ersetzen."""

    special = _special_occurrences(load_graph(root))
    if not special:
        return text
    try:
        source_path = source.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        source_path = source.as_posix()
    lines = text.splitlines()
    output: list[str] = []
    cursor = 0
    for occurrence in scan_wikilinks(text, source):
        line = lines[occurrence.line - 1] if 0 < occurrence.line <= len(lines) else ""
        if line.startswith("    ") or line.startswith("\t"):
            continue
        resolved = special.get((source_path, occurrence.raw))
        if resolved is None:
            continue
        status, node_id = resolved
        status_label = STATUS_LABELS[status]
        css_status = re.sub(r"[^a-z0-9-]+", "-", status.casefold()).strip("-")
        badge = (
            f'<span class="kg-link__badge" aria-hidden="true">{escape(status_label)}</span>'
            f'<span class="visually-hidden"> ({escape(status_label)})</span>'
        )
        embed_hint = (
            '<span class="visually-hidden">Einbettung: </span>'
            if occurrence.embed else ""
        )
        if status == "planned":
            href = "/knowledge-graph/?node=" + quote(node_id or occurrence.target, safe="")
            replacement = (
                f'<a class="kg-link kg-link--{css_status}" href="{href}" '
                f'data-kg-status="{escape(status, quote=True)}">'
                f"{embed_hint}{escape(occurrence.label)}{badge}</a>"
            )
        else:
            replacement = (
                f'<span class="kg-link kg-link--{css_status}" role="note" '
                f'data-kg-status="{escape(status, quote=True)}">'
                f"{embed_hint}{escape(occurrence.label)}{badge}</span>"
            )
        output.extend([text[cursor:occurrence.start], replacement])
        cursor = occurrence.end
    if not output:
        return text
    output.append(text[cursor:])
    return "".join(output)


def _node_url(node: dict[str, object]) -> str | None:
    url = node.get("url")
    if isinstance(url, str) and url.strip():
        candidate = url.strip()
        parsed = urlsplit(candidate)
        decoded_path = unquote(parsed.path)
        if (
            candidate.startswith("/")
            and not candidate.startswith("//")
            and not parsed.scheme
            and not parsed.netloc
            and "\\" not in candidate
            and not any(ord(char) < 32 for char in candidate)
            and not any(part in {".", ".."} for part in Path(decoded_path).parts)
        ):
            return candidate
        return None
    path = node.get("path")
    if not isinstance(path, str) or not path.endswith(".md"):
        return None
    without_suffix = path[:-3]
    if without_suffix.endswith("/README"):
        without_suffix = without_suffix[:-7]
    return "/" + without_suffix.strip("/") + "/"


def render_fallback_markdown(data: dict[str, object]) -> str:
    nodes = sorted(
        _as_list(data.get("nodes")),
        key=lambda node: (str(node.get("type") or ""), str(node.get("label") or node.get("id") or "").casefold()),
    )
    edges = _as_list(data.get("edges"))
    issues = _as_list(data.get("issues"))
    node_types = Counter(str(node.get("type") or "unbekannt") for node in nodes)
    edge_types = Counter(str(edge.get("type") or "unbekannt") for edge in edges)
    statuses = Counter(_node_status(node) for node in nodes)
    statuses.update(str(issue.get("status") or issue.get("code") or "problem") for issue in issues)
    lifecycles = Counter(_lifecycle_status(node) for node in nodes)

    lines = [
        "## Semantische Graphansicht",
        "",
        "Diese Tabellen sind die vollständige textuelle Alternative zur interaktiven Darstellung und bleiben auch ohne JavaScript verfügbar.",
        "",
        f"**{len(nodes)} Knoten · {len(edges)} Beziehungen · {len(issues)} gemeldete Probleme**",
        "",
        "### Kennzahlen",
        "",
        "| Kategorie | Anzahl |",
        "|---|---:|",
    ]
    lines.extend(f"| Knoten: `{escape(kind)}` | {count} |" for kind, count in sorted(node_types.items()))
    lines.extend(f"| Beziehung: `{escape(kind)}` | {count} |" for kind, count in sorted(edge_types.items()))
    lines.extend(f"| Status: `{escape(kind)}` | {count} |" for kind, count in sorted(statuses.items()) if kind != "ok")
    lines.extend(
        f"| Lebenszyklus: {escape(LIFECYCLE_LABELS.get(kind, kind))} | {count} |"
        for kind, count in sorted(lifecycles.items())
    )

    lines.extend(["", "### Link- und Strukturprobleme", ""])
    if issues:
        lines.extend([
            '<table class="knowledge-graph-issues">',
            "<thead><tr><th>Status</th><th>Ziel</th><th>Fundstelle</th><th>Hinweis</th></tr></thead>",
            "<tbody>",
        ])
        for issue in issues:
            status = str(issue.get("status") or issue.get("code") or issue.get("type") or "Problem")
            target = str(issue.get("requested_target") or issue.get("target") or issue.get("target_id") or "—")
            path = str(issue.get("path") or issue.get("source_path") or "—")
            line = issue.get("line")
            location = f"{path}:{line}" if line else path
            message = str(issue.get("message") or issue.get("detail") or "—")
            lines.append(
                "<tr>"
                f"<td><strong>{escape(STATUS_LABELS.get(status, status))}</strong></td>"
                f"<td><code>{escape(target)}</code></td>"
                f"<td><code>{escape(location)}</code></td>"
                f"<td>{escape(message)}</td>"
                "</tr>"
            )
        lines.extend(["</tbody></table>"])
    else:
        lines.append("Keine ungeklärten internen Link- oder Strukturprobleme im aktuellen Build.")

    lines.extend([
        "", "### Knotenverzeichnis", "",
        '<div class="knowledge-graph-table-wrap">',
        '<table data-kg-node-table>',
        "<thead><tr><th>Knoten</th><th>Typ</th><th>Graphstatus</th>"
        "<th>Lebenszyklus</th><th>Pfad oder ID</th></tr></thead>",
        "<tbody>",
    ])
    for node in nodes:
        label = str(node.get("label") or node.get("title") or node.get("id") or "Unbenannt")
        node_type = str(node.get("type") or "document")
        status = _node_status(node)
        lifecycle = _lifecycle_status(node)
        identifier = str(node.get("path") or node.get("id") or "—")
        url = _node_url(node)
        shown_label = (
            f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'
            if url and status == "ok" else escape(label)
        )
        lines.append(
            f'<tr data-kg-node-row data-node-id="{escape(str(node.get("id") or ""), quote=True)}" '
            f'data-node-type="{escape(node_type, quote=True)}" '
            f'data-node-status="{escape(status, quote=True)}" '
            f'data-node-lifecycle="{escape(lifecycle, quote=True)}">'
            f"<td>{shown_label}</td><td><code>{escape(node_type)}</code></td>"
            f"<td>{escape(STATUS_LABELS.get(status, status))}</td>"
            f"<td>{escape(LIFECYCLE_LABELS.get(lifecycle, lifecycle))}</td>"
            f"<td><code>{escape(identifier)}</code></td></tr>"
        )
    lines.extend(["</tbody></table></div>"])

    labels = {
        str(node.get("id") or ""): str(
            node.get("label") or node.get("title") or node.get("id") or "Unbenannt"
        )
        for node in nodes
    }
    lines.extend([
        "", "### Beziehungen", "",
        '<div class="knowledge-graph-table-wrap">',
        '<table data-kg-edge-table>',
        "<thead><tr><th>Quelle</th><th>Beziehung</th><th>Ziel</th><th>Status</th><th>Fundstellen</th></tr></thead>",
        "<tbody>",
    ])
    for edge in edges:
        source_id = str(edge.get("source") or "")
        target_id = str(edge.get("target") or "")
        relation = str(edge.get("type") or "unbekannt")
        edge_status = str(edge.get("status") or "ok")
        count = edge.get("count")
        lines.append(
            "<tr>"
            f"<td>{escape(labels.get(source_id, source_id))}</td>"
            f"<td><code>{escape(relation)}</code></td>"
            f"<td>{escape(labels.get(target_id, target_id))}</td>"
            f"<td>{escape(STATUS_LABELS.get(edge_status, edge_status))}</td>"
            f"<td>{escape(str(count if count is not None else '—'))}</td>"
            "</tr>"
        )
    lines.extend(["</tbody></table></div>"])
    return "\n".join(lines) + "\n"


def render_runtime_markdown(status: dict[str, object]) -> str:
    state = str(status.get("status") or "unknown")
    metrics = status.get("metrics") if isinstance(status.get("metrics"), dict) else {}
    context = status.get("context") if isinstance(status.get("context"), dict) else {}
    error = status.get("error") if isinstance(status.get("error"), dict) else {}
    recovery = (
        status.get("recovery")
        if isinstance(status.get("recovery"), dict)
        else {}
    )
    duration = status.get("duration_seconds")
    duration_label = "nicht verfügbar" if duration is None else f"{duration} s"
    nodes = metrics.get("nodes", metrics.get("node_count", "—"))
    edges = metrics.get("edges", metrics.get("edge_count", "—"))
    errors = metrics.get("errors", metrics.get("error_count", "—"))
    warnings = metrics.get("warnings", metrics.get("warning_count", "—"))
    lines = [
        "## Letzter Generatorlauf",
        "",
        f"**Wissensgraph: {escape(RUN_STATUS_LABELS.get(state, state))}**",
        "",
        "| Merkmal | Wert |",
        "|---|---|",
        f"| Zeitpunkt | {escape(_format_timestamp(status.get('ended_at') or status.get('updated_at')))} |",
        f"| Phase | `{escape(str(status.get('phase') or 'unbekannt'))}` |",
        f"| Revision | {escape(str(status.get('revision') or 'nicht verfügbar'))} |",
        f"| Git-Commit | `{escape(str(context.get('commit_sha') or 'nicht verfügbar'))}` |",
        f"| Branch / PR | `{escape(str(context.get('branch') or '—'))}` / {escape('#' + str(context['pr_number']) if context.get('pr_number') else '—')} |",
        f"| Laufzeit | {escape(duration_label)} |",
        f"| Knoten | {escape(str(nodes))} |",
        f"| Kanten | {escape(str(edges))} |",
        f"| Fehler / Warnungen | {escape(str(errors))} / {escape(str(warnings))} |",
    ]
    if state in {"failed", "blocked", "recovering", "recovered"}:
        lines.extend([
            "",
            "> [!failure] Generatorfehler und Recovery",
            f"> **Fehlerklasse:** `{escape(str(error.get('class') or 'unbekannt'))}`  ",
            f"> **Fehlercode:** `{escape(str(error.get('code') or 'unknown_error'))}`  ",
            f"> **Hinweis:** {escape(str(error.get('message') or 'Keine Detailmeldung vorhanden.'))}  ",
            f"> **Recovery-Level:** `{escape(str(recovery.get('level') or 'unbekannt'))}`  ",
            f"> **Recovery:** {escape(str(recovery.get('action') or 'Diagnosebericht prüfen.'))}  ",
            "> **Neuer Inhalt erforderlich:** "
            + ("ja  " if recovery.get("new_content_required") else "nein  "),
            "> **Nächster Generatorlauf blockiert:** "
            + (
                "ja"
                if recovery.get("block_next_run")
                and not recovery.get("acknowledged")
                else "nein"
            ),
        ])
    elif state == "unknown":
        lines.extend([
            "",
            "> [!warning] Laufstatus nicht verfügbar",
            "> Die statische Graph- und Tabellenansicht bleibt nutzbar; der Zeitpunkt des letzten Generatorlaufs konnte nicht geladen werden.",
        ])
    return "\n".join(lines) + "\n"


def inject_fallback(text: str, root: Path) -> str:
    if RUNTIME_START in text and RUNTIME_END in text:
        before, remainder = text.split(RUNTIME_START, 1)
        _, after = remainder.split(RUNTIME_END, 1)
        runtime = render_runtime_markdown(load_runtime_status(root))
        text = before + RUNTIME_START + "\n\n" + runtime + "\n" + RUNTIME_END + after
    if FALLBACK_START in text and FALLBACK_END in text:
        before, remainder = text.split(FALLBACK_START, 1)
        _, after = remainder.split(FALLBACK_END, 1)
        fallback = render_fallback_markdown(load_graph(root))
        text = before + FALLBACK_START + "\n\n" + fallback + "\n" + FALLBACK_END + after
    return text


def copy_graph_outputs(root: Path, docs: Path) -> list[str]:
    source_json = graph_json_path(root)
    if source_json is None:
        raise FileNotFoundError("Wissensgraph-JSON wurde vor dem Dokumentationsbuild nicht erzeugt")
    destination = docs / "knowledge-graph" / "data"
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    candidates = {
        "knowledge-graph.json": source_json,
        "knowledge-graph.mmd": source_json.with_suffix(".mmd"),
        "knowledge-graph.graphml": source_json.with_suffix(".graphml"),
        "graph-report.md": source_json.parent / "graph-report.md",
        "graph-report.json": source_json.parent / "graph-report.json",
        "runtime-status.json": next(
            (root / relative for relative in RUNTIME_STATUS_CANDIDATES if (root / relative).is_file()),
            root / RUNTIME_STATUS_CANDIDATES[0],
        ),
    }
    for name, source in candidates.items():
        if source.is_file():
            shutil_target = destination / name
            shutil_target.write_bytes(source.read_bytes())
            copied.append(name)
    return copied
