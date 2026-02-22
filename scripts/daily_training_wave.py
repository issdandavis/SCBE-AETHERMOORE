#!/usr/bin/env python3
"""
Daily training wave orchestrator.

Builds training artifacts from local work products, then merges into
training-data/sft_combined.jsonl (+ chat variant).

Pipeline:
  1) Notion raw JSONL -> sft_notion.jsonl
  2) Isekai markdown -> sft_iseki.jsonl
  3) Spiralverse codex -> sft_spiralverse.jsonl
  4) Merge all sources -> sft_combined(.jsonl/.chat.jsonl)
  5) Optional upload to Hugging Face dataset
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    printable = " ".join(cmd)
    print(f"\n[wave] {printable}")
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run daily SCBE training wave pipeline")
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload merged dataset to Hugging Face",
    )
    parser.add_argument(
        "--repo-id",
        default="issdandavis/scbe-aethermoore-training-data",
        help="HF dataset repo id used when --upload is set",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    notion_raw = REPO_ROOT / "training-data" / "notion_raw_clean.jsonl"
    if notion_raw.exists():
        run(
            [
                sys.executable,
                "scripts/convert_to_sft.py",
                str(notion_raw),
                "-o",
                "training-data/sft_notion.jsonl",
            ]
        )
    else:
        print("[wave] skip notion conversion: training-data/notion_raw_clean.jsonl not found")

    iseki_md = REPO_ROOT / "training" / "notion_ingest" / "iseki_story_notion_api_20260218.md"
    if iseki_md.exists():
        run(
            [
                sys.executable,
                "scripts/iseki_markdown_to_sft.py",
                "--input",
                str(iseki_md),
                "--output",
                "training-data/sft_iseki.jsonl",
            ]
        )
    else:
        print("[wave] skip iseki conversion: training/notion_ingest/iseki_story_notion_api_20260218.md not found")

    kernel_manifest = REPO_ROOT / "training" / "kernel_manifest.yaml"
    if kernel_manifest.exists():
        run(
            [
                sys.executable,
                "scripts/kernel_manifest_to_sft.py",
                "--manifest",
                str(kernel_manifest),
                "--output",
                "training-data/sft_kernel_manifest.jsonl",
            ]
        )
    else:
        print("[wave] skip kernel conversion: training/kernel_manifest.yaml not found")

    run([sys.executable, "scripts/spiralverse_to_sft.py"])

    merge_cmd = [sys.executable, "scripts/merge_and_upload.py"]
    if args.upload:
        merge_cmd.extend(["--upload", "--repo-id", args.repo_id])
    run(merge_cmd)

    print("\n[wave] done")


if __name__ == "__main__":
    main()
