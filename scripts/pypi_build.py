#!/usr/bin/env python3
"""Clean generated packaging state and build PyPI artifacts."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

GENERATED_PATHS = (
    Path("build"),
    Path("src") / "build",
    Path("src") / "scbe_aethermoore.egg-info",
)


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def ensure_build_module_available(auto_bootstrap: bool = True) -> bool:
    if importlib.util.find_spec("build") is not None:
        return True

    if not auto_bootstrap:
        print("[error] Python package 'build' is not installed. Re-run without --no-bootstrap-build.", file=sys.stderr)
        return False

    print("[info] Python package 'build' not found; installing via pip...")
    install = subprocess.run([sys.executable, "-m", "pip", "install", "build"], check=False)
    if install.returncode != 0:
        print("[error] Failed to install Python package 'build'.", file=sys.stderr)
        return False

    importlib.invalidate_caches()
    return importlib.util.find_spec("build") is not None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build clean PyPI sdist and wheel artifacts.")
    parser.add_argument("--dist-dir", default="artifacts/pypi-dist", help="Output directory for PyPI artifacts.")
    parser.add_argument(
        "--no-bootstrap-build",
        action="store_true",
        help="Do not auto-install the Python 'build' package when missing.",
    )
    args = parser.parse_args(argv)

    if not ensure_build_module_available(auto_bootstrap=not args.no_bootstrap_build):
        return 2

    for path in GENERATED_PATHS:
        remove_path(path)

    dist_dir = Path(args.dist_dir)
    if dist_dir.exists():
        for child in dist_dir.iterdir():
            if child.is_file() and (child.name.endswith(".whl") or child.name.endswith(".tar.gz")):
                child.unlink()
    else:
        dist_dir.mkdir(parents=True, exist_ok=True)

    return subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", str(dist_dir)],
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
