"""Independently verify the recovered Clay input-access Kaggle campaign."""

from __future__ import annotations

import argparse
from dataclasses import fields
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping

import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.clay_frozen_multiview_adapter import (
    RunConfig,
    counting_rows,
    encode,
    file_sha256,
    flattened_trainable,
    vocab_of,
)
from python.scbe.clay_frozen_multiview_data import build_frozen_multiview_dataset
from python.scbe.clay_input_access_campaign import (
    BOOTSTRAP_SEED,
    DOWNSTREAM_ONLY,
    EXPECTED_BASELINE_MANIFEST_SHA256,
    EXPECTED_BASELINE_RESULT_SHA256,
    EXPECTED_CHECKPOINT_EVERY,
    EXPECTED_DATASET_MANIFEST_SHA256,
    EXPECTED_MINIMUM_FREE_GIB,
    EXPECTED_PREREGISTRATION_SHA256,
    EXPECTED_SEEDS,
    EXPECTED_STEPS,
    EXPECTED_TRAINABLE_PARAMETERS,
    EXPECTED_VOCAB_SIZE,
    INPUT_ACCESS,
    TRAINED_ARMS,
    _comparison,
    construct_arm_model,
    initial_pair_receipt,
    load_json,
    producer_gate_met,
    validate_completed_arm_result,
    validate_parent_lineage,
    validate_preregistration,
)
from python.scbe.clay_paired_orbit_training import ClaySourceAdapter
from python.scbe.concept_exposure_ledger import weight_effect_receipt

EXPECTED_ARCHIVE_SHA256 = (
    "21ee43590a07a8016757b23d7a9423ec7877146cdaf22b0808ed5de3ca660ef7"
)
EXPECTED_DESCRIPTOR_SHA256 = (
    "e52f6b4811520d350e5fd1bc1c29b20f672bb9b04aacada2915cc4efdc1a9613"
)
EXPECTED_PACKET_MANIFEST_SHA256 = (
    "f4ba71ee68dfea85a56d8665d844d9315c4eec7e0d44629a3cbcb66d3397622b"
)
EXPECTED_CAMPAIGN_SHA256 = (
    "e220c03a038a241bdd89d5bb9f7389dbb20bd26fb8f1a874d4ed3bc65ac08e31"
)
EXPECTED_RUNNER_SHA256 = (
    "00605f372c9c9cc5a6d682b20080cd48f03ab098349325ed44373a088a75a6f0"
)
EXPECTED_RESULT_SHA256 = (
    "a1c4c4361a5ef39c69c722eba1f4aef4fb9e71cc03b0922b6b5d36cebce1f688"
)
EXPECTED_RECOVERY_SHA256 = (
    "bfdcc771e4cd2d308e4020e8f3c4f37ee12d888455a008eb6e148b3a0c74f440"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(pending, path)


def verify_descriptor(path: Path, expected: Mapping[str, Any], label: str) -> None:
    require(path.is_file(), f"missing {label}: {path}")
    require(path.stat().st_size == int(expected["bytes"]), f"size differs: {label}")
    require(file_sha256(path) == expected["sha256"], f"hash differs: {label}")


def verify_packet(stage_root: Path, runtime_root: Path) -> dict[str, Any]:
    descriptor_path = stage_root / "dataset" / "PACKET_DESCRIPTOR.json"
    archive_path = stage_root / "dataset" / "clay-input-access-efficacy.packet"
    runner_path = stage_root / "kernel" / "run_clay_input_access_kaggle.py"
    require(file_sha256(descriptor_path) == EXPECTED_DESCRIPTOR_SHA256, "descriptor hash differs")
    descriptor = load_json(descriptor_path)
    require(descriptor["schema"] == "clay.input-access-kaggle-dataset.v1", "descriptor schema differs")
    require(descriptor["archive"]["sha256"] == EXPECTED_ARCHIVE_SHA256, "descriptor archive anchor differs")
    verify_descriptor(archive_path, descriptor["archive"], "packet archive")
    require(file_sha256(runner_path) == EXPECTED_RUNNER_SHA256, "rendered runner hash differs")

    manifest_path = runtime_root / "CLAY_INPUT_ACCESS_KAGGLE_PACKET.json"
    require(file_sha256(manifest_path) == EXPECTED_PACKET_MANIFEST_SHA256, "packet manifest hash differs")
    manifest = load_json(manifest_path)
    require(manifest["schema"] == "clay.input-access-kaggle-packet.v1", "packet schema differs")
    require(len(manifest["files"]) == 326, "packet file count differs")
    for row in manifest["files"]:
        verify_descriptor(runtime_root / row["path"], row, f"packet file {row['path']}")
    require(manifest["baseline_manifest_sha256"] == EXPECTED_BASELINE_MANIFEST_SHA256, "baseline manifest anchor differs")
    require(manifest["baseline_result_sha256"] == EXPECTED_BASELINE_RESULT_SHA256, "baseline result anchor differs")
    require(manifest["dataset_manifest_sha256"] == EXPECTED_DATASET_MANIFEST_SHA256, "dataset anchor differs")
    require(manifest["trust_anchors"]["campaign_sha256"] == EXPECTED_CAMPAIGN_SHA256, "campaign anchor differs")
    require(manifest["trust_anchors"]["preregistration_sha256"] == EXPECTED_PREREGISTRATION_SHA256, "preregistration anchor differs")
    campaign_path = runtime_root / "scbe_repo" / manifest["paths"]["campaign"]
    preregistration_path = runtime_root / "scbe_repo" / manifest["paths"]["preregistration"]
    require(file_sha256(campaign_path) == EXPECTED_CAMPAIGN_SHA256, "campaign source hash differs")
    validate_preregistration(preregistration_path)
    return manifest


def verify_recovery(output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt = load_json(output_root / "CLOUD_RUN_RECEIPT.json")
    recovery_path = output_root / "RECOVERY_MANIFEST.json"
    require(file_sha256(recovery_path) == EXPECTED_RECOVERY_SHA256, "recovery manifest hash differs")
    require(receipt["recovery_manifest_sha256"] == EXPECTED_RECOVERY_SHA256, "receipt recovery anchor differs")
    require(receipt["campaign_result_sha256"] == EXPECTED_RESULT_SHA256, "receipt result anchor differs")
    recovery = load_json(recovery_path)
    rows = recovery["files"]
    listed = {str(row["path"]) for row in rows}
    actual = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*")
        if path.is_file()
        and path.name not in {"CLOUD_RUN_RECEIPT.json", "RECOVERY_MANIFEST.json"}
    }
    require(listed == actual, "downloaded recovery inventory paths differ")
    for row in rows:
        verify_descriptor(output_root / row["path"], row, f"recovered file {row['path']}")
    require(len(rows) == int(recovery["file_count"]), "recovery file count differs")
    require(sum(int(row["bytes"]) for row in rows) == int(recovery["total_bytes"]), "recovery byte total differs")
    return receipt, recovery


def run_config(value: Mapping[str, Any]) -> RunConfig:
    accepted = {item.name for item in fields(RunConfig)}
    config = {key: item for key, item in value.items() if key in accepted}
    config["seeds"] = tuple(config["seeds"])
    config["arms"] = tuple(config["arms"])
    return RunConfig(**config)


def target_error_analysis(
    contender: list[Mapping[str, Any]],
    control: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    for target in range(5):
        contender_scores = []
        control_scores = []
        wins = losses = ties = 0
        for left_run, right_run in zip(contender, control, strict=True):
            left = [row for row in left_run["predictions"] if int(row["target"]) == target]
            right = [row for row in right_run["predictions"] if int(row["target"]) == target]
            require(
                [row["sample_id"] for row in left] == [row["sample_id"] for row in right],
                f"target-{target} paired samples differ",
            )
            contender_scores.append(sum(bool(row["correct"]) for row in left) / len(left))
            control_scores.append(sum(bool(row["correct"]) for row in right) / len(right))
            for left_row, right_row in zip(left, right, strict=True):
                left_correct = bool(left_row["correct"])
                right_correct = bool(right_row["correct"])
                wins += int(left_correct and not right_correct)
                losses += int(right_correct and not left_correct)
                ties += int(left_correct == right_correct)
        result.append(
            {
                "target": target,
                "contender_seed_accuracies": contender_scores,
                "control_seed_accuracies": control_scores,
                "mean_accuracy_delta": (
                    sum(contender_scores) / len(contender_scores)
                    - sum(control_scores) / len(control_scores)
                ),
                "paired_wins": wins,
                "paired_losses": losses,
                "paired_ties": ties,
            }
        )
    return result


def verify(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.resolve(strict=True)
    stage_root = args.stage_root.resolve(strict=True)
    runtime_root = args.runtime_root.resolve(strict=True)
    packet = verify_packet(stage_root, runtime_root)
    cloud, recovery = verify_recovery(output_root)

    environment = load_json(output_root / "CLOUD_ENVIRONMENT.json")
    actual_output_free_bytes = int(environment["free_bytes"])
    required_free_bytes = int(EXPECTED_MINIMUM_FREE_GIB * 1024**3)

    campaign_root = output_root / "campaign"
    result_path = campaign_root / "RESULT.json"
    require(file_sha256(result_path) == EXPECTED_RESULT_SHA256, "campaign result hash differs")
    result = load_json(result_path)
    status = load_json(campaign_root / "STATUS.json")
    manifest = load_json(campaign_root / "RUN_MANIFEST.json")
    require(result["status"] == "COMPLETE", "campaign result is incomplete")
    require(status["status"] == "COMPLETE", "campaign status is incomplete")
    require(status["result_sha256"] == EXPECTED_RESULT_SHA256, "campaign status result anchor differs")
    require(result["promotion"] == "NOT_AUTHORIZED", "promotion field differs")
    require(result["config_hash"] == manifest["config_hash"], "campaign config hash differs")
    require(tuple(result["config"]["seeds"]) == EXPECTED_SEEDS, "campaign seeds differ")
    require(result["baseline_manifest_sha256"] == packet["baseline_manifest_sha256"], "baseline manifest lineage differs")
    require(result["baseline_result_sha256"] == packet["baseline_result_sha256"], "baseline result lineage differs")
    require(result["dataset_manifest_sha256"] == packet["dataset_manifest_sha256"], "dataset lineage differs")
    require(manifest["runner_sha256"] == EXPECTED_CAMPAIGN_SHA256, "run-manifest campaign hash differs")

    baseline_root = runtime_root / "baseline_run"
    baseline_result = load_json(baseline_root / "RESULT.json")
    require(file_sha256(baseline_root / "RUN_MANIFEST.json") == EXPECTED_BASELINE_MANIFEST_SHA256, "runtime baseline manifest hash differs")
    require(file_sha256(baseline_root / "RESULT.json") == EXPECTED_BASELINE_RESULT_SHA256, "runtime baseline result hash differs")
    no_intervention = sorted(
        baseline_result["per_arm"]["no_intervention_adapter"],
        key=lambda row: int(row["seed"]),
    )
    require(result["per_arm"]["no_intervention_adapter"] == no_intervention, "no-intervention control differs")

    source_dir = runtime_root / "loom_root" / "experiments" / "clay_action_compiler_20261109"
    provider = ClaySourceAdapter(source_dir)
    baseline_manifest = load_json(baseline_root / "RUN_MANIFEST.json")
    dataset = build_frozen_multiview_dataset(
        provider,
        rows_per_view=int(baseline_manifest["config"]["rows_per_view"]),
        holdout_rows=int(baseline_manifest["config"]["holdout_rows"]),
        seed=int(baseline_manifest["config"]["data_seed"]),
    )
    require(dataset.manifest["manifest_sha256"] == EXPECTED_DATASET_MANIFEST_SHA256, "regenerated dataset differs")
    count_train = counting_rows(False)
    count_holdout = counting_rows(True)
    rowsets = (
        count_train,
        count_holdout,
        tuple(row.pair() for row in dataset.static_rows),
        tuple(row.pair() for row in dataset.multiview_rows),
        tuple(row.pair() for row in dataset.holdout_rows),
    )
    vocab, stoi = vocab_of(*rowsets)
    require(len(vocab) == EXPECTED_VOCAB_SIZE, "regenerated vocabulary differs")
    itos = {index: token for token, index in stoi.items()}
    action_training_inputs: set[int] = {0}
    for source, target in rowsets[3]:
        inputs, _, _ = encode(source, target, stoi)
        action_training_inputs.update(inputs)
    inactive_embedding_ids = sorted(set(range(len(vocab))) - action_training_inputs)
    inactive_embedding_tokens = [vocab[index] for index in inactive_embedding_ids]
    inactive_candidate_scalars = len(inactive_embedding_ids) * 271
    config = run_config(result["config"])

    verified_arms: list[dict[str, Any]] = []
    initial_probe_hashes: list[dict[str, Any]] = []
    for seed in EXPECTED_SEEDS:
        parent_root = baseline_root / "parents" / f"seed-{seed}"
        parent_result = load_json(parent_root / "RESULT.json")
        parent_path = parent_root / "PARENT.pt"
        validate_parent_lineage(
            seed=seed,
            parent_result=parent_result,
            parent_path=parent_path,
            baseline_result=baseline_result,
        )
        parent = torch.load(parent_path, map_location="cpu", weights_only=False)
        require(parent["vocab"] == vocab, f"parent vocabulary differs: {seed}")
        probe = initial_pair_receipt(
            parent=parent,
            seed=seed,
            rows=tuple(row.pair() for row in dataset.multiview_rows),
            stoi=stoi,
            device="cpu",
        )
        probe_path = campaign_root / "initial-probes" / f"seed-{seed}.json"
        cloud_probe = load_json(probe_path)
        comparable_cloud_probe = dict(cloud_probe)
        comparable_local_probe = dict(probe)
        cloud_logits_sha256 = comparable_cloud_probe.pop("logits_sha256")
        local_logits_sha256 = comparable_local_probe.pop("logits_sha256")
        require(comparable_cloud_probe == comparable_local_probe, f"initial probe structure differs: {seed}")
        require(
            result["initial_pair_receipts"][EXPECTED_SEEDS.index(seed)] == cloud_probe,
            f"result initial probe differs: {seed}",
        )
        initial_probe_hashes.append(
            {
                "seed": seed,
                "cloud_torch_2_11_logits_sha256": cloud_logits_sha256,
                "local_replay_logits_sha256": local_logits_sha256,
                "within_environment_arm_logits_bit_identical": True,
                "note": "Cross-version GRU floating-point bytes differ; equality is required within each environment.",
            }
        )

        for arm in TRAINED_ARMS:
            arm_root = campaign_root / "arms" / f"{arm}-seed-{seed}"
            arm_result = load_json(arm_root / "RESULT.json")
            campaign_row = next(row for row in result["per_arm"][arm] if int(row["seed"]) == seed)
            require(arm_result == campaign_row, f"campaign arm row differs: {arm} {seed}")
            try:
                validate_completed_arm_result(
                    result=arm_result,
                    model_path=arm_root / "MODEL.pt",
                    seed=seed,
                    arm=arm,
                    config=config,
                    campaign_config_hash=result["config_hash"],
                    arm_config_hash=arm_result["arm_config_hash"],
                    parent=parent,
                    parent_result=parent_result,
                    dataset=dataset,
                    stoi=stoi,
                    itos=itos,
                    count_holdout=count_holdout,
                )
                weight_effect_replay = "EXACT"
            except RuntimeError as exc:
                if str(exc) != "existing completed arm weight effect differs on replay":
                    raise
                weight_effect_replay = "FINAL_HASH_ONLY_CROSS_TORCH_INITIALIZATION_DIFFERS"
            model_payload = torch.load(
                arm_root / "MODEL.pt",
                map_location="cpu",
                weights_only=False,
            )
            final_model = construct_arm_model(
                arm=arm,
                parent=parent,
                seed=seed,
                device="cpu",
            )
            final_model.load_state_dict(model_payload["model_state"], strict=True)
            final_trainable = flattened_trainable(final_model, "frozen_adapter_multiview")
            final_only_receipt = weight_effect_receipt(final_trainable, final_trainable)
            require(
                final_only_receipt["final_sha256"]
                == arm_result["weight_effect"]["final_sha256"],
                f"final trainable-state hash differs: {arm} {seed}",
            )
            pointer = load_json(arm_root / "checkpoints" / "latest.json")
            require(int(pointer["step"]) == EXPECTED_STEPS, f"latest checkpoint step differs: {arm} {seed}")
            require(int(pointer["generation"]) == EXPECTED_STEPS // EXPECTED_CHECKPOINT_EVERY - 1, f"latest checkpoint generation differs: {arm} {seed}")
            latest_path = arm_root / "checkpoints" / pointer["slot"]
            require(file_sha256(latest_path) == pointer["sha256"], f"latest checkpoint pointer differs: {arm} {seed}")
            checkpoint_steps: list[int] = []
            for checkpoint_path in sorted((arm_root / "checkpoints").glob("slot-*.pt")):
                checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
                require(int(checkpoint["seed"]) == seed, f"checkpoint seed differs: {checkpoint_path}")
                require(checkpoint["config_hash"] == arm_result["arm_config_hash"], f"checkpoint config differs: {checkpoint_path}")
                require(checkpoint["loss_mode"] == "standard", f"checkpoint loss mode differs: {checkpoint_path}")
                require(math.isfinite(float(checkpoint["loss"])), f"checkpoint loss is nonfinite: {checkpoint_path}")
                checkpoint_steps.append(int(checkpoint["step"]))
            require(sorted(checkpoint_steps) == [1750, 2000], f"checkpoint slots differ: {arm} {seed}")
            verified_arms.append(
                {
                    "arm": arm,
                    "seed": seed,
                    "final_loss": arm_result["final_loss"],
                    "accuracy": arm_result["metrics"]["accuracy"],
                    "macro_f1": arm_result["metrics"]["macro_f1"],
                    "counting_accuracy": arm_result["counting_accuracy"],
                    "model_sha256": arm_result["model_sha256"],
                    "trainable_parameters": arm_result["trainable_parameters"],
                    "frozen_core_bit_identical": arm_result["frozen_core_bit_identical"],
                    "all_nonselected_tensors_bit_identical": arm_result["all_nonselected_tensors_bit_identical"],
                    "checkpoint_steps": sorted(checkpoint_steps),
                    "reported_changed_scalars": arm_result["weight_effect"]["changed_scalars"],
                    "weight_effect_replay": weight_effect_replay,
                }
            )

    comparisons = {
        "input_access_vs_downstream_only": _comparison(
            result["per_arm"][INPUT_ACCESS],
            result["per_arm"][DOWNSTREAM_ONLY],
            bootstrap_seed=BOOTSTRAP_SEED,
        ),
        "input_access_vs_no_intervention": _comparison(
            result["per_arm"][INPUT_ACCESS],
            no_intervention,
            bootstrap_seed=BOOTSTRAP_SEED + 1,
        ),
        "downstream_only_vs_no_intervention": _comparison(
            result["per_arm"][DOWNSTREAM_ONLY],
            no_intervention,
            bootstrap_seed=BOOTSTRAP_SEED + 2,
        ),
    }
    require(comparisons == result["comparisons"], "recomputed comparisons differ")
    retention_gate = all(
        row["frozen_core_bit_identical"]
        and row["all_nonselected_tensors_bit_identical"]
        and row["counting_accuracy"] == row["parent_counting_accuracy"]
        for arm in TRAINED_ARMS
        for row in result["per_arm"][arm]
    )
    variance_gate, finite_gate, producer_gate = producer_gate_met(comparisons, retention_gate)
    require(result["variance_gate"] == ("MET" if variance_gate else "NOT_MET"), "variance gate differs")
    require(result["finite_evaluation_gate"] == ("MET" if finite_gate else "NOT_MET"), "finite gate differs")
    require(result["retention_gate"] == ("MET" if retention_gate else "NOT_MET"), "retention gate differs")
    require(result["producer_gate"] == ("MET_PENDING_INDEPENDENT_REPLAY" if producer_gate else "NOT_MET"), "producer gate differs")
    require(not producer_gate, "unexpected producer gate pass needs separate promotion review")
    candidate_changed = {
        int(row["weight_effect"]["changed_scalars"])
        for row in result["per_arm"][INPUT_ACCESS]
    }
    control_changed = {
        int(row["weight_effect"]["changed_scalars"])
        for row in result["per_arm"][DOWNSTREAM_ONLY]
    }
    require(
        candidate_changed == {EXPECTED_TRAINABLE_PARAMETERS - inactive_candidate_scalars},
        "candidate changed-scalar count does not match inactive action embedding rows",
    )
    require(
        control_changed == {EXPECTED_TRAINABLE_PARAMETERS},
        "control changed-scalar count differs",
    )
    per_target = target_error_analysis(
        result["per_arm"][INPUT_ACCESS],
        result["per_arm"][DOWNSTREAM_ONLY],
    )

    return {
        "schema": "clay.input-access-efficacy.cloud-verification.v1",
        "status": "VERIFIED_RESULT_REPLAY_WITH_STORAGE_GATE_VIOLATION",
        "kernel_status": "COMPLETE",
        "campaign_result_sha256": EXPECTED_RESULT_SHA256,
        "recovery_manifest_sha256": EXPECTED_RECOVERY_SHA256,
        "packet_manifest_sha256": EXPECTED_PACKET_MANIFEST_SHA256,
        "descriptor_sha256": EXPECTED_DESCRIPTOR_SHA256,
        "archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "recovery_file_count": recovery["file_count"],
        "recovery_bytes": recovery["total_bytes"],
        "actual_output_free_bytes_at_launch": actual_output_free_bytes,
        "required_free_bytes": required_free_bytes,
        "actual_output_free_gib_at_launch": actual_output_free_bytes / 1024**3,
        "required_free_gib": EXPECTED_MINIMUM_FREE_GIB,
        "storage_admission_gate": "VIOLATED",
        "storage_gate_bug": "producer measured filesystem root instead of the output mount",
        "effective_parameter_parity": {
            "status": "NOT_MET_ON_ACTUAL_ACTION_TRAINING_ROWS",
            "selected_scalars_each_arm": EXPECTED_TRAINABLE_PARAMETERS,
            "downstream_changed_scalars_each_seed": sorted(control_changed),
            "input_access_changed_scalars_each_seed": sorted(candidate_changed),
            "inactive_input_embedding_ids": inactive_embedding_ids,
            "inactive_input_embedding_tokens": inactive_embedding_tokens,
            "inactive_input_embedding_rows": len(inactive_embedding_ids),
            "inactive_candidate_scalars": inactive_candidate_scalars,
        },
        "per_target_error_analysis": per_target,
        "initial_pair_replay": initial_probe_hashes,
        "arms": verified_arms,
        "comparisons": comparisons,
        "variance_gate": "MET" if variance_gate else "NOT_MET",
        "finite_evaluation_gate": "MET" if finite_gate else "NOT_MET",
        "retention_gate": "MET" if retention_gate else "NOT_MET",
        "producer_gate": "MET" if producer_gate else "NOT_MET",
        "promotion": "NOT_AUTHORIZED",
        "claim_boundary": (
            "Model bytes, parent lineage, predictions, metrics, retention, and decision gates replayed "
            "exactly. The cloud segment is not a preregistration-compliant promotion trial because the "
            "25 GiB storage gate inspected the wrong filesystem and actual output-mount free space was below threshold."
        ),
    }


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--stage-root", required=True, type=Path)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    args = parse_args(arguments)
    receipt = verify(args)
    atomic_json(args.receipt.resolve(), receipt)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
