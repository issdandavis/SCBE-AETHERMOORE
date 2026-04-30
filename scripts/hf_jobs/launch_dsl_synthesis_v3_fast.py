#!/usr/bin/env python3
"""Hugging Face Jobs helper for DSL / TRL-style training.

`package.json` references this path. HF Jobs are launched with the `hf` CLI after
`hf auth login`. This script does not embed a full training image; it validates the
CLI and prints a copy-paste template.

Typical flow:
  1. `hf auth login`
  2. Put a PEP 723 `hf jobs uv run` script in-repo or use
     `npm run training:dispatch-coding-agent` to emit a coding-agent job payload.
  3. `hf jobs uv run --flavor <gpu> [--detach] your_script.py`

Usage:
  python scripts/hf_jobs/launch_dsl_synthesis_v3_fast.py --flavor l4x1
"""

from __future__ import annotations

import argparse
import shutil
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HF Jobs launch template (DSL / TRL lanes)"
    )
    parser.add_argument(
        "--flavor",
        default="l4x1",
        help="HF Jobs hardware flavor (e.g. l4x1, a10g-small)",
    )
    parser.add_argument(
        "--detach",
        action="store_true",
        help="Pass --detach to hf jobs (run in background on Hub)",
    )
    args = parser.parse_args()

    hf = shutil.which("hf")
    if not hf:
        print(
            "[hf_jobs] Install the Hugging Face CLI: pip install 'huggingface_hub[cli]'",
            file=sys.stderr,
        )
        return 2

    detach = " --detach" if args.detach else ""
    print("[hf_jobs] Hugging Face CLI found. Example job invocation:\n")
    print(
        f"  hf jobs uv run --flavor {args.flavor}{detach} "
        "scripts/path/to/your_pep723_train_script.py\n"
    )
    print("[hf_jobs] For SCBE coding-agent UV scripts, see:")
    print("  npm run training:dispatch-coding-agent")
    print("[hf_jobs] For surface overview (Colab + Kaggle + HF):")
    print("  npm run training:surfaces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
