#!/usr/bin/env python3
"""Measure a conservative storage envelope from one completed Clay campaign."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any

SCHEMA = "clay.checkpoint-storage-envelope.v1"
MEASUREMENT_AUTHORITY = "MEASUREMENT_ONLY_NO_TRAINING_AUTHORITY"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _require_atomic_contract(runner_source: Path, helper_source: Path) -> dict[str, bool]:
    runner = runner_source.read_text(encoding="utf-8")
    helper = helper_source.read_text(encoding="utf-8")
    checks = {
        "runner_uses_two_slot_checkpoint": "TwoSlotCheckpoint" in runner,
        "runner_uses_atomic_model_save": "atomic_torch_save" in runner,
        "helper_defines_two_slot_checkpoint": "class TwoSlotCheckpoint" in helper,
        "helper_defines_atomic_torch_save": "def atomic_torch_save" in helper,
        "helper_uses_atomic_replace": "os.replace(" in helper,
        "helper_uses_temporary_write": ".tmp" in helper,
        "helper_names_both_slots": "slot-a.pt" in helper and "slot-b.pt" in helper,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"atomic checkpoint contract is incomplete: {', '.join(failed)}")
    return checks


def measure_storage_envelope(
    *,
    run_dir: Path,
    runner_source: Path,
    helper_source: Path,
    free_bytes: int | None = None,
) -> dict[str, Any]:
    run_dir = run_dir.resolve(strict=True)
    runner_source = runner_source.resolve(strict=True)
    helper_source = helper_source.resolve(strict=True)
    manifest_path = (run_dir / "RUN_MANIFEST.json").resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("run manifest must be a JSON object")
    config = manifest.get("config")
    if not isinstance(config, dict):
        raise ValueError("run manifest config is missing")
    floor_bytes = int(config.get("minimum_free_bytes", 0))
    if floor_bytes <= 0:
        raise ValueError("run manifest minimum_free_bytes must be positive")

    contract = _require_atomic_contract(runner_source, helper_source)
    pending = sorted(
        str(path)
        for path in run_dir.rglob("*")
        if path.is_file() and (path.name.endswith(".tmp") or path.name.endswith(".pending"))
    )
    if pending:
        raise ValueError(f"completed run still contains pending writes: {pending}")

    files = sorted(path for path in run_dir.rglob("*") if path.is_file())
    if not files:
        raise ValueError("run directory has no artifacts")
    horses_root = run_dir / "horses"
    if not horses_root.is_dir():
        raise ValueError("run directory has no horses directory")

    horses: list[dict[str, Any]] = []
    trained_horses = 0
    for horse_dir in sorted(path for path in horses_root.iterdir() if path.is_dir()):
        horse_files = sorted(path for path in horse_dir.rglob("*") if path.is_file())
        if not horse_files:
            continue
        checkpoint_slots = [path for path in horse_files if path.name in {"slot-a.pt", "slot-b.pt"}]
        trained = bool(checkpoint_slots and (horse_dir / "MODEL.pt").is_file())
        trained_horses += int(trained)
        horses.append(
            {
                "name": horse_dir.name,
                "trained": trained,
                "file_count": len(horse_files),
                "persistent_bytes": sum(path.stat().st_size for path in horse_files),
                "largest_file_bytes": max(path.stat().st_size for path in horse_files),
                "checkpoint_slot_bytes": sorted(path.stat().st_size for path in checkpoint_slots),
            }
        )
    if not horses or trained_horses == 0:
        raise ValueError("run has no completed trained horse with checkpoint slots and MODEL.pt")

    observed_run_bytes = sum(path.stat().st_size for path in files)
    peak_atomic_payload_bytes = max(path.stat().st_size for path in files)
    largest_horse_bytes = max(int(row["persistent_bytes"]) for row in horses)
    # For this exact sequential runner, reserve one complete observed campaign
    # plus one simultaneous temporary serialization of its largest artifact.
    recovery_margin_bytes = observed_run_bytes
    required_above_floor_bytes = recovery_margin_bytes + peak_atomic_payload_bytes
    observed_free_bytes = int(free_bytes) if free_bytes is not None else int(shutil.disk_usage(run_dir).free)
    available_above_floor_bytes = observed_free_bytes - floor_bytes
    positive_recovery_margin_bytes = available_above_floor_bytes - required_above_floor_bytes
    status = "SPACE_ENVELOPE_OPEN" if positive_recovery_margin_bytes >= 0 else "SPACE_ENVELOPE_CLOSED"

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "authority": MEASUREMENT_AUTHORITY,
        "run": {
            "path": str(run_dir),
            "manifest": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "config_hash": manifest.get("config_hash"),
            "arms": manifest.get("arms"),
            "seeds": config.get("seeds"),
            "observed_artifact_count": len(files),
            "observed_run_bytes": observed_run_bytes,
            "trained_horse_count": trained_horses,
            "largest_horse_bytes": largest_horse_bytes,
        },
        "implementation": {
            "runner_source": str(runner_source),
            "runner_sha256": sha256_file(runner_source),
            "checkpoint_helper_source": str(helper_source),
            "checkpoint_helper_sha256": sha256_file(helper_source),
            "atomic_contract_checks": contract,
        },
        "storage_envelope": {
            "observed_free_bytes": observed_free_bytes,
            "floor_bytes": floor_bytes,
            "available_above_floor_bytes": available_above_floor_bytes,
            "measured_peak_write_reserve_bytes": peak_atomic_payload_bytes,
            "recovery_margin_bytes": recovery_margin_bytes,
            "required_above_floor_bytes": required_above_floor_bytes,
            "positive_recovery_margin_bytes": positive_recovery_margin_bytes,
        },
        "horses": horses,
        "claim_boundary": (
            "This envelope is measured from one completed campaign and its hash-bound sequential "
            "two-slot runner. It applies only to a same-shape continuation. It does not authorize "
            "training, a larger model, parallel writers, promotion, merge, or partial unfreezing."
        ),
    }
    report["report_sha256"] = canonical_sha256(report)
    return report


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(pending, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--runner-source", required=True, type=Path)
    parser.add_argument("--checkpoint-helper-source", required=True, type=Path)
    parser.add_argument("--free-bytes", type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = measure_storage_envelope(
        run_dir=args.run_dir,
        runner_source=args.runner_source,
        helper_source=args.checkpoint_helper_source,
        free_bytes=args.free_bytes,
    )
    atomic_json(args.output, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "report_sha256": report["report_sha256"],
                **report["storage_envelope"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
