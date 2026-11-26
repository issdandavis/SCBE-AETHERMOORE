"""Headless successor gate for the Clay byte-embedding thaw campaign.

The watcher starts no training until the frozen baseline has an atomic final
result, its independent replay and final-only watch receipt are hash-bound and
closed, and the configured floor-plus-reserve storage envelope is available.
The child is hidden, resume-safe, and writes all output to a bounded local log.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any


PASS_REPLAY_STATUS = "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION"
COMPLETE_WATCH_STATUS = "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(pending, path)


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def baseline_replay_evidence(baseline_run: Path) -> dict[str, Any]:
    result_path = baseline_run / "RESULT.json"
    replay_path = baseline_run / "INDEPENDENT_REPLAY.json"
    watch_path = baseline_run / "INDEPENDENT_REPLAY_WATCH_STATUS.json"
    evidence: dict[str, Any] = {
        "baseline_result": str(result_path),
        "baseline_replay": str(replay_path),
        "baseline_replay_watch": str(watch_path),
        "baseline_result_sha256": None,
        "baseline_replay_sha256": None,
        "baseline_replay_watch_sha256": None,
    }
    if not result_path.is_file():
        return {**evidence, "state": "WAITING_FOR_FROZEN_BASELINE"}

    result_sha256 = file_sha256(result_path)
    evidence["baseline_result_sha256"] = result_sha256
    if not replay_path.is_file() or not watch_path.is_file():
        return {
            **evidence,
            "state": "WAITING_FOR_BASELINE_INDEPENDENT_REPLAY",
        }

    replay_sha256 = file_sha256(replay_path)
    watch_sha256 = file_sha256(watch_path)
    evidence["baseline_replay_sha256"] = replay_sha256
    evidence["baseline_replay_watch_sha256"] = watch_sha256
    try:
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        watch = json.loads(watch_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        return {
            **evidence,
            "state": "BASELINE_INDEPENDENT_REPLAY_REVIEW_REQUIRED",
            "baseline_replay_error": f"{type(error).__name__}: {error}",
        }

    replay_ok = (
        replay.get("status") == PASS_REPLAY_STATUS
        and replay.get("producer_result_sha256") == result_sha256
        and replay.get("errors") == []
        and replay.get("promotion") == "NONE"
        and replay.get("partial_unfreeze_authorized") is False
    )
    watch_ok = (
        watch.get("status") == COMPLETE_WATCH_STATUS
        and watch.get("producer_result_sha256") == result_sha256
        and watch.get("replay_receipt_sha256") == replay_sha256
        and watch.get("replay_status") == PASS_REPLAY_STATUS
        and watch.get("replay_error_count") == 0
        and watch.get("authority_boundary_passed") is True
        and watch.get("verifier_contract_binding_matches") is True
        and watch.get("verifier_contract_stable_during_replay") is True
    )
    return {
        **evidence,
        "state": (
            "BASELINE_INDEPENDENT_REPLAY_CLOSED"
            if replay_ok and watch_ok
            else "BASELINE_INDEPENDENT_REPLAY_REVIEW_REQUIRED"
        ),
        "baseline_replay_status": replay.get("status"),
        "baseline_replay_error_count": len(replay.get("errors", [])),
        "baseline_replay_watch_status": watch.get("status"),
        "baseline_replay_binding_matches": replay.get("producer_result_sha256")
        == result_sha256,
        "baseline_replay_watch_binding_matches": watch.get(
            "replay_receipt_sha256"
        )
        == replay_sha256,
    }


def gate_state(
    *,
    baseline_run: Path,
    output_dir: Path,
    minimum_free_bytes: int,
    peak_write_reserve_bytes: int,
    recovery_margin_bytes: int,
) -> dict[str, Any]:
    free = shutil.disk_usage(output_dir.anchor or "C:/").free
    required = (
        minimum_free_bytes + peak_write_reserve_bytes + recovery_margin_bytes
    )
    storage = {
        "free_bytes": free,
        "floor_bytes": minimum_free_bytes,
        "minimum_free_bytes": minimum_free_bytes,
        "peak_write_reserve_bytes": peak_write_reserve_bytes,
        "recovery_margin_bytes": recovery_margin_bytes,
        "required_free_bytes": required,
        "remaining_margin_bytes": free - required,
        "storage_observed_at_utc": utc_now(),
    }
    if (output_dir / "RESULT.json").is_file():
        return {**storage, "state": "SUCCESSOR_COMPLETE"}
    replay = baseline_replay_evidence(baseline_run)
    if replay["state"] != "BASELINE_INDEPENDENT_REPLAY_CLOSED":
        return {**storage, **replay, "state": replay["state"]}
    if free < required:
        return {**storage, **replay, "state": "WAITING_FOR_STORAGE_ENVELOPE"}
    return {**storage, **replay, "state": "READY_TO_LAUNCH"}


def _rotate_log(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.stat().st_size > 2 * 1024 * 1024:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        previous = path.with_suffix(path.suffix + f".{stamp}.previous")
        path.replace(previous)


def run(args: argparse.Namespace) -> int:
    baseline_run = args.baseline_run.resolve(strict=True)
    campaign_script = args.campaign_script.resolve(strict=True)
    preregistration = args.preregistration.resolve(strict=True)
    output_dir = args.output_dir.resolve()
    status_path = args.status.resolve()
    log_path = args.log.resolve()
    minimum_free_bytes = int(args.minimum_free_gib * 1024**3)
    peak_write_reserve_bytes = int(args.peak_write_reserve_mib * 1024**2)
    recovery_margin_bytes = int(args.recovery_margin_mib * 1024**2)
    retries = 0
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    while True:
        gate = gate_state(
            baseline_run=baseline_run,
            output_dir=output_dir,
            minimum_free_bytes=minimum_free_bytes,
            peak_write_reserve_bytes=peak_write_reserve_bytes,
            recovery_margin_bytes=recovery_margin_bytes,
        )
        state = str(gate["state"])
        atomic_json(
            status_path,
            {
                "schema": "clay.byte-embedding-thaw-successor-gate.v1",
                **gate,
                "baseline_run": str(baseline_run),
                "output_dir": str(output_dir),
                "retries": retries,
                "updated_at_utc": utc_now(),
            },
        )
        if state == "SUCCESSOR_COMPLETE":
            return 0
        if state != "READY_TO_LAUNCH":
            time.sleep(args.poll_seconds)
            continue

        _rotate_log(log_path)
        python = Path(sys.executable)
        if python.name.lower() == "pythonw.exe":
            python = python.with_name("python.exe")
        command = [
            str(python),
            str(campaign_script),
            "--baseline-run",
            str(baseline_run),
            "--output-dir",
            str(output_dir),
            "--preregistration",
            str(preregistration),
            "--grow-steps",
            str(args.grow_steps),
            "--checkpoint-every",
            str(args.checkpoint_every),
            "--batch-size",
            str(args.batch_size),
            "--learning-rate",
            str(args.learning_rate),
            "--threads",
            str(args.threads),
            "--minimum-free-gib",
            str(args.minimum_free_gib),
            "--peak-write-reserve-mib",
            str(args.peak_write_reserve_mib),
            "--recovery-margin-mib",
            str(args.recovery_margin_mib),
        ]
        with log_path.open("ab", buffering=0) as output:
            output.write(f"\n[start {utc_now()}]\n".encode("utf-8"))
            completed = subprocess.run(
                command,
                cwd=str(campaign_script.parents[2]),
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=output,
                creationflags=flags,
            )
            output.write(f"\n[exit {completed.returncode}]\n".encode("utf-8"))
        if completed.returncode == 0 and (output_dir / "RESULT.json").is_file():
            continue
        retries += 1
        if retries >= args.maximum_retries:
            atomic_json(
                status_path,
                {
                    "schema": "clay.byte-embedding-thaw-successor-gate.v1",
                    "state": "STOPPED_AFTER_MAXIMUM_FAILED_LAUNCHES",
                    "baseline_run": str(baseline_run),
                    "output_dir": str(output_dir),
                    "free_bytes": shutil.disk_usage(output_dir.anchor or "C:/").free,
                    "floor_bytes": minimum_free_bytes,
                    "minimum_free_bytes": minimum_free_bytes,
                    "peak_write_reserve_bytes": peak_write_reserve_bytes,
                    "recovery_margin_bytes": recovery_margin_bytes,
                    "required_free_bytes": (
                        minimum_free_bytes
                        + peak_write_reserve_bytes
                        + recovery_margin_bytes
                    ),
                    "retries": retries,
                    "updated_at_utc": utc_now(),
                },
            )
            return 2
        time.sleep(args.retry_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--campaign-script", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--minimum-free-gib", type=float, default=25.0)
    parser.add_argument("--peak-write-reserve-mib", type=float, required=True)
    parser.add_argument("--recovery-margin-mib", type=float, required=True)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--retry-seconds", type=int, default=60)
    parser.add_argument("--maximum-retries", type=int, default=3)
    parser.add_argument("--grow-steps", type=int, default=18_000)
    parser.add_argument("--checkpoint-every", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=0.002)
    parser.add_argument("--threads", type=int, default=2)
    return parser.parse_args()


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
