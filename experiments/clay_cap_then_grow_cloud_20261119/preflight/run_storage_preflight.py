"""Measure Kaggle writable target volumes for the sealed Clay campaign."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import shutil
import sys


SCHEMA = "clay.cap-then-grow-cloud-storage-preflight.v1"
PREREGISTRATION_COMMIT = "a546670c7"
PREREGISTRATION_SHA256 = "4669cc76d0428915dbbc806817a2ba532bf036cf74beb81786f52a1f4348def6"
REQUIRED_FREE_BYTES = 25 * 1024**3
OUTPUT = Path("/kaggle/working/CLOUD_STORAGE_PREFLIGHT.json")
TARGETS = (
    Path("/kaggle/working"),
    Path("/kaggle/temp"),
    Path("/tmp"),
    Path("/dev/shm"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def main() -> int:
    measurements: list[dict[str, object]] = []
    for target in TARGETS:
        row: dict[str, object] = {
            "path": str(target),
            "exists": target.exists(),
            "is_dir": target.is_dir(),
            "writable": os.access(target, os.W_OK) if target.exists() else False,
        }
        if target.is_dir():
            usage = shutil.disk_usage(target)
            stat = target.stat()
            row.update(
                {
                    "device_id": int(stat.st_dev),
                    "free_bytes": int(usage.free),
                    "total_bytes": int(usage.total),
                    "used_bytes": int(usage.used),
                    "free_gib": usage.free / 1024**3,
                    "passes_25_gib_gate": bool(
                        os.access(target, os.W_OK) and usage.free >= REQUIRED_FREE_BYTES
                    ),
                }
            )
        measurements.append(row)

    eligible = [
        row["path"]
        for row in measurements
        if row.get("passes_25_gib_gate") is True
    ]
    receipt = {
        "schema": SCHEMA,
        "checked_at_utc": utc_now(),
        "status": "PASS" if eligible else "BLOCKED_INSUFFICIENT_TARGET_CAPACITY",
        "authority": "CAPACITY_PREFLIGHT_ONLY_NO_TRAINING_NO_PROMOTION",
        "preregistration": {
            "commit": PREREGISTRATION_COMMIT,
            "sha256": PREREGISTRATION_SHA256,
        },
        "gate": {
            "required_free_bytes": REQUIRED_FREE_BYTES,
            "required_free_gib": 25.0,
            "lowered": False,
        },
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "cwd": str(Path.cwd()),
        },
        "measurements": measurements,
        "eligible_targets": eligible,
        "training_started": False,
        "models_loaded": False,
        "datasets_attached": False,
    }
    unsigned = canonical_json(receipt)
    receipt["receipt_sha256"] = sha256(unsigned).hexdigest()
    OUTPUT.write_bytes(canonical_json(receipt))
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
