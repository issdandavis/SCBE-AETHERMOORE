from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


HERE = Path(__file__).resolve().parent
RUNNER_PATH = HERE / "run_operand_context_kaggle.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("tested_operand_context_release", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_packet_is_private_offline_cpu_and_launch_disabled() -> None:
    metadata = json.loads((HERE / "kernel-metadata.json").read_text(encoding="utf-8"))
    admission = json.loads((HERE / "EXECUTION_ADMISSION.json").read_text(encoding="utf-8"))
    assert metadata["is_private"] is True
    assert metadata["enable_internet"] is False
    assert metadata["enable_gpu"] is False
    assert metadata["dataset_sources"] == [
        "issacizrealdavis/clay-input-access-efficacy-input-20261119"
    ]
    assert admission["state"] == "NOT_CONSUMED"
    assert admission["execution_authorized"] is False
    assert admission["consumed_at_utc"] is None


def test_reviewed_sources_are_byte_exact_and_execution_fails_closed() -> None:
    runner = load_runner()
    assert runner.verify_sources() == runner.EXPECTED_SOURCE_HASHES
    with pytest.raises(RuntimeError, match="staged but not authorized"):
        runner.require_execution_admission()


def test_contract_matches_reviewed_preregistration() -> None:
    runner = load_runner()
    prereg = json.loads(runner.PREREGISTRATION_PATH.read_text(encoding="utf-8"))
    assert tuple(prereg["training_contract"]["seeds"]) == runner.SEEDS
    assert prereg["training_contract"]["updates_per_trained_arm"] == runner.UPDATES
    assert prereg["training_contract"]["checkpoint_every"] == runner.CHECKPOINT_EVERY
    assert prereg["training_contract"]["batch_size"] == runner.BATCH_SIZE
    assert prereg["training_contract"]["learning_rate"] == runner.LEARNING_RATE
    assert prereg["mechanism_change"]["exact_trainable_parameters_per_trained_arm"] == (
        runner.EXPECTED_TRAINABLE
    )
    assert runner.TRAINED_ARMS == ("candidate", "context_permuted", "target_shuffle")
    assert runner.ARMS[-1] == "zero_update"


def test_local_smoke_proves_mechanics_without_parent_or_cloud(tmp_path: Path) -> None:
    output = tmp_path / "SMOKE.json"
    completed = subprocess.run(
        [sys.executable, str(RUNNER_PATH), "--smoke-output", str(output)],
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS_NO_PARENT_LOAD_NO_CLOUD_EXECUTION"
    assert receipt["cloud_execution"] is False
    assert receipt["admission_state"] == "NOT_CONSUMED"
    assert receipt["campaign_trainable_parameters"] == 142_164
    assert receipt["matched_initialization"] is True
    assert receipt["frozen_tensors_bit_identical_after_synthetic_update"] is True


def test_release_has_no_kaggle_mutator_or_network_client() -> None:
    texts = [
        RUNNER_PATH.read_text(encoding="utf-8"),
        (HERE / "independent_replay.py").read_text(encoding="utf-8"),
    ]
    forbidden = (
        "kernels push",
        "dataset_create",
        "dataset_new",
        "competition_submit",
        "requests.",
        "urllib.request",
        "http://",
        "https://",
    )
    for text in texts:
        assert all(token not in text for token in forbidden)


def test_two_slot_resume_state_is_preserved() -> None:
    text = RUNNER_PATH.read_text(encoding="utf-8")
    for token in (
        "core.TwoSlotCheckpoint",
        '"optimizer_state": optimizer.state_dict()',
        '"sampler_state": sampler.state_dict()',
        '"torch_rng_state": torch.get_rng_state()',
        'optimizer.load_state_dict(payload["optimizer_state"])',
        'sampler.load_state_dict(payload["sampler_state"])',
        'torch.set_rng_state(payload["torch_rng_state"])',
    ):
        assert token in text
