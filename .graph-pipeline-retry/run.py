#!/usr/bin/env python3
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
apply = ROOT / ".graph-pipeline-final" / "apply.py"
retry_dir = ROOT / ".graph-pipeline-retry"
retry_workflow = ROOT / ".github" / "workflows" / "retry-graph-pipeline-final.yml"

if apply.is_file():
    text = apply.read_text(encoding="utf-8")
    old = 'await expect(page.locator("[data-kg-canvas] canvas")).toHaveCount(1);'
    new = 'await expect(page.locator("[data-kg-canvas] canvas").first()).toBeVisible();'
    if old in text:
        text = text.replace(old, new, 1)
    cleanup = 'shutil.rmtree(BOOTSTRAP)\nWORKFLOW.unlink(missing_ok=True)\n'
    replacement = (
        'shutil.rmtree(BOOTSTRAP)\n'
        'WORKFLOW.unlink(missing_ok=True)\n'
        'shutil.rmtree(ROOT / ".graph-pipeline-retry", ignore_errors=True)\n'
        '(ROOT / ".github" / "workflows" / "retry-graph-pipeline-final.yml").unlink(missing_ok=True)\n'
    )
    if replacement not in text:
        if cleanup not in text:
            raise RuntimeError("Cleanup-Anker im Phase-3-Anwender fehlt")
        text = text.replace(cleanup, replacement, 1)
    apply.write_text(text, encoding="utf-8")
    subprocess.run(["python3", str(apply)], cwd=ROOT, check=True)
else:
    # The phase may already have completed before this retry was scheduled.
    shutil.rmtree(retry_dir, ignore_errors=True)
    retry_workflow.unlink(missing_ok=True)
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], cwd=ROOT, check=True)
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], cwd=ROOT, check=True)
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode != 0:
        subprocess.run(["git", "commit", "-m", "chore: entferne abgeschlossenen Pipeline-Retry"], cwd=ROOT, check=True)
        subprocess.run(["git", "push", "origin", "HEAD:agent/wissensgraph-pipeline-final"], cwd=ROOT, check=True)
