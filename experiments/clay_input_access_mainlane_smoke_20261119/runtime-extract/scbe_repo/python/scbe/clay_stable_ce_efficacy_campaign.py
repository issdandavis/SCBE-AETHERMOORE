"""Controlled stable-cross-entropy efficacy segment for Clay.

This runner starts two matched adapter arms from each immutable parent in the
pinned frozen-multiview baseline.  The only intervention is the hard-target
cross-entropy mode: unchanged PyTorch ``standard`` versus ``stable_log1p``.
The untouched parent is retained as the no-intervention control.  Results are
measurement only and cannot promote, merge, execute, or dispatch tools.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import threading
import time
from typing import Any, Iterable, Mapping, Sequence

import torch

from python.scbe.clay_frozen_multiview_adapter import (
    ARM_SEED_OFFSET,
    FrozenActionModel,
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
    path_for_arm,
    predict_action_rows,
    stable_hash,
    train_steps,
    vocab_of,
)
from python.scbe.clay_frozen_multiview_data import build_frozen_multiview_dataset
from python.scbe.clay_paired_orbit_training import ClaySourceAdapter
from python.scbe.clay_stable_cross_entropy import STANDARD, STABLE_LOG1P
from python.scbe.concept_exposure_ledger import (
    ConceptExposureLedger,
    weight_effect_receipt,
)

SCHEMA = "clay.stable-ce-efficacy-campaign.v1"
AUTHORITY = "MEASUREMENT_ONLY_NO_EXECUTION_NO_PROMOTION_NO_WEIGHT_OVERWRITE"
TRAIN_STAGE = "frozen_adapter_multiview"
LOSS_ARMS = (STANDARD, STABLE_LOG1P)
EXPECTED_BASELINE_MANIFEST_SHA256 = (
    "7f2516af8ae5a122f357565afad60ab412fdf54e76a3018cd8f1ddbfdb702a97"
)
EXPECTED_BASELINE_RESULT_SHA256 = (
    "c5261ada862a2851db0b1dd7e53835b5ddef22299660921527a249a866361482"
)
EXPECTED_DATASET_MANIFEST_SHA256 = (
    "7460665cbb718097438227c452f1915e88bdc5a10ac643122b17908b505d0041"
)
EXPECTED_SEEDS = (20261134, 20261135, 20261136)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected one JSON object: {path}")
    return value


def require_storage(output: Path, minimum_free_gib: float) -> float:
    anchor = Path(output.anchor or "/")
    free = shutil.disk_usage(anchor).free / (1024**3)
    if free < minimum_free_gib:
        raise RuntimeError(
            f"storage admission closed: {free:.3f} GiB < {minimum_free_gib:.3f} GiB"
        )
    return free


def _progress_monitor(
    *,
    pointer: Path,
    status: Path,
    stop: threading.Event,
    seed: int,
    loss_mode: str,
    poll_seconds: float,
) -> None:
    last_step = -1
    while not stop.wait(poll_seconds):
        if not pointer.is_file():
            continue
        value = load_json(pointer)
        step = int(value["step"])
        if step == last_step:
            continue
        last_step = step
        receipt = {
            "schema": f"{SCHEMA}.progress",
            "status": "TRAINING",
            "seed": seed,
            "loss_mode": loss_mode,
            "step": step,
            "generation": int(value["generation"]),
            "checkpoint_sha256": str(value["sha256"]),
            "updated_at_utc": utc_now(),
        }
        atomic_json(status, receipt)
        print(json.dumps(receipt, sort_keys=True), flush=True)


def _train_one_arm(
    *,
    seed: int,
    loss_mode: str,
    output: Path,
    config: RunConfig,
    config_hash: str,
    parent: Mapping[str, Any],
    parent_result: Mapping[str, Any],
    dataset: Any,
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    count_holdout: Sequence[tuple[str, str]],
    poll_seconds: float,
) -> dict[str, Any]:
    directory = output / "arms" / f"{loss_mode}-seed-{seed}"
    result_path = directory / "RESULT.json"
    model_path = directory / "MODEL.pt"
    if result_path.is_file():
        result = load_json(result_path)
        if result.get("loss_mode") != loss_mode:
            raise RuntimeError("existing result loss mode differs")
        if file_sha256(model_path) != result["model_sha256"]:
            raise RuntimeError("existing model hash differs")
        return result

    torch.manual_seed(seed + ARM_SEED_OFFSET[TRAIN_STAGE])
    model = FrozenActionModel(len(parent["vocab"])).to(config.device)
    model.load_state_dict(parent["model_state"])
    model.set_path(path_for_arm(TRAIN_STAGE))
    frozen_before = frozen_state(model)
    initial = flattened_trainable(model, TRAIN_STAGE).copy()
    records = dataset.multiview_rows
    pairs = tuple(row.pair() for row in records)
    ledger = ConceptExposureLedger(
        [
            *(row.sample for row in records),
            *(row.sample for row in dataset.holdout_rows),
        ],
        gradient_width=5,
        minimum_exposures_per_concept=max(1, config.grow_steps),
    )

    pointer = directory / "checkpoints" / "latest.json"
    progress_path = output / "PROGRESS.json"
    stop = threading.Event()
    monitor = threading.Thread(
        target=_progress_monitor,
        kwargs={
            "pointer": pointer,
            "status": progress_path,
            "stop": stop,
            "seed": seed,
            "loss_mode": loss_mode,
            "poll_seconds": poll_seconds,
        },
        daemon=True,
    )
    monitor.start()
    started = time.perf_counter()
    try:
        steps, loss, trainable = train_steps(
            model=model,
            stage=TRAIN_STAGE,
            seed=seed,
            rows=pairs,
            samples=records,
            ledger=ledger,
            stoi=stoi,
            config=config,
            total_steps=config.grow_steps,
            checkpoint_dir=directory / "checkpoints",
            config_hash=config_hash,
            loss_mode=loss_mode,
        )
    finally:
        stop.set()
        monitor.join(timeout=max(1.0, poll_seconds * 2.0))

    if not frozen_state_identical(frozen_before, model):
        raise RuntimeError(f"frozen tensors changed for {loss_mode} seed {seed}")
    predictions = predict_action_rows(
        model,
        path=path_for_arm(TRAIN_STAGE),
        rows=dataset.holdout_rows,
        stoi=stoi,
        itos=itos,
        device=config.device,
    )
    count_score = counting_accuracy(
        model=model,
        rows=count_holdout,
        stoi=stoi,
        itos=itos,
        device=config.device,
    )
    final = flattened_trainable(model, TRAIN_STAGE)
    payload = {
        "schema": f"{SCHEMA}.model",
        "seed": seed,
        "loss_mode": loss_mode,
        "config_hash": config_hash,
        "parent_sha256": parent_result["parent_sha256"],
        "model_state": model.state_dict(),
        "vocab": parent["vocab"],
    }
    atomic_torch(model_path, payload)
    result = {
        "schema": f"{SCHEMA}.arm-result",
        "status": "COMPLETE",
        "authority": AUTHORITY,
        "seed": seed,
        "loss_mode": loss_mode,
        "steps": steps,
        "trainable_parameters": trainable,
        "final_loss": loss,
        "metrics": action_metrics(predictions),
        "predictions": predictions,
        "counting_accuracy": count_score,
        "parent_counting_accuracy": float(parent_result["counting_accuracy"]),
        "parent_sha256": parent_result["parent_sha256"],
        "frozen_core_bit_identical": True,
        "weight_effect": weight_effect_receipt(initial, final),
        "exposure_report": ledger.report(),
        "model_sha256": file_sha256(model_path),
        "elapsed_seconds": time.perf_counter() - started,
        "completed_at_utc": utc_now(),
    }
    atomic_json(result_path, result)
    final_progress = {
        "schema": f"{SCHEMA}.progress",
        "status": "ARM_COMPLETE",
        "seed": seed,
        "loss_mode": loss_mode,
        "step": steps,
        "model_sha256": result["model_sha256"],
        "updated_at_utc": utc_now(),
    }
    atomic_json(progress_path, final_progress)
    print(json.dumps(final_progress, sort_keys=True), flush=True)
    return result


def _comparison(
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


def run_campaign(args: argparse.Namespace) -> dict[str, Any]:
    baseline = args.baseline_run.resolve(strict=True)
    output = args.output_dir.resolve()
    if args.seeds != EXPECTED_SEEDS:
        raise ValueError(f"seeds must remain pinned to {EXPECTED_SEEDS}")
    admitted_free_gib = require_storage(output, args.minimum_free_gib)
    baseline_manifest_path = baseline / "RUN_MANIFEST.json"
    baseline_result_path = baseline / "RESULT.json"
    if file_sha256(baseline_manifest_path) != EXPECTED_BASELINE_MANIFEST_SHA256:
        raise RuntimeError("baseline manifest hash differs")
    if file_sha256(baseline_result_path) != EXPECTED_BASELINE_RESULT_SHA256:
        raise RuntimeError("baseline result hash differs")
    baseline_manifest = load_json(baseline_manifest_path)
    baseline_result = load_json(baseline_result_path)
    if tuple(baseline_manifest["config"]["seeds"]) != EXPECTED_SEEDS:
        raise RuntimeError("baseline seeds differ")

    preregistration = args.preregistration.resolve(strict=True)
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)
    provider = ClaySourceAdapter(args.source_dir.resolve(strict=True))
    dataset = build_frozen_multiview_dataset(
        provider,
        rows_per_view=int(baseline_manifest["config"]["rows_per_view"]),
        holdout_rows=int(baseline_manifest["config"]["holdout_rows"]),
        seed=int(baseline_manifest["config"]["data_seed"]),
    )
    if dataset.manifest["manifest_sha256"] != EXPECTED_DATASET_MANIFEST_SHA256:
        raise RuntimeError("regenerated dataset manifest differs")

    count_train = counting_rows(False)
    count_holdout = counting_rows(True)
    static_pairs = tuple(row.pair() for row in dataset.static_rows)
    multiview_pairs = tuple(row.pair() for row in dataset.multiview_rows)
    holdout_pairs = tuple(row.pair() for row in dataset.holdout_rows)
    vocab, stoi = vocab_of(
        count_train,
        count_holdout,
        static_pairs,
        multiview_pairs,
        holdout_pairs,
    )
    itos = {index: char for char, index in stoi.items()}

    config = RunConfig(
        seeds=EXPECTED_SEEDS,
        data_seed=int(baseline_manifest["config"]["data_seed"]),
        rows_per_view=int(baseline_manifest["config"]["rows_per_view"]),
        holdout_rows=int(baseline_manifest["config"]["holdout_rows"]),
        count_steps=int(baseline_manifest["config"]["count_steps"]),
        grow_steps=args.steps,
        checkpoint_every=args.checkpoint_every,
        batch_size=args.batch_size,
        learning_rate=float(baseline_manifest["config"]["learning_rate"]),
        threads=args.threads,
        device="cpu",
        source_dir=str(args.source_dir.resolve(strict=True)),
        source_hashes=dict(sorted(provider.source_hashes.items())),
        dataset_manifest_sha256=str(dataset.manifest["manifest_sha256"]),
        authority=AUTHORITY,
        arms=("no_intervention_adapter", STANDARD, STABLE_LOG1P),
    )
    campaign_identity = {
        "schema": SCHEMA,
        "config": asdict(config),
        "baseline_manifest_sha256": EXPECTED_BASELINE_MANIFEST_SHA256,
        "baseline_result_sha256": EXPECTED_BASELINE_RESULT_SHA256,
        "preregistration_sha256": file_sha256(preregistration),
    }
    config_hash = stable_hash(campaign_identity)
    manifest = {
        **campaign_identity,
        "config_hash": config_hash,
        "runner": str(Path(__file__).resolve()),
        "runner_sha256": file_sha256(Path(__file__).resolve()),
        "baseline_run": str(baseline),
        "dataset": dict(dataset.manifest),
        "admitted_free_gib": admitted_free_gib,
        "minimum_free_gib": args.minimum_free_gib,
        "authority": AUTHORITY,
        "claim_boundary": "Controlled training measurement only; no promotion or overwrite authority.",
    }
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "RUN_MANIFEST.json"
    if manifest_path.is_file():
        existing = load_json(manifest_path)
        comparable = dict(existing)
        comparable["admitted_free_gib"] = admitted_free_gib
        if comparable != manifest:
            raise RuntimeError("existing campaign manifest differs")
    else:
        atomic_json(manifest_path, manifest)

    no_intervention = sorted(
        baseline_result["per_arm"]["no_intervention_adapter"],
        key=lambda row: int(row["seed"]),
    )
    by_mode: dict[str, list[dict[str, Any]]] = {mode: [] for mode in LOSS_ARMS}
    for seed in EXPECTED_SEEDS:
        parent_dir = baseline / "parents" / f"seed-{seed}"
        parent_result = load_json(parent_dir / "RESULT.json")
        parent_path = parent_dir / "PARENT.pt"
        if file_sha256(parent_path) != parent_result["parent_sha256"]:
            raise RuntimeError(f"parent hash differs for seed {seed}")
        parent = torch.load(parent_path, map_location="cpu", weights_only=False)
        if parent["vocab"] != vocab:
            raise RuntimeError(f"parent vocabulary differs for seed {seed}")
        for mode in LOSS_ARMS:
            atomic_json(
                output / "PROGRESS.json",
                {
                    "schema": f"{SCHEMA}.progress",
                    "status": "STARTING_ARM",
                    "seed": seed,
                    "loss_mode": mode,
                    "step": 0,
                    "updated_at_utc": utc_now(),
                },
            )
            by_mode[mode].append(
                _train_one_arm(
                    seed=seed,
                    loss_mode=mode,
                    output=output,
                    config=config,
                    config_hash=config_hash,
                    parent=parent,
                    parent_result=parent_result,
                    dataset=dataset,
                    stoi=stoi,
                    itos=itos,
                    count_holdout=count_holdout,
                    poll_seconds=args.progress_poll_seconds,
                )
            )

    comparisons = {
        "stable_vs_standard": _comparison(by_mode[STABLE_LOG1P], by_mode[STANDARD]),
        "stable_vs_no_intervention": _comparison(by_mode[STABLE_LOG1P], no_intervention),
        "standard_vs_no_intervention": _comparison(by_mode[STANDARD], no_intervention),
    }
    producer_gate = all(
        comparisons[name]["metrics"][metric]["clears_positive_gate"]
        for name in ("stable_vs_standard", "stable_vs_no_intervention")
        for metric in ("accuracy", "macro_f1")
    )
    result = {
        "schema": f"{SCHEMA}.result",
        "status": "COMPLETE",
        "authority": AUTHORITY,
        "promotion": "NOT_AUTHORIZED",
        "config": asdict(config),
        "config_hash": config_hash,
        "baseline_manifest_sha256": EXPECTED_BASELINE_MANIFEST_SHA256,
        "baseline_result_sha256": EXPECTED_BASELINE_RESULT_SHA256,
        "dataset_manifest_sha256": EXPECTED_DATASET_MANIFEST_SHA256,
        "per_arm": {
            "no_intervention_adapter": no_intervention,
            STANDARD: by_mode[STANDARD],
            STABLE_LOG1P: by_mode[STABLE_LOG1P],
        },
        "comparisons": comparisons,
        "producer_gate": "MET_PENDING_INDEPENDENT_REPLAY" if producer_gate else "NOT_MET",
        "claim_boundary": (
            "A 2,000-step bounded segment can measure direction and variance but does not replace "
            "the preregistered full-budget campaign or authorize promotion."
        ),
        "completed_at_utc": utc_now(),
    }
    if any(not math.isfinite(float(row["final_loss"])) for mode in LOSS_ARMS for row in by_mode[mode]):
        raise RuntimeError("non-finite final loss")
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


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-run", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--preregistration", required=True, type=Path)
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--checkpoint-every", type=int, default=250)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--minimum-free-gib", type=float, default=25.0)
    parser.add_argument("--progress-poll-seconds", type=float, default=2.0)
    parsed = parser.parse_args(arguments)
    parsed.seeds = EXPECTED_SEEDS
    if parsed.steps < 1 or parsed.checkpoint_every < 1 or parsed.batch_size < 1:
        parser.error("steps, checkpoint interval, and batch size must be positive")
    return parsed


def main(arguments: Iterable[str] | None = None) -> int:
    result = run_campaign(parse_args(arguments))
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "status": result["status"],
                "producer_gate": result["producer_gate"],
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
