"""Independently verify a recovered stable-CE Kaggle campaign."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import torch

from python.scbe.clay_frozen_multiview_adapter import (
    FrozenActionModel,
    frozen_state,
    frozen_state_identical,
    metric_comparison,
    paired_prediction_comparison,
)

EXPECTED_SEEDS = (20261134, 20261135, 20261136)
LOSS_MODES = ("standard", "stable_log1p")
EXPECTED_PACKET_MANIFEST_SHA256 = (
    "9d2cd300d8508a888edf9f7b09171dd87829ece99768f79815a5f7cc9600e887"
)


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected one JSON object: {path}")
    return value


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
    require(sha256_file(path) == expected["sha256"], f"hash differs: {label}")


def verify_packet(runtime_root: Path) -> dict[str, Any]:
    manifest_path = runtime_root / "CLAY_STABLE_CE_KAGGLE_PACKET.json"
    require(
        sha256_file(manifest_path) == EXPECTED_PACKET_MANIFEST_SHA256,
        "packet manifest hash differs",
    )
    manifest = load_json(manifest_path)
    require(manifest["schema"] == "clay.stable-ce-kaggle-packet.v1", "packet schema differs")
    for descriptor in manifest["files"]:
        verify_descriptor(
            runtime_root / descriptor["path"],
            descriptor,
            f"packet file {descriptor['path']}",
        )
    return manifest


def verify_recovery_inventory(output_root: Path) -> tuple[dict[str, Any], int]:
    cloud = load_json(output_root / "CLOUD_RUN_RECEIPT.json")
    recovery_path = output_root / "RECOVERY_MANIFEST.json"
    require(
        sha256_file(recovery_path) == cloud["recovery_manifest_sha256"],
        "recovery manifest hash differs",
    )
    recovery = load_json(recovery_path)
    rows = recovery["files"]
    listed = {str(row["path"]) for row in rows}
    actual = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*")
        if path.is_file()
        and path.name not in {"CLOUD_RUN_RECEIPT.json", "RECOVERY_MANIFEST.json"}
    }
    require(listed == actual, "recovery inventory paths differ from downloaded output")
    for descriptor in rows:
        verify_descriptor(
            output_root / descriptor["path"],
            descriptor,
            f"recovered file {descriptor['path']}",
        )
    require(len(rows) == int(recovery["file_count"]), "recovery file count differs")
    total = sum(int(row["bytes"]) for row in rows)
    require(total == int(recovery["total_bytes"]), "recovery byte total differs")
    return cloud, total


def comparison(
    primary: Sequence[Mapping[str, Any]],
    control: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "metrics": {
            metric: metric_comparison(primary, control, metric)
            for metric in ("accuracy", "macro_f1")
        },
        "paired": paired_prediction_comparison(primary, control),
    }


def loaded_model(payload: Mapping[str, Any]) -> FrozenActionModel:
    model = FrozenActionModel(len(payload["vocab"]))
    model.load_state_dict(payload["model_state"])
    return model


def verify_arm(
    *,
    campaign_root: Path,
    baseline_root: Path,
    config_hash: str,
    loss_mode: str,
    row: Mapping[str, Any],
) -> dict[str, Any]:
    seed = int(row["seed"])
    require(seed in EXPECTED_SEEDS, f"unexpected seed: {seed}")
    arm_root = campaign_root / "arms" / f"{loss_mode}-seed-{seed}"
    result = load_json(arm_root / "RESULT.json")
    require(result == row, f"arm result differs from campaign result: {loss_mode} {seed}")
    require(result["status"] == "COMPLETE", f"arm incomplete: {loss_mode} {seed}")
    require(result["loss_mode"] == loss_mode, f"arm loss mode differs: {loss_mode} {seed}")
    require(int(result["steps"]) == 2000, f"arm step count differs: {loss_mode} {seed}")
    require(math.isfinite(float(result["final_loss"])), f"arm loss non-finite: {loss_mode} {seed}")
    require(result["frozen_core_bit_identical"] is True, f"producer frozen gate failed: {loss_mode} {seed}")

    parent_root = baseline_root / "parents" / f"seed-{seed}"
    parent_result = load_json(parent_root / "RESULT.json")
    parent_path = parent_root / "PARENT.pt"
    require(sha256_file(parent_path) == parent_result["parent_sha256"], f"parent hash differs: {seed}")
    require(result["parent_sha256"] == parent_result["parent_sha256"], f"arm parent differs: {loss_mode} {seed}")

    model_path = arm_root / "MODEL.pt"
    require(sha256_file(model_path) == result["model_sha256"], f"model hash differs: {loss_mode} {seed}")
    parent_payload = torch.load(parent_path, map_location="cpu", weights_only=True)
    model_payload = torch.load(model_path, map_location="cpu", weights_only=True)
    require(model_payload["loss_mode"] == loss_mode, f"model loss mode differs: {loss_mode} {seed}")
    require(int(model_payload["seed"]) == seed, f"model seed differs: {loss_mode} {seed}")
    require(model_payload["config_hash"] == config_hash, f"model config differs: {loss_mode} {seed}")
    require(model_payload["parent_sha256"] == result["parent_sha256"], f"model parent differs: {loss_mode} {seed}")
    require(model_payload["vocab"] == parent_payload["vocab"], f"model vocab differs: {loss_mode} {seed}")

    parent_model = loaded_model(parent_payload)
    arm_model = loaded_model(model_payload)
    frozen_before = frozen_state(parent_model)
    require(
        frozen_state_identical(frozen_before, arm_model),
        f"independent frozen-core comparison failed: {loss_mode} {seed}",
    )

    pointer = load_json(arm_root / "checkpoints" / "latest.json")
    require(int(pointer["step"]) == 2000, f"latest checkpoint step differs: {loss_mode} {seed}")
    require(int(pointer["generation"]) == 7, f"latest generation differs: {loss_mode} {seed}")
    latest_path = arm_root / "checkpoints" / pointer["slot"]
    require(sha256_file(latest_path) == pointer["sha256"], f"latest pointer hash differs: {loss_mode} {seed}")
    checkpoint_steps = []
    for checkpoint_path in sorted((arm_root / "checkpoints").glob("slot-*.pt")):
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        require(checkpoint["loss_mode"] == loss_mode, f"checkpoint loss mode differs: {checkpoint_path}")
        require(int(checkpoint["seed"]) == seed, f"checkpoint seed differs: {checkpoint_path}")
        require(checkpoint["config_hash"] == config_hash, f"checkpoint config differs: {checkpoint_path}")
        require(math.isfinite(float(checkpoint["loss"])), f"checkpoint loss non-finite: {checkpoint_path}")
        checkpoint_model = FrozenActionModel(len(parent_payload["vocab"]))
        checkpoint_model.load_state_dict(checkpoint["model_state"])
        require(
            frozen_state_identical(frozen_before, checkpoint_model),
            f"checkpoint frozen core differs: {checkpoint_path}",
        )
        checkpoint_steps.append(int(checkpoint["step"]))
    require(sorted(checkpoint_steps) == [1750, 2000], f"checkpoint slots differ: {loss_mode} {seed}")

    return {
        "loss_mode": loss_mode,
        "seed": seed,
        "model_sha256": result["model_sha256"],
        "parent_sha256": result["parent_sha256"],
        "final_loss": result["final_loss"],
        "accuracy": result["metrics"]["accuracy"],
        "macro_f1": result["metrics"]["macro_f1"],
        "counting_accuracy": result["counting_accuracy"],
        "frozen_core_bit_identical": True,
        "checkpoint_steps": checkpoint_steps,
    }


def verify(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.resolve(strict=True)
    runtime_root = args.runtime_root.resolve(strict=True)
    packet = verify_packet(runtime_root)
    cloud, recovery_bytes = verify_recovery_inventory(output_root)
    campaign_root = output_root / "campaign"
    result_path = campaign_root / "RESULT.json"
    require(sha256_file(result_path) == cloud["campaign_result_sha256"], "campaign result hash differs")
    result = load_json(result_path)
    status = load_json(campaign_root / "STATUS.json")
    require(status["status"] == "COMPLETE", "campaign status is not complete")
    require(status["result_sha256"] == cloud["campaign_result_sha256"], "status result hash differs")
    require(result["status"] == "COMPLETE", "campaign result is not complete")
    require(result["promotion"] == "NOT_AUTHORIZED", "campaign promotion field differs")
    require(result["config_hash"] == load_json(campaign_root / "RUN_MANIFEST.json")["config_hash"], "config hash differs")
    require(tuple(result["config"]["seeds"]) == EXPECTED_SEEDS, "campaign seeds differ")
    require(result["baseline_manifest_sha256"] == packet["baseline_manifest_sha256"], "baseline manifest lineage differs")
    require(result["baseline_result_sha256"] == packet["baseline_result_sha256"], "baseline result lineage differs")
    require(result["dataset_manifest_sha256"] == packet["dataset_manifest_sha256"], "dataset lineage differs")

    baseline_root = runtime_root / "baseline_run"
    baseline_result = load_json(baseline_root / "RESULT.json")
    no_intervention = sorted(
        baseline_result["per_arm"]["no_intervention_adapter"],
        key=lambda row: int(row["seed"]),
    )
    require(
        result["per_arm"]["no_intervention_adapter"] == no_intervention,
        "no-intervention control differs from pinned baseline",
    )

    arms = []
    for loss_mode in LOSS_MODES:
        rows = result["per_arm"][loss_mode]
        require([int(row["seed"]) for row in rows] == list(EXPECTED_SEEDS), f"arm seeds differ: {loss_mode}")
        for row in rows:
            arms.append(
                verify_arm(
                    campaign_root=campaign_root,
                    baseline_root=baseline_root,
                    config_hash=result["config_hash"],
                    loss_mode=loss_mode,
                    row=row,
                )
            )

    recomputed = {
        "stable_vs_standard": comparison(
            result["per_arm"]["stable_log1p"], result["per_arm"]["standard"]
        ),
        "stable_vs_no_intervention": comparison(
            result["per_arm"]["stable_log1p"], no_intervention
        ),
        "standard_vs_no_intervention": comparison(
            result["per_arm"]["standard"], no_intervention
        ),
    }
    require(recomputed == result["comparisons"], "recomputed comparisons differ")
    producer_gate = all(
        recomputed[name]["metrics"][metric]["clears_positive_gate"]
        for name in ("stable_vs_standard", "stable_vs_no_intervention")
        for metric in ("accuracy", "macro_f1")
    )
    expected_gate = "MET_PENDING_INDEPENDENT_REPLAY" if producer_gate else "NOT_MET"
    require(result["producer_gate"] == expected_gate, "producer gate differs from replay")
    require(not producer_gate, "unexpected producer gate pass requires separate promotion review")

    return {
        "schema": "clay.stable-ce-efficacy.cloud-verification.v1",
        "status": "VERIFIED_COMPLETE",
        "kernel_status": "COMPLETE",
        "campaign_result_sha256": cloud["campaign_result_sha256"],
        "recovery_manifest_sha256": cloud["recovery_manifest_sha256"],
        "packet_manifest_sha256": EXPECTED_PACKET_MANIFEST_SHA256,
        "recovery_file_count": load_json(output_root / "RECOVERY_MANIFEST.json")["file_count"],
        "recovery_bytes": recovery_bytes,
        "arms": arms,
        "comparisons": recomputed,
        "producer_gate": expected_gate,
        "promotion": "NOT_AUTHORIZED",
        "claim_boundary": (
            "This receipt verifies the bounded training comparison only. Stable did not beat "
            "standard cross entropy by more than two pooled standard deviations on both primary "
            "metrics. Numerical-fidelity evidence is recorded separately."
        ),
    }


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
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
