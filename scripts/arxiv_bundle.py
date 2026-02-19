#!/usr/bin/env python3
"""Create arXiv submission tarball from generated artifacts."""

from __future__ import annotations

import argparse
import tarfile
from pathlib import Path


REQUIRED_FILES = ["paper.tex", "manifest.json"]


def bundle(input_dir: Path, output_tgz: Path) -> None:
    for name in REQUIRED_FILES:
        p = input_dir / name
        if not p.exists():
            raise FileNotFoundError(f"missing required file: {p}")

    output_tgz.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output_tgz, mode="w:gz") as tf:
        for name in REQUIRED_FILES:
            p = input_dir / name
            tf.add(p, arcname=name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bundle arXiv submission artifacts")
    parser.add_argument("--input-dir", default="artifacts/arxiv")
    parser.add_argument("--output", default="artifacts/arxiv/arxiv-submission.tar.gz")
    args = parser.parse_args()

    bundle(input_dir=Path(args.input_dir), output_tgz=Path(args.output))
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
