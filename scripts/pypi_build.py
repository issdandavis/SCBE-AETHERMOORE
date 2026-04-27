#!/usr/bin/env python3
"""Clean generated packaging state and build PyPI artifacts."""

from __future__ import annotations

import argparse
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build clean PyPI sdist and wheel artifacts.")
    parser.add_argument("--dist-dir", default="artifacts/pypi-dist", help="Output directory for PyPI artifacts.")
    args = parser.parse_args(argv)

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
