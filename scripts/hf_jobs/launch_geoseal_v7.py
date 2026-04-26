#!/usr/bin/env python3
"""Launch the geoseal-stage6-repair-v7 training run on HF Jobs.

HF Jobs lets us pick the GPU class explicitly (t4-small, l4x1, a10g-small),
so there's no Kaggle-style CPU fallback lottery.

Usage:
    python scripts/hf_jobs/launch_geoseal_v7.py [--flavor t4-small]
    python scripts/hf_jobs/launch_geoseal_v7.py --flavor l4x1   # faster

Cost estimates (Qwen2.5-Coder-0.5B + LoRA, ~360 steps):
    t4-small  $0.40/hr * ~1.5h = ~$0.60
    l4x1      $0.80/hr * ~1.0h = ~$0.80
    a10g-small $1.00/hr * ~0.7h = ~$0.70
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "train_geoseal_v7.py"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--flavor",
        default="l4x1",
        choices=["t4-small", "t4-medium", "l4x1", "a10g-small"],
        help="HF Jobs hardware flavor (default: l4x1 — Pro plan, ~1h at $0.80/hr)",
    )
    ap.add_argument("--detach", action="store_true", help="Don't tail logs")
    args = ap.parse_args()

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        print("ERROR: set HF_TOKEN env var first", file=sys.stderr)
        return 2

    if not SCRIPT.exists():
        print(f"ERROR: {SCRIPT} not found", file=sys.stderr)
        return 2

    cmd = [
        "hf",
        "jobs",
        "uv",
        "run",
    ]
    if args.detach:
        cmd.append("--detach")
    cmd += [
        "--flavor",
        args.flavor,
        "--env",
        "PYTHONIOENCODING=utf-8",
        "--env",
        "PYTHONUTF8=1",
        "--env",
        "LANG=C.UTF-8",
        "--env",
        "LC_ALL=C.UTF-8",
        "--env",
        "HF_HUB_DISABLE_PROGRESS_BARS=1",
        "--env",
        "HF_DATASETS_DISABLE_PROGRESS_BARS=1",
        "--env",
        "TQDM_DISABLE=1",
        "--secrets",
        f"HF_TOKEN={token}",
        str(SCRIPT),
    ]

    print(f"Launching on flavor={args.flavor}")
    print("CMD:", " ".join(c if "HF_TOKEN=" not in c else "HF_TOKEN=***" for c in cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
