"""Final-only watcher for the byte-embedding thaw independent replay.

The watcher polls only for the campaign's atomic RESULT.json. It never opens
partial checkpoints, never trains, and never overwrites an existing replay or
ledger whose producer/verifier binding requires review.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import json
from pathlib import Path
import time
from typing import Any

import torch

from python.scbe import clay_byte_embedding_thaw_replay as replay_module
from python.scbe.clay_frozen_multiview_replay_watch import (
    atomic_json,
    read_json,
    sha256_file,
    utc_now,
)


SCHEMA = "clay.byte-embedding-thaw-replay-watch.v1"
AUTHORITY = {
    "training": "NONE",
    "execution": "NONE",
    "merge": "NONE",
    "promotion": "NONE",
    "partial_unfreeze": "NONE",
}
TERMINAL_STATUSES = {
    "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION",
    "REPLAY_FAILED_REVIEW_REQUIRED",
    "REPLAY_WATCH_ERROR_REVIEW_REQUIRED",
    "VERIFIER_SOURCE_HASH_MISMATCH_REVIEW_REQUIRED",
    "STALE_OR_UNBOUND_REPLAY_REQUIRES_REVIEW",
    "ORPHANED_LEDGER_REQUIRES_REVIEW",
}


class VerifierHashMismatchError(RuntimeError):
    """The pinned replay verifier differs from the source on disk."""


def verifier_sha256() -> str:
    return sha256_file(Path(replay_module.__file__).resolve(strict=True))


def validate_verifier_sha256(expected: str) -> str:
    normalized = expected.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError("expected verifier SHA-256 must be 64 hexadecimal characters")
    current = verifier_sha256()
    if current != normalized:
        raise VerifierHashMismatchError(
            f"replay verifier SHA-256 mismatch: expected {normalized}, found {current}"
        )
    return current


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
    ledger_output: Path,
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
        "ledger_output": str(ledger_output),
        "ledger_output_exists": ledger_output.is_file(),
        "campaign_state": _campaign_state(run_dir),
        **fields,
        "updated_at_utc": utc_now(),
    }


def _receipt_state(
    *,
    run: Path,
    producer_path: Path,
    replay_path: Path,
    ledger_path: Path,
    expected_verifier_sha256: str,
) -> dict[str, Any]:
    receipt = read_json(replay_path)
    producer_sha256 = sha256_file(producer_path)
    current_verifier_sha256 = validate_verifier_sha256(expected_verifier_sha256)
    producer_bound = receipt.get("producer_result_sha256") == producer_sha256
    verifier_bound = (
        receipt.get("independent_verifier_sha256")
        == expected_verifier_sha256.lower()
        == current_verifier_sha256
    )
    ledger = receipt.get("ledger") if isinstance(receipt.get("ledger"), dict) else {}
    ledger_bound = (
        ledger_path.is_file()
        and ledger.get("path") == str(ledger_path)
        and ledger.get("sha256") == sha256_file(ledger_path)
    )
    authority_ok = (
        receipt.get("promotion") == "NONE"
        and receipt.get("partial_unfreeze_authorized") is False
        and receipt.get("authority") == AUTHORITY
    )
    errors = receipt.get("errors") if isinstance(receipt.get("errors"), list) else [
        "malformed error list"
    ]
    if not (producer_bound and verifier_bound and ledger_bound):
        status = "STALE_OR_UNBOUND_REPLAY_REQUIRES_REVIEW"
    elif (
        receipt.get("status") == "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION"
        and not errors
        and authority_ok
    ):
        status = "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION"
    else:
        status = "REPLAY_FAILED_REVIEW_REQUIRED"
    return _watch_state(
        run_dir=run,
        status=status,
        producer_result=producer_path,
        replay_output=replay_path,
        ledger_output=ledger_path,
        producer_result_sha256=producer_sha256,
        verifier_sha256=current_verifier_sha256,
        expected_verifier_sha256=expected_verifier_sha256.lower(),
        verifier_source_matches_expected=True,
        replay_receipt_sha256=sha256_file(replay_path),
        ledger_receipt_sha256=sha256_file(ledger_path) if ledger_path.is_file() else None,
        producer_binding_matches=producer_bound,
        verifier_binding_matches=verifier_bound,
        ledger_binding_matches=ledger_bound,
        replay_status=receipt.get("status"),
        replay_error_count=len(errors),
        authority_boundary_passed=authority_ok,
        claim_boundary="Existing replay and ledger inspected read-only; neither was overwritten.",
    )


def inspect_or_replay(
    run_dir: Path,
    *,
    expected_verifier_sha256: str,
    status_output: Path | None = None,
    replay_output: Path | None = None,
    ledger_output: Path | None = None,
    tolerance: float = 1e-12,
    verifier: Callable[..., dict[str, Any]] = replay_module.verify_run,
) -> dict[str, Any]:
    run = run_dir.resolve(strict=True)
    if not (run / "RUN_MANIFEST.json").is_file():
        raise FileNotFoundError(run / "RUN_MANIFEST.json")
    current_verifier_sha256 = validate_verifier_sha256(
        expected_verifier_sha256
    )
    status_path = (
        status_output or run / "INDEPENDENT_REPLAY_WATCH_STATUS.json"
    ).resolve()
    replay_path = (replay_output or run / "INDEPENDENT_REPLAY.json").resolve()
    ledger_path = (
        ledger_output or run / "INDEPENDENT_REPLAY_LEDGER.jsonl"
    ).resolve()
    producer_path = run / "RESULT.json"

    if not producer_path.is_file():
        state = _watch_state(
            run_dir=run,
            status="WAITING_FOR_ATOMIC_CAMPAIGN_RESULT",
            producer_result=producer_path,
            replay_output=replay_path,
            ledger_output=ledger_path,
            verifier_sha256=current_verifier_sha256,
            expected_verifier_sha256=expected_verifier_sha256.lower(),
            verifier_source_matches_expected=True,
            claim_boundary=(
                "File-existence polling only; no checkpoint, horse result, model "
                "state, prediction, or producer metric was opened."
            ),
        )
        atomic_json(status_path, state)
        return state

    if replay_path.is_file():
        state = _receipt_state(
            run=run,
            producer_path=producer_path,
            replay_path=replay_path,
            ledger_path=ledger_path,
            expected_verifier_sha256=expected_verifier_sha256,
        )
        atomic_json(status_path, state)
        return state

    if ledger_path.is_file():
        state = _watch_state(
            run_dir=run,
            status="ORPHANED_LEDGER_REQUIRES_REVIEW",
            producer_result=producer_path,
            replay_output=replay_path,
            ledger_output=ledger_path,
            producer_result_sha256=sha256_file(producer_path),
            verifier_sha256=current_verifier_sha256,
            expected_verifier_sha256=expected_verifier_sha256.lower(),
            verifier_source_matches_expected=True,
            ledger_receipt_sha256=sha256_file(ledger_path),
            claim_boundary="An unbound ledger is preserved; replay was not rerun.",
        )
        atomic_json(status_path, state)
        return state

    running = _watch_state(
        run_dir=run,
        status="RUNNING_INDEPENDENT_REPLAY",
        producer_result=producer_path,
        replay_output=replay_path,
        ledger_output=ledger_path,
        producer_result_sha256=sha256_file(producer_path),
        verifier_sha256=current_verifier_sha256,
        expected_verifier_sha256=expected_verifier_sha256.lower(),
        verifier_source_matches_expected=True,
        claim_boundary="Independent measurement only; every authority remains NONE.",
    )
    atomic_json(status_path, running)
    receipt = verifier(run, tolerance=tolerance, ledger_output=ledger_path)
    atomic_json(replay_path, receipt)
    state = _receipt_state(
        run=run,
        producer_path=producer_path,
        replay_path=replay_path,
        ledger_path=ledger_path,
        expected_verifier_sha256=expected_verifier_sha256,
    )
    atomic_json(status_path, state)
    return state


def watch(
    run_dir: Path,
    *,
    expected_verifier_sha256: str,
    status_output: Path | None = None,
    replay_output: Path | None = None,
    ledger_output: Path | None = None,
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
                expected_verifier_sha256=expected_verifier_sha256,
                status_output=status_output,
                replay_output=replay_output,
                ledger_output=ledger_output,
                tolerance=tolerance,
                verifier=verifier,
            )
        except Exception as error:
            run = run_dir.resolve()
            producer_path = run / "RESULT.json"
            replay_path = (replay_output or run / "INDEPENDENT_REPLAY.json").resolve()
            ledger_path = (
                ledger_output or run / "INDEPENDENT_REPLAY_LEDGER.jsonl"
            ).resolve()
            status_path = (
                status_output or run / "INDEPENDENT_REPLAY_WATCH_STATUS.json"
            ).resolve()
            terminal_error = producer_path.is_file()
            verifier_hash_mismatch = isinstance(error, VerifierHashMismatchError)
            state = _watch_state(
                run_dir=run,
                status=(
                    "VERIFIER_SOURCE_HASH_MISMATCH_REVIEW_REQUIRED"
                    if verifier_hash_mismatch
                    else (
                        "REPLAY_WATCH_ERROR_REVIEW_REQUIRED"
                        if terminal_error
                        else "REPLAY_WATCH_ERROR_RETRYING"
                    )
                ),
                producer_result=producer_path,
                replay_output=replay_path,
                ledger_output=ledger_path,
                error_type=type(error).__name__,
                error_message=str(error),
                expected_verifier_sha256=expected_verifier_sha256.lower(),
                verifier_sha256=verifier_sha256(),
                verifier_source_matches_expected=False
                if verifier_hash_mismatch
                else None,
                claim_boundary="Watcher failure grants no replay verdict or authority.",
            )
            atomic_json(status_path, state)
        print(
            json.dumps(
                {
                    "status": state["status"],
                    "producer_result_exists": state["producer_result_exists"],
                    "replay_output_exists": state["replay_output_exists"],
                    "ledger_output_exists": state["ledger_output_exists"],
                },
                sort_keys=True,
            ),
            flush=True,
        )
        if once:
            return 0 if state["status"] not in TERMINAL_STATUSES - {
                "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION"
            } else 1
        if state["status"] in TERMINAL_STATUSES:
            return (
                0
                if state["status"] == "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION"
                else 1
            )
        time.sleep(poll_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--status-output", type=Path)
    parser.add_argument("--replay-output", type=Path)
    parser.add_argument("--ledger-output", type=Path)
    parser.add_argument("--verifier-sha256", required=True)
    parser.add_argument("--tolerance", type=float, default=1e-12)
    parser.add_argument("--poll-seconds", type=int, default=600)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.threads < 1:
        raise ValueError("threads must be positive")
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)
    return watch(
        args.run_dir,
        expected_verifier_sha256=args.verifier_sha256,
        status_output=args.status_output,
        replay_output=args.replay_output,
        ledger_output=args.ledger_output,
        tolerance=args.tolerance,
        poll_seconds=args.poll_seconds,
        once=args.once,
    )


if __name__ == "__main__":
    raise SystemExit(main())
