#!/usr/bin/env python3
"""
Cross-platform equivalent of scripts/run_node_fleet_pipeline.ps1.

Runs:
1) optional doc ingest
2) node-fleet 3-specialty training
3) optional news generation
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List


def run(cmd: List[str]) -> str:
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    print(proc.stdout, end="")
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}")
    return proc.stdout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-glob", action="append", default=[], help="Extra glob(s) to ingest.")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--model-repo", default="issdandavis/phdm-21d-embedding")
    parser.add_argument("--conversation-spin-gist", default="c38b2eface8d456b90c6bf02678871d8")
    parser.add_argument("--push-to-hub", action="store_true", default=False)
    parser.add_argument("--generate-news", action="store_true", default=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)

    extra_globs: List[str] = []
    if args.docs_glob:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        ingest_out = f"training/ingest/docs_{stamp}.jsonl"
        cmd = ["python", "scripts/ingest_docs_to_training_jsonl.py", "--out", ingest_out]
        for g in args.docs_glob:
            cmd.extend(["--glob", g])
        run(cmd)
        extra_globs.append(ingest_out)

    train_cmd = [
        "python",
        "training/train_node_fleet_three_specialty.py",
        "--epochs",
        str(args.epochs),
        "--conversation-spin-gist",
        args.conversation_spin_gist,
        "--model-repo",
        args.model_repo,
    ]

    if args.push_to_hub:
        train_cmd.append("--push-to-hub")
    for g in extra_globs:
        train_cmd.extend(["--local-glob", g])

    output = run(train_cmd)
    m = re.findall(r"^Run dir:\s*(.+)$", output, flags=re.MULTILINE)
    if not m:
        raise RuntimeError("Could not parse run directory from training output.")
    run_dir = m[-1].strip()

    if args.generate_news:
        run(["python", "scripts/generate_node_fleet_news.py", "--run-dir", run_dir])

    print("")
    print("Pipeline complete.")
    print(f"RunDir: {run_dir}")
    if args.generate_news:
        print("News: docs/news/latest.md")


if __name__ == "__main__":
    main()

