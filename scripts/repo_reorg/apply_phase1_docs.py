"""Phase 1 \u2014 docs consolidation. Reads the inventory artifact written by
``plan_repo_shape.py`` and performs ``git mv`` for every Phase 1 entry.

Idempotent. Re-running after a partial move is safe: existing destinations
are skipped, and any source already moved is reported as ``already_moved``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INVENTORY = REPO / "artifacts" / "repo_reorg" / "inventory_2026-04.json"

PHASE_TO_DEST = {
    "phase1_docs_specs": REPO / "docs" / "specs",
    "phase1_docs_ops": REPO / "docs" / "ops",
    "phase1_docs_business": REPO / "docs" / "business",
}


def git_mv(src: Path, dst: Path) -> tuple[str, str]:
    """Try ``git mv`` and fall back to a plain move if git refuses."""

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
    if not INVENTORY.exists():
        print(f"Inventory not found at {INVENTORY}", file=sys.stderr)
        return 2
    data = json.loads(INVENTORY.read_text(encoding="utf-8"))

    summary = {
        "moved": [],
        "already_moved": [],
        "skipped_collision": [],
        "errors": [],
    }

    for phase, dest_dir in PHASE_TO_DEST.items():
        dest_dir.mkdir(parents=True, exist_ok=True)
        for name in data["phases"].get(phase, []):
            src = REPO / name
            dst = dest_dir / name
            if dst.exists() and not src.exists():
                summary["already_moved"].append(f"{name} -> {dst.relative_to(REPO).as_posix()}")
                continue
            if dst.exists() and src.exists():
                summary["skipped_collision"].append(f"{name} (both src and dst exist; manual review)")
                continue
            if not src.exists():
                summary["errors"].append(f"{name} (source missing)")
                continue
            kind, msg = git_mv(src, dst)
            if msg == "ok" or kind == "rename":
                summary["moved"].append(f"{name} -> {dst.relative_to(REPO).as_posix()} via {kind}")
            else:
                summary["errors"].append(f"{name}: {msg}")

    print(json.dumps(summary, indent=2))
    return 0 if not summary["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
