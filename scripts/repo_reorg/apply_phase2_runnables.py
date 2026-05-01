"""Phase 2 \u2014 archive *truly* unreferenced root entry points and debris files.

Industry-grade rules used to build this list:
  - keep at root: anything referenced by CI workflows, ``package.json`` scripts,
    ``tests/``, or ``scripts/windows/scbe.bat`` (the active dispatcher).
  - move to ``runnables/legacy/``: orphaned CLIs/scripts with no active refs.
  - move to ``archive/data-snapshots/``: stale JSON/text dumps.
  - move to ``archive/manuscripts/``: long-form text artifacts.
  - move to ``archive/public-pages/``: leftover HTML pages not served anywhere.

KEPT AT ROOT (load-bearing, do NOT touch):
  scbe.py, scbe-cli.py, scbe-agent.py, six-tongues-cli.py, enhanced_scbe_cli.py
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

MOVES: list[tuple[str, str]] = [
    ("scbe-geo.py", "runnables/legacy/scbe-geo.py"),
    ("scbe.js", "runnables/legacy/scbe.js"),
    ("scbe.ps1", "runnables/legacy/scbe.ps1"),
    ("quick-test.js", "runnables/legacy/quick-test.js"),
    ("RUN_SCBE.bat", "runnables/legacy/RUN_SCBE.bat"),
    ("build_apk.bat", "runnables/legacy/build_apk.bat"),
    ("test_jdk.bat", "runnables/legacy/test_jdk.bat"),
    ("scbe_inter_lattice_binder.py", "runnables/legacy/scbe_inter_lattice_binder.py"),
    ("index.js", "runnables/legacy/index.js"),
    ("index.html", "archive/public-pages/index.html"),
    ("product-landing.html", "archive/public-pages/product-landing.html"),
    ("triangulated_notion_update.json", "archive/data-snapshots/triangulated_notion_update.json"),
    ("The_Six_Tongues_Protocol.txt", "archive/manuscripts/The_Six_Tongues_Protocol.txt"),
    ("test_telemetry_advanced_math.json", "artifacts/legacy/test_telemetry_advanced_math.json"),
]

WHY_HERE = """\
# WHY_HERE

Files in this folder were moved here during the 2026-04 repo-shape reorg.
They are kept for history but are no longer referenced by tests, CI, npm
scripts, or the active scbe dispatcher (`scripts/windows/scbe.bat`).

Active root entry points that intentionally stayed at the repo root:

- `scbe.py` (used by CI: nightly-ops, overnight-pipeline)
- `scbe-cli.py` (used by `npm run cli` and `tests/test_turning_lane.py`)
- `scbe-agent.py` (used by `scripts/windows/scbe.bat agent`)
- `six-tongues-cli.py` (used by `tests/test_six_tongues_cli.py`,
  `tests/test_spiralverse_canonical_registry.py`)
- `enhanced_scbe_cli.py` (used by `tests/test_enhanced_scbe_cli.py`)

If you are bringing one of these files back to active use, restore the
original location and add a test or npm script that exercises it.
"""


def git_mv(src: Path, dst: Path) -> tuple[str, str]:
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
        return ("git_mv", f"rc={result.returncode} stderr={result.stderr.strip()}")
    except FileNotFoundError:
        src.rename(dst)
        return ("rename", "git missing; used Path.rename")


def main() -> int:
    summary = {"moved": [], "already_moved": [], "skipped": [], "errors": []}
    seen_dirs: set[Path] = set()

    for src_rel, dst_rel in MOVES:
        src = REPO / src_rel
        dst = REPO / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.parent not in seen_dirs:
            why = dst.parent / "WHY_HERE.md"
            if not why.exists():
                why.write_text(WHY_HERE, encoding="utf-8")
            seen_dirs.add(dst.parent)

        if dst.exists() and not src.exists():
            summary["already_moved"].append(f"{src_rel} -> {dst_rel}")
            continue
        if not src.exists():
            summary["skipped"].append(f"{src_rel} (source missing)")
            continue
        if dst.exists() and src.exists():
            summary["errors"].append(f"{src_rel} (collision; both exist)")
            continue

        kind, msg = git_mv(src, dst)
        if msg == "ok" or kind == "rename":
            summary["moved"].append(f"{src_rel} -> {dst_rel} via {kind}")
        else:
            summary["errors"].append(f"{src_rel}: {msg}")

    print(json.dumps(summary, indent=2))
    return 0 if not summary["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
