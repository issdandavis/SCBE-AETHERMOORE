#!/usr/bin/env python3
"""Governed JSONL dataset push to Hugging Face datasets."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def governed_load_check(token: str | None, repo: str, files: list[Path]) -> tuple[bool, str]:
    if not token:
        return False, "HUGGINGFACE_TOKEN missing"
    if not files:
        return False, "no JSONL files found"
    if any(not f.exists() for f in files):
        return False, "one or more JSONL files do not exist"
    if "/" not in repo:
        return False, "repo must be namespaced like owner/name"
    return True, "governed load check passed"


def main() -> int:
    parser = argparse.ArgumentParser(description="Push JSONL dataset files to HF")
    parser.add_argument("--repo", required=True, help="HF dataset repo (owner/name)")
    parser.add_argument("--input", default="training-data", help="Directory containing JSONL files")
    args = parser.parse_args()

    token = os.environ.get("HUGGINGFACE_TOKEN")
    input_dir = Path(args.input)
    files = sorted(input_dir.glob("*.jsonl"))

    ok, reason = governed_load_check(token, args.repo, files)
    if not ok:
        print(f"[QUARANTINE] {reason}")
        return 2

    try:
        from huggingface_hub import HfApi
    except Exception as exc:  # pragma: no cover
        print(f"[QUARANTINE] huggingface_hub unavailable: {exc}")
        return 2

    api = HfApi(token=token)
    for file_path in files:
        print(f"Uploading {file_path.name} -> {args.repo}")
        api.upload_file(
            path_or_fileobj=str(file_path),
            path_in_repo=f"data/{file_path.name}",
            repo_id=args.repo,
            repo_type="dataset",
            commit_message=f"Update dataset {file_path.name}",
        )

    print(f"Uploaded {len(files)} JSONL file(s) to {args.repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
