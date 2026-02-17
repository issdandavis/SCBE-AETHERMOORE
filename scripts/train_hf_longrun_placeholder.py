#!/usr/bin/env python3
"""Placeholder Hugging Face long-run training driver.

This file is intentionally non-op so the overnight bootstrap can run from day one.
It writes a training manifest for the selected run and reports exactly what is missing
before you connect your real HF trainer command.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hugging Face long-run placeholder")
    parser.add_argument("--dataset-repo", required=True, help="HF dataset repo identifier")
    parser.add_argument("--model-repo", required=True, help="HF model repo identifier")
    parser.add_argument("--duration-hours", type=float, default=8.0, help="Run duration budget")
    parser.add_argument(
        "--run-dir",
        default="training/runs/huggingface",
        help="Run directory to write manifest/log placeholders",
    )
    parser.add_argument(
        "--plan",
        default=None,
        help="Optional extra run metadata JSON path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "provider": "huggingface",
        "status": "placeholder",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_repo": args.dataset_repo,
        "model_repo": args.model_repo,
        "duration_hours": args.duration_hours,
        "run_dir": str(run_dir),
        "status_note": (
            "No real HF training command is wired yet. "
            "Replace this placeholder with your actual long-form trainer integration."
        ),
    }

    if args.plan:
        manifest["input_plan"] = args.plan

    manifest_path = run_dir / "hf_longrun_placeholder.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("HF long-run placeholder executed.")
    print("Manifest:", manifest_path)
    print("Replace this script and training plan command with your real trainer integration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
