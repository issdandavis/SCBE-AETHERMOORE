from __future__ import annotations

import json
from pathlib import Path

from python.scbe.clay_frozen_multiview_replay_watch import (
    inspect_or_replay,
    sha256_file,
    verifier_sha256,
    watch,
)


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _run(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    run.mkdir()
    _write(run / "RUN_MANIFEST.json", {"schema": "fixture"})
    _write(
        run / "STATUS.json",
        {"status": "RUNNING", "stage": "frozen_adapter_null", "seed": 7},
    )
    return run


def _passing_receipt(run: Path) -> dict:
    return {
        "status": "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION",
        "promotion": "NONE",
        "partial_unfreeze_authorized": False,
        "producer_result_sha256": sha256_file(run / "RESULT.json"),
        "independent_dataset_builder_sha256": verifier_sha256(),
        "errors": [],
    }


def test_waits_without_opening_partial_checkpoint_state(tmp_path: Path) -> None:
    run = _run(tmp_path)
    checkpoint = run / "horses" / "partial" / "slot-a.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"must remain unopened")
    called = False

    def verifier(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("verifier must not run before atomic campaign result")

    state = inspect_or_replay(run, verifier=verifier)

    assert state["status"] == "WAITING_FOR_ATOMIC_CAMPAIGN_RESULT"
    assert state["producer_result_exists"] is False
    assert called is False
    assert checkpoint.read_bytes() == b"must remain unopened"


def test_runs_and_seals_final_replay_once(tmp_path: Path) -> None:
    run = _run(tmp_path)
    _write(run / "RESULT.json", {"status": "COMPLETE"})
    calls = 0

    def verifier(path: Path, *, tolerance: float) -> dict:
        nonlocal calls
        calls += 1
        assert path == run.resolve()
        assert tolerance == 1e-12
        return _passing_receipt(run)

    first = inspect_or_replay(run, verifier=verifier)
    second = inspect_or_replay(run, verifier=verifier)

    assert first["status"] == "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION"
    assert second["status"] == "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION"
    assert calls == 1
    assert second["producer_binding_matches"] is True
    assert second["verifier_binding_matches"] is True


def test_preserves_stale_receipt_for_review(tmp_path: Path) -> None:
    run = _run(tmp_path)
    _write(run / "RESULT.json", {"status": "COMPLETE"})
    stale = _write(
        run / "INDEPENDENT_REPLAY.json",
        {
            "status": "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION",
            "producer_result_sha256": "0" * 64,
            "independent_dataset_builder_sha256": verifier_sha256(),
            "errors": [],
        },
    )
    before = stale.read_bytes()

    state = inspect_or_replay(
        run,
        verifier=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("stale receipt must not be overwritten")),
    )

    assert state["status"] == "STALE_OR_UNBOUND_REPLAY_REQUIRES_REVIEW"
    assert state["producer_binding_matches"] is False
    assert stale.read_bytes() == before


def test_fail_closed_when_replay_or_authority_fails(tmp_path: Path) -> None:
    run = _run(tmp_path)
    _write(run / "RESULT.json", {"status": "COMPLETE"})

    def verifier(path: Path, *, tolerance: float) -> dict:
        return {
            **_passing_receipt(run),
            "status": "FAIL_INDEPENDENT_INFERENCE_REPLAY",
            "promotion": "AUTHORIZED",
            "errors": ["fixture mismatch"],
        }

    state = inspect_or_replay(run, verifier=verifier)

    assert state["status"] == "REPLAY_FAILED_REVIEW_REQUIRED"
    assert state["replay_error_count"] == 1
    assert state["authority_boundary_passed"] is False
    assert state["authority"]["promotion"] == "NONE"


def test_existing_bound_receipt_cannot_claim_pass_with_errors(tmp_path: Path) -> None:
    run = _run(tmp_path)
    _write(run / "RESULT.json", {"status": "COMPLETE"})
    receipt = _passing_receipt(run)
    receipt["errors"] = ["contradictory pass receipt"]
    replay = _write(run / "INDEPENDENT_REPLAY.json", receipt)
    before = replay.read_bytes()

    state = inspect_or_replay(run)

    assert state["status"] == "REPLAY_FAILED_REVIEW_REQUIRED"
    assert state["producer_binding_matches"] is True
    assert state["verifier_binding_matches"] is True
    assert state["replay_error_count"] == 1
    assert replay.read_bytes() == before


def test_watcher_records_terminal_replay_exception_and_stops(tmp_path: Path) -> None:
    run = _run(tmp_path)
    _write(run / "RESULT.json", {"status": "COMPLETE"})

    def verifier(path: Path, *, tolerance: float) -> dict:
        raise RuntimeError("fixture replay failure")

    exit_code = watch(run, poll_seconds=60, once=True, verifier=verifier)
    state = json.loads((run / "INDEPENDENT_REPLAY_WATCH_STATUS.json").read_text(encoding="utf-8"))

    assert exit_code == 1
    assert state["status"] == "REPLAY_WATCH_ERROR_REVIEW_REQUIRED"
    assert state["error_type"] == "RuntimeError"
    assert state["authority"]["promotion"] == "NONE"
