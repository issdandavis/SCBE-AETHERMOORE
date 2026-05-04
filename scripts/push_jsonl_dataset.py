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


_DATACARD_FILES = ("README.md", "datacard.json", "manifest.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Push JSONL dataset files to HF")
    parser.add_argument("--repo", required=True, help="HF dataset repo (owner/name)")
    parser.add_argument("--input", default="training-data", help="Directory containing JSONL files")
    parser.add_argument(
        "--create-repo",
        action="store_true",
        help="Create the dataset repo if it does not already exist",
    )
    parser.add_argument(
        "--skip-datacard",
        action="store_true",
        help="Do not upload README.md / datacard.json / manifest.json from the input dir",
    )
    args = parser.parse_args()

    # Accept either HUGGINGFACE_TOKEN (legacy) or HF_TOKEN (current convention).
    token = os.environ.get("HUGGINGFACE_TOKEN") or os.environ.get("HF_TOKEN")
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

    if args.create_repo:
        api.create_repo(repo_id=args.repo, repo_type="dataset", exist_ok=True)
        print(f"Ensured dataset repo exists: {args.repo}")

    for file_path in files:
        print(f"Uploading {file_path.name} -> {args.repo}/data/{file_path.name}")
        api.upload_file(
            path_or_fileobj=str(file_path),
            path_in_repo=f"data/{file_path.name}",
            repo_id=args.repo,
            repo_type="dataset",
            commit_message=f"Update dataset {file_path.name}",
        )

    datacard_uploaded = 0
    if not args.skip_datacard:
        for name in _DATACARD_FILES:
            candidate = input_dir / name
            if not candidate.exists():
                continue
            # README.md goes to the repo root so HF renders it on the dataset page.
            path_in_repo = name
            print(f"Uploading {name} -> {args.repo}/{path_in_repo}")
            api.upload_file(
                path_or_fileobj=str(candidate),
                path_in_repo=path_in_repo,
                repo_id=args.repo,
                repo_type="dataset",
                commit_message=f"Update {name}",
            )
            datacard_uploaded += 1

    print(f"Uploaded {len(files)} JSONL + {datacard_uploaded} datacard file(s) to {args.repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
