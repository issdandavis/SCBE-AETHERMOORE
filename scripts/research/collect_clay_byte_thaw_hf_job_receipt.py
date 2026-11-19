#!/usr/bin/env python3
"""Persist a sanitized HF Job terminal receipt and exact provider log transcript."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from huggingface_hub import HfApi


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_text_atomic(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(value, encoding="utf-8", newline="\n")
    pending.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api = HfApi()
    job = api.inspect_job(job_id=args.job_id)
    log_text = "".join(api.fetch_job_logs(job_id=args.job_id))
    log_path = args.output_dir / f"{args.job_id}.log"
    write_text_atomic(log_path, log_text)
    receipt = {
        "schema": "clay.byte-thaw-finalize-hf-job-terminal.v1",
        "captured_at_utc": utc_now(),
        "job": {
            "id": job.id,
            "created_at": job.created_at.isoformat(),
            "docker_image": job.docker_image,
            "flavor": job.flavor,
            "status": {
                "stage": job.status.stage,
                "message": job.status.message,
            },
            "environment": dict(job.environment or {}),
            "secret_names": sorted(job.secrets or []),
            "url": job.url,
        },
        "provider_spend": {
            "amount": None,
            "currency": None,
            "reported_by_job_api": False,
        },
        "log": {
            "path": log_path.name,
            "bytes": len(log_text.encode("utf-8")),
            "sha256": sha256(log_text.encode("utf-8")).hexdigest(),
        },
    }
    receipt_path = args.output_dir / f"{args.job_id}.json"
    write_text_atomic(receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
