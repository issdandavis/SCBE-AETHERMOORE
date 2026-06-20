"""Build GeoShell (the React ``scbe-visual-system``) and copy the static
output into the Kindle/Fire deployment target ``kindle-app/www/geoshell/``.

This is the integration pipe between the new App Store and the user's
actual mobile app. Runs three steps:

  1. ``npm install`` inside ``scbe-visual-system/`` (idempotent)
  2. ``npm run build`` to produce ``scbe-visual-system/dist/``
  3. mirror ``dist/`` into ``kindle-app/www/geoshell/``

After this script, the Kindle app loads the GeoShell at ``/geoshell/``.

Usage::

    python scripts/repo_reorg/build_geoshell_into_kindle.py [--skip-install]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "scbe-visual-system"
DIST = SRC / "dist"
DST = REPO / "kindle-app" / "www" / "geoshell"


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    """Run a subprocess and return (rc, combined_output)."""

    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def _has_npm_script(name: str) -> bool:
    pkg = json.loads((SRC / "package.json").read_text(encoding="utf-8"))
    return name in pkg.get("scripts", {})


def install(skip: bool) -> None:
    if skip:
        print("[skip] npm install (--skip-install)")
        return
    print("[run]  npm install in scbe-visual-system/")
    rc, out = _run(["npm", "install", "--no-audit", "--no-fund"], SRC)
    if rc != 0:
        sys.stderr.write(out + "\n")
        raise SystemExit(rc)


def build() -> None:
    if not _has_npm_script("build"):
        raise SystemExit("scbe-visual-system/package.json has no 'build' script")
    print("[run]  npm run build in scbe-visual-system/")
    rc, out = _run(["npm", "run", "build"], SRC)
    if rc != 0:
        sys.stderr.write(out + "\n")
        raise SystemExit(rc)
    if not DIST.exists():
        raise SystemExit(f"build did not produce {DIST}")


def mirror() -> None:
    if DST.exists():
        print(f"[run]  removing existing {DST.relative_to(REPO).as_posix()}")
        shutil.rmtree(DST)
    DST.parent.mkdir(parents=True, exist_ok=True)
    print(f"[run]  copying {DIST.relative_to(REPO).as_posix()} -> " f"{DST.relative_to(REPO).as_posix()}")
    shutil.copytree(DIST, DST)


def write_manifest() -> None:
    """Drop a small manifest the Kindle app can read for the GeoShell entry."""

    manifest = {
        "schema_version": "geoshell_kindle_manifest_v1",
        "geoshell_path": "geoshell/index.html",
        "registry_path": "geoshell/apps-registry.json",
        "build_root": "scbe-visual-system",
    }
    out = DST.parent / "geoshell-manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[run]  wrote {out.relative_to(REPO).as_posix()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-install", action="store_true", help="Skip npm install.")
    args = parser.parse_args()

    install(skip=args.skip_install)
    build()
    mirror()
    write_manifest()
    print("[done] GeoShell built and copied into kindle-app/www/geoshell/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
