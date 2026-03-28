#!/usr/bin/env python3
"""
Push SCBE-AETHERMOORE Training Lab SFT JSONL to the SCBE training dataset repo on Hugging Face.

This uploads a single file (does not bulk-upload the whole directory).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / "config" / "connector_oauth" / ".env.connector.oauth"


def load_env_best_effort() -> None:
    if not ENV_FILE.exists():
        return
    try:
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    except Exception:
        return


def main() -> int:
    load_env_best_effort()

    p = argparse.ArgumentParser(description="Upload SCBE-AETHERMOORE Training Lab SFT JSONL to Hugging Face dataset repo")
    p.add_argument("--path", default=str(REPO_ROOT / "training-data" / "sft" / "ai_ide_sft.jsonl"))
    p.add_argument("--repo", default="issdandavis/scbe-aethermoore-training-data")
    p.add_argument("--path-in-repo", default="sft/ai_ide_sft.jsonl")
    p.add_argument("--token", default=os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN"))
    p.add_argument("--message", default="Add SCBE-AETHERMOORE Training Lab SFT export")
    args = p.parse_args()

    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"error: missing file: {path}")
    if not args.token:
        raise SystemExit("error: missing HF token. Set HF_TOKEN or HUGGINGFACE_TOKEN.")

    from huggingface_hub import HfApi

    api = HfApi(token=args.token)
    api.upload_file(
        path_or_fileobj=str(path),
        path_in_repo=str(args.path_in_repo),
        repo_id=str(args.repo),
        repo_type="dataset",
        commit_message=str(args.message),
    )

    print(f"Uploaded {path} -> {args.repo}:{args.path_in_repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
