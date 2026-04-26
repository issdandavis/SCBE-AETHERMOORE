#!/usr/bin/env python3
"""Launch regularized coding-model v8 on HF Jobs after remote-data preflight."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from huggingface_hub import HfApi

SCRIPT = Path(__file__).parent / "train_regularized_coding_v8.py"
DATASET_REPO = "issdandavis/scbe-training-regularized-20260426"
REQUIRED = [
    "regularized/coding_model/coding_model_train.regularized.jsonl",
    "regularized/coding_model/coding_model_eval.regularized.jsonl",
]


def preflight() -> bool:
    api = HfApi()
    try:
        files = set(api.list_repo_files(repo_id=DATASET_REPO, repo_type="dataset"))
    except Exception as exc:
        print(f"ERROR: cannot list dataset {DATASET_REPO}: {exc}", file=sys.stderr)
        return False
    missing = [name for name in REQUIRED if name not in files]
    if missing:
        print(f"ERROR: missing remote dataset files: {missing}", file=sys.stderr)
        return False
    print(f"Preflight OK: {DATASET_REPO} has {len(REQUIRED)} required files.")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--flavor", default="l4x1", choices=["t4-small", "t4-medium", "l4x1", "a10g-small"])
    ap.add_argument("--timeout", default="4h")
    ap.add_argument("--detach", action="store_true")
    ap.add_argument("--no-preflight", action="store_true")
    args = ap.parse_args()

    if not SCRIPT.exists():
        print(f"ERROR: {SCRIPT} not found", file=sys.stderr)
        return 2
    if not (os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")):
        print("ERROR: set HF_TOKEN env var first", file=sys.stderr)
        return 2
    if not args.no_preflight and not preflight():
        return 3

    cmd = ["hf", "jobs", "uv", "run"]
    if args.detach:
        cmd.append("--detach")
    cmd += [
        "--flavor",
        args.flavor,
        "--timeout",
        args.timeout,
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
        "HF_TOKEN",
        str(SCRIPT),
    ]

    print(f"Launching regularized coding v8 on flavor={args.flavor}, timeout={args.timeout}")
    print("CMD:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
