"""Phase 4 \u2014 triage stray UI roots.

Decisions baked in based on hand-inspection (see ``docs/ops/REPO_REORG_2026-04.md``):

  Archive (empty stubs / superseded by other surfaces):
    aetherbrowse/   -> archive/ui-graveyard/aetherbrowse/
    app/            -> archive/ui-graveyard/app/
    ui/             -> archive/ui-graveyard/ui/

  Keep (alive, real, referenced or actively maintained):
    aether-browser/   (Python security layer paired with src/aetherbrowser/)
    desktop/          (Electron AetherBrowser standalone)
    kindle-app/       (Capacitor Android \u2014 GeoShell deployment target)
    prototype/        (toy_phdm research surface; has README + requirements)
    conference-app/   (real Vite + Vercel app)
    ai-ide/           (real Vite/React IDE \u2014 surfaced as a GeoShell tile)
    apps/             (contains real subprojects: outreach, scbe-github-app)
    dashboard/        (HTML dashboards \u2014 surfaced as GeoShell tiles)

This script only handles the archive moves. ``apps-registry.json`` already
exposes ai-ide / dashboard via the ``services`` category.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

ARCHIVE_TARGETS: list[tuple[str, str]] = [
    ("aetherbrowse", "archive/ui-graveyard/aetherbrowse"),
    ("app", "archive/ui-graveyard/app"),
    ("ui", "archive/ui-graveyard/ui"),
]

WHY_HERE = """\
# WHY_HERE

These UI roots moved here during the 2026-04 GeoShell consolidation because
they were either empty stubs (only `__init__.py` and empty subdirs) or
superseded by sibling roots.

| Folder | Reason |
|---|---|
| `aetherbrowse/` | Empty stub (4 files, 0MB). The active surface is `src/aetherbrowser/`. The Electron desktop wrapper lives at `desktop/`. |
| `app/` | Generic Express server (5 files: `index.html`, `package.json`, `server.js`, `server.ts`, `tsconfig.json`). Superseded by `desktop/`, `kindle-app/`, and `apps/scbe-github-app/`. |
| `ui/` | 3-file stub (`index.html`, `components/LayerStack.js`, `styles/main.css`). Replaced by the GeoShell shell at `scbe-visual-system/`. |

To restore any of these, `git mv` the folder back to the repo root and add a
test or npm script that exercises it.
"""


def git_mv_dir(src: Path, dst: Path) -> tuple[str, str]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["git", "mv", "-k", str(src), str(dst)],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return ("git_mv", "ok")
        # Fallback: shutil if git mv refused (untracked dir).
        shutil.move(str(src), str(dst))
        return ("shutil_move", f"git mv refused; fell back. stderr={result.stderr.strip()[:200]}")
    except FileNotFoundError:
        shutil.move(str(src), str(dst))
        return ("shutil_move", "git missing; used shutil")


def main() -> int:
    summary = {"moved": [], "skipped": [], "errors": []}
    archive_root = REPO / "archive" / "ui-graveyard"
    archive_root.mkdir(parents=True, exist_ok=True)
    why = archive_root / "WHY_HERE.md"
    if not why.exists():
        why.write_text(WHY_HERE, encoding="utf-8")

    for src_rel, dst_rel in ARCHIVE_TARGETS:
        src = REPO / src_rel
        dst = REPO / dst_rel
        if not src.exists():
            summary["skipped"].append(f"{src_rel} (already moved or missing)")
            continue
        if dst.exists():
            summary["errors"].append(f"{src_rel} -> {dst_rel} (dst already exists)")
            continue
        kind, msg = git_mv_dir(src, dst)
        if msg == "ok" or kind in {"shutil_move"}:
            summary["moved"].append(f"{src_rel} -> {dst_rel} via {kind}")
        else:
            summary["errors"].append(f"{src_rel}: {msg}")

    print(json.dumps(summary, indent=2))
    return 0 if not summary["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
