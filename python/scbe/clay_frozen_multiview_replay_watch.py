"""Final-only watcher for the frozen multi-view campaign's independent replay.

The watcher performs no training and never opens partial checkpoints. It waits
for the producer's atomic campaign RESULT.json, runs the separately implemented
inference replay once, seals a status receipt, and exits. Existing replay
receipts are never overwritten when their producer or verifier binding differs.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

import torch

from python.scbe import clay_frozen_multiview_replay as replay_module

SCHEMA = "clay.frozen-multiview-adapter-replay-watch.v1"
AUTHORITY = {
    "training": "NONE",
    "execution": "NONE",
    "promotion": "NONE",
    "partial_unfreeze": "NONE",
}
TERMINAL_STATUSES = {
    "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION",
    "REPLAY_FAILED_REVIEW_REQUIRED",
    "REPLAY_WATCH_ERROR_REVIEW_REQUIRED",
    "STALE_OR_UNBOUND_REPLAY_REQUIRES_REVIEW",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(pending, path)


def verifier_sha256() -> str:
    return sha256_file(Path(replay_module.__file__).resolve(strict=True))


def _campaign_state(run_dir: Path) -> dict[str, Any]:
    status_path = run_dir / "STATUS.json"
    if not status_path.is_file():
        return {}
    status = read_json(status_path)
    return {
        key: status[key]
        for key in ("status", "stage", "seed", "updated_at_utc")
        if key in status
    }


def _watch_state(
    *,
    run_dir: Path,
    status: str,
    producer_result: Path,
    replay_output: Path,
    **fields: Any,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "authority": AUTHORITY,
        "run_dir": str(run_dir),
        "producer_result": str(producer_result),
        "producer_result_exists": producer_result.is_file(),
        "replay_output": str(replay_output),
        "replay_output_exists": replay_output.is_file(),
        "campaign_state": _campaign_state(run_dir),
        **fields,
        "updated_at_utc": utc_now(),
    }


def inspect_or_replay(
    run_dir: Path,
    *,
    status_output: Path | None = None,
    replay_output: Path | None = None,
    tolerance: float = 1e-12,
    verifier: Callable[..., dict[str, Any]] = replay_module.verify_run,
) -> dict[str, Any]:
    """Inspect one campaign state and run final replay only when terminal."""

    run = run_dir.resolve(strict=True)
    if not (run / "RUN_MANIFEST.json").is_file():
        raise FileNotFoundError(run / "RUN_MANIFEST.json")
    status_path = (
        status_output or run / "INDEPENDENT_REPLAY_WATCH_STATUS.json"
    ).resolve()
    replay_path = (replay_output or run / "INDEPENDENT_REPLAY.json").resolve()
    producer_path = run / "RESULT.json"
    current_verifier_sha256 = verifier_sha256()

    if not producer_path.is_file():
        state = _watch_state(
            run_dir=run,
            status="WAITING_FOR_ATOMIC_CAMPAIGN_RESULT",
            producer_result=producer_path,
            replay_output=replay_path,
            verifier_sha256=current_verifier_sha256,
            claim_boundary=(
                "File-existence polling only; no checkpoint, labels, model state, "
                "optimizer state, or producer metrics were opened."
            ),
        )
        atomic_json(status_path, state)
        return state

    producer_sha256 = sha256_file(producer_path)
    if replay_path.is_file():
        receipt = read_json(replay_path)
        producer_bound = receipt.get("producer_result_sha256") == producer_sha256
        verifier_bound = (
            receipt.get("independent_dataset_builder_sha256") == current_verifier_sha256
        )
        receipt_errors = receipt.get("errors", [])
        authority_ok = (
            receipt.get("promotion") == "NONE"
            and receipt.get("partial_unfreeze_authorized") is False
        )
        if not (producer_bound and verifier_bound):
            status = "STALE_OR_UNBOUND_REPLAY_REQUIRES_REVIEW"
        elif (
            receipt.get("status") == "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION"
            and not receipt_errors
            and authority_ok
        ):
            status = "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION"
        else:
            status = "REPLAY_FAILED_REVIEW_REQUIRED"
        state = _watch_state(
            run_dir=run,
            status=status,
            producer_result=producer_path,
            replay_output=replay_path,
            producer_result_sha256=producer_sha256,
            verifier_sha256=current_verifier_sha256,
            replay_receipt_sha256=sha256_file(replay_path),
            producer_binding_matches=producer_bound,
            verifier_binding_matches=verifier_bound,
            replay_status=receipt.get("status"),
            replay_error_count=len(receipt_errors),
            authority_boundary_passed=authority_ok,
            claim_boundary="Existing replay receipt inspected read-only; it was not overwritten.",
        )
        atomic_json(status_path, state)
        return state

    running = _watch_state(
        run_dir=run,
        status="RUNNING_INDEPENDENT_REPLAY",
        producer_result=producer_path,
        replay_output=replay_path,
        producer_result_sha256=producer_sha256,
        verifier_sha256=current_verifier_sha256,
        claim_boundary="Independent measurement only; no promotion or partial unfreeze authority.",
    )
    atomic_json(status_path, running)
    receipt = verifier(run, tolerance=tolerance)
    atomic_json(replay_path, receipt)
    authority_ok = (
        receipt.get("promotion") == "NONE"
        and receipt.get("partial_unfreeze_authorized") is False
    )
    passed = (
        receipt.get("status") == "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION"
        and not receipt.get("errors")
        and authority_ok
    )
    state = _watch_state(
        run_dir=run,
        status=(
            "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION"
            if passed
            else "REPLAY_FAILED_REVIEW_REQUIRED"
        ),
        producer_result=producer_path,
        replay_output=replay_path,
        producer_result_sha256=producer_sha256,
        verifier_sha256=current_verifier_sha256,
        replay_receipt_sha256=sha256_file(replay_path),
        replay_status=receipt.get("status"),
        replay_error_count=len(receipt.get("errors", [])),
        authority_boundary_passed=authority_ok,
        claim_boundary=(
            "Final independent replay is evidence only. Selection, promotion, "
            "partial unfreeze, merging, and execution remain unauthorized."
        ),
    )
    atomic_json(status_path, state)
    return state


def watch(
    run_dir: Path,
    *,
    status_output: Path | None = None,
    replay_output: Path | None = None,
    tolerance: float = 1e-12,
    poll_seconds: int = 600,
    once: bool = False,
    verifier: Callable[..., dict[str, Any]] = replay_module.verify_run,
) -> int:
    if poll_seconds < 60:
        raise ValueError("poll_seconds must be at least 60")
    while True:
        try:
            state = inspect_or_replay(
                run_dir,
                status_output=status_output,
                replay_output=replay_output,
                tolerance=tolerance,
                verifier=verifier,
            )
        except Exception as error:
            run = run_dir.resolve()
            producer_path = run / "RESULT.json"
            replay_path = (replay_output or run / "INDEPENDENT_REPLAY.json").resolve()
            status_path = (
                status_output or run / "INDEPENDENT_REPLAY_WATCH_STATUS.json"
            ).resolve()
            terminal_error = producer_path.is_file()
            state = _watch_state(
                run_dir=run,
                status=(
                    "REPLAY_WATCH_ERROR_REVIEW_REQUIRED"
                    if terminal_error
                    else "REPLAY_WATCH_ERROR_RETRYING"
                ),
                producer_result=producer_path,
                replay_output=replay_path,
                error_type=type(error).__name__,
                error_message=str(error),
                claim_boundary=(
                    "Watcher failure cannot authorize a replay verdict, promotion, "
                    "or partial unfreeze."
                ),
            )
            atomic_json(status_path, state)
        print(
            json.dumps(
                {
                    "status": state["status"],
                    "producer_result_exists": state["producer_result_exists"],
                    "replay_output_exists": state["replay_output_exists"],
                },
                sort_keys=True,
            ),
            flush=True,
        )
        if once:
            return (
                0
                if state["status"]
                not in TERMINAL_STATUSES - {"COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION"}
                else 1
            )
        if state["status"] in TERMINAL_STATUSES:
            return (
                0
                if state["status"] == "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION"
                else 1
            )
        time.sleep(poll_seconds)


def configure_threads(threads: int) -> None:
    if threads < 1:
        raise ValueError("threads must be positive")
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
