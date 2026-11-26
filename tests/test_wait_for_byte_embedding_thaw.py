from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from python.scbe.wait_for_byte_embedding_thaw import file_sha256, gate_state


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return path


def _seal_baseline(baseline: Path) -> tuple[str, str]:
    result = _write(baseline / "RESULT.json", {"status": "COMPLETE"})
    result_sha256 = file_sha256(result)
    replay = _write(
        baseline / "INDEPENDENT_REPLAY.json",
        {
            "status": "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION",
            "producer_result_sha256": result_sha256,
            "errors": [],
            "promotion": "NONE",
            "partial_unfreeze_authorized": False,
        },
    )
    replay_sha256 = file_sha256(replay)
    _write(
        baseline / "INDEPENDENT_REPLAY_WATCH_STATUS.json",
        {
            "status": "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION",
            "producer_result_sha256": result_sha256,
            "replay_receipt_sha256": replay_sha256,
            "replay_status": "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION",
            "replay_error_count": 0,
            "authority_boundary_passed": True,
            "verifier_contract_binding_matches": True,
            "verifier_contract_stable_during_replay": True,
        },
    )
    return result_sha256, replay_sha256


def _gate(baseline: Path, output: Path) -> dict:
    return gate_state(
        baseline_run=baseline,
        output_dir=output,
        minimum_free_bytes=25,
        peak_write_reserve_bytes=5,
        recovery_margin_bytes=10,
    )


def test_successor_completion_has_precedence(tmp_path: Path, monkeypatch) -> None:
    baseline = tmp_path / "baseline"
    output = tmp_path / "output"
    baseline.mkdir()
    output.mkdir()
    _write(output / "RESULT.json", {"status": "COMPLETE"})
    monkeypatch.setattr(
        "python.scbe.wait_for_byte_embedding_thaw.shutil.disk_usage",
        lambda _: SimpleNamespace(total=100, used=99, free=1),
    )

    state = _gate(baseline, output)

    assert state["state"] == "SUCCESSOR_COMPLETE"


def test_successor_waits_for_bound_independent_replay(tmp_path: Path, monkeypatch) -> None:
    baseline = tmp_path / "baseline"
    output = tmp_path / "output"
    baseline.mkdir()
    output.mkdir()
    monkeypatch.setattr(
        "python.scbe.wait_for_byte_embedding_thaw.shutil.disk_usage",
        lambda _: SimpleNamespace(total=100, used=50, free=50),
    )

    assert _gate(baseline, output)["state"] == "WAITING_FOR_FROZEN_BASELINE"
    _write(baseline / "RESULT.json", {"status": "COMPLETE"})
    assert _gate(baseline, output)["state"] == "WAITING_FOR_BASELINE_INDEPENDENT_REPLAY"
    _seal_baseline(baseline)
    replay = json.loads((baseline / "INDEPENDENT_REPLAY.json").read_text(encoding="utf-8"))
    replay["producer_result_sha256"] = "0" * 64
    _write(baseline / "INDEPENDENT_REPLAY.json", replay)

    state = _gate(baseline, output)

    assert state["state"] == "BASELINE_INDEPENDENT_REPLAY_REVIEW_REQUIRED"
    assert state["baseline_replay_binding_matches"] is False


def test_storage_envelope_requires_floor_reserve_and_recovery_margin(tmp_path: Path, monkeypatch) -> None:
    baseline = tmp_path / "baseline"
    output = tmp_path / "output"
    baseline.mkdir()
    output.mkdir()
    result_sha256, replay_sha256 = _seal_baseline(baseline)
    free = 39
    monkeypatch.setattr(
        "python.scbe.wait_for_byte_embedding_thaw.shutil.disk_usage",
        lambda _: SimpleNamespace(total=100, used=100 - free, free=free),
    )

    state = _gate(baseline, output)

    assert state["state"] == "WAITING_FOR_STORAGE_ENVELOPE"
    assert state["required_free_bytes"] == 40
    assert state["remaining_margin_bytes"] == -1
    assert state["baseline_result_sha256"] == result_sha256
    assert state["baseline_replay_sha256"] == replay_sha256


def test_storage_envelope_opens_at_exact_threshold(tmp_path: Path, monkeypatch) -> None:
    baseline = tmp_path / "baseline"
    output = tmp_path / "output"
    baseline.mkdir()
    output.mkdir()
    result_sha256, replay_sha256 = _seal_baseline(baseline)
    monkeypatch.setattr(
        "python.scbe.wait_for_byte_embedding_thaw.shutil.disk_usage",
        lambda _: SimpleNamespace(total=100, used=60, free=40),
    )

    state = _gate(baseline, output)

    assert state["state"] == "READY_TO_LAUNCH"
    assert state["remaining_margin_bytes"] == 0
    assert state["baseline_result_sha256"] == result_sha256
    assert state["baseline_replay_sha256"] == replay_sha256
    assert state["baseline_replay_watch_sha256"] == file_sha256(baseline / "INDEPENDENT_REPLAY_WATCH_STATUS.json")


def test_rejects_incomplete_replay_watch_receipt(tmp_path: Path, monkeypatch) -> None:
    baseline = tmp_path / "baseline"
    output = tmp_path / "output"
    baseline.mkdir()
    output.mkdir()
    _seal_baseline(baseline)
    watch = json.loads((baseline / "INDEPENDENT_REPLAY_WATCH_STATUS.json").read_text(encoding="utf-8"))
    watch["verifier_contract_stable_during_replay"] = False
    _write(baseline / "INDEPENDENT_REPLAY_WATCH_STATUS.json", watch)
    monkeypatch.setattr(
        "python.scbe.wait_for_byte_embedding_thaw.shutil.disk_usage",
        lambda _: SimpleNamespace(total=100, used=50, free=50),
    )

    state = _gate(baseline, output)

    assert state["state"] == "BASELINE_INDEPENDENT_REPLAY_REVIEW_REQUIRED"
