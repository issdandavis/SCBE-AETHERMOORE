"""Verify and replay the recovered Clay hybrid input-access Kaggle campaign.

This verifier is intentionally read-only.  It authenticates the sealed packet and
the complete cloud recovery inventory, rebuilds the pinned dataset, reopens every
model and checkpoint, recomputes held-out predictions and retention, and reruns
the preregistered decision gates.  It never authorizes promotion.
"""

from __future__ import annotations

import argparse
from dataclasses import fields
from hashlib import sha256
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
    FrozenActionModel,
    RunConfig,
    action_metrics,
    counting_accuracy,
    counting_rows,
    encode,
    frozen_state,
    frozen_state_identical,
    path_for_arm,
    predict_action_rows,
    vocab_of,
)
from python.scbe.clay_frozen_multiview_data import build_frozen_multiview_dataset
from python.scbe.clay_hybrid_input_access_campaign import (
    AUTHENTICATED_PREVIOUS_RUN_MANIFEST_SHA256,
    AUTHENTICATED_PREVIOUS_RUNNER_SHA256,
    COMPACT_INPUT_ROWS,
    EXPECTED_COMPACT_FULL_IDS,
    HYBRID_INPUT_ACCESS,
    PREREGISTRATION_SHA256,
    TRAINED_ARMS,
    HybridInputAccessActionModel,
)
from python.scbe.clay_input_access_campaign import (
    BOOTSTRAP_SEED,
    DOWNSTREAM_ONLY,
    EXPECTED_BASELINE_MANIFEST_SHA256,
    EXPECTED_BASELINE_RESULT_SHA256,
    EXPECTED_CHECKPOINT_EVERY,
    EXPECTED_DATASET_MANIFEST_SHA256,
    EXPECTED_SEEDS,
    EXPECTED_STEPS,
    EXPECTED_TRAINABLE_PARAMETERS,
    EXPECTED_VOCAB_SIZE,
    TRAIN_STAGE,
    _comparison,
    producer_gate_met,
    validate_parent_lineage,
)
from python.scbe.clay_paired_orbit_training import ClaySourceAdapter


EXPECTED_PACKET_MANIFEST_SHA256 = (
    "55eaa4afa116d49d5ab7d23cfb3b87efe2b44ae40db46307769628e034d8cfc6"
)
EXPECTED_ARCHIVE_SHA256 = (
    "ed5aa4c17e1e600571141983fb9b14efb1f2b0beafa7afa82ea25b84e24ae027"
)
EXPECTED_DESCRIPTOR_SHA256 = (
    "60cd8a8069f953614f8103b0b06137e0302c39a066a56912157347ca50cef711"
)
EXPECTED_CAMPAIGN_SHA256 = (
    "2f8c833d5dd63c8de78cdf760a501e931ccb1906402f1aeaaf8657a0a09b270d"
)
EXPECTED_RUNNER_SHA256 = (
    "02860b156636aece52207aa4e500a3e5e17ea30c07e7512fc8729bf7812d4b59"
)
EXPECTED_PRIOR_RECOVERY_SHA256 = (
    "0ddcc28db948d02bc7053610a6632c00d3dc5cd6d45e205b3bb8f63e5c0c261c"
)
EXPECTED_KERNEL_REF = "issacizrealdavis/clay-hybrid-input-access-efficacy-20261119"
EXPECTED_KERNEL_VERSION = 2
EXPECTED_PACKET_DATASET_REF = (
    "issacizrealdavis/clay-hybrid-input-access-efficacy-input-20261119"
)
EXPECTED_RECOVERY_DATASET_REF = (
    "issacizrealdavis/clay-hybrid-input-access-recovery-20261119"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(pending, path)


def verify_descriptor(path: Path, descriptor: Mapping[str, Any], label: str) -> None:
    require(path.is_file(), f"missing {label}: {path}")
    require(path.stat().st_size == int(descriptor["bytes"]), f"size differs: {label}")
    require(sha256_file(path) == descriptor["sha256"], f"hash differs: {label}")


def verify_packet(stage_root: Path, runtime_root: Path) -> dict[str, Any]:
    build_receipt = load_json(stage_root / "BUILD_RECEIPT.json")
    require(
        build_receipt["trust_anchors"]["prior_recovery_sha256"]
        == EXPECTED_PRIOR_RECOVERY_SHA256,
        "prior recovery build anchor differs",
    )
    descriptor_path = stage_root / "dataset" / "PACKET_DESCRIPTOR.json"
    archive_path = stage_root / "dataset" / "clay-hybrid-input-access-efficacy.packet"
    runner_path = stage_root / "kernel" / "run_clay_hybrid_input_access_kaggle.py"
    require(sha256_file(descriptor_path) == EXPECTED_DESCRIPTOR_SHA256, "descriptor hash differs")
    descriptor = load_json(descriptor_path)
    require(descriptor["archive"]["sha256"] == EXPECTED_ARCHIVE_SHA256, "archive anchor differs")
    verify_descriptor(archive_path, descriptor["archive"], "packet archive")
    require(sha256_file(runner_path) == EXPECTED_RUNNER_SHA256, "runner hash differs")

    manifest_path = runtime_root / "CLAY_HYBRID_INPUT_ACCESS_KAGGLE_PACKET.json"
    require(sha256_file(manifest_path) == EXPECTED_PACKET_MANIFEST_SHA256, "packet manifest hash differs")
    manifest = load_json(manifest_path)
    require(manifest["schema"] == "clay.hybrid-input-access-kaggle-packet.v1", "packet schema differs")
    require(len(manifest["files"]) == 327, "packet inventory count differs")
    for row in manifest["files"]:
        verify_descriptor(runtime_root / row["path"], row, f"packet file {row['path']}")
    anchors = manifest["trust_anchors"]
    require(anchors["campaign_sha256"] == EXPECTED_CAMPAIGN_SHA256, "campaign anchor differs")
    require(anchors["preregistration_sha256"] == PREREGISTRATION_SHA256, "preregistration anchor differs")
    require(manifest["baseline_manifest_sha256"] == EXPECTED_BASELINE_MANIFEST_SHA256, "baseline manifest differs")
    require(manifest["baseline_result_sha256"] == EXPECTED_BASELINE_RESULT_SHA256, "baseline result differs")
    require(manifest["dataset_manifest_sha256"] == EXPECTED_DATASET_MANIFEST_SHA256, "dataset anchor differs")
    campaign_path = runtime_root / "scbe_repo" / manifest["paths"]["campaign"]
    prereg_path = runtime_root / "scbe_repo" / manifest["paths"]["preregistration"]
    require(sha256_file(campaign_path) == EXPECTED_CAMPAIGN_SHA256, "campaign source differs")
    require(sha256_file(prereg_path) == PREREGISTRATION_SHA256, "preregistration bytes differ")
    return manifest


def verify_recovery(output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    cloud = load_json(output_root / "CLOUD_RUN_RECEIPT.json")
    recovery_path = output_root / "RECOVERY_MANIFEST.json"
    recovery_sha = sha256_file(recovery_path)
    require(cloud["recovery_manifest_sha256"] == recovery_sha, "cloud recovery anchor differs")
    recovery = load_json(recovery_path)
    listed = {str(row["path"]) for row in recovery["files"]}
    actual = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*")
        if path.is_file()
        and path.name not in {"CLOUD_RUN_RECEIPT.json", "RECOVERY_MANIFEST.json"}
    }
    require(listed == actual, "recovery inventory paths differ")
    for row in recovery["files"]:
        verify_descriptor(output_root / row["path"], row, f"recovered file {row['path']}")
    require(len(recovery["files"]) == int(recovery["file_count"]), "recovery file count differs")
    require(
        sum(int(row["bytes"]) for row in recovery["files"]) == int(recovery["total_bytes"]),
        "recovery byte total differs",
    )
    return cloud, recovery


def run_config(value: Mapping[str, Any]) -> RunConfig:
    accepted = {item.name for item in fields(RunConfig)}
    config = {key: item for key, item in value.items() if key in accepted}
    config["seeds"] = tuple(config["seeds"])
    config["arms"] = tuple(config["arms"])
    return RunConfig(**config)


def independent_model(payload: Mapping[str, Any]) -> FrozenActionModel:
    arm = str(payload["arm"])
    vocab_size = len(payload["vocab"])
    if arm == DOWNSTREAM_ONLY:
        model: FrozenActionModel = FrozenActionModel(vocab_size)
    elif arm == HYBRID_INPUT_ACCESS:
        compact = tuple(int(value) for value in payload["compact_input_ids"])
        require(compact == EXPECTED_COMPACT_FULL_IDS, "model compact alphabet differs")
        require(len(compact) == COMPACT_INPUT_ROWS, "model compact row count differs")
        model = HybridInputAccessActionModel(vocab_size, compact)
    else:
        raise RuntimeError(f"unknown model arm: {arm}")
    model.load_state_dict(payload["model_state"], strict=True)
    model.set_path(path_for_arm(TRAIN_STAGE))
    model.eval()
    return model


def verify_arm(
    *,
    campaign_root: Path,
    baseline_root: Path,
    result_row: Mapping[str, Any],
    dataset: Any,
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    count_holdout: tuple[tuple[str, str], ...],
    baseline_result: Mapping[str, Any],
    config: RunConfig,
) -> dict[str, Any]:
    seed = int(result_row["seed"])
    arm = str(result_row["arm"])
    require(seed in EXPECTED_SEEDS, f"unexpected arm seed: {seed}")
    require(arm in TRAINED_ARMS, f"unexpected arm: {arm}")
    arm_root = campaign_root / "arms" / f"{arm}-seed-{seed}"
    arm_result = load_json(arm_root / "RESULT.json")
    require(arm_result == result_row, f"campaign arm row differs: {arm} {seed}")
    require(arm_result["status"] == "COMPLETE", f"arm incomplete: {arm} {seed}")
    require(arm_result["loss_mode"] == "standard", f"arm loss differs: {arm} {seed}")
    require(int(arm_result["steps"]) == EXPECTED_STEPS, f"arm steps differ: {arm} {seed}")
    require(math.isfinite(float(arm_result["final_loss"])), f"arm loss nonfinite: {arm} {seed}")
    require(int(arm_result["trainable_parameters"]) == EXPECTED_TRAINABLE_PARAMETERS, "selected capacity differs")
    require(int(arm_result["effective_changed_scalars"]) == EXPECTED_TRAINABLE_PARAMETERS, "changed capacity differs")

    parent_root = baseline_root / "parents" / f"seed-{seed}"
    parent_result = load_json(parent_root / "RESULT.json")
    parent_path = parent_root / "PARENT.pt"
    validate_parent_lineage(
        seed=seed,
        parent_result=parent_result,
        parent_path=parent_path,
        baseline_result=baseline_result,
    )
    parent_payload = torch.load(parent_path, map_location="cpu", weights_only=False)
    model_path = arm_root / "MODEL.pt"
    require(sha256_file(model_path) == arm_result["model_sha256"], f"model hash differs: {arm} {seed}")
    payload = torch.load(model_path, map_location="cpu", weights_only=False)
    for key, expected in {
        "seed": seed,
        "arm": arm,
        "loss_mode": "standard",
        "campaign_config_hash": arm_result["campaign_config_hash"],
        "arm_config_hash": arm_result["arm_config_hash"],
        "parent_sha256": parent_result["parent_sha256"],
        "vocab": parent_payload["vocab"],
    }.items():
        require(payload.get(key) == expected, f"model field differs ({key}): {arm} {seed}")
    model = independent_model(payload)
    parent_model = FrozenActionModel(len(parent_payload["vocab"]))
    parent_model.load_state_dict(parent_payload["model_state"], strict=True)
    require(
        frozen_state_identical(frozen_state(parent_model), model),
        f"frozen core differs: {arm} {seed}",
    )
    if arm == HYBRID_INPUT_ACCESS:
        require(
            tuple(int(value) for value in payload["compact_input_ids"])
            == tuple(int(value) for value in result_row["compact_input_ids"]),
            f"compact alphabet result differs: {seed}",
        )
    predictions = predict_action_rows(
        model,
        path=path_for_arm(TRAIN_STAGE),
        rows=dataset.holdout_rows,
        stoi=stoi,
        itos=itos,
        device="cpu",
    )
    require(predictions == arm_result["predictions"], f"prediction replay differs: {arm} {seed}")
    metrics = action_metrics(predictions)
    require(metrics == arm_result["metrics"], f"metric replay differs: {arm} {seed}")
    count_score = counting_accuracy(
        model=model,
        rows=count_holdout,
        stoi=stoi,
        itos=itos,
        device="cpu",
    )
    require(count_score == arm_result["counting_accuracy"], f"retention replay differs: {arm} {seed}")
    require(count_score == float(parent_result["counting_accuracy"]), f"parent retention failed: {arm} {seed}")
    require(arm_result["frozen_core_bit_identical"] is True, "producer frozen gate differs")
    require(arm_result["all_nonselected_tensors_bit_identical"] is True, "producer nonselected gate differs")

    pointer = load_json(arm_root / "checkpoints" / "latest.json")
    require(int(pointer["step"]) == EXPECTED_STEPS, f"latest step differs: {arm} {seed}")
    require(
        int(pointer["generation"]) == EXPECTED_STEPS // EXPECTED_CHECKPOINT_EVERY - 1,
        f"latest generation differs: {arm} {seed}",
    )
    latest = arm_root / "checkpoints" / pointer["slot"]
    require(sha256_file(latest) == pointer["sha256"], f"checkpoint pointer differs: {arm} {seed}")
    checkpoint_steps: list[int] = []
    for checkpoint_path in sorted((arm_root / "checkpoints").glob("slot-*.pt")):
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        require(int(checkpoint["seed"]) == seed, f"checkpoint seed differs: {checkpoint_path}")
        require(checkpoint["loss_mode"] == "standard", f"checkpoint loss differs: {checkpoint_path}")
        require(checkpoint["config_hash"] == arm_result["arm_config_hash"], f"checkpoint config differs: {checkpoint_path}")
        require(math.isfinite(float(checkpoint["loss"])), f"checkpoint nonfinite: {checkpoint_path}")
        checkpoint_payload = {
            "arm": arm,
            "vocab": parent_payload["vocab"],
            "compact_input_ids": list(EXPECTED_COMPACT_FULL_IDS),
            "model_state": checkpoint["model_state"],
        }
        checkpoint_model = independent_model(checkpoint_payload)
        require(
            frozen_state_identical(frozen_state(parent_model), checkpoint_model),
            f"checkpoint frozen core differs: {checkpoint_path}",
        )
        checkpoint_steps.append(int(checkpoint["step"]))
    require(sorted(checkpoint_steps) == [1750, 2000], f"checkpoint slots differ: {arm} {seed}")
    return {
        "seed": seed,
        "arm": arm,
        "model_sha256": arm_result["model_sha256"],
        "final_loss": arm_result["final_loss"],
        "accuracy": metrics["accuracy"],
        "macro_f1": metrics["macro_f1"],
        "counting_accuracy": count_score,
        "checkpoint_steps": sorted(checkpoint_steps),
        "frozen_core_bit_identical": True,
        "effective_changed_scalars": arm_result["effective_changed_scalars"],
    }


def verify(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.resolve(strict=True)
    stage_root = args.stage_root.resolve(strict=True)
    runtime_root = args.runtime_root.resolve(strict=True)
    packet = verify_packet(stage_root, runtime_root)
    cloud, recovery = verify_recovery(output_root)
    campaign_root = output_root / "campaign"
    result_path = campaign_root / "RESULT.json"
    result_sha = sha256_file(result_path)
    require(cloud["campaign_result_sha256"] == result_sha, "cloud result anchor differs")
    result = load_json(result_path)
    status = load_json(campaign_root / "STATUS.json")
    manifest = load_json(campaign_root / "RUN_MANIFEST.json")
    require(result["status"] == "COMPLETE", "campaign result incomplete")
    require(status["status"] == "COMPLETE", "campaign status incomplete")
    require(status["result_sha256"] == result_sha, "status result anchor differs")
    require(result["promotion"] == "NOT_AUTHORIZED", "promotion field differs")
    require(result["config_hash"] == manifest["config_hash"], "campaign config differs")
    require(tuple(result["config"]["seeds"]) == EXPECTED_SEEDS, "campaign seeds differ")
    # Version 2 resumed the authenticated v1 campaign in place.  Its durable run
    # manifest therefore identifies the v1 campaign source, while the sealed v2
    # packet (verified above) identifies the recovery-aware source that resumed
    # it.  Check both links instead of incorrectly treating the v1 manifest as a
    # fresh v2 manifest.
    require(
        sha256_file(campaign_root / "RUN_MANIFEST.json")
        == AUTHENTICATED_PREVIOUS_RUN_MANIFEST_SHA256,
        "authenticated previous run manifest differs",
    )
    require(
        manifest["runner_sha256"] == AUTHENTICATED_PREVIOUS_RUNNER_SHA256,
        "authenticated previous run source differs",
    )
    require(result["baseline_manifest_sha256"] == packet["baseline_manifest_sha256"], "baseline manifest lineage differs")
    require(result["baseline_result_sha256"] == packet["baseline_result_sha256"], "baseline result lineage differs")
    require(result["dataset_manifest_sha256"] == packet["dataset_manifest_sha256"], "dataset lineage differs")
    require(tuple(result["compact_input_ids"]) == EXPECTED_COMPACT_FULL_IDS, "result compact alphabet differs")

    baseline_root = runtime_root / "baseline_run"
    baseline_result = load_json(baseline_root / "RESULT.json")
    require(sha256_file(baseline_root / "RUN_MANIFEST.json") == EXPECTED_BASELINE_MANIFEST_SHA256, "runtime baseline manifest differs")
    require(sha256_file(baseline_root / "RESULT.json") == EXPECTED_BASELINE_RESULT_SHA256, "runtime baseline result differs")
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
    observed = {0}
    for source, target in rowsets[3]:
        inputs, _, _ = encode(source, target, stoi)
        observed.update(int(value) for value in inputs)
    require(tuple(sorted(observed)) == EXPECTED_COMPACT_FULL_IDS, "regenerated compact alphabet differs")
    config = run_config(result["config"])

    arms: list[dict[str, Any]] = []
    for arm in TRAINED_ARMS:
        rows = result["per_arm"][arm]
        require([int(row["seed"]) for row in rows] == list(EXPECTED_SEEDS), f"arm seeds differ: {arm}")
        for row in rows:
            arms.append(
                verify_arm(
                    campaign_root=campaign_root,
                    baseline_root=baseline_root,
                    result_row=row,
                    dataset=dataset,
                    stoi=stoi,
                    itos=itos,
                    count_holdout=count_holdout,
                    baseline_result=baseline_result,
                    config=config,
                )
            )

    comparisons = {
        "hybrid_vs_downstream_only": _comparison(
            result["per_arm"][HYBRID_INPUT_ACCESS],
            result["per_arm"][DOWNSTREAM_ONLY],
            bootstrap_seed=BOOTSTRAP_SEED + 100,
        ),
        "hybrid_vs_no_intervention": _comparison(
            result["per_arm"][HYBRID_INPUT_ACCESS],
            no_intervention,
            bootstrap_seed=BOOTSTRAP_SEED + 101,
        ),
        "downstream_only_vs_no_intervention": _comparison(
            result["per_arm"][DOWNSTREAM_ONLY],
            no_intervention,
            bootstrap_seed=BOOTSTRAP_SEED + 102,
        ),
    }
    require(comparisons == result["comparisons"], "comparison replay differs")
    retention_gate = all(
        row["frozen_core_bit_identical"]
        and row["all_nonselected_tensors_bit_identical"]
        and row["counting_accuracy"] == row["parent_counting_accuracy"]
        and int(row["effective_changed_scalars"]) == EXPECTED_TRAINABLE_PARAMETERS
        for arm in TRAINED_ARMS
        for row in result["per_arm"][arm]
    )
    variance_gate, finite_gate, producer_gate = producer_gate_met(
        {
            "input_access_vs_downstream_only": comparisons["hybrid_vs_downstream_only"],
            "input_access_vs_no_intervention": comparisons["hybrid_vs_no_intervention"],
        },
        retention_gate,
    )
    require(result["variance_gate"] == ("MET" if variance_gate else "NOT_MET"), "variance gate differs")
    require(result["finite_evaluation_gate"] == ("MET" if finite_gate else "NOT_MET"), "finite gate differs")
    require(
        result["retention_and_effective_capacity_gate"]
        == ("MET" if retention_gate else "NOT_MET"),
        "retention gate differs",
    )
    expected_producer = "MET_PENDING_INDEPENDENT_REPLAY" if producer_gate else "NOT_MET"
    require(result["producer_gate"] == expected_producer, "producer gate differs")
    promotion = "REPLICATION_REQUIRED_NO_WEIGHT_PROMOTION" if producer_gate else "NOT_AUTHORIZED"
    return {
        "schema": "clay.hybrid-input-access-efficacy.cloud-verification.v1",
        "status": "VERIFIED_COMPLETE",
        "kernel": {
            "ref": EXPECTED_KERNEL_REF,
            "version": EXPECTED_KERNEL_VERSION,
            "status": "COMPLETE",
        },
        "datasets": {
            "packet": EXPECTED_PACKET_DATASET_REF,
            "prior_recovery": EXPECTED_RECOVERY_DATASET_REF,
        },
        "campaign_result_sha256": result_sha,
        "recovery_manifest_sha256": sha256_file(output_root / "RECOVERY_MANIFEST.json"),
        "packet_manifest_sha256": EXPECTED_PACKET_MANIFEST_SHA256,
        "archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "descriptor_sha256": EXPECTED_DESCRIPTOR_SHA256,
        "recovery_file_count": recovery["file_count"],
        "recovery_bytes": recovery["total_bytes"],
        "arms": arms,
        "comparisons": comparisons,
        "variance_gate": "MET" if variance_gate else "NOT_MET",
        "finite_evaluation_gate": "MET" if finite_gate else "NOT_MET",
        "retention_and_effective_capacity_gate": "MET" if retention_gate else "NOT_MET",
        "producer_gate": "MET" if producer_gate else "NOT_MET",
        "promotion": promotion,
        "claim_boundary": (
            "This receipt verifies the bounded discovery campaign. A producer-gate pass "
            "would require fresh replication and still cannot promote or overwrite weights. "
            "This hybrid architecture comparison is not evidence about stable cross entropy."
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
