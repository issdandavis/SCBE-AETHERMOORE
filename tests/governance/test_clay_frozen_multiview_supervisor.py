from __future__ import annotations

import json
from pathlib import Path

from python.scbe.clay_frozen_multiview_supervisor import (
    POINTER_SCHEMA,
    SupervisorContract,
    inspect_and_maybe_restart,
    sha256_file,
)


def _write(path: Path, value: str | dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, dict):
        path.write_text(json.dumps(value), encoding="utf-8")
    else:
        path.write_text(value, encoding="utf-8")
    return path


def _fixture(tmp_path: Path) -> SupervisorContract:
    root = tmp_path / "repo"
    run = tmp_path / "run"
    run.mkdir()
    runner = _write(root / "python" / "scbe" / "runner.py", "runner")
    builder = _write(root / "python" / "scbe" / "builder.py", "builder")
    preregistration = _write(root / "docs" / "prereg.md", "preregistered")
    training_cli = _write(
        root / "scripts" / "research" / "run_clay_frozen_multiview_adapter.py",
        "cli",
    )
    launcher = _write(tmp_path / "pc-health" / "run_headless.py", "launcher")
    config = {
        "seeds": [11, 12, 13],
        "data_seed": 7,
        "rows_per_view": 10,
        "holdout_rows": 15,
        "count_steps": 20,
        "grow_steps": 30,
        "checkpoint_every": 5,
        "batch_size": 4,
        "learning_rate": 0.002,
        "threads": 2,
        "source_dir": str(tmp_path / "source"),
    }
    Path(config["source_dir"]).mkdir()
    manifest = {
        "schema": "clay.frozen-multiview-adapter-campaign.v1.manifest",
        "runner": str(runner),
        "runner_sha256": sha256_file(runner),
        "data_builder": str(builder),
        "data_builder_sha256": sha256_file(builder),
        "preregistration": str(preregistration),
        "preregistration_sha256": sha256_file(preregistration),
        "minimum_free_gib": 25.0,
        "config": config,
    }
    manifest_path = _write(run / "RUN_MANIFEST.json", manifest)
    arguments = " ".join(
        [
            "-X utf8 -B",
            str(training_cli),
            "--output-dir",
            str(run),
            "--source-dir",
            config["source_dir"],
            "--preregistration",
            str(preregistration),
            "--seeds 11,12,13",
            "--data-seed 7",
            "--rows-per-view 10",
            "--holdout-rows 15",
            "--count-steps 20",
            "--grow-steps 30",
            "--checkpoint-every 5",
            "--batch-size 4",
            "--learning-rate 0.002",
            "--threads 2",
            "--minimum-free-gib 25.0",
        ]
    )
    executable = _write(tmp_path / "python.exe", "python")
    headless = _write(
        tmp_path / "headless.json",
        {
            "executable": str(executable),
            "arguments": arguments,
            "working_directory": str(root),
            "log": str(tmp_path / "headless.log"),
        },
    )
    return SupervisorContract(
        run_dir=run,
        run_manifest_sha256=sha256_file(manifest_path),
        headless_config=headless,
        headless_config_sha256=sha256_file(headless),
        headless_launcher=launcher,
        headless_launcher_sha256=sha256_file(launcher),
        training_cli=training_cli,
        training_cli_sha256=sha256_file(training_cli),
        status_output=run / "TRAINING_SUPERVISOR_STATUS.json",
        lock_path=run / "TRAINING_SUPERVISOR.lock",
        grace_seconds=0,
        startup_seconds=0,
    )


def _process(contract: SupervisorContract, pid: int = 123) -> dict:
    return {
        "ProcessId": pid,
        "ParentProcessId": 10,
        "ExecutablePath": "python.exe",
        "CommandLine": (f"python.exe {contract.training_cli} --output-dir {contract.run_dir}"),
    }


def _no_sleep(_: float) -> None:
    return None


def test_does_not_restart_when_atomic_campaign_result_exists(tmp_path: Path) -> None:
    contract = _fixture(tmp_path)
    _write(contract.run_dir / "RESULT.json", {"status": "COMPLETE"})
    launches = []

    state = inspect_and_maybe_restart(
        contract,
        process_lister=lambda: [],
        launcher=lambda value: launches.append(value) or 1,
        sleeper=_no_sleep,
    )

    assert state["status"] == "COMPLETE_RESULT_PRESENT_NO_RESTART"
    assert launches == []


def test_observes_matching_producer_without_launching(tmp_path: Path) -> None:
    contract = _fixture(tmp_path)
    launches = []

    state = inspect_and_maybe_restart(
        contract,
        process_lister=lambda: [_process(contract)],
        launcher=lambda value: launches.append(value) or 1,
        sleeper=_no_sleep,
    )

    assert state["status"] == "RUNNING_EXACT_PRODUCER"
    assert state["matching_trainers"][0]["pid"] == 123
    assert launches == []


def test_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    contract = _fixture(tmp_path)
    contract.training_cli.write_text("changed", encoding="utf-8")
    launches = []

    state = inspect_and_maybe_restart(
        contract,
        process_lister=lambda: [],
        launcher=lambda value: launches.append(value) or 1,
        sleeper=_no_sleep,
    )

    assert state["status"] == "INTEGRITY_BLOCKED_RESTART_NEEDS_REVIEW"
    assert "training CLI hash differs" in state["error_message"]
    assert launches == []


def test_checkpoint_pointer_mismatch_fails_closed(tmp_path: Path) -> None:
    contract = _fixture(tmp_path)
    directory = contract.run_dir / "horses" / "candidate" / "checkpoints"
    slot = _write(directory / "slot-a.pt", "checkpoint")
    _write(
        directory / "latest.json",
        {
            "schema": POINTER_SCHEMA,
            "slot": slot.name,
            "sha256": "0" * 64,
            "generation": 2,
            "step": 10,
        },
    )

    state = inspect_and_maybe_restart(
        contract,
        process_lister=lambda: [],
        sleeper=_no_sleep,
    )

    assert state["status"] == "INTEGRITY_BLOCKED_RESTART_NEEDS_REVIEW"
    assert "does not match its slot" in state["error_message"]


def test_storage_gate_blocks_restart(tmp_path: Path) -> None:
    contract = _fixture(tmp_path)
    launches = []

    state = inspect_and_maybe_restart(
        contract,
        process_lister=lambda: [],
        launcher=lambda value: launches.append(value) or 1,
        free_bytes=lambda _: 24 * 1024**3,
        sleeper=_no_sleep,
    )

    assert state["status"] == "STORAGE_GATE_BLOCKED_LOCAL_RESTART"
    assert state["cloud_failover"] == "ELIGIBLE_FOR_SEPARATE_PINNED_CLOUD_FAILOVER"
    assert launches == []


def test_launches_exactly_once_and_observes_restarted_producer(tmp_path: Path) -> None:
    contract = _fixture(tmp_path)
    launched = False
    launches = []

    def processes() -> list[dict]:
        return [_process(contract, 456)] if launched else []

    def launch(value: SupervisorContract) -> int:
        nonlocal launched
        launched = True
        launches.append(value)
        return 321

    state = inspect_and_maybe_restart(
        contract,
        process_lister=processes,
        launcher=launch,
        free_bytes=lambda _: 30 * 1024**3,
        sleeper=_no_sleep,
    )

    assert state["status"] == "RUNNING_AFTER_EXACT_RESTART"
    assert state["restart_count"] == 1
    assert state["wrapper_pid"] == 321
    assert state["matching_trainers"][0]["pid"] == 456
    assert len(launches) == 1


def test_restart_limit_prevents_another_launch(tmp_path: Path) -> None:
    contract = _fixture(tmp_path)
    first = inspect_and_maybe_restart(
        contract,
        process_lister=lambda: [],
        launcher=lambda _: 1,
        free_bytes=lambda _: 30 * 1024**3,
        sleeper=_no_sleep,
    )
    status = json.loads(contract.status_output.read_text(encoding="utf-8"))
    status["restart_count"] = contract.max_restarts
    status["last_restart_progress_signature"] = first["progress"]["signature_sha256"]
    contract.status_output.write_text(json.dumps(status), encoding="utf-8")
    launches = []

    state = inspect_and_maybe_restart(
        contract,
        process_lister=lambda: [],
        launcher=lambda value: launches.append(value) or 2,
        free_bytes=lambda _: 30 * 1024**3,
        sleeper=_no_sleep,
    )

    assert state["status"] == "RESTART_LIMIT_REACHED_NEEDS_REVIEW"
    assert state["restart_count"] == contract.max_restarts
    assert launches == []
