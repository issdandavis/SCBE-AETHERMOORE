#!/usr/bin/env python3
"""Stage and independently read back the private HF byte-thaw recovery packet."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path

from huggingface_hub import CommitOperationAdd, HfApi, hf_hub_download

REPO_ID = "issdandavis/clay-byte-thaw-finalize-20261119"
REPO_TYPE = "dataset"
EXPECTED = {
    "input/v2/clay-byte-thaw-finalize.packet": (
        36184119,
        "5af43e7e138e3c1109fb40689fb2bb3400384610342bae8aebac636266723686",
    ),
    "input/v2/PACKET_DESCRIPTOR.json": (
        712,
        "471647529905de1afcc84e6f4a89814fe730f9929baf80170bea8df95767b241",
    ),
    "code/run_clay_byte_thaw_finalize_kaggle.py": (
        20207,
        "359b56fa6776a7f7e171b1f5ee4f674c2d76eb2a2bed4de69c92434b3b23126f",
    ),
}


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(pending, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--job-script", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    packet_dir = args.packet_dir.resolve(strict=True)
    runner = args.runner.resolve(strict=True)
    job_script = args.job_script.resolve(strict=True)
    receipt_path = args.receipt.resolve()
    if receipt_path.exists():
        raise FileExistsError(f"receipt already exists: {receipt_path}")

    local = {
        "input/v2/clay-byte-thaw-finalize.packet": packet_dir / "clay-byte-thaw-finalize.packet",
        "input/v2/PACKET_DESCRIPTOR.json": packet_dir / "PACKET_DESCRIPTOR.json",
        "code/run_clay_byte_thaw_finalize_kaggle.py": runner,
        "code/run_clay_byte_thaw_finalize_hf_job.py": job_script,
    }
    rows: list[dict[str, object]] = []
    for relative, path in local.items():
        path.resolve(strict=True)
        row = {"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        if relative in EXPECTED and (row["bytes"], row["sha256"]) != EXPECTED[relative]:
            raise RuntimeError(f"pinned local input differs: {relative}")
        rows.append(row)

    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN is not set")
    api = HfApi(token=token)
    api.create_repo(repo_id=REPO_ID, repo_type=REPO_TYPE, private=True, exist_ok=True)
    info = api.repo_info(repo_id=REPO_ID, repo_type=REPO_TYPE)
    if not bool(info.private):
        raise RuntimeError("result dataset is not private")
    commit = api.create_commit(
        repo_id=REPO_ID,
        repo_type=REPO_TYPE,
        operations=[
            CommitOperationAdd(path_in_repo=relative, path_or_fileobj=str(path)) for relative, path in local.items()
        ],
        commit_message="Stage private hash-pinned Clay byte-thaw finalize packet v2",
    )

    readback: list[dict[str, object]] = []
    for row in rows:
        relative = str(row["path"])
        cached = Path(
            hf_hub_download(
                repo_id=REPO_ID,
                repo_type=REPO_TYPE,
                filename=relative,
                revision=commit.oid,
                token=token,
                force_download=True,
            )
        )
        got = {"path": relative, "bytes": cached.stat().st_size, "sha256": sha256_file(cached)}
        if got["bytes"] != row["bytes"] or got["sha256"] != row["sha256"]:
            raise RuntimeError(f"provider readback differs: {relative}")
        readback.append(got)

    receipt = {
        "schema": "clay.byte-thaw-finalize-hf-stage.v1",
        "status": "PRIVATE_PACKET_STAGED_AND_PROVIDER_READBACK_VERIFIED",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_id": REPO_ID,
        "repo_type": REPO_TYPE,
        "private": bool(info.private),
        "commit_oid": commit.oid,
        "local": rows,
        "provider_readback": readback,
        "training_occurred": False,
        "optimizer_updates": 0,
        "publication": "NONE_PRIVATE_DATASET_ONLY",
        "promotion": "NONE",
    }
    write_json(receipt_path, receipt)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
