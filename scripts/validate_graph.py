#!/usr/bin/env python3
"""Validate the canonical knowledge graph and emit machine-readable reports.

The validator deliberately checks both layers of the contract: the published
JSON Schema and project-specific invariants which cannot be expressed usefully
in the schema (unique identifiers, edge endpoints, paths, URLs and statistics).
Every controlled failure is also written to ``graph-report.json`` and
``graph-report.md`` so CI retains useful diagnostics.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any, Iterable, Mapping
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "build" / "knowledge-graph" / "knowledge-graph.json"
SCHEMA = ROOT / "knowledge-graph" / "knowledge-graph.schema.json"
REPORT_JSON = ROOT / "build" / "knowledge-graph" / "graph-report.json"
REPORT_MD = ROOT / "build" / "knowledge-graph" / "graph-report.md"

ALLOWED_NODE_TYPES = frozenset({
    "asset", "chapter", "concept", "document", "glossary", "intro",
    "placeholder", "planned", "reference", "section", "technical",
})
ALLOWED_RELATIONS = frozenset({
    "cites", "contains", "embed", "planned_in", "prerequisite", "related",
    "sequence", "tagged_with", "wikilink",
})
ALLOWED_EDGE_STATUSES = frozenset({
    "ambiguous", "malformed", "missing-document", "missing-heading",
    "missing-reference", "ok", "planned",
})
ALLOWED_NODE_FIELDS = frozenset({
    "aliases", "anchor", "candidates", "difficulty", "document_id", "doi",
    "content_status", "estimated_time", "evidence", "evidence_grade",
    "evidence_type", "exists", "heading", "id", "issue_code", "label",
    "last_reviewed", "level", "lifecycle_status", "line",
    "maximum_reading_minutes", "minimum_reading_minutes", "path", "planned",
    "planned_type", "pmid", "reason", "reference_id", "requested_target",
    "roadmap", "scope", "status", "tags", "type", "url",
})
DOCUMENT_NODE_TYPES = frozenset({
    "asset", "chapter", "document", "glossary", "intro", "reference",
    "section", "technical",
})


@dataclass
class ValidationResult:
    """Structured result shared by the CLI, generator and tests."""

    graph: dict[str, Any] | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    computed_stats: dict[str, Any] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return not self.errors

    def add_error(self, code: str, message: str, **context: Any) -> None:
        self.errors.append(_message(code, "error", message, **context))

    def add_warning(self, code: str, message: str, **context: Any) -> None:
        self.warnings.append(_message(code, "warning", message, **context))


def _message(code: str, severity: str, message: str, **context: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": code, "severity": severity, "message": message,
    }
    payload.update({key: value for key, value in context.items() if value is not None})
    return payload


def _json_path(parts: Iterable[Any]) -> str:
    path = "$"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def _type_matches(value: Any, expected: str) -> bool:
    checks = {
        "array": lambda item: isinstance(item, list),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "null": lambda item: item is None,
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "object": lambda item: isinstance(item, dict),
        "string": lambda item: isinstance(item, str),
    }
    return checks.get(expected, lambda _item: True)(value)


def _fallback_schema_errors(
    instance: Any, schema: Mapping[str, Any], path: tuple[Any, ...] = (),
) -> list[tuple[str, str]]:
    """Validate the subset of Draft 2020-12 used by the shipped schema.

    CI installs ``jsonschema`` and therefore uses the standards-complete path.
    This fallback keeps local/offline validation deterministic instead of
    silently skipping schema validation when the optional package is absent.
    """

    errors: list[tuple[str, str]] = []
    expected = schema.get("type")
    types = [expected] if isinstance(expected, str) else expected
    if isinstance(types, list) and not any(_type_matches(instance, item) for item in types):
        return [(_json_path(path), f"expected type {types}, got {type(instance).__name__}")]
    if "const" in schema and instance != schema["const"]:
        errors.append((_json_path(path), f"must equal {schema['const']!r}"))
    if "enum" in schema and instance not in schema["enum"]:
        errors.append((_json_path(path), f"must be one of {schema['enum']!r}"))
    if isinstance(instance, str) and len(instance) < int(schema.get("minLength", 0)):
        errors.append((_json_path(path), "string is shorter than minLength"))
    if (
        isinstance(instance, (int, float)) and not isinstance(instance, bool)
        and "minimum" in schema and instance < schema["minimum"]
    ):
        errors.append((_json_path(path), f"must be >= {schema['minimum']}"))
    if isinstance(instance, dict):
        required = schema.get("required", [])
        for key in required if isinstance(required, list) else []:
            if key not in instance:
                errors.append((_json_path((*path, key)), "required property is missing"))
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            properties = {}
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in properties and isinstance(properties[key], dict):
                errors.extend(_fallback_schema_errors(value, properties[key], (*path, key)))
            elif additional is False:
                errors.append((_json_path((*path, key)), "additional property is not allowed"))
            elif isinstance(additional, dict):
                errors.extend(_fallback_schema_errors(value, additional, (*path, key)))
    if isinstance(instance, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, value in enumerate(instance):
                errors.extend(_fallback_schema_errors(value, item_schema, (*path, index)))
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in instance]
            if len(encoded) != len(set(encoded)):
                errors.append((_json_path(path), "array items must be unique"))
    return errors


def _schema_errors(data: Any, schema: dict[str, Any]) -> list[tuple[str, str]]:
    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import SchemaError
    except ImportError:
        return _fallback_schema_errors(data, schema)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        return [("$schema", f"invalid Draft 2020-12 schema: {exc.message}")]
    validator = Draft202012Validator(schema)
    return [
        (_json_path(error.absolute_path), error.message)
        for error in sorted(
            validator.iter_errors(data),
            key=lambda item: tuple(str(part) for part in item.absolute_path),
        )
    ]


def _safe_relative_path(value: str) -> str | None:
    if not value or "\\" in value or "\x00" in value or re.match(r"^[A-Za-z]:", value):
        return "Pfad ist leer, enthält Backslashes/NUL oder ein Laufwerkspräfix"
    decoded = unquote(value)
    candidate = PurePosixPath(decoded)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        return "Pfad muss relativ sein und darf keine Punktsegmente enthalten"
    return None


def _safe_internal_url(value: str) -> str | None:
    if not value or "\\" in value or "\x00" in value or any(ord(char) < 32 for char in value):
        return "URL ist leer oder enthält unzulässige Zeichen"
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or not value.startswith("/") or value.startswith("//"):
        return "URL muss ein interner absoluter Site-Pfad sein"
    decoded_path = unquote(parsed.path)
    if any(part in {".", ".."} for part in PurePosixPath(decoded_path).parts):
        return "URL darf keine Punktsegmente enthalten"
    return None


def _computed_stats(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]], issues: list[dict[str, Any]],
) -> dict[str, Any]:
    def counter_key(value: Any) -> str:
        return value if isinstance(value, str) else f"<invalid:{type(value).__name__}>"

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "issue_count": len(issues),
        "error_count": sum(issue.get("severity") == "error" for issue in issues),
        "warning_count": sum(issue.get("severity") == "warning" for issue in issues),
        "nodes_by_type": dict(sorted(Counter(counter_key(node.get("type")) for node in nodes).items())),
        "edges_by_type": dict(sorted(Counter(counter_key(edge.get("type")) for edge in edges).items())),
        "issues_by_code": dict(sorted(Counter(counter_key(issue.get("code")) for issue in issues).items())),
    }


def _validate_node(
    result: ValidationResult, node: dict[str, Any], index: int, root: Path,
) -> None:
    location = f"$.nodes[{index}]"
    unknown = sorted(set(node) - ALLOWED_NODE_FIELDS)
    if unknown:
        result.add_error(
            "unknown-node-fields", f"Unbekannte Node-Felder: {', '.join(unknown)}",
            path=location,
        )
    node_id = node.get("id")
    label = node.get("label")
    node_type = node.get("type")
    is_document_type = isinstance(node_type, str) and node_type in DOCUMENT_NODE_TYPES
    if not isinstance(node_id, str) or not node_id.strip():
        result.add_error("invalid-node-id", "Node-ID muss eine nichtleere Zeichenkette sein", path=location)
    if not isinstance(label, str) or not label.strip():
        result.add_error("invalid-node-label", "Node-Label muss eine nichtleere Zeichenkette sein", path=location)
    if not isinstance(node_type, str) or node_type not in ALLOWED_NODE_TYPES:
        result.add_error("invalid-node-type", f"Unbekannter Node-Typ: {node_type!r}", path=location)
    if not isinstance(node.get("scope"), str) or not str(node.get("scope", "")).strip():
        result.add_error("invalid-node-scope", "Node-Scope muss eine nichtleere Zeichenkette sein", path=location)

    exists, planned = node.get("exists"), node.get("planned")
    if node_type == "planned" and (exists is not False or planned is not True):
        result.add_error("invalid-planned-node", "Geplante Nodes benötigen exists=false und planned=true", path=location)
    elif node_type == "placeholder" and (exists is not False or planned is not False):
        result.add_error("invalid-placeholder-node", "Placeholder benötigen exists=false und planned=false", path=location)
    elif (
        isinstance(node_type, str) and node_type not in {"planned", "placeholder"}
        and (exists is not True or planned is not False)
    ):
        result.add_error("invalid-existing-node", "Vorhandene Nodes benötigen exists=true und planned=false", path=location)

    path_value = node.get("path")
    if path_value is not None:
        if not isinstance(path_value, str):
            result.add_error("invalid-node-path", "Node-Pfad muss eine Zeichenkette sein", path=location)
        else:
            path_error = _safe_relative_path(path_value)
            if path_error:
                result.add_error("unsafe-node-path", path_error, path=location, value=path_value)
            elif exists is True and is_document_type:
                target = (root / path_value).resolve()
                try:
                    target.relative_to(root.resolve())
                except ValueError:
                    result.add_error("unsafe-node-path", "Node-Pfad verlässt die Repositorywurzel", path=location)
                else:
                    if not target.is_file():
                        result.add_error(
                            "missing-node-path", f"Als vorhanden markierte Zieldatei fehlt: {path_value}",
                            path=location,
                        )
    elif is_document_type:
        result.add_error("missing-node-path", f"Node-Typ {node_type!r} benötigt einen Pfad", path=location)

    url_value = node.get("url")
    if url_value is not None:
        if not isinstance(url_value, str):
            result.add_error("invalid-node-url", "Node-URL muss eine Zeichenkette sein", path=location)
        else:
            url_error = _safe_internal_url(url_value)
            if url_error:
                result.add_error("unsafe-node-url", url_error, path=location, value=url_value)
    elif exists is True and is_document_type:
        result.add_error("missing-node-url", f"Node-Typ {node_type!r} benötigt eine Web-URL", path=location)


def _validate_edge(
    result: ValidationResult, edge: dict[str, Any], index: int,
    nodes_by_id: dict[str, dict[str, Any]],
) -> None:
    location = f"$.edges[{index}]"
    edge_type = edge.get("type")
    status = edge.get("status")
    if not isinstance(edge_type, str) or edge_type not in ALLOWED_RELATIONS:
        result.add_error("invalid-relation", f"Unbekannter Relationstyp: {edge_type!r}", path=location)
    if not isinstance(status, str) or status not in ALLOWED_EDGE_STATUSES:
        result.add_error("invalid-edge-status", f"Unbekannter Kantenstatus: {status!r}", path=location)
    source, target = edge.get("source"), edge.get("target")
    if not isinstance(source, str) or source not in nodes_by_id:
        result.add_error("missing-edge-source", f"Kantenquelle existiert nicht: {source!r}", path=location)
    if not isinstance(target, str) or target not in nodes_by_id:
        result.add_error("missing-edge-target", f"Kantenziel existiert nicht: {target!r}", path=location)

    occurrences = edge.get("occurrences")
    count = edge.get("count")
    if isinstance(occurrences, list):
        encoded = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in occurrences]
        if len(encoded) != len(set(encoded)):
            result.add_error("duplicate-edge-occurrence", "Kante enthält doppelte Fundstellen", path=location)
        if occurrences and count != len(occurrences):
            result.add_error(
                "edge-count-mismatch",
                f"Kantenzähler {count!r} entspricht nicht {len(occurrences)} Fundstellen",
                path=location,
            )
        for occurrence_index, occurrence in enumerate(occurrences):
            if not isinstance(occurrence, dict):
                continue
            occurrence_path = occurrence.get("path")
            if isinstance(occurrence_path, str) and _safe_relative_path(occurrence_path):
                result.add_error(
                    "unsafe-occurrence-path", "Fundstellenpfad ist nicht sicher",
                    path=f"{location}.occurrences[{occurrence_index}]", value=occurrence_path,
                )

    target_node = nodes_by_id.get(target) if isinstance(target, str) else None
    source_node = nodes_by_id.get(source) if isinstance(source, str) else None
    endpoint_types = {
        str(node.get("type")) for node in (source_node, target_node) if node is not None
    }
    if status == "ok" and endpoint_types.intersection({"planned", "placeholder"}):
        result.add_error("edge-status-target-mismatch", "Status ok darf keinen planned/placeholder-Endpunkt haben", path=location)
    if status == "planned" and "planned" not in endpoint_types:
        result.add_error("edge-status-target-mismatch", "Status planned benötigt einen geplanten Endpunkt", path=location)
    if (
        isinstance(status, str) and status not in {"ok", "planned"}
        and "placeholder" not in endpoint_types
    ):
        result.add_error("edge-status-target-mismatch", "Fehlerstatus benötigt einen Placeholder-Endpunkt", path=location)
    if edge_type == "contains" and (
        not source_node or not target_node or target_node.get("type") != "section"
    ):
        result.add_error("invalid-contains-relation", "contains muss auf einen Section-Node zeigen", path=location)
    if (
        edge_type == "tagged_with" and target_node
        and str(target_node.get("type")) not in {"concept", "section"}
    ):
        result.add_error("invalid-tag-relation", "tagged_with muss auf concept/section zeigen", path=location)
    if (
        edge_type == "cites" and target_node
        and str(target_node.get("type")) not in {"reference", "placeholder"}
    ):
        result.add_error("invalid-citation-relation", "cites muss auf reference/placeholder zeigen", path=location)
    if edge_type == "planned_in" and target_node and target_node.get("type") != "planned":
        result.add_error("invalid-planned-relation", "planned_in muss auf einen geplanten Node zeigen", path=location)


def validate_graph_data(
    data: Any,
    schema: dict[str, Any],
    *,
    root: Path = ROOT,
    expected_revision: str | None = None,
) -> ValidationResult:
    """Validate already parsed graph data without writing files."""

    result = ValidationResult(graph=data if isinstance(data, dict) else None)
    for path, message in _schema_errors(data, schema):
        result.add_error("schema-error", message, path=path)
    if not isinstance(data, dict):
        result.add_error("invalid-graph-root", "Wissensgraph muss ein JSON-Objekt sein", path="$")
        return result

    raw_nodes, raw_edges, raw_issues = data.get("nodes"), data.get("edges"), data.get("issues")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list) or not isinstance(raw_issues, list):
        return result
    nodes = [item for item in raw_nodes if isinstance(item, dict)]
    edges = [item for item in raw_edges if isinstance(item, dict)]
    issues = [item for item in raw_issues if isinstance(item, dict)]

    node_ids = [node.get("id") for node in nodes if isinstance(node.get("id"), str)]
    duplicate_node_ids = sorted(key for key, count in Counter(node_ids).items() if count > 1)
    for node_id in duplicate_node_ids:
        result.add_error("duplicate-node-id", f"Doppelte Node-ID: {node_id}", path="$.nodes")
    nodes_by_id = {
        node["id"]: node for node in nodes
        if isinstance(node.get("id"), str) and node["id"] not in duplicate_node_ids
    }
    for index, node in enumerate(nodes):
        _validate_node(result, node, index, root)

    edge_ids = [edge.get("id") for edge in edges if isinstance(edge.get("id"), str)]
    for edge_id, count in sorted(Counter(edge_ids).items()):
        if count > 1:
            result.add_error("duplicate-edge-id", f"Doppelte Edge-ID: {edge_id}", path="$.edges")
    for index, edge in enumerate(edges):
        if not isinstance(edge.get("id"), str) or not str(edge.get("id", "")).strip():
            result.add_error("invalid-edge-id", "Edge-ID muss eine nichtleere Zeichenkette sein", path=f"$.edges[{index}]")
        _validate_edge(result, edge, index, nodes_by_id)

    result.computed_stats = _computed_stats(nodes, edges, issues)
    graph_stats = data.get("stats")
    if isinstance(graph_stats, dict):
        for key, expected in result.computed_stats.items():
            if graph_stats.get(key) != expected:
                result.add_error(
                    "stats-mismatch",
                    f"stats.{key}={graph_stats.get(key)!r}, tatsächlich {expected!r}",
                    path=f"$.stats.{key}",
                )

    expected_scopes = sorted({str(node.get("scope")) for node in nodes if node.get("scope")})
    if data.get("scopes") != expected_scopes:
        result.add_error(
            "scopes-mismatch", f"scopes={data.get('scopes')!r}, tatsächlich {expected_scopes!r}",
            path="$.scopes",
        )
    # Keep the library function deterministic: callers opt into a revision
    # gate explicitly. The CLI still defaults to GITHUB_SHA in CI.
    revision = expected_revision
    if revision and data.get("source_revision") != revision:
        result.add_error(
            "source-revision-mismatch",
            f"source_revision entspricht nicht erwarteter Revision {revision}",
            path="$.source_revision",
        )
    for index, issue in enumerate(issues):
        if issue.get("severity") == "error":
            result.add_error(
                "blocking-graph-issue", str(issue.get("message") or "Unbekannter Graphfehler"),
                path=f"$.issues[{index}]", issue_code=issue.get("code"),
                source_path=issue.get("path"), line=issue.get("line"),
            )
    return result


def _empty_stats() -> dict[str, Any]:
    return {
        "node_count": 0, "edge_count": 0, "issue_count": 0,
        "error_count": 0, "warning_count": 0,
        "nodes_by_type": {}, "edges_by_type": {}, "issues_by_code": {},
    }


def report_payload(result: ValidationResult) -> dict[str, Any]:
    graph = result.graph or {}
    stats = graph.get("stats") if isinstance(graph.get("stats"), dict) else result.computed_stats
    raw_issues = graph.get("issues") if isinstance(graph.get("issues"), list) else []
    issues = [issue for issue in raw_issues if isinstance(issue, dict)]
    return {
        "schema_version": graph.get("schema_version"),
        "source_revision": graph.get("source_revision"),
        "valid": result.valid,
        "stats": stats or _empty_stats(),
        "issues": issues,
        "validation": {
            "error_count": len(result.errors),
            "warning_count": len(result.warnings),
            "errors": result.errors,
            "warnings": result.warnings,
        },
    }


def render_validation_report(result: ValidationResult) -> str:
    payload = report_payload(result)
    stats = payload["stats"]
    lines = [
        "# Wissensgraph-Bericht", "",
        f"- Ergebnis: **{'gültig' if result.valid else 'FEHLERHAFT'}**",
        f"- Schema: `{payload.get('schema_version') or 'nicht verfügbar'}`",
        f"- Quellrevision: `{payload.get('source_revision') or 'nicht verfügbar'}`",
        f"- Knoten: **{stats.get('node_count', 0)}**",
        f"- Kanten: **{stats.get('edge_count', 0)}**",
        f"- Graphfehler: **{stats.get('error_count', 0)}**",
        f"- Graphwarnungen: **{stats.get('warning_count', 0)}**",
        f"- Validierungsfehler: **{len(result.errors)}**",
        f"- Validierungswarnungen: **{len(result.warnings)}**", "",
        "## Knoten nach Typ", "",
    ]
    node_types = stats.get("nodes_by_type", {})
    if not isinstance(node_types, dict):
        node_types = {}
    lines.extend(f"- `{key}`: {value}" for key, value in node_types.items())
    if not node_types:
        lines.append("- keine Daten")
    lines.extend(["", "## Kanten nach Typ", ""])
    edge_types = stats.get("edges_by_type", {})
    if not isinstance(edge_types, dict):
        edge_types = {}
    lines.extend(f"- `{key}`: {value}" for key, value in edge_types.items())
    if not edge_types:
        lines.append("- keine Daten")
    lines.extend(["", "## Graphprobleme", ""])
    issues = payload["issues"]
    if not issues:
        lines.append("- keine")
    for issue in issues:
        location = str(issue.get("path") or "Repository")
        if issue.get("line"):
            location += f":{issue['line']}"
        lines.append(
            f"- **{issue.get('severity', 'error')} · `{issue.get('code', 'unknown')}`** — "
            f"{location}: {issue.get('message', '')}"
        )
    lines.extend(["", "## Validator", ""])
    messages = [*result.errors, *result.warnings]
    if not messages:
        lines.append("- keine zusätzlichen Befunde")
    for message in messages:
        location = f" ({message['path']})" if message.get("path") else ""
        lines.append(
            f"- **{message['severity']} · `{message['code']}`**{location} — {message['message']}"
        )
    return "\n".join(lines) + "\n"


def write_reports(result: ValidationResult, json_path: Path, markdown_path: Path) -> None:
    for path in (json_path, markdown_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report_payload(result), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_validation_report(result), encoding="utf-8")


def validate_graph_file(
    graph_path: Path = GRAPH,
    schema_path: Path = SCHEMA,
    *,
    root: Path = ROOT,
    report_json: Path | None = REPORT_JSON,
    report_markdown: Path | None = REPORT_MD,
    expected_revision: str | None = None,
) -> ValidationResult:
    result = ValidationResult()
    try:
        schema_data = json.loads(schema_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        result.add_error("missing-schema", f"Graphschema fehlt: {schema_path}")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result.add_error("invalid-schema-file", f"Graphschema kann nicht gelesen werden: {exc}")
    else:
        try:
            graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            result.add_error("missing-graph", f"Graphausgabe fehlt: {graph_path}")
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            result.add_error("invalid-graph-json", f"Graphausgabe kann nicht gelesen werden: {exc}")
        else:
            result = validate_graph_data(
                graph_data, schema_data, root=root, expected_revision=expected_revision,
            )
    if report_json is not None and report_markdown is not None:
        write_reports(result, report_json, report_markdown)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=GRAPH)
    parser.add_argument("--schema", type=Path, default=SCHEMA)
    parser.add_argument("--report-json", type=Path, default=REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=REPORT_MD)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--expected-revision", default=os.getenv("GITHUB_SHA"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = validate_graph_file(
        args.graph, args.schema, root=args.root,
        report_json=args.report_json, report_markdown=args.report_md,
        expected_revision=args.expected_revision,
    )
    if not result.valid:
        print("Knowledge graph validation failed:")
        for error in result.errors:
            location = f" [{error['path']}]" if error.get("path") else ""
            print(f"- {error['code']}{location}: {error['message']}")
        print(f"Reports: {args.report_json}, {args.report_md}")
        return 1
    stats = result.computed_stats
    print(
        "Knowledge graph valid: "
        f"{stats.get('node_count', 0)} nodes, {stats.get('edge_count', 0)} edges"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
