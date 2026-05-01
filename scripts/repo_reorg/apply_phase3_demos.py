"""Phase 3b \u2014 archive throwaway ``demos/`` scripts to ``archive/demos/``.

The ``demo/`` folder (singular) contains the AetherMoor game and is left
alone. Only the explicit ``demos/`` (plural) folder is archived because it
holds throwaway pitch/showcase scripts. Inside the GeoShell App Store, those
demos surface as service or static tiles instead of raw Python entry points.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "demos"
DST = REPO / "archive" / "demos"

WHY_HERE = """\
# WHY_HERE

These demo scripts moved here from the repo root ``demos/`` folder during the
2026-04 GeoShell consolidation. Their content is preserved for history.

**Industry-grade replacement:** every demo that needs to be runnable lives
as a tile inside the GeoShell App Store
(`scbe-visual-system/apps-registry.json`). To resurrect any of these as a
nested service, point a tile's ``service.envUrl`` at a uvicorn process
serving the equivalent FastAPI surface and remove the file from this archive.
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
    if not SRC.exists():
        print("demos/ already moved or missing; nothing to do.")
        return 0
    DST.mkdir(parents=True, exist_ok=True)
    why = DST / "WHY_HERE.md"
    if not why.exists():
        why.write_text(WHY_HERE, encoding="utf-8")

    summary = {"moved": [], "errors": []}
    for src in sorted(SRC.iterdir()):
        if src.is_dir():
            summary["errors"].append(f"{src.name} (subdir not handled by this script)")
            continue
        dst = DST / src.name
        if dst.exists():
            summary["errors"].append(f"{src.name} (dst exists)")
            continue
        kind, msg = git_mv(src, dst)
        if msg == "ok" or kind == "rename":
            summary["moved"].append(f"demos/{src.name} -> {dst.relative_to(REPO).as_posix()}")
        else:
            summary["errors"].append(f"demos/{src.name}: {msg}")

    # Try to remove the now-empty demos/ folder (best-effort; leave if non-empty).
    try:
        SRC.rmdir()
        summary["removed_dir"] = "demos/"
    except OSError:
        summary["removed_dir"] = None

    print(json.dumps(summary, indent=2))
    return 0 if not summary["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
