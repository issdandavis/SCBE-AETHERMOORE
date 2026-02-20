#!/usr/bin/env python3
"""Upload PHDM model artifacts to Hugging Face model repo."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload PHDM model artifacts")
    parser.add_argument("--repo", default="issdandavis/phdm-21d-embedding", help="HF model repo id")
    parser.add_argument("--model-dir", default=".", help="Directory containing model artifacts")
    args = parser.parse_args()

    token = os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        print("[QUARANTINE] HUGGINGFACE_TOKEN missing; refusing artifact upload.")
        return 2

    try:
        from huggingface_hub import HfApi
    except Exception as exc:  # pragma: no cover
        print(f"[QUARANTINE] huggingface_hub unavailable: {exc}")
        return 2

    model_dir = Path(args.model_dir)
    required = [model_dir / "config.json", model_dir / "pytorch_model.bin"]
    missing = [p.name for p in required if not p.exists()]
    if missing:
        print(f"[QUARANTINE] Missing required artifacts: {', '.join(missing)}")
        return 2

    api = HfApi(token=token)
    for artifact in required:
        print(f"Uploading {artifact.name} -> {args.repo}")
        api.upload_file(
            path_or_fileobj=str(artifact),
            path_in_repo=artifact.name,
            repo_id=args.repo,
            repo_type="model",
            commit_message=f"Upload {artifact.name}",
        )

    print("Upload complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
