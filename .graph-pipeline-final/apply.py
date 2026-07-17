#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import importlib.metadata
import json
import re
import shutil
import subprocess
import textwrap
import yaml

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "agent/wissensgraph-pipeline-final"
BOOTSTRAP = ROOT / ".graph-pipeline-final"
WORKFLOW = ROOT / ".github" / "workflows" / "apply-graph-pipeline-final.yml"


def write(path: str, content: str) -> None:
    destination = ROOT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def append_section(path: str, marker: str, content: str) -> None:
    destination = ROOT / path
    text = destination.read_text(encoding="utf-8")
    if marker in text:
        return
    destination.write_text(text.rstrip() + "\n\n" + textwrap.dedent(content).strip() + "\n", encoding="utf-8")


def run(*command: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


# The phase-3 branch must start from the merged phase-2 state.
required_phase2 = [
    ROOT / "assets" / "javascripts" / "knowledge-graph.js",
    ROOT / "assets" / "stylesheets" / "knowledge-graph.css",
    ROOT / "scripts" / "graph_web.py",
]
missing_phase2 = [str(path.relative_to(ROOT)) for path in required_phase2 if not path.is_file()]
if missing_phase2:
    raise RuntimeError("Phase 2 fehlt auf der Branchbasis: " + ", ".join(missing_phase2))

# Resolve and pin the latest available Playwright and jsonschema releases exactly at implementation time.
run("npm", "install", "--save-dev", "--save-exact", "@playwright/test")
run("python", "-m", "pip", "install", "--disable-pip-version-check", "jsonschema")
jsonschema_version = importlib.metadata.version("jsonschema")
requirements = ROOT / "requirements-docs.txt"
requirements_text = requirements.read_text(encoding="utf-8")
requirements_text = re.sub(r"(?m)^jsonschema==[^\n]+\n?", "", requirements_text).rstrip() + f"\njsonschema=={jsonschema_version}\n"
requirements.write_text(requirements_text, encoding="utf-8")

write(
    "playwright.config.mjs",
    r'''
    import { defineConfig } from "@playwright/test";

    export default defineConfig({
      testDir: "tests/web",
      timeout: 30_000,
      retries: 0,
      workers: 1,
      use: {
        baseURL: "http://127.0.0.1:8765",
        browserName: "chromium",
        headless: true,
        reducedMotion: "reduce",
      },
      webServer: {
        command: "python3 -m http.server 8765 --directory site",
        url: "http://127.0.0.1:8765/knowledge-graph/",
        reuseExistingServer: false,
        timeout: 30_000,
      },
      reporter: [["line"]],
    });
    ''',
)

write(
    "tests/web/knowledge-graph.spec.mjs",
    r'''
    import { test, expect } from "@playwright/test";

    test("interactive graph loads, filters and exposes semantic fallback", async ({ page }) => {
      const errors = [];
      page.on("console", (message) => {
        if (message.type() === "error") errors.push(message.text());
      });
      page.on("pageerror", (error) => errors.push(error.message));

      await page.goto("/knowledge-graph/");
      await expect(page.locator("[data-knowledge-graph]")).toBeVisible();
      await expect(page.locator("[data-kg-canvas] canvas")).toHaveCount(1);
      await expect(page.locator("[data-kg-live]")).toContainText(/Knoten sichtbar|von .* Knoten/);
      await expect(page.getByRole("heading", { name: "Semantische Graphansicht" })).toBeVisible();
      await expect(page.locator("table[data-kg-node-table]")).toBeVisible();

      const search = page.locator("[data-kg-search]");
      await search.fill("Genetik");
      await expect(page.locator("[data-kg-live]")).toContainText(/Knoten sichtbar/);

      await page.locator("[data-kg-reset]").click();
      await expect(search).toHaveValue("");
      expect(errors).toEqual([]);
    });

    test("fallback remains available without JavaScript", async ({ browser }) => {
      const context = await browser.newContext({ javaScriptEnabled: false });
      const page = await context.newPage();
      await page.goto("http://127.0.0.1:8765/knowledge-graph/");
      await expect(page.getByRole("heading", { name: "Semantische Graphansicht" })).toBeVisible();
      await expect(page.locator("table[data-kg-node-table] tbody tr").first()).toBeVisible();
      await context.close();
    });

    test("controls and fallback rows are keyboard reachable", async ({ page }) => {
      await page.goto("/knowledge-graph/");
      await page.locator("[data-kg-search]").focus();
      await expect(page.locator("[data-kg-search]")).toBeFocused();
      const firstRow = page.locator("[data-kg-node-row]").first();
      await firstRow.focus();
      await expect(firstRow).toBeFocused();
      await firstRow.press("Enter");
      await expect(page.locator("[data-kg-details] h2")).not.toHaveText("Details");
    });
    ''',
)

write(
    "scripts/validate_graph.py",
    r'''
    #!/usr/bin/env python3
    """Validate the generated knowledge graph against its schema and release policy."""

    from __future__ import annotations

    import argparse
    import json
    import os
    from pathlib import Path
    import sys

    from jsonschema import Draft202012Validator

    ROOT = Path(__file__).resolve().parents[1]
    GRAPH_CANDIDATES = (
        ROOT / "build" / "knowledge-graph" / "knowledge-graph.json",
        ROOT / "build" / "knowledge-graph.json",
    )
    SCHEMA_CANDIDATES = (
        ROOT / "knowledge-graph" / "knowledge-graph.schema.json",
        ROOT / "knowledge-graph" / "schema.json",
    )
    BLOCKING_STATUSES = {"missing", "missing-document", "missing-heading", "ambiguous", "malformed"}


    def first_existing(candidates: tuple[Path, ...], label: str) -> Path:
        for path in candidates:
            if path.is_file():
                return path
        raise FileNotFoundError(f"{label} nicht gefunden: " + ", ".join(str(path.relative_to(ROOT)) for path in candidates))


    def main() -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument("--allow-errors", action="store_true", help="Bericht erzeugen, aber bei Graphproblemen noch nicht abbrechen")
        args = parser.parse_args()

        graph_path = first_existing(GRAPH_CANDIDATES, "Graph-JSON")
        schema_path = first_existing(SCHEMA_CANDIDATES, "Graphschema")
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors: list[str] = []

        for error in sorted(Draft202012Validator(schema).iter_errors(data), key=lambda item: list(item.absolute_path)):
            location = "/".join(str(part) for part in error.absolute_path) or "<root>"
            errors.append(f"Schema {location}: {error.message}")

        nodes = data.get("nodes", []) if isinstance(data, dict) else []
        edges = data.get("edges", []) if isinstance(data, dict) else []
        issues = data.get("issues", []) if isinstance(data, dict) else []
        ids = [str(node.get("id")) for node in nodes if isinstance(node, dict)]
        id_set = set(ids)
        if len(ids) != len(id_set):
            errors.append("Knoten-IDs sind nicht eindeutig")
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            source = str(edge.get("source") or "")
            target = str(edge.get("target") or "")
            if source not in id_set:
                errors.append(f"Kante {edge.get('id', '?')}: unbekannte Quelle {source}")
            if target not in id_set:
                errors.append(f"Kante {edge.get('id', '?')}: unbekanntes Ziel {target}")

        blocking = []
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            status = str(issue.get("status") or issue.get("code") or issue.get("type") or "")
            if status in BLOCKING_STATUSES:
                blocking.append(issue)
        if blocking:
            for issue in blocking:
                target = issue.get("requested_target") or issue.get("target") or issue.get("target_id") or "?"
                path = issue.get("path") or issue.get("source_path") or "?"
                line = issue.get("line")
                errors.append(f"{issue.get('status') or issue.get('code')}: {target} in {path}{':' + str(line) if line else ''}")

        summary = f"nodes={len(nodes)};edges={len(edges)};issues={len(issues)};blocking={len(blocking)};errors={len(errors)}"
        if os.getenv("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
                handle.write(f"summary={summary}\n")
                handle.write(f"failed={'true' if errors else 'false'}\n")
        if errors:
            print("Wissensgraph-Validierung:")
            for error in errors:
                print(f"- {error}")
            return 0 if args.allow_errors else 1
        print(f"Wissensgraph gültig: {len(nodes)} Knoten, {len(edges)} Kanten, {len(issues)} Hinweise")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
    ''',
)

write(
    "scripts/graph_ci_summary.py",
    r'''
    #!/usr/bin/env python3
    """Create a compact Markdown health summary for CI, PR comments and artifacts."""

    from __future__ import annotations

    import argparse
    from collections import Counter
    import json
    import os
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]
    CANDIDATES = (
        ROOT / "build" / "knowledge-graph" / "knowledge-graph.json",
        ROOT / "build" / "knowledge-graph.json",
    )


    def graph_path() -> Path:
        for path in CANDIDATES:
            if path.is_file():
                return path
        raise FileNotFoundError("Wissensgraph-JSON fehlt")


    def status(item: dict[str, object]) -> str:
        if item.get("planned") is True:
            return "planned"
        return str(item.get("status") or item.get("code") or "ok")


    def main() -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--append", type=Path)
        args = parser.parse_args()
        data = json.loads(graph_path().read_text(encoding="utf-8"))
        nodes = [item for item in data.get("nodes", []) if isinstance(item, dict)]
        edges = [item for item in data.get("edges", []) if isinstance(item, dict)]
        issues = [item for item in data.get("issues", []) if isinstance(item, dict)]
        node_types = Counter(str(item.get("type") or "unbekannt") for item in nodes)
        edge_types = Counter(str(item.get("type") or "unbekannt") for item in edges)
        issue_statuses = Counter(status(item) for item in issues)
        planned = sum(1 for item in nodes if status(item) == "planned")
        orphans = sum(1 for item in nodes if int(item.get("in_degree") or 0) + int(item.get("out_degree") or 0) == 0)

        lines = [
            "## Wissensgraph",
            "",
            f"- Knoten: **{len(nodes)}**",
            f"- Kanten: **{len(edges)}**",
            f"- geplante Seiten: **{planned}**",
            f"- gemeldete Probleme/Hinweise: **{len(issues)}**",
            f"- verwaiste Knoten: **{orphans}**",
            "- Knotentypen: " + ", ".join(f"`{key}` {value}" for key, value in sorted(node_types.items())),
            "- Beziehungstypen: " + ", ".join(f"`{key}` {value}" for key, value in sorted(edge_types.items())),
        ]
        if issue_statuses:
            lines.append("- Problemstatus: " + ", ".join(f"`{key}` {value}" for key, value in sorted(issue_statuses.items())))
        lines.append("")
        summary = "\n".join(lines)
        print(summary)
        if args.append:
            args.append.parent.mkdir(parents=True, exist_ok=True)
            with args.append.open("a", encoding="utf-8") as handle:
                handle.write("\n" + summary)
        if os.getenv("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
                handle.write(summary)


    if __name__ == "__main__":
        main()
    ''',
)

# Make the static fallback table genuinely keyboard-addressable and synchronisable.
graph_web = ROOT / "scripts" / "graph_web.py"
graph_web_text = graph_web.read_text(encoding="utf-8")
start = graph_web_text.index("def render_fallback_markdown")
end = graph_web_text.index("\n\ndef inject_fallback", start)
replacement = r'''def render_fallback_markdown(data: dict[str, object]) -> str:
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

    lines.extend(["", "### Link- und Strukturprobleme", ""])
    if issues:
        lines.extend(["| Status | Ziel | Fundstelle | Hinweis |", "|---|---|---|---|"])
        for issue in issues:
            issue_status = str(issue.get("status") or issue.get("code") or issue.get("type") or "Problem")
            target = str(issue.get("requested_target") or issue.get("target") or issue.get("target_id") or "—")
            path = str(issue.get("path") or issue.get("source_path") or "—")
            line = issue.get("line")
            location = f"`{escape(path)}:{line}`" if line else f"`{escape(path)}`"
            message = str(issue.get("message") or issue.get("detail") or "—").replace("|", "\\|")
            lines.append(f"| **{escape(STATUS_LABELS.get(issue_status, issue_status))}** | `{escape(target)}` | {location} | {escape(message)} |")
    else:
        lines.append("Keine ungeklärten internen Link- oder Strukturprobleme im aktuellen Build.")

    lines.extend([
        "",
        "### Knotenverzeichnis",
        "",
        '<table data-kg-node-table><thead><tr><th>Knoten</th><th>Typ</th><th>Status</th><th>Pfad oder ID</th></tr></thead><tbody>',
    ])
    for node in nodes:
        label = str(node.get("label") or node.get("title") or node.get("id") or "Unbenannt")
        node_type = str(node.get("type") or "document")
        node_status = _node_status(node)
        identifier = str(node.get("path") or node.get("id") or "—")
        node_id = str(node.get("id") or "")
        url = _node_url(node)
        shown_label = f'<a href="{escape(url)}">{escape(label)}</a>' if url and node_status == "ok" else escape(label)
        lines.append(
            f'<tr data-kg-node-row data-node-id="{escape(node_id)}" tabindex="0">'
            f'<td>{shown_label}</td><td><code>{escape(node_type)}</code></td>'
            f'<td>{escape(STATUS_LABELS.get(node_status, node_status))}</td>'
            f'<td><code>{escape(identifier)}</code></td></tr>'
        )
    lines.append("</tbody></table>")
    return "\n".join(lines) + "\n"
'''
graph_web.write_text(graph_web_text[:start] + replacement + graph_web_text[end:], encoding="utf-8")

# Add keyboard activation to semantic rows.
js = ROOT / "assets" / "javascripts" / "knowledge-graph.js"
js_text = js.read_text(encoding="utf-8")
old_row_handler = '''        fallbackRows.forEach((row) => {
          row.addEventListener("click", () => {
            if (!cy) return;
            const node = cy.getElementById(row.dataset.nodeId);
            if (node.length) {
              node.select();
              cy.center(node);
            }
          });
        });'''
new_row_handler = '''        fallbackRows.forEach((row) => {
          const activate = () => {
            if (!cy) return;
            const node = cy.getElementById(row.dataset.nodeId);
            if (node.length) {
              node.select();
              cy.center(node);
            }
          };
          row.addEventListener("click", activate);
          row.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              activate();
            }
          });
        });'''
if new_row_handler not in js_text:
    if old_row_handler not in js_text:
        raise RuntimeError("Fallback-Row-Handler in knowledge-graph.js nicht gefunden")
    js_text = js_text.replace(old_row_handler, new_row_handler, 1)
js.write_text(js_text, encoding="utf-8")

# Build docs may continue in explicit preview mode after collecting link errors.
build_docs = ROOT / "scripts" / "build_docs.py"
build_docs_text = build_docs.read_text(encoding="utf-8")
old_validation = '''errors = validate_all(ROOT)
if errors:
    raise ValueError("Ungültige Obsidian-Links:\\n" + "\\n".join(f"- {error}" for error in errors))
'''
new_validation = '''errors = validate_all(ROOT)
if errors and os.getenv("GRAPH_ALLOW_BROKEN_LINKS") != "1":
    raise ValueError("Ungültige Obsidian-Links:\\n" + "\\n".join(f"- {error}" for error in errors))
'''
if new_validation not in build_docs_text:
    if old_validation not in build_docs_text:
        raise RuntimeError("Validierungsblock in build_docs.py nicht gefunden")
    build_docs_text = build_docs_text.replace("from pathlib import Path\n", "from pathlib import Path\nimport os\n", 1)
    build_docs_text = build_docs_text.replace(old_validation, new_validation, 1)
build_docs.write_text(build_docs_text, encoding="utf-8")

# Add graph artifacts to public downloads.
exports = ROOT / "scripts" / "build_exports.py"
exports_text = exports.read_text(encoding="utf-8")
metadata_anchor = '    "references.json": ("CSL JSON", "application/json"),\n'
metadata_addition = metadata_anchor + '''    "knowledge-graph.json": ("Wissensgraph JSON", "application/json"),
    "knowledge-graph.graphml": ("Wissensgraph GraphML", "application/graphml+xml"),
    "knowledge-graph.mmd": ("Wissensgraph Mermaid", "text/plain"),
    "knowledge-graph-report.md": ("Wissensgraph-Bericht", "text/markdown"),
    "knowledge-graph-report.json": ("Wissensgraph-Bericht JSON", "application/json"),
'''
if '"knowledge-graph.graphml"' not in exports_text:
    if metadata_anchor not in exports_text:
        raise RuntimeError("ARTIFACT_METADATA-Anker fehlt")
    exports_text = exports_text.replace(metadata_anchor, metadata_addition, 1)

if "def build_graph_exports" not in exports_text:
    function_anchor = "\n\ndef vault_files() -> list[Path]:\n"
    graph_function = r'''

def build_graph_exports() -> None:
    """Copy canonical graph data and reports into the public download bundle."""

    graph_candidates = [
        BUILD / "knowledge-graph" / "knowledge-graph.json",
        BUILD / "knowledge-graph.json",
    ]
    graph_json = next((path for path in graph_candidates if path.is_file()), None)
    if graph_json is None:
        raise FileNotFoundError("Wissensgraph-JSON fehlt vor dem Exportbuild")
    sources = {
        graph_json: ARTIFACTS / "knowledge-graph.json",
        graph_json.with_suffix(".graphml"): ARTIFACTS / "knowledge-graph.graphml",
        graph_json.with_suffix(".mmd"): ARTIFACTS / "knowledge-graph.mmd",
        graph_json.parent / "graph-report.md": ARTIFACTS / "knowledge-graph-report.md",
        graph_json.parent / "graph-report.json": ARTIFACTS / "knowledge-graph-report.json",
    }
    for source, destination in sources.items():
        shutil.copy2(require_file(source), destination)
'''
    if function_anchor not in exports_text:
        raise RuntimeError("Einfügeanker für build_graph_exports fehlt")
    exports_text = exports_text.replace(function_anchor, graph_function + function_anchor, 1)
if "    build_graph_exports()\n" not in exports_text:
    exports_text = exports_text.replace("    copy_generated_sources()\n", "    copy_generated_sources()\n    build_graph_exports()\n", 1)
exports.write_text(exports_text, encoding="utf-8")

# Canonicalise title-based prerequisites to stable repository paths.
frontmatter_re = re.compile(r"\A---\n(.*?)\n---\n", re.S)
markdown_paths = sorted(path for path in ROOT.rglob("*.md") if not any(part in {".git", "build", "site", "node_modules"} for part in path.parts))
title_to_path: dict[str, str] = {}
for path in markdown_paths:
    match = frontmatter_re.match(path.read_text(encoding="utf-8"))
    if not match:
        continue
    metadata = yaml.safe_load(match.group(1))
    if isinstance(metadata, dict) and isinstance(metadata.get("title"), str):
        title_to_path[metadata["title"].strip().casefold()] = path.relative_to(ROOT).with_suffix("").as_posix()

for path in sorted((ROOT / "01-Grundlagen").glob("*.md")):
    text = path.read_text(encoding="utf-8")
    match = frontmatter_re.match(text)
    if not match:
        continue
    metadata = yaml.safe_load(match.group(1))
    prerequisites = metadata.get("prerequisites") if isinstance(metadata, dict) else None
    if not isinstance(prerequisites, list):
        continue
    canonical = [title_to_path.get(str(value).strip().casefold(), str(value).strip().removesuffix(".md")) for value in prerequisites]
    line = "prerequisites: " + json.dumps(canonical, ensure_ascii=False) + "\n"
    updated_frontmatter, count = re.subn(r"(?m)^prerequisites:\s*.*\n", line, match.group(1) + "\n", count=1)
    if count != 1:
        raise RuntimeError(f"prerequisites-Zeile fehlt in {path.relative_to(ROOT)}")
    path.write_text("---\n" + updated_frontmatter.rstrip("\n") + "\n---\n" + text[match.end():], encoding="utf-8")

# Merge planned roadmap nodes, skipping pages that already exist.
planned_file = ROOT / "knowledge-graph" / "planned-nodes.yaml"
planned_data = yaml.safe_load(planned_file.read_text(encoding="utf-8")) if planned_file.is_file() else {"nodes": []}
if not isinstance(planned_data, dict):
    planned_data = {"nodes": []}
planned_nodes = planned_data.setdefault("nodes", [])
if not isinstance(planned_nodes, list):
    planned_nodes = []
    planned_data["nodes"] = planned_nodes
existing_planned = {str(item.get("path")) for item in planned_nodes if isinstance(item, dict)}
roadmap_nodes = [
    ("01-Grundlagen/11-Schlaf-Bewegung-und-koerperliche-Gesundheit", "Schlaf, Bewegung und körperliche Gesundheit", "chapter", "Grundlagen", "ROADMAP.md#grundlagen"),
    ("01-Grundlagen/12-Komorbiditaet-Depression-und-Suizidalitaet", "Komorbidität Depression und Suizidalität", "chapter", "Grundlagen", "ROADMAP.md#grundlagen"),
    ("02-Vertiefung/01-Pharmakologie-und-Psychotherapie", "Pharmakologie und Psychotherapie", "chapter", "Vertiefung", "ROADMAP.md#vertiefung"),
    ("02-Vertiefung/02-Autismus-ADHS-Ueberlappung", "Autismus/ADHS-Überlappung", "chapter", "Vertiefung", "ROADMAP.md#vertiefung"),
    ("02-Vertiefung/03-Parkinson-mechanistische-Vergleiche", "Parkinson: mechanistische Vergleiche und Grenzen", "chapter", "Vertiefung", "ROADMAP.md#vertiefung"),
    ("02-Vertiefung/04-Studienmethodik-Effektgroessen-Bias-und-Kausalitaet", "Studienmethodik, Effektgrößen, Bias und Kausalität", "chapter", "Vertiefung", "ROADMAP.md#vertiefung"),
    ("03-Forschungsniveau/01-Genomik-Bildgebung-und-Computational-Psychiatry", "Genomik, Bildgebung und Computational Psychiatry", "chapter", "Forschungsniveau", "ROADMAP.md#forschungsniveau"),
    ("03-Forschungsniveau/02-Kausale-Inferenz-und-longitudinale-Modelle", "Kausale Inferenz und longitudinale Modelle", "chapter", "Forschungsniveau", "ROADMAP.md#forschungsniveau"),
    ("03-Forschungsniveau/03-Personalisierte-Behandlung", "Personalisierte Behandlung: Möglichkeiten und Grenzen", "chapter", "Forschungsniveau", "ROADMAP.md#forschungsniveau"),
    ("03-Forschungsniveau/04-Offene-Forschungsfragen-und-Replikation", "Offene Forschungsfragen und Replikationsprobleme", "chapter", "Forschungsniveau", "ROADMAP.md#forschungsniveau"),
]
for path_value, title, node_type, level, roadmap in roadmap_nodes:
    if (ROOT / f"{path_value}.md").is_file() or path_value in existing_planned:
        continue
    planned_nodes.append({
        "path": path_value,
        "title": title,
        "type": node_type,
        "scope": "learning",
        "level": level,
        "roadmap": roadmap,
        "reason": "in der veröffentlichten Roadmap vorgesehene Lerneinheit",
    })
planned_nodes.sort(key=lambda item: str(item.get("path")) if isinstance(item, dict) else "")
planned_file.write_text(yaml.safe_dump(planned_data, allow_unicode=True, sort_keys=False), encoding="utf-8")

# Replace validation workflow with a preview-first, gate-last pipeline.
write(
    ".github/workflows/validate.yml",
    r'''
    name: Validate compendium

    on:
      push:
        branches: [main]
      pull_request:
        types: [opened, synchronize, reopened, ready_for_review]
      workflow_dispatch:

    permissions:
      contents: read
      issues: write
      pull-requests: write

    concurrency:
      group: validate-${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
      cancel-in-progress: true

    jobs:
      validate:
        name: Validate, preview and test
        runs-on: ubuntu-24.04
        timeout-minutes: 35

        steps:
          - name: Checkout repository
            uses: actions/checkout@v7

          - name: Set up Python
            uses: actions/setup-python@v6
            with:
              python-version: '3.12'
              cache: pip
              cache-dependency-path: |
                requirements-docs.txt
                requirements-export.txt

          - name: Set up Node.js
            uses: actions/setup-node@v6
            with:
              node-version: '24'
              cache: npm

          - name: Install dependencies
            run: |
              python -m pip install --disable-pip-version-check -r requirements-docs.txt -r requirements-export.txt
              npm ci
              npx playwright install --with-deps chromium
              python -m pip check

          - name: Check whitespace and source syntax
            run: |
              git diff --check
              python -m compileall -q scripts tests
              find Sync -type f -name '*.sh' -print0 | xargs -0 -r -n1 bash -n
              npm test

          - name: Run unit and integration tests
            run: python -m unittest discover -s tests -p 'test_*.py'

          - name: Build literature and citation exports
            run: python scripts/build_literature.py

          - name: Verify generated bibliography is committed
            run: |
              mkdir -p build
              git add --intent-to-add Literatur.md references.bib references.json
              if ! git diff --quiet -- Literatur.md references.bib references.json; then
                {
                  echo '# Bibliografie-Generatorabweichung'
                  echo
                  echo 'Die folgenden generierten Dateien stimmen nicht mit dem Commit überein:'
                  echo
                  echo '```diff'
                  git diff -- Literatur.md references.bib references.json
                  echo '```'
                } | tee build/validation-report.txt
                exit 1
              fi

          - name: Build knowledge graph
            run: python scripts/build_graph.py

          - name: Validate knowledge graph schema and policy
            id: graph_validation
            run: python scripts/validate_graph.py --allow-errors

          - name: Validate Obsidian links
            id: link_validation
            continue-on-error: true
            run: python scripts/validate_links.py

          - name: Validate compendium
            id: compendium_validation
            run: python scripts/validate_compendium.py

          - name: Append graph health summary
            if: always()
            run: python scripts/graph_ci_summary.py --append build/validation-report.txt

          - name: Build combined document and Anki deck
            run: |
              python scripts/build_combined.py
              python scripts/build_anki.py

          - name: Build preview documentation
            env:
              GRAPH_ALLOW_BROKEN_LINKS: '1'
            run: |
              python scripts/build_docs.py
              mkdocs build --strict

          - name: Browser smoke and accessibility tests
            run: npx playwright test

          - name: Upload validation and graph preview
            if: always()
            uses: actions/upload-artifact@v7
            with:
              name: validation-and-graph-preview
              path: |
                build/validation-report.txt
                build/knowledge-graph/
                build/knowledge-graph.json
                build/knowledge-graph.mmd
                site/knowledge-graph/
                test-results/
              if-no-files-found: warn
              retention-days: 14

          - name: Comment validation report
            if: always() && github.event_name == 'pull_request'
            continue-on-error: true
            env:
              GH_TOKEN: ${{ github.token }}
            run: |
              if [[ -f build/validation-report.txt ]]; then
                jq -Rs '{body: .}' build/validation-report.txt > /tmp/comment.json
                gh api --method POST \
                  repos/H234598/ADHS-Lernpfad/issues/${{ github.event.pull_request.number }}/comments \
                  --input /tmp/comment.json
              fi

          - name: Enforce final validation gates
            if: always()
            env:
              LINK_OUTCOME: ${{ steps.link_validation.outcome }}
              GRAPH_FAILED: ${{ steps.graph_validation.outputs.failed }}
              COMPENDIUM_FAILED: ${{ steps.compendium_validation.outputs.failed }}
            run: |
              failed=false
              [[ "$LINK_OUTCOME" == 'failure' ]] && failed=true
              [[ "$GRAPH_FAILED" == 'true' ]] && failed=true
              [[ "$COMPENDIUM_FAILED" == 'true' ]] && failed=true
              if [[ "$failed" == 'true' ]]; then
                cat build/validation-report.txt || true
                exit 1
              fi

      export-smoke:
        name: Build all download formats
        if: github.event_name != 'push'
        needs: validate
        runs-on: ubuntu-24.04
        timeout-minutes: 35

        steps:
          - uses: actions/checkout@v7
          - uses: actions/setup-python@v6
            with:
              python-version: '3.12'
              cache: pip
              cache-dependency-path: requirements-export.txt
          - name: Install Python dependencies
            run: python -m pip install --disable-pip-version-check -r requirements-docs.txt -r requirements-export.txt
          - name: Build source artifacts
            run: |
              python scripts/build_literature.py
              git diff --exit-code -- Literatur.md references.bib references.json
              python scripts/build_graph.py
              python scripts/validate_graph.py
              python scripts/validate_links.py
              python scripts/build_combined.py
              python scripts/build_anki.py
          - name: Install Pandoc and LuaLaTeX
            run: |
              sudo apt-get update
              sudo apt-get install --yes --no-install-recommends pandoc texlive-luatex texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended texlive-lang-german fonts-dejavu-core
          - name: Build complete download bundle
            run: python scripts/build_exports.py
          - name: Verify expected downloads
            run: |
              for file in ADHS-Lernpfad.pdf ADHS-Lernpfad.epub ADHS-Lernpfad.html ADHS-Lernpfad.tex ADHS-Lernpfad-Gesamtdokument.md ADHS-Lernpfad-Obsidian-Vault.zip ADHS-Lernpfad.apkg references.bib references.json knowledge-graph.json knowledge-graph.graphml knowledge-graph.mmd knowledge-graph-report.md knowledge-graph-report.json downloads.json SHA256SUMS.txt; do
                test -s "build/artifacts/$file"
              done
              cd build/artifacts
              sha256sum --check SHA256SUMS.txt
          - name: Upload preview download bundle
            uses: actions/upload-artifact@v7
            with:
              name: download-center-preview
              path: build/artifacts/
              if-no-files-found: error
              retention-days: 7
    ''',
)

# Production pages and export workflows get strict graph validation.
for workflow_name in (".github/workflows/pages.yml", ".github/workflows/export.yml"):
    workflow = ROOT / workflow_name
    text = workflow.read_text(encoding="utf-8")
    if "python scripts/validate_graph.py" not in text:
        text = text.replace(
            "          python scripts/build_graph.py\n",
            "          python scripts/build_graph.py\n          python scripts/validate_graph.py\n",
        )
    workflow.write_text(text, encoding="utf-8")

# Make graph downloads explicit in DOWNLOADS and operating documentation.
append_section(
    "DOWNLOADS.md",
    "## Wissensgraph-Daten",
    r'''
    ## Wissensgraph-Daten

    Der Downloadbereich veröffentlicht zusätzlich die bei jedem Build neu erzeugten Graphdaten:

    - `knowledge-graph.json` als kanonische, versionierte Knoten- und Kantenstruktur,
    - `knowledge-graph.graphml` für Gephi, Cytoscape Desktop und andere Netzwerkwerkzeuge,
    - `knowledge-graph.mmd` als kompakte Mermaid-Diagnoseansicht,
    - `knowledge-graph-report.md` und `.json` als Qualitäts- und Problembericht.

    Alle Dateien sind im Downloadmanifest enthalten und durch `SHA256SUMS.txt` abgesichert.
    ''',
)
append_section(
    "WARTUNG.md",
    "## Wissensgraph 2.0: Betrieb und Freigabepolicy",
    r'''
    ## Wissensgraph 2.0: Betrieb und Freigabepolicy

    `scripts/build_graph.py` erzeugt den kanonischen Graphen vor Web-, Export- und Validierungsschritten. `scripts/validate_graph.py` prüft JSON-Schema, eindeutige IDs, vorhandene Kantenendpunkte und die Linkstatus-Policy. Ausdrücklich registrierte geplante Seiten sind zulässig; ungeplant fehlende Dokumente oder Überschriften, Mehrdeutigkeiten und ungültige Ziele blockieren die Freigabe.

    Pull Requests erhalten auch bei solchen Fehlern soweit technisch möglich eine markierte Webvorschau und den Graphbericht. Erst der letzte Workflow-Schritt setzt die harten Gates durch. Dadurch bleibt der Fehler sichtbar und reparierbar, ohne die Qualitätsanforderungen an `main` zu schwächen.

    Die Browser-Smoke-Tests prüfen die interaktive Ansicht, Suche, semantische No-JavaScript-Alternative und Tastaturerreichbarkeit. Produktionsbuilds validieren den Graph erneut im strikten Modus.
    ''',
)
append_section(
    "CONTRIBUTING.md",
    "## Kanonische Wissensgraph-Metadaten",
    r'''
    ## Kanonische Wissensgraph-Metadaten

    Beziehungen im YAML-Frontmatter verwenden stabile repositoryrelative Pfade ohne `.md`:

    ```yaml
    prerequisites:
      - 01-Grundlagen/01-Was-ist-ADHS
      - 01-Grundlagen/08-Neuroentwicklung-und-Lebensspanne
    related:
      - Glossar#Neuroentwicklung
    ```

    Titelbasierte Altwerte werden nicht neu eingeführt. Noch nicht existierende, aber bewusst geplante Seiten werden ausschließlich in `knowledge-graph/planned-nodes.yaml` registriert. Ein fehlender Link ohne solchen Registry-Eintrag ist ein Fehler. Sobald die Seite existiert, muss der überholte Planned-Eintrag entfernt werden.

    Nach inhaltlichen Änderungen gehören `python scripts/build_graph.py`, `python scripts/validate_graph.py`, die Unit-Tests und der strikte MkDocs-Build zu den Pflichtprüfungen. Graphkanten werden niemals parallel manuell gepflegt.
    ''',
)
append_section(
    "knowledge-graph/README.md",
    "## Qualitätssicherung und Downloads",
    r'''
    ## Qualitätssicherung und Downloads

    Die CI veröffentlicht den Graphbericht und eine Webvorschau als Pull-Request-Artefakt. Auf `main` sind nur vorhandene oder ausdrücklich als geplant registrierte Ziele zulässig. Öffentliche JSON-, GraphML-, Mermaid- und Berichtsdateien stehen im Downloadcenter mit SHA-256-Prüfsummen bereit.
    ''',
)

# Update automation prompts without weakening the existing safety boundaries.
for prompt_path in (
    "prompts/AUTOMATION-PROMPT.md",
    "prompts/PR-REPAIR-PROMPT.md",
    "prompts/MERGE-AUTOMATION-PROMPT.md",
):
    append_section(
        prompt_path,
        "## Wissensgraph-2.0-Regeln",
        r'''
        ## Wissensgraph-2.0-Regeln

        - Pflege `prerequisites` und optionale `related`-Beziehungen als kanonische repositoryrelative Pfade ohne `.md`.
        - Entferne beim Anlegen einer zuvor geplanten Seite den passenden Eintrag aus `knowledge-graph/planned-nodes.yaml`.
        - Führe `python3 scripts/build_graph.py`, `python3 scripts/validate_graph.py` und die Graph-/Linktests aus.
        - Lies `build/knowledge-graph/graph-report.md` beziehungsweise den tatsächlich erzeugten Graphbericht und nenne Knoten, Kanten, geplante Ziele sowie Problemstatus im PR.
        - Erhöhe die Graphdichte niemals durch künstliche oder wissenschaftlich unbegründete Links.
        - Ungeplant fehlende Dokumente oder Überschriften, mehrdeutige Ziele und ungültige Links dürfen nicht durch Abschwächung der Validierung freigegeben werden.
        - Änderungen an Graphschema, Validatoren, Web- oder Veröffentlichungsinfrastruktur tragen `<!-- manual-merge-required -->`.
        ''',
    )

# Changelog entry immediately below the first heading.
changelog = ROOT / "CHANGELOG.md"
changelog_text = changelog.read_text(encoding="utf-8")
entry = """
## 2026-07-17 – Wissensgraph 2.0

- gemeinsamer kanonischer Inhaltsindex und Resolver für YAML-Beziehungen, Wikilinks, Überschriften und Referenzen
- deterministische JSON-, Mermaid-, GraphML- und Qualitätsberichte
- interaktive, filterbare Webansicht mit semantischer No-JavaScript-Alternative
- sichtbare Kennzeichnung geplanter und defekter Ziele ohne unmarkierte 404-Navigation
- Schema-, Endpoint-, Browser- und Accessibility-Smoke-Tests in CI
- öffentliche Graphdownloads mit Manifest und SHA-256-Prüfsummen
- kanonische Voraussetzungen und explizite Planned-Node-Registry

"""
if "## 2026-07-17 – Wissensgraph 2.0" not in changelog_text:
    heading_end = changelog_text.find("\n", changelog_text.find("# ")) + 1
    changelog_text = changelog_text[:heading_end] + "\n" + entry + changelog_text[heading_end:].lstrip("\n")
    changelog.write_text(changelog_text, encoding="utf-8")

# Complete the checked implementation plan.
plan = ROOT / "knowledge-graph" / "IMPLEMENTIERUNGSPLAN.md"
plan_text = plan.read_text(encoding="utf-8")
plan_text = plan_text.replace(
    "- [ ] **Phase 3 – CI, Exporte, Migration und Betriebsdokumentation:",
    "- [x] **Phase 3 – CI, Exporte, Migration und Betriebsdokumentation:",
)
completion = r'''
## Abschlussstatus

- [x] Jede eingeschlossene Markdown-Datei wird als kanonischer Knoten erfasst.
- [x] Relationale YAML-Metadaten, Wikilinks, Einbettungen, Überschriften, Quellen und Lernpfadreihenfolge werden typisiert verarbeitet.
- [x] Knoten und Kanten besitzen stabile IDs und Provenienz.
- [x] Geplante Seiten sind explizit registriert und in Webtext sowie Graph sichtbar markiert.
- [x] Ungeplant fehlende Dokumente oder Überschriften, mehrdeutige und ungültige Ziele blockieren die Freigabe.
- [x] JSON-Schema, eindeutige IDs und alle Kantenendpunkte werden in CI geprüft.
- [x] Die Webfassung bietet Suche, Filter, Layouts, Details, mobile Bedienung und reduzierte Bewegung.
- [x] Eine semantische No-JavaScript-, Tastatur- und Druckalternative ist vorhanden.
- [x] Pull Requests erhalten Graphbericht und Webvorschau vor dem letzten Qualitätsgate.
- [x] Browser-Smoke-Tests prüfen Interaktion und Fallbackansicht.
- [x] JSON, GraphML, Mermaid und Berichte werden als geprüfte Downloads veröffentlicht.
- [x] Wartung, Beitragsregeln, Changelog und Automationsprompts entsprechen der Implementierung.

**Der dreiphasige Implementierungsplan ist technisch abgeschlossen.** Künftige Erweiterungen erfolgen als normale, versionierte Verbesserungen des Graphschemas oder der Benutzeroberfläche.
'''
if "## Abschlussstatus" not in plan_text:
    plan_text = plan_text.rstrip() + "\n\n" + textwrap.dedent(completion).strip() + "\n"
plan.write_text(plan_text, encoding="utf-8")

# Remove the transport before any verification or commit.
shutil.rmtree(BOOTSTRAP)
WORKFLOW.unlink(missing_ok=True)

# Install the now-pinned project dependencies and the Chromium test runtime.
run("python", "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements-docs.txt", "-r", "requirements-export.txt")
run("npm", "ci")
run("npx", "playwright", "install", "--with-deps", "chromium")
run("python", "-m", "pip", "check")
run("python", "-m", "compileall", "-q", "scripts", "tests")
run("python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py")
run("npm", "test")
run("git", "diff", "--check")
run("python", "scripts/build_literature.py")
run("git", "diff", "--exit-code", "--", "Literatur.md", "references.bib", "references.json")
run("python", "scripts/build_graph.py")
run("python", "scripts/validate_graph.py")
run("python", "scripts/validate_links.py")
run("python", "scripts/validate_compendium.py")
run("python", "scripts/graph_ci_summary.py", "--append", "build/validation-report.txt")
run("python", "scripts/build_combined.py")
run("python", "scripts/build_anki.py")
run("python", "scripts/build_docs.py")
run("mkdocs", "build", "--strict")
run("npx", "playwright", "test")

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", "-A")
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
    print("Keine Phase-3-Änderungen anzuwenden")
    raise SystemExit(0)
run("git", "commit", "-m", "Wissensgraph 2.0: Pipeline, Exporte und Dokumentation")
run("git", "push", "origin", f"HEAD:{BRANCH}")
print("Phase 3 vollständig angewendet, geprüft und veröffentlicht")
