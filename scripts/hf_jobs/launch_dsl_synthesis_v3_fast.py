#!/usr/bin/env python3
"""Launch DSL synthesis v3-fast on HF Jobs.

Use this when Kaggle has both GPU slots occupied. The run is bounded to 90
steps and refuses CPU fallback inside the training script.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from huggingface_hub import HfApi

SCRIPT = Path(__file__).parent / "train_dsl_synthesis_v3_fast.py"
DATASET_REPO = "issdandavis/scbe-coding-agent-sft-dsl-synthesis-v1"
REQUIRED = [
    "bijective_dsl_v1_train.sft.jsonl",
    "bijective_codeflow_v1_train.sft.jsonl",
    "cross_tongue_dialogue_bijective_v1_train.sft.jsonl",
    "atomic_workflow_stage6_repair_train.sft.jsonl",
    "command_lattice_seed_train.sft.jsonl",
    "binary_interpretation_matrix_v1.sft.jsonl",
    "bijective_dsl_v1_holdout.sft.jsonl",
    "functional_coding_benchmark_repairs_v1_eval.sft.jsonl",
    "operator_agent_bus_extracted_v1_eval.sft.jsonl",
]


def remote_has(files: set[str], name: str) -> bool:
    return any(candidate in files for candidate in (name, f"sft/{name}", f"training-data/sft/{name}"))


def preflight() -> bool:
    api = HfApi()
    try:
        files = set(api.list_repo_files(repo_id=DATASET_REPO, repo_type="dataset"))
    except Exception as exc:
        print(f"ERROR: cannot list dataset {DATASET_REPO}: {exc}", file=sys.stderr)
        return False
    missing = [name for name in REQUIRED if not remote_has(files, name)]
    if missing:
        print(f"ERROR: missing remote dataset files: {missing}", file=sys.stderr)
        return False
    print(f"Preflight OK: {DATASET_REPO} has {len(REQUIRED)} required files.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flavor", default="l4x1", choices=["t4-small", "t4-medium", "l4x1", "a10g-small"])
    parser.add_argument("--timeout", default="3h")
    parser.add_argument("--detach", action="store_true")
    parser.add_argument("--no-preflight", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        print("ERROR: set HF_TOKEN env var first", file=sys.stderr)
        return 2
    if not SCRIPT.exists():
        print(f"ERROR: {SCRIPT} not found", file=sys.stderr)
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

    print(f"Launching DSL synthesis v3-fast on HF Jobs flavor={args.flavor}, timeout={args.timeout}")
    print("CMD:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
