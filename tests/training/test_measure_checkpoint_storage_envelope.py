from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.training.measure_checkpoint_storage_envelope import measure_storage_envelope


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    run = tmp_path / "run"
    horse = run / "horses" / "candidate-seed-1"
    checkpoints = horse / "checkpoints"
    checkpoints.mkdir(parents=True)
    manifest = {
        "arms": ["candidate"],
        "config_hash": "a" * 64,
        "config": {"minimum_free_bytes": 1_000, "seeds": [1]},
    }
    (run / "RUN_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    (checkpoints / "slot-a.pt").write_bytes(b"a" * 500)
    (checkpoints / "slot-b.pt").write_bytes(b"b" * 480)
    (checkpoints / "latest.json").write_text("{}", encoding="utf-8")
    (horse / "MODEL.pt").write_bytes(b"m" * 300)
    (horse / "PREDICTIONS.jsonl").write_bytes(b"p" * 100)
    (horse / "RESULT.json").write_text("{}", encoding="utf-8")
    runner = tmp_path / "runner.py"
    runner.write_text("TwoSlotCheckpoint(path)\natomic_torch_save(path, value)\n", encoding="utf-8")
    helper = tmp_path / "helper.py"
    helper.write_text(
        "class TwoSlotCheckpoint:\n"
        "    slots = ('slot-a.pt', 'slot-b.pt')\n"
        "def atomic_torch_save(path, value):\n"
        "    temp = '.tmp'\n"
        "    os.replace(temp, path)\n",
        encoding="utf-8",
    )
    return run, runner, helper


def test_opens_only_after_full_observed_campaign_and_peak_temp_fit(tmp_path: Path) -> None:
    run, runner, helper = _fixture(tmp_path)
    probe = measure_storage_envelope(run_dir=run, runner_source=runner, helper_source=helper, free_bytes=10_000)
    required = probe["storage_envelope"]["required_above_floor_bytes"]
    report = measure_storage_envelope(
        run_dir=run,
        runner_source=runner,
        helper_source=helper,
        free_bytes=1_000 + required,
    )
    assert report["status"] == "SPACE_ENVELOPE_OPEN"
    assert report["storage_envelope"]["positive_recovery_margin_bytes"] == 0
    assert report["storage_envelope"]["measured_peak_write_reserve_bytes"] == 500
    assert report["run"]["trained_horse_count"] == 1
    assert report["authority"] == "MEASUREMENT_ONLY_NO_TRAINING_AUTHORITY"


def test_closes_one_byte_below_required_envelope(tmp_path: Path) -> None:
    run, runner, helper = _fixture(tmp_path)
    probe = measure_storage_envelope(run_dir=run, runner_source=runner, helper_source=helper, free_bytes=10_000)
    required = probe["storage_envelope"]["required_above_floor_bytes"]
    report = measure_storage_envelope(
        run_dir=run,
        runner_source=runner,
        helper_source=helper,
        free_bytes=1_000 + required - 1,
    )
    assert report["status"] == "SPACE_ENVELOPE_CLOSED"
    assert report["storage_envelope"]["positive_recovery_margin_bytes"] == -1


def test_rejects_pending_atomic_write(tmp_path: Path) -> None:
    run, runner, helper = _fixture(tmp_path)
    (run / ".MODEL.pt.9.tmp").write_bytes(b"unfinished")
    with pytest.raises(ValueError, match="pending writes"):
        measure_storage_envelope(run_dir=run, runner_source=runner, helper_source=helper, free_bytes=10_000)


def test_rejects_incomplete_atomic_contract(tmp_path: Path) -> None:
    run, runner, helper = _fixture(tmp_path)
    helper.write_text("def atomic_torch_save(path, value): pass\n", encoding="utf-8")
    with pytest.raises(ValueError, match="atomic checkpoint contract is incomplete"):
        measure_storage_envelope(run_dir=run, runner_source=runner, helper_source=helper, free_bytes=10_000)
