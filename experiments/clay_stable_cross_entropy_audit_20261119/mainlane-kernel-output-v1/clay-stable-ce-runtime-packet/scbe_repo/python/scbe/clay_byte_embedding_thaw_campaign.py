"""Resume-safe controlled campaign for Clay's action-gated byte-row thaw.

This successor reuses completed parents and the exact source-disjoint dataset
from a sealed frozen-multiview baseline.  It never mutates those inputs.  The
primary stable-byte arm must beat both the frozen baseline and an equally sized
per-sample shuffled-byte arm before it can be considered for independent
replay.  No result grants execution or promotion authority.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping, Sequence

import torch

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from python.scbe.clay_byte_embedding_thaw import (
    ActionGatedByteEmbeddingThaw,
    THAW_ARMS,
    sample_local_byte_shuffle_rows,
)
from python.scbe.clay_frozen_multiview_adapter import (
    RunConfig,
    action_metrics,
    atomic_json,
    atomic_torch,
    counting_accuracy,
    counting_rows,
    file_sha256,
    flattened_trainable,
    frozen_state,
    frozen_state_identical,
    metric_comparison,
    paired_prediction_comparison,
    predict_action_rows,
    stable_hash,
    train_steps,
    utc_now,
)
from python.scbe.clay_frozen_multiview_data import (
    ActionTextRow,
    FrozenMultiviewDataset,
    build_frozen_multiview_dataset,
)
from python.scbe.clay_paired_orbit_training import ClaySourceAdapter
from python.scbe.concept_exposure_ledger import (
    ConceptExposureLedger,
    weight_effect_receipt,
)

SCHEMA = "clay.byte-embedding-thaw-campaign.v1"
AUTHORITY = "MEASUREMENT_ONLY_NO_EXECUTION_NO_PROMOTION"
PRIMARY = "byte_thaw_multiview"
SHUFFLED = "byte_thaw_sample_shuffled"
STATIC = "byte_thaw_static"
IMPORTED_CONTROLS = ("frozen_adapter_multiview", "no_intervention_adapter")
GATE_CONTROLS = ("frozen_adapter_multiview", SHUFFLED)
CONTROL_SHUFFLE_SEED = 20261115


@dataclass(frozen=True, slots=True)
class ThawCampaignConfig:
    baseline_run: str
    baseline_manifest_sha256: str
    baseline_result_sha256: str
    dataset_manifest_sha256: str
    seeds: tuple[int, ...]
    grow_steps: int
    checkpoint_every: int
    batch_size: int
    learning_rate: float
    threads: int
    device: str
    source_dir: str
    source_hashes: Mapping[str, str]
    control_shuffle_seed: int = CONTROL_SHUFFLE_SEED
    authority: str = AUTHORITY
    arms: tuple[str, ...] = THAW_ARMS


def require_storage(output: Path, minimum_free_gib: float) -> float:
    anchor = Path(output.anchor or "C:/")
    free = shutil.disk_usage(anchor).free / (1024**3)
    if free < minimum_free_gib:
        raise RuntimeError(
            f"storage admission closed: {free:.3f} GiB < {minimum_free_gib:.3f} GiB"
        )
    return free


def _baseline_rows(baseline: Mapping[str, Any], arm: str) -> list[dict[str, Any]]:
    rows = [dict(row) for row in baseline["per_arm"][arm]]
    if len(rows) != 3:
        raise RuntimeError(f"baseline arm {arm} must contain exactly three seeds")
    return sorted(rows, key=lambda row: int(row["seed"]))


def _arm_rows(
    arm: str, dataset: FrozenMultiviewDataset
) -> tuple[tuple[ActionTextRow, ...], tuple[ActionTextRow, ...]]:
    if arm == PRIMARY:
        return dataset.multiview_rows, dataset.holdout_rows
    if arm == STATIC:
        return dataset.static_rows, dataset.holdout_rows
    if arm == SHUFFLED:
        return (
            sample_local_byte_shuffle_rows(
                dataset.multiview_rows,
                seed=CONTROL_SHUFFLE_SEED,
            ),
            sample_local_byte_shuffle_rows(
                dataset.holdout_rows,
                seed=CONTROL_SHUFFLE_SEED,
            ),
        )
    raise ValueError(f"unknown thaw arm: {arm}")


def _training_config(
    campaign: ThawCampaignConfig,
    baseline_manifest: Mapping[str, Any],
) -> RunConfig:
    base = baseline_manifest["config"]
    return RunConfig(
        seeds=campaign.seeds,
        data_seed=int(base["data_seed"]),
        rows_per_view=int(base["rows_per_view"]),
        holdout_rows=int(base["holdout_rows"]),
        count_steps=int(base["count_steps"]),
        grow_steps=campaign.grow_steps,
        checkpoint_every=campaign.checkpoint_every,
        batch_size=campaign.batch_size,
        learning_rate=campaign.learning_rate,
        threads=campaign.threads,
        device=campaign.device,
        source_dir=campaign.source_dir,
        source_hashes=campaign.source_hashes,
        dataset_manifest_sha256=campaign.dataset_manifest_sha256,
        authority=campaign.authority,
        arms=campaign.arms,
    )


def train_arm(
    *,
    arm: str,
    seed: int,
    output: Path,
    campaign: ThawCampaignConfig,
    baseline_manifest: Mapping[str, Any],
    parent: Mapping[str, Any],
    parent_result: Mapping[str, Any],
    dataset: FrozenMultiviewDataset,
    config_hash: str,
) -> dict[str, Any]:
    directory = output / "horses" / f"{arm}-seed-{seed}"
    model_path = directory / "MODEL.pt"
    result_path = directory / "RESULT.json"
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if file_sha256(model_path) != result["model_sha256"]:
            raise RuntimeError("thaw horse model hash differs")
        return result

    vocab = list(parent["vocab"])
    stoi = {token: index for index, token in enumerate(vocab)}
    itos = {index: token for token, index in stoi.items()}
    torch.manual_seed(seed + 1701)
    model = ActionGatedByteEmbeddingThaw(vocab).to(campaign.device)
    model.load_parent_state(parent["model_state"])
    frozen_before = frozen_state(model)
    initial = flattened_trainable(model, arm).copy()
    train_rows, eval_rows = _arm_rows(arm, dataset)
    pairs = tuple(row.pair() for row in train_rows)
    ledger = ConceptExposureLedger(
        [
            *(row.sample for row in train_rows),
            *(row.sample for row in eval_rows),
        ],
        gradient_width=5,
        minimum_exposures_per_concept=max(1, campaign.grow_steps),
    )
    steps, loss, trainable = train_steps(
        model=model,
        stage=arm,
        seed=seed,
        rows=pairs,
        samples=train_rows,
        ledger=ledger,
        stoi=stoi,
        config=_training_config(campaign, baseline_manifest),
        total_steps=campaign.grow_steps,
        checkpoint_dir=directory / "checkpoints",
        config_hash=config_hash,
    )
    core_identical = frozen_state_identical(frozen_before, model)
    if not core_identical:
        raise RuntimeError(f"base parent tensors changed for {arm} seed {seed}")
    predictions = predict_action_rows(
        model,
        path="adapter",
        rows=eval_rows,
        stoi=stoi,
        itos=itos,
        device=campaign.device,
    )
    count_score = counting_accuracy(
        model,
        rows=counting_rows(True),
        stoi=stoi,
        itos=itos,
        device=campaign.device,
    )
    final = flattened_trainable(model, arm)
    payload = {
        "schema": f"{SCHEMA}.horse",
        "arm": arm,
        "seed": seed,
        "config_hash": config_hash,
        "parent_sha256": parent_result["parent_sha256"],
        "model_state": model.state_dict(),
        "vocab": vocab,
    }
    atomic_torch(model_path, payload)
    result = {
        "schema": f"{SCHEMA}.horse-result",
        "status": "COMPLETE",
        "authority": AUTHORITY,
        "arm": arm,
        "seed": seed,
        "steps": steps,
        "trainable_parameters": trainable,
        "final_loss": loss,
        "metrics": action_metrics(predictions),
        "predictions": predictions,
        "counting_accuracy": count_score,
        "parent_counting_accuracy": parent_result["counting_accuracy"],
        "base_parent_bit_identical": core_identical,
        "thaw_receipt": model.thaw_receipt(),
        "weight_effect": weight_effect_receipt(initial, final),
        "exposure_report": ledger.report(),
        "model_sha256": file_sha256(model_path),
        "completed_at_utc": utc_now(),
    }
    atomic_json(result_path, result)
    return result


def aggregate(
    learned: Sequence[Mapping[str, Any]],
    baseline: Mapping[str, Any],
    campaign: ThawCampaignConfig,
) -> dict[str, Any]:
    by_arm: dict[str, list[dict[str, Any]]] = {
        arm: sorted(
            (dict(row) for row in learned if row["arm"] == arm),
            key=lambda row: int(row["seed"]),
        )
        for arm in THAW_ARMS
    }
    for arm in IMPORTED_CONTROLS:
        by_arm[arm] = _baseline_rows(baseline, arm)
    comparisons = {}
    paired = {}
    for control in (*GATE_CONTROLS, STATIC):
        name = f"{PRIMARY}_vs_{control}"
        comparisons[name] = {
            metric: metric_comparison(by_arm[PRIMARY], by_arm[control], metric)
            for metric in ("accuracy", "macro_f1")
        }
        paired[name] = paired_prediction_comparison(by_arm[PRIMARY], by_arm[control])
    learned_parameter_counts = {
        int(row["trainable_parameters"]) for arm in THAW_ARMS for row in by_arm[arm]
    }
    retained = all(
        math.isclose(
            float(row["counting_accuracy"]),
            float(row["parent_counting_accuracy"]),
            abs_tol=1e-12,
        )
        and bool(row["base_parent_bit_identical"])
        for arm in THAW_ARMS
        for row in by_arm[arm]
    )
    rows_changed = all(
        int(row["thaw_receipt"]["changed_byte_rows"]) > 0
        for arm in THAW_ARMS
        for row in by_arm[arm]
    )
    gate_names = [f"{PRIMARY}_vs_{control}" for control in GATE_CONTROLS]
    producer_gate = (
        len(learned_parameter_counts) == 1
        and retained
        and rows_changed
        and all(
            comparisons[name][metric]["clears_positive_gate"]
            for name in gate_names
            for metric in ("accuracy", "macro_f1")
        )
        and all(paired[name]["clears_finite_uncertainty_gate"] for name in gate_names)
    )
    return {
        "schema": f"{SCHEMA}.result",
        "status": "COMPLETE",
        "authority": AUTHORITY,
        "promotion": "NOT_AUTHORIZED",
        "producer_gate": (
            "MET_PENDING_INDEPENDENT_REPLAY" if producer_gate else "NOT_MET"
        ),
        "config": asdict(campaign),
        "learned_parameter_count_matched": len(learned_parameter_counts) == 1,
        "counting_and_base_parent_preserved": retained,
        "thawed_rows_changed": rows_changed,
        "comparisons": comparisons,
        "paired_comparisons": paired,
        "per_arm": by_arm,
        "completed_at_utc": utc_now(),
    }


def _status(output: Path, **fields: Any) -> None:
    atomic_json(
        output / "STATUS.json",
        {
            "schema": f"{SCHEMA}.status",
            "status": "RUNNING",
            **fields,
            "updated_at_utc": utc_now(),
        },
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    baseline_run = args.baseline_run.resolve(strict=True)
    baseline_manifest_path = baseline_run / "RUN_MANIFEST.json"
    baseline_result_path = baseline_run / "RESULT.json"
    if not baseline_result_path.is_file():
        raise RuntimeError("frozen baseline is not complete")
    baseline_manifest = json.loads(baseline_manifest_path.read_text(encoding="utf-8"))
    baseline = json.loads(baseline_result_path.read_text(encoding="utf-8"))
    seeds = tuple(int(seed) for seed in baseline_manifest["config"]["seeds"])
    if len(seeds) != 3:
        raise RuntimeError("the thaw campaign requires the baseline's three seeds")
    output = args.output_dir.resolve()
    admitted_free_gib = require_storage(output, args.minimum_free_gib)
    preregistration = args.preregistration.resolve(strict=True)
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)

    provider = ClaySourceAdapter(Path(baseline_manifest["config"]["source_dir"]))
    dataset = build_frozen_multiview_dataset(
        provider,
        rows_per_view=int(baseline_manifest["config"]["rows_per_view"]),
        holdout_rows=int(baseline_manifest["config"]["holdout_rows"]),
        seed=int(baseline_manifest["config"]["data_seed"]),
    )
    dataset_hash = str(dataset.manifest["manifest_sha256"])
    if dataset_hash != baseline_manifest["dataset"]["manifest_sha256"]:
        raise RuntimeError("regenerated thaw dataset differs from baseline")
    campaign = ThawCampaignConfig(
        baseline_run=str(baseline_run),
        baseline_manifest_sha256=file_sha256(baseline_manifest_path),
        baseline_result_sha256=file_sha256(baseline_result_path),
        dataset_manifest_sha256=dataset_hash,
        seeds=seeds,
        grow_steps=args.grow_steps,
        checkpoint_every=args.checkpoint_every,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        threads=args.threads,
        device="cpu",
        source_dir=str(Path(baseline_manifest["config"]["source_dir"]).resolve()),
        source_hashes=dict(sorted(provider.source_hashes.items())),
    )
    config_hash = stable_hash(asdict(campaign))
    thaw_module_path = (
        Path(__file__).with_name("clay_byte_embedding_thaw.py").resolve(strict=True)
    )
    manifest = {
        "schema": f"{SCHEMA}.manifest",
        "config": asdict(campaign),
        "config_hash": config_hash,
        "runner": str(Path(__file__).resolve()),
        "runner_sha256": file_sha256(Path(__file__).resolve()),
        "thaw_module": str(thaw_module_path),
        "thaw_module_sha256": file_sha256(thaw_module_path),
        "preregistration": str(preregistration),
        "preregistration_sha256": file_sha256(preregistration),
        "dataset": dict(dataset.manifest),
        "admitted_free_gib": admitted_free_gib,
        "minimum_free_gib": args.minimum_free_gib,
    }
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "RUN_MANIFEST.json"
    if manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        comparable = dict(existing)
        comparable["admitted_free_gib"] = admitted_free_gib
        if comparable != manifest:
            raise RuntimeError("existing thaw manifest differs; use a new output")
    else:
        atomic_json(manifest_path, manifest)

    parent_results = {int(row["seed"]): row for row in baseline.get("parents", [])}
    learned = []
    for seed in seeds:
        parent_dir = baseline_run / "parents" / f"seed-{seed}"
        parent_path = parent_dir / "PARENT.pt"
        parent_result = parent_results.get(seed)
        if parent_result is None:
            parent_result = json.loads(
                (parent_dir / "RESULT.json").read_text(encoding="utf-8")
            )
        if file_sha256(parent_path) != parent_result["parent_sha256"]:
            raise RuntimeError(f"baseline parent hash differs for seed {seed}")
        parent = torch.load(parent_path, map_location="cpu", weights_only=False)
        for arm in THAW_ARMS:
            _status(output, seed=seed, stage=arm)
            result = train_arm(
                arm=arm,
                seed=seed,
                output=output,
                campaign=campaign,
                baseline_manifest=baseline_manifest,
                parent=parent,
                parent_result=parent_result,
                dataset=dataset,
                config_hash=config_hash,
            )
            learned.append(result)
            print(
                f"{arm:32s} seed={seed} "
                f"accuracy={result['metrics']['accuracy']:.6f} "
                f"macro_f1={result['metrics']['macro_f1']:.6f} "
                f"count={result['counting_accuracy']:.6f}",
                flush=True,
            )
    result = aggregate(learned, baseline, campaign)
    atomic_json(output / "RESULT.json", result)
    atomic_json(
        output / "STATUS.json",
        {
            "schema": f"{SCHEMA}.status",
            "status": "COMPLETE",
            "result_sha256": file_sha256(output / "RESULT.json"),
            "updated_at_utc": utc_now(),
        },
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--grow-steps", type=int, default=18_000)
    parser.add_argument("--checkpoint-every", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=0.002)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--minimum-free-gib", type=float, default=25.0)
    return parser.parse_args()


def main() -> int:
    result = run(parse_args())
    print(json.dumps({"producer_gate": result["producer_gate"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
