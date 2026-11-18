from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

import pytest
import torch

from python.scbe.clay_frozen_multiview_adapter import (
    FrozenActionModel,
    RunConfig,
    frozen_state,
    frozen_state_identical,
    stable_hash,
)
from python.scbe.clay_frozen_multiview_data import BYTE_TOKEN_BASE
from python.scbe.clay_prime_scissor_input import (
    ARMS,
    ActionGatedPrimeScissorInput,
    build_feature_tables,
    build_occurrence_derangement,
)
from python.scbe.clay_prime_scissor_input_campaign import (
    CLAY_MATH_COMMIT,
    PrimeScissorCampaignConfig,
    _preflight_rows,
    aggregate,
    candidate_has_no_hidden_zero_slices,
    clay_math_provenance,
    parse_args,
    require_storage,
    run_mechanics_preflight,
    sample_blocked_prediction_comparison,
    train_feature_steps,
    verify_preflight_authority,
)
from python.scbe.concept_exposure_ledger import ConceptExposureLedger


def _vocab() -> list[str]:
    controls = ["\x00", "\x02", "\x1f", "\x03", "K", " ", ":", "=", ">", *list("01234")]
    return controls + [chr(BYTE_TOKEN_BASE + value) for value in range(256)]


def _config() -> RunConfig:
    return RunConfig(
        seeds=(101, 102, 103),
        data_seed=7,
        rows_per_view=5,
        holdout_rows=5,
        count_steps=1,
        grow_steps=2,
        checkpoint_every=1,
        batch_size=5,
        learning_rate=0.002,
        threads=1,
        device="cpu",
        source_dir="synthetic",
        source_hashes={"synthetic": "0" * 64},
        dataset_manifest_sha256="1" * 64,
        arms=ARMS,
    )


def _ledger(rows):
    return ConceptExposureLedger(
        [row.sample for row in rows],
        gradient_width=5,
        minimum_exposures_per_concept=1,
    )


def test_storage_floor_cannot_be_lowered(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot be below 25.0"):
        require_storage(tmp_path, 24.99)


def test_calibration_only_is_an_explicit_mutually_exclusive_execution_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "runner",
            "--baseline-run",
            "baseline",
            "--output-dir",
            "output",
            "--preregistration",
            "prereg.md",
            "--preflight-receipt",
            "preflight.json",
            "--clay-math-root",
            "clay-math",
            "--source-dir",
            "source",
            "--calibration-only",
        ],
    )
    args = parse_args()
    assert args.calibration_only
    assert not args.aggregate_only


def test_clay_math_provenance_is_exact_clean_commit() -> None:
    root = Path(r"C:\dev\_wt_clay_debruijn_shell_20261118")
    receipt = clay_math_provenance(root)
    assert receipt["commit"] == CLAY_MATH_COMMIT
    assert receipt["mode"] == "clean-git-commit-and-file-hashes"
    assert set(receipt["source_hashes"]) == {
        "prime_lane_scissors.py",
        "universal_cycle_curriculum.py",
        "universal_prime_scissors.py",
    }


def test_two_slot_resume_extends_same_horse_and_preserves_frozen_parent(
    tmp_path: Path,
) -> None:
    rows = _preflight_rows("train")
    binding = build_occurrence_derangement(rows, seed=771, split_name="preflight")
    tables = build_feature_tables()
    vocab = _vocab()
    stoi = {token: index for index, token in enumerate(vocab)}
    torch.manual_seed(101)
    parent = FrozenActionModel(len(vocab))
    parent_state = parent.state_dict()

    first = ActionGatedPrimeScissorInput(vocab, arm="prime_scissor_input", tables=tables)
    first.load_parent_state(parent_state)
    before = frozen_state(first)
    step, _, count = train_feature_steps(
        model=first,
        arm="prime_scissor_input",
        seed=101,
        rows=rows,
        binding=binding,
        ledger=_ledger(rows),
        stoi=stoi,
        config=_config(),
        total_steps=1,
        checkpoint_dir=tmp_path / "checkpoints",
        config_hash="2" * 64,
    )
    assert step == 1
    assert count > 0
    assert frozen_state_identical(before, first)

    resumed = ActionGatedPrimeScissorInput(vocab, arm="prime_scissor_input", tables=tables)
    resumed.load_parent_state(parent_state)
    step, _, resumed_count = train_feature_steps(
        model=resumed,
        arm="prime_scissor_input",
        seed=101,
        rows=rows,
        binding=binding,
        ledger=_ledger(rows),
        stoi=stoi,
        config=_config(),
        total_steps=2,
        checkpoint_dir=tmp_path / "checkpoints",
        config_hash="2" * 64,
    )
    assert step == 2
    assert resumed_count == count
    assert frozen_state_identical(before, resumed)
    assert (tmp_path / "checkpoints" / "latest.json").is_file()


def test_three_seed_five_arm_mechanics_preflight_passes() -> None:
    result = run_mechanics_preflight()
    assert result["status"] == "PASS"
    assert result["evidence"] == "SYNTHETIC_MECHANICS_ONLY_NOT_CAPABILITY_EVIDENCE"
    assert result["seeds"] == [101, 102, 103]
    assert result["arms"] == list(ARMS)
    assert len(result["records"]) == 15
    assert all(row["parent_preserved"] for row in result["records"])


def _prediction_horses(*, candidate: bool, losing_seed: int | None = None):
    horses = []
    for seed in (101, 102, 103):
        predictions = []
        for index in range(20):
            correct = candidate
            if losing_seed == seed:
                correct = False
            predictions.append(
                {
                    "sample_id": f"held-{index}",
                    "example_index": index,
                    "correct": correct,
                }
            )
        horses.append({"seed": seed, "predictions": predictions})
    return horses


def test_sample_blocked_gate_uses_held_examples_and_requires_three_of_three_seeds() -> None:
    control = _prediction_horses(candidate=False)
    passing = sample_blocked_prediction_comparison(_prediction_horses(candidate=True), control)
    assert passing["sample_blocks"] == 20
    assert passing["wins"] == 20
    assert passing["per_seed_direction_3_of_3"]
    assert passing["clears_finite_uncertainty_gate"]

    failing = sample_blocked_prediction_comparison(_prediction_horses(candidate=True, losing_seed=103), control)
    assert not failing["per_seed_direction_3_of_3"]
    assert not failing["clears_finite_uncertainty_gate"]


def test_aggregate_rejects_horses_from_a_different_runner_revision() -> None:
    campaign = PrimeScissorCampaignConfig(
        baseline_run="baseline",
        baseline_manifest_sha256="1" * 64,
        baseline_result_sha256="2" * 64,
        dataset_manifest_sha256="3" * 64,
        train_occurrence_binding_sha256="4" * 64,
        holdout_occurrence_binding_sha256="5" * 64,
        feature_table_receipt_sha256="6" * 64,
        runner_sha256="7" * 64,
        input_module_sha256="8" * 64,
        preregistration_sha256="9" * 64,
        preflight_receipt_sha256="d" * 64,
        clay_math_commit=CLAY_MATH_COMMIT,
        clay_math_source_hashes={"component": "a" * 64},
        seeds=(101, 102, 103),
        grow_steps=18_000,
        checkpoint_every=500,
        batch_size=128,
        learning_rate=0.002,
        threads=2,
        requested_device="auto",
        actual_device="cuda",
        source_dir_authority="hashes",
        source_hashes={"source": "b" * 64},
    )
    old_revision = replace(campaign, runner_sha256="c" * 64)
    old_hash = stable_hash(asdict(old_revision))
    rows = [{"arm": arm, "seed": seed, "config_hash": old_hash} for seed in campaign.seeds for arm in ARMS]
    with pytest.raises(RuntimeError, match="config-mismatched horse"):
        aggregate(rows, campaign)


def test_candidate_hidden_zero_gate_checks_every_seed_action_and_sector() -> None:
    healthy = [
        {
            "metrics": {
                "worst_action_accuracy": 0.1,
                "per_sector_accuracy": {"0": 0.2, "1": 0.3},
            }
        }
        for _ in range(3)
    ]
    assert candidate_has_no_hidden_zero_slices(healthy)
    hidden_action = [dict(row) for row in healthy]
    hidden_action[1] = {
        "metrics": {
            "worst_action_accuracy": 0.0,
            "per_sector_accuracy": {"0": 0.2, "1": 0.3},
        }
    }
    assert not candidate_has_no_hidden_zero_slices(hidden_action)
    hidden_sector = [dict(row) for row in healthy]
    hidden_sector[2] = {
        "metrics": {
            "worst_action_accuracy": 0.1,
            "per_sector_accuracy": {"0": 0.2, "1": 0.0},
        }
    }
    assert not candidate_has_no_hidden_zero_slices(hidden_sector)


def test_preflight_authority_rejects_a_regenerated_table_mismatch() -> None:
    path = Path(__file__).parents[1] / "docs" / "research" / "CLAY_PRIME_SCISSOR_INPUT_PREFLIGHT_20261118.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    actual = {
        "dataset_manifest_sha256": receipt["dataset_manifest_sha256"],
        "feature_receipt_sha256": receipt["feature_tables"]["feature_receipt_sha256"],
        "table_sha256": {
            "prime_scissor": receipt["feature_tables"]["prime_scissor_sha256"],
            "canonical_onehot_matched": receipt["feature_tables"]["canonical_onehot_matched_sha256"],
            "deterministic_random_matched": receipt["feature_tables"]["deterministic_random_matched_sha256"],
            "no_intervention": receipt["feature_tables"]["no_intervention_sha256"],
        },
        "pivot_indices_sha256": receipt["feature_tables"]["pivot_indices_sha256"],
        "pivot_descriptors_sha256": receipt["feature_tables"]["pivot_descriptors_sha256"],
        "empirical_conditioning_receipt_sha256": receipt["empirical_conditioning_receipt_sha256"],
        "train_binding_seal_sha256": receipt["train_binding"]["seal_sha256"],
        "train_binding_mapped_sha256": receipt["train_binding"]["mapped_values_sha256"],
        "holdout_binding_seal_sha256": receipt["holdout_binding"]["seal_sha256"],
        "holdout_binding_mapped_sha256": receipt["holdout_binding"]["mapped_values_sha256"],
    }
    verify_preflight_authority(receipt, actual)
    mismatched = dict(actual)
    mismatched["table_sha256"] = {
        **actual["table_sha256"],
        "deterministic_random_matched": "0" * 64,
    }
    with pytest.raises(RuntimeError, match="differ from the preflight receipt") as error:
        verify_preflight_authority(receipt, mismatched)
    assert "table_sha256.deterministic_random_matched" in str(error.value)
    assert receipt["feature_tables"]["deterministic_random_matched_sha256"] in str(error.value)
    assert "0" * 64 in str(error.value)
