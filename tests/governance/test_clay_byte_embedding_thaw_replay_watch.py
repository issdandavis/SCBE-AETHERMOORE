from __future__ import annotations

import json
from pathlib import Path

import pytest

from python.scbe import clay_byte_embedding_thaw_replay as replay
from python.scbe import clay_byte_embedding_thaw_replay_watch as watch


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _run(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    run.mkdir()
    _write(run / "RUN_MANIFEST.json", {"schema": "fixture"})
    return run


def _inspect(run: Path, **kwargs) -> dict:
    return watch.inspect_or_replay(
        run,
        expected_verifier_sha256=watch.verifier_sha256(),
        **kwargs,
    )


def _passing_verifier(run: Path, *, tolerance: float, ledger_output: Path) -> dict:
    del tolerance
    ledger = replay.atomic_jsonl(
        ledger_output,
        [{"arm": "fixture", "seed": 1, "sample_id": "one"}],
    )
    return {
        "schema": replay.SCHEMA,
        "status": "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION",
        "authority": watch.AUTHORITY,
        "promotion": "NONE",
        "partial_unfreeze_authorized": False,
        "producer_result_sha256": watch.sha256_file(run / "RESULT.json"),
        "independent_verifier_sha256": watch.verifier_sha256(),
        "ledger": ledger,
        "errors": [],
    }


def test_waits_without_opening_partial_artifacts(tmp_path: Path) -> None:
    run = _run(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError((args, kwargs))

    state = _inspect(run, verifier=forbidden)
    assert state["status"] == "WAITING_FOR_ATOMIC_CAMPAIGN_RESULT"
    assert state["producer_result_exists"] is False
    assert state["ledger_output_exists"] is False


def test_runs_once_and_preserves_bound_receipt(tmp_path: Path) -> None:
    run = _run(tmp_path)
    _write(run / "RESULT.json", {"status": "COMPLETE"})
    first = _inspect(run, verifier=_passing_verifier)
    assert first["status"] == "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION"
    replay_sha = watch.sha256_file(run / "INDEPENDENT_REPLAY.json")
    ledger_sha = watch.sha256_file(run / "INDEPENDENT_REPLAY_LEDGER.jsonl")

    def forbidden(*args, **kwargs):
        raise AssertionError((args, kwargs))

    second = _inspect(run, verifier=forbidden)
    assert second["status"] == "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION"
    assert watch.sha256_file(run / "INDEPENDENT_REPLAY.json") == replay_sha
    assert watch.sha256_file(run / "INDEPENDENT_REPLAY_LEDGER.jsonl") == ledger_sha


def test_stale_producer_binding_is_preserved_for_review(tmp_path: Path) -> None:
    run = _run(tmp_path)
    _write(run / "RESULT.json", {"status": "COMPLETE"})
    _inspect(run, verifier=_passing_verifier)
    _write(run / "RESULT.json", {"status": "CHANGED"})
    state = _inspect(run, verifier=_passing_verifier)
    assert state["status"] == "STALE_OR_UNBOUND_REPLAY_REQUIRES_REVIEW"
    assert state["producer_binding_matches"] is False


def test_orphaned_ledger_is_not_overwritten(tmp_path: Path) -> None:
    run = _run(tmp_path)
    _write(run / "RESULT.json", {"status": "COMPLETE"})
    ledger = run / "INDEPENDENT_REPLAY_LEDGER.jsonl"
    ledger.write_text("fixture\n", encoding="utf-8")

    def forbidden(*args, **kwargs):
        raise AssertionError((args, kwargs))

    state = _inspect(run, verifier=forbidden)
    assert state["status"] == "ORPHANED_LEDGER_REQUIRES_REVIEW"
    assert ledger.read_text(encoding="utf-8") == "fixture\n"


def test_pinned_verifier_hash_rejects_source_drift_before_result(
    tmp_path: Path,
) -> None:
    run = _run(tmp_path)
    with pytest.raises(watch.VerifierHashMismatchError, match="SHA-256 mismatch"):
        watch.inspect_or_replay(
            run,
            expected_verifier_sha256="0" * 64,
        )
    assert not (run / "INDEPENDENT_REPLAY_WATCH_STATUS.json").exists()

    status_path = run / "PINNED_WATCH_STATUS.json"
    exit_code = watch.watch(
        run,
        expected_verifier_sha256="0" * 64,
        status_output=status_path,
        poll_seconds=60,
        once=True,
    )
    state = json.loads(status_path.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert state["status"] == "VERIFIER_SOURCE_HASH_MISMATCH_REVIEW_REQUIRED"
    assert state["expected_verifier_sha256"] == "0" * 64
    assert state["verifier_source_matches_expected"] is False


def test_expected_verifier_hash_must_be_sha256(tmp_path: Path) -> None:
    run = _run(tmp_path)
    with pytest.raises(ValueError, match="64 hexadecimal"):
        watch.inspect_or_replay(
            run,
            expected_verifier_sha256="not-a-digest",
        )
