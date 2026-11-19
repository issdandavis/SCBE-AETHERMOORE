"""Controlled Clay input-access versus downstream-only adapter campaign.

The candidate gives a new skill a causal embedding/GRU path over the raw token
inputs before the frozen recurrence bottleneck.  The matched control receives
only the frozen recurrence output.  Both trained arms expose exactly 140,820
trainable parameters and start from bit-identical action logits.  The pinned
no-intervention baseline is retained as the second control.

This module is measurement-only.  It cannot promote, merge, execute tools, or
overwrite the immutable parent checkpoints.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import threading
import time
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import torch
from torch import Tensor, nn

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
    make_batch,
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
from python.scbe.clay_stable_cross_entropy import STANDARD
from python.scbe.concept_exposure_ledger import (
    ConceptExposureLedger,
    weight_effect_receipt,
)

SCHEMA = "clay.input-access-efficacy-campaign.v1"
AUTHORITY = "MEASUREMENT_ONLY_NO_EXECUTION_NO_PROMOTION_NO_WEIGHT_OVERWRITE"
TRAIN_STAGE = "frozen_adapter_multiview"
DOWNSTREAM_ONLY = "downstream_only"
INPUT_ACCESS = "input_access"
TRAINED_ARMS = (DOWNSTREAM_ONLY, INPUT_ACCESS)
EXPECTED_BASELINE_MANIFEST_SHA256 = (
    "7f2516af8ae5a122f357565afad60ab412fdf54e76a3018cd8f1ddbfdb702a97"
)
EXPECTED_BASELINE_RESULT_SHA256 = (
    "c5261ada862a2851db0b1dd7e53835b5ddef22299660921527a249a866361482"
)
EXPECTED_DATASET_MANIFEST_SHA256 = (
    "7460665cbb718097438227c452f1915e88bdc5a10ac643122b17908b505d0041"
)
EXPECTED_PREREGISTRATION_SCHEMA = "clay.input-access-efficacy-preregistration.v1"
EXPECTED_PREREGISTRATION_SHA256 = (
    "f5613e79353dfcdaddb2935e8b087d66f50c025cb31ca75824e17e1bca0f4080"
)
EXPECTED_SEEDS = (20261134, 20261135, 20261136)
EXPECTED_VOCAB_SIZE = 276
EXPECTED_TRAINABLE_PARAMETERS = 140_820
INPUT_EMBEDDING_WIDTH = 271
INPUT_RECURRENT_WIDTH = 12
FROZEN_HIDDEN_WIDTH = 192
EXPECTED_STEPS = 2000
EXPECTED_CHECKPOINT_EVERY = 250
EXPECTED_BATCH_SIZE = 128
EXPECTED_THREADS = 2
EXPECTED_MINIMUM_FREE_GIB = 25.0
FINITE_FAMILY_ALPHA = 0.05
FINITE_TEST_COUNT = 4
FINITE_PER_TEST_ALPHA = FINITE_FAMILY_ALPHA / FINITE_TEST_COUNT
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20261119


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected one JSON object: {path}")
    return value


def require_storage(output: Path, minimum_free_gib: float) -> float:
    anchor = output.resolve()
    while not anchor.exists():
        parent = anchor.parent
        if parent == anchor:
            raise RuntimeError(f"cannot locate storage filesystem for {output}")
        anchor = parent
    free = shutil.disk_usage(anchor).free / (1024**3)
    if free < minimum_free_gib:
        raise RuntimeError(
            f"storage admission closed: {free:.3f} GiB < {minimum_free_gib:.3f} GiB"
        )
    return free


def validate_preregistered_budget(args: argparse.Namespace) -> None:
    expected = {
        "steps": EXPECTED_STEPS,
        "checkpoint_every": EXPECTED_CHECKPOINT_EVERY,
        "batch_size": EXPECTED_BATCH_SIZE,
        "threads": EXPECTED_THREADS,
        "minimum_free_gib": EXPECTED_MINIMUM_FREE_GIB,
    }
    actual = {key: getattr(args, key) for key in expected}
    if actual != expected:
        raise ValueError(f"official input-access budget differs: {actual} != {expected}")


def tensor_sha256(value: Tensor) -> str:
    array = value.detach().cpu().contiguous().numpy()
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def trainable_parameter_names(model: FrozenActionModel) -> tuple[str, ...]:
    selected = {id(parameter) for parameter in model.parameters_for(TRAIN_STAGE)}
    names = tuple(
        name for name, parameter in model.named_parameters() if id(parameter) in selected
    )
    selected_count = sum(
        parameter.numel()
        for parameter in model.parameters_for(TRAIN_STAGE)
    )
    named_count = sum(dict(model.named_parameters())[name].numel() for name in names)
    if selected_count != named_count:
        raise RuntimeError("selected trainable parameters are not uniquely named")
    return names


def nonselected_state(model: FrozenActionModel) -> dict[str, Tensor]:
    selected = set(trainable_parameter_names(model))
    return {
        key: value.detach().cpu().clone()
        for key, value in model.state_dict().items()
        if key not in selected
    }


def state_identical(before: Mapping[str, Tensor], model: FrozenActionModel) -> bool:
    after = nonselected_state(model)
    return before.keys() == after.keys() and all(
        torch.equal(before[key], after[key]) for key in before
    )


def pinned_parent_result(
    baseline_result: Mapping[str, Any], seed: int
) -> Mapping[str, Any]:
    matches = [row for row in baseline_result["parents"] if int(row["seed"]) == seed]
    if len(matches) != 1:
        raise RuntimeError(f"pinned aggregate parent row differs for seed {seed}")
    return matches[0]


def validate_preregistration(path: Path) -> dict[str, Any]:
    if file_sha256(path) != EXPECTED_PREREGISTRATION_SHA256:
        raise RuntimeError("preregistration hash differs")
    value = load_json(path)
    if value.get("schema") != EXPECTED_PREREGISTRATION_SCHEMA:
        raise RuntimeError("preregistration schema differs")
    if value.get("status") != "PREREGISTERED_BEFORE_RESULTS":
        raise RuntimeError("preregistration status differs")
    return value


def validate_parent_lineage(
    *,
    seed: int,
    parent_result: Mapping[str, Any],
    parent_path: Path,
    baseline_result: Mapping[str, Any],
) -> Mapping[str, Any]:
    aggregate = pinned_parent_result(baseline_result, seed)
    expected = {
        "seed": seed,
        "parent_sha256": aggregate["parent_sha256"],
        "counting_accuracy": float(aggregate["counting_accuracy"]),
    }
    for key, value in expected.items():
        if parent_result.get(key) != value:
            raise RuntimeError(f"adjacent parent result differs from aggregate: {key}")
    if file_sha256(parent_path) != aggregate["parent_sha256"]:
        raise RuntimeError(f"parent hash differs from aggregate for seed {seed}")
    return aggregate


class InputAccessActionModel(FrozenActionModel):
    """Frozen parent plus a causal raw-input sidecar with matched capacity.

    The exact pinned vocabulary makes the sidecar and the ordinary downstream
    adapter equal in trainable scalar count:

      Embedding(276,271) + GRU(271,12) + Linear(12,192)
      + Linear(192,276) == 140,820.
    """

    def __init__(self, vocab_size: int) -> None:
        if vocab_size != EXPECTED_VOCAB_SIZE:
            raise ValueError(
                f"input-access architecture is pinned to vocab {EXPECTED_VOCAB_SIZE}, "
                f"got {vocab_size}"
            )
        super().__init__(vocab_size)
        self.input_embedding = nn.Embedding(
            vocab_size,
            INPUT_EMBEDDING_WIDTH,
        )
        self.input_recurrence = nn.GRU(
            INPUT_EMBEDDING_WIDTH,
            INPUT_RECURRENT_WIDTH,
            batch_first=True,
        )
        self.input_up = nn.Linear(INPUT_RECURRENT_WIDTH, FROZEN_HIDDEN_WIDTH)
        nn.init.zeros_(self.input_up.weight)
        nn.init.zeros_(self.input_up.bias)

    def set_path(self, path: str) -> None:
        if path != "adapter":
            raise ValueError(f"input-access arm supports only the adapter schedule, got {path}")
        self.active_path = path

    def action_logits_from_hidden(
        self,
        inputs: Tensor,
        frozen_hidden: Tensor,
        input_state: Tensor | None = None,
    ) -> tuple[Tensor, Tensor]:
        sidecar_inputs = inputs
        drop_anchor = input_state is None
        if drop_anchor:
            anchor = torch.zeros(
                (inputs.shape[0], 1),
                dtype=inputs.dtype,
                device=inputs.device,
            )
            sidecar_inputs = torch.cat((anchor, inputs), dim=1)
        sidecar, input_state = self.input_recurrence(
            self.input_embedding(sidecar_inputs),
            input_state,
        )
        if drop_anchor:
            sidecar = sidecar[:, 1:]
        return self.adapter_head(frozen_hidden + self.input_up(sidecar)), input_state

    def forward(
        self,
        inputs: Tensor,
        head: str,
        state: Any = None,
    ) -> tuple[Tensor, Any]:
        if isinstance(state, tuple):
            core_state, input_state = state
        else:
            core_state, input_state = state, None
        hidden, core_state = self.g(self.e(inputs), core_state)
        if head == "count":
            return self.count_head(hidden), core_state
        logits, input_state = self.action_logits_from_hidden(
            inputs,
            hidden,
            input_state,
        )
        return logits, (core_state, input_state)

    def parameters_for(self, stage: str) -> list[nn.Parameter]:
        if stage == "count_parent":
            return super().parameters_for(stage)
        if stage != TRAIN_STAGE:
            raise ValueError(f"unknown input-access stage: {stage}")
        modules: tuple[nn.Module, ...] = (
            self.input_embedding,
            self.input_recurrence,
            self.input_up,
            self.adapter_head,
        )
        return [parameter for module in modules for parameter in module.parameters()]


def construct_arm_model(
    *,
    arm: str,
    parent: Mapping[str, Any],
    seed: int,
    device: str,
) -> FrozenActionModel:
    if arm not in TRAINED_ARMS:
        raise ValueError(f"unknown arm: {arm}")
    vocab_size = len(parent["vocab"])
    if vocab_size != EXPECTED_VOCAB_SIZE:
        raise RuntimeError(f"pinned parent vocab differs: {vocab_size}")
    torch.manual_seed(seed + ARM_SEED_OFFSET[TRAIN_STAGE])
    model: FrozenActionModel
    if arm == INPUT_ACCESS:
        model = InputAccessActionModel(vocab_size)
    else:
        model = FrozenActionModel(vocab_size)
    incompatible = model.load_state_dict(parent["model_state"], strict=False)
    if arm == DOWNSTREAM_ONLY:
        if incompatible.missing_keys or incompatible.unexpected_keys:
            raise RuntimeError(f"downstream parent state differs: {incompatible}")
    else:
        expected_missing = {
            "input_embedding.weight",
            "input_recurrence.weight_ih_l0",
            "input_recurrence.weight_hh_l0",
            "input_recurrence.bias_ih_l0",
            "input_recurrence.bias_hh_l0",
            "input_up.weight",
            "input_up.bias",
        }
        if set(incompatible.missing_keys) != expected_missing or incompatible.unexpected_keys:
            raise RuntimeError(f"input-access parent state differs: {incompatible}")
    model.to(device)
    model.set_path(path_for_arm(TRAIN_STAGE))
    trainable = sum(parameter.numel() for parameter in model.parameters_for(TRAIN_STAGE))
    if trainable != EXPECTED_TRAINABLE_PARAMETERS:
        raise RuntimeError(
            f"{arm} trainable parameter count differs: {trainable} != "
            f"{EXPECTED_TRAINABLE_PARAMETERS}"
        )
    return model


@torch.inference_mode()
def initial_pair_receipt(
    *,
    parent: Mapping[str, Any],
    seed: int,
    rows: Sequence[tuple[str, str]],
    stoi: Mapping[str, int],
    device: str,
) -> dict[str, Any]:
    indices = list(range(min(8, len(rows))))
    inputs, _, _ = make_batch(rows, indices, stoi, device)
    downstream = construct_arm_model(
        arm=DOWNSTREAM_ONLY,
        parent=parent,
        seed=seed,
        device=device,
    )
    candidate = construct_arm_model(
        arm=INPUT_ACCESS,
        parent=parent,
        seed=seed,
        device=device,
    )
    downstream.eval()
    candidate.eval()
    downstream_logits, _ = downstream(inputs, "action")
    candidate_logits, _ = candidate(inputs, "action")
    if not torch.equal(downstream_logits, candidate_logits):
        raise RuntimeError(f"initial arm logits differ for seed {seed}")
    return {
        "schema": f"{SCHEMA}.initial-pair",
        "seed": seed,
        "examples": len(indices),
        "bit_identical_logits": True,
        "logits_sha256": tensor_sha256(downstream_logits),
        "downstream_trainable_parameters": sum(
            parameter.numel() for parameter in downstream.parameters_for(TRAIN_STAGE)
        ),
        "input_access_trainable_parameters": sum(
            parameter.numel() for parameter in candidate.parameters_for(TRAIN_STAGE)
        ),
        "downstream_trainable_parameter_names": list(
            trainable_parameter_names(downstream)
        ),
        "input_access_trainable_parameter_names": list(
            trainable_parameter_names(candidate)
        ),
    }


def _progress_monitor(
    *,
    pointer: Path,
    status: Path,
    stop: threading.Event,
    seed: int,
    arm: str,
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
            "arm": arm,
            "step": step,
            "generation": int(value["generation"]),
            "checkpoint_sha256": str(value["sha256"]),
            "updated_at_utc": utc_now(),
        }
        atomic_json(status, receipt)
        print(json.dumps(receipt, sort_keys=True), flush=True)


def validate_completed_arm_result(
    *,
    result: Mapping[str, Any],
    model_path: Path,
    seed: int,
    arm: str,
    config: RunConfig,
    campaign_config_hash: str,
    arm_config_hash: str,
    parent: Mapping[str, Any],
    parent_result: Mapping[str, Any],
    dataset: Any,
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    count_holdout: Sequence[tuple[str, str]],
) -> None:
    """Fail closed when reusing a completed arm, then replay its measurements."""

    initial_model = construct_arm_model(
        arm=arm,
        parent=parent,
        seed=seed,
        device=config.device,
    )
    selected_names = trainable_parameter_names(initial_model)
    expected = {
        "schema": f"{SCHEMA}.arm-result",
        "status": "COMPLETE",
        "authority": AUTHORITY,
        "seed": seed,
        "arm": arm,
        "loss_mode": STANDARD,
        "campaign_config_hash": campaign_config_hash,
        "arm_config_hash": arm_config_hash,
        "steps": config.grow_steps,
        "trainable_parameters": EXPECTED_TRAINABLE_PARAMETERS,
        "parent_sha256": parent_result["parent_sha256"],
        "frozen_core_bit_identical": True,
        "all_nonselected_tensors_bit_identical": True,
        "trainable_parameter_names": list(selected_names),
        "parent_counting_accuracy": float(parent_result["counting_accuracy"]),
    }
    for key, value in expected.items():
        if result.get(key) != value:
            raise RuntimeError(f"existing completed arm field differs: {key}")
    if not math.isfinite(float(result["final_loss"])):
        raise RuntimeError("existing completed arm loss is non-finite")
    if not model_path.is_file() or file_sha256(model_path) != result.get("model_sha256"):
        raise RuntimeError("existing completed arm model hash differs")

    payload = torch.load(model_path, map_location=config.device, weights_only=False)
    payload_expected = {
        "schema": f"{SCHEMA}.model",
        "seed": seed,
        "arm": arm,
        "loss_mode": STANDARD,
        "campaign_config_hash": campaign_config_hash,
        "arm_config_hash": arm_config_hash,
        "parent_sha256": parent_result["parent_sha256"],
        "vocab": parent["vocab"],
    }
    for key, value in payload_expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"existing completed model field differs: {key}")
    if not isinstance(payload.get("model_state"), Mapping):
        raise RuntimeError("existing completed model state is missing")

    initial_trainable = flattened_trainable(initial_model, TRAIN_STAGE).copy()
    frozen_before = frozen_state(initial_model)
    nonselected_before = nonselected_state(initial_model)
    initial_model.load_state_dict(payload["model_state"], strict=True)
    if not frozen_state_identical(frozen_before, initial_model):
        raise RuntimeError("existing completed model changed frozen tensors")
    if not state_identical(nonselected_before, initial_model):
        raise RuntimeError("existing completed model changed non-selected tensors")
    predictions = predict_action_rows(
        initial_model,
        path=path_for_arm(TRAIN_STAGE),
        rows=dataset.holdout_rows,
        stoi=stoi,
        itos=itos,
        device=config.device,
    )
    if result.get("predictions") != predictions:
        raise RuntimeError("existing completed arm predictions differ on replay")
    if result.get("metrics") != action_metrics(predictions):
        raise RuntimeError("existing completed arm metrics differ on replay")
    count_score = counting_accuracy(
        model=initial_model,
        rows=count_holdout,
        stoi=stoi,
        itos=itos,
        device=config.device,
    )
    if result.get("counting_accuracy") != count_score:
        raise RuntimeError("existing completed arm counting score differs on replay")
    if count_score != float(parent_result["counting_accuracy"]):
        raise RuntimeError("existing completed arm did not retain parent counting")
    effect = weight_effect_receipt(
        initial_trainable,
        flattened_trainable(initial_model, TRAIN_STAGE),
    )
    if result.get("weight_effect") != effect:
        raise RuntimeError("existing completed arm weight effect differs on replay")


def _train_one_arm(
    *,
    seed: int,
    arm: str,
    output: Path,
    config: RunConfig,
    campaign_config_hash: str,
    parent: Mapping[str, Any],
    parent_result: Mapping[str, Any],
    dataset: Any,
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    count_holdout: Sequence[tuple[str, str]],
    poll_seconds: float,
) -> dict[str, Any]:
    directory = output / "arms" / f"{arm}-seed-{seed}"
    result_path = directory / "RESULT.json"
    model_path = directory / "MODEL.pt"
    arm_config_hash = stable_hash(
        {"campaign_config_hash": campaign_config_hash, "arm": arm}
    )
    if result_path.is_file():
        result = load_json(result_path)
        validate_completed_arm_result(
            result=result,
            model_path=model_path,
            seed=seed,
            arm=arm,
            config=config,
            campaign_config_hash=campaign_config_hash,
            arm_config_hash=arm_config_hash,
            parent=parent,
            parent_result=parent_result,
            dataset=dataset,
            stoi=stoi,
            itos=itos,
            count_holdout=count_holdout,
        )
        return result

    model = construct_arm_model(arm=arm, parent=parent, seed=seed, device=config.device)
    frozen_before = frozen_state(model)
    nonselected_before = nonselected_state(model)
    selected_names = trainable_parameter_names(model)
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
            "arm": arm,
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
            config_hash=arm_config_hash,
            loss_mode=STANDARD,
        )
    finally:
        stop.set()
        monitor.join(timeout=max(1.0, poll_seconds * 2.0))

    if trainable != EXPECTED_TRAINABLE_PARAMETERS:
        raise RuntimeError(f"optimizer parameter count differs for {arm}: {trainable}")
    if not frozen_state_identical(frozen_before, model):
        raise RuntimeError(f"frozen tensors changed for {arm} seed {seed}")
    if not state_identical(nonselected_before, model):
        raise RuntimeError(f"non-selected tensors changed for {arm} seed {seed}")
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
    parent_count_score = float(parent_result["counting_accuracy"])
    if count_score != parent_count_score:
        raise RuntimeError(
            f"counting retention differs for {arm} seed {seed}: "
            f"{count_score} != {parent_count_score}"
        )
    final = flattened_trainable(model, TRAIN_STAGE)
    payload = {
        "schema": f"{SCHEMA}.model",
        "seed": seed,
        "arm": arm,
        "loss_mode": STANDARD,
        "campaign_config_hash": campaign_config_hash,
        "arm_config_hash": arm_config_hash,
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
        "arm": arm,
        "loss_mode": STANDARD,
        "campaign_config_hash": campaign_config_hash,
        "arm_config_hash": arm_config_hash,
        "steps": steps,
        "trainable_parameters": trainable,
        "final_loss": loss,
        "metrics": action_metrics(predictions),
        "predictions": predictions,
        "counting_accuracy": count_score,
        "parent_counting_accuracy": parent_count_score,
        "parent_sha256": parent_result["parent_sha256"],
        "frozen_core_bit_identical": True,
        "all_nonselected_tensors_bit_identical": True,
        "trainable_parameter_names": list(selected_names),
        "weight_effect": weight_effect_receipt(initial, final),
        "exposure_report": ledger.report(),
        "model_sha256": file_sha256(model_path),
        "elapsed_seconds": time.perf_counter() - started,
        "completed_at_utc": utc_now(),
    }
    if not math.isfinite(float(loss)):
        raise RuntimeError(f"non-finite loss for {arm} seed {seed}")
    atomic_json(result_path, result)
    progress = {
        "schema": f"{SCHEMA}.progress",
        "status": "ARM_COMPLETE",
        "seed": seed,
        "arm": arm,
        "step": steps,
        "model_sha256": result["model_sha256"],
        "updated_at_utc": utc_now(),
    }
    atomic_json(output / "PROGRESS.json", progress)
    print(json.dumps(progress, sort_keys=True), flush=True)
    return result


def _prediction_arrays(
    runs: Sequence[Mapping[str, Any]],
) -> tuple[np.ndarray, np.ndarray]:
    ordered = sorted(
        (
            int(row["seed"]),
            int(item["example_index"]),
            int(item["target"]),
            -1 if item["prediction"] is None else int(item["prediction"]),
        )
        for row in runs
        for item in row["predictions"]
    )
    keys = np.asarray([(seed, index) for seed, index, _, _ in ordered], dtype=np.int64)
    values = np.asarray([(target, prediction) for _, _, target, prediction in ordered])
    return keys, values


def paired_macro_f1_bootstrap(
    contender: Sequence[Mapping[str, Any]],
    control: Sequence[Mapping[str, Any]],
    *,
    seed: int,
) -> dict[str, Any]:
    """Deterministic seed-and-target-stratified bootstrap for macro-F1."""

    left_keys, left = _prediction_arrays(contender)
    right_keys, right = _prediction_arrays(control)
    if not np.array_equal(left_keys, right_keys) or not np.array_equal(left[:, 0], right[:, 0]):
        raise RuntimeError("paired macro-F1 prediction keys or targets differ")
    targets = left[:, 0]
    left_prediction = left[:, 1]
    right_prediction = right[:, 1]
    seeds = left_keys[:, 0]
    unique_seeds = np.unique(seeds)
    strata = [
        np.flatnonzero((seeds == run_seed) & (targets == label))
        for run_seed in unique_seeds
        for label in range(5)
    ]
    if any(not len(indices) for indices in strata):
        raise RuntimeError("paired macro-F1 bootstrap requires every target class")
    generator = np.random.default_rng(seed)
    deltas = np.empty(BOOTSTRAP_REPLICATES, dtype=np.float64)
    offset = 0
    chunk_size = 100
    while offset < BOOTSTRAP_REPLICATES:
        size = min(chunk_size, BOOTSTRAP_REPLICATES - offset)
        sampled = np.concatenate(
            [generator.choice(indices, size=(size, len(indices)), replace=True) for indices in strata],
            axis=1,
        )
        sampled_seeds = seeds[sampled]
        sampled_targets = targets[sampled]
        sampled_left = left_prediction[sampled]
        sampled_right = right_prediction[sampled]
        scores = []
        for predictions in (sampled_left, sampled_right):
            seed_f1 = []
            for run_seed in unique_seeds:
                class_f1 = []
                seed_mask = sampled_seeds == run_seed
                for label in range(5):
                    true_positive = np.sum(
                        seed_mask
                        & (predictions == label)
                        & (sampled_targets == label),
                        axis=1,
                    )
                    false_positive = np.sum(
                        seed_mask
                        & (predictions == label)
                        & (sampled_targets != label),
                        axis=1,
                    )
                    false_negative = np.sum(
                        seed_mask
                        & (predictions != label)
                        & (sampled_targets == label),
                        axis=1,
                    )
                    denominator = 2 * true_positive + false_positive + false_negative
                    class_f1.append(
                        np.divide(
                            2 * true_positive,
                            denominator,
                            out=np.zeros(size, dtype=np.float64),
                            where=denominator != 0,
                        )
                    )
                seed_f1.append(np.mean(np.stack(class_f1, axis=1), axis=1))
            scores.append(np.mean(np.stack(seed_f1, axis=1), axis=1))
        deltas[offset : offset + size] = scores[0] - scores[1]
        offset += size
    ordered = np.sort(deltas)
    lower_index = max(0, math.ceil(FINITE_PER_TEST_ALPHA * BOOTSTRAP_REPLICATES) - 1)
    observed = (
        sum(float(row["metrics"]["macro_f1"]) for row in contender) / len(contender)
        - sum(float(row["metrics"]["macro_f1"]) for row in control) / len(control)
    )
    lower_bound = float(ordered[lower_index])
    return {
        "method": "deterministic_seed_target_stratified_paired_bootstrap",
        "seed": seed,
        "replicates": BOOTSTRAP_REPLICATES,
        "family_alpha": FINITE_FAMILY_ALPHA,
        "test_count": FINITE_TEST_COUNT,
        "per_test_alpha": FINITE_PER_TEST_ALPHA,
        "observed_mean_macro_f1_delta": observed,
        "lower_order_statistic_index": lower_index,
        "one_sided_lower_bound": lower_bound,
        "clears_finite_uncertainty_gate": observed > 0.0 and lower_bound > 0.0,
    }


def _comparison(
    primary: Sequence[Mapping[str, Any]],
    control: Sequence[Mapping[str, Any]],
    *,
    bootstrap_seed: int,
) -> dict[str, Any]:
    accuracy = paired_prediction_comparison(primary, control)
    accuracy.update(
        {
            "method": "two_sided_exact_mcnemar",
            "family_alpha": FINITE_FAMILY_ALPHA,
            "test_count": FINITE_TEST_COUNT,
            "per_test_alpha": FINITE_PER_TEST_ALPHA,
            "clears_finite_uncertainty_gate": (
                int(accuracy["wins"]) > int(accuracy["losses"])
                and float(accuracy["two_sided_exact_p"]) <= FINITE_PER_TEST_ALPHA
            ),
        }
    )
    return {
        "metrics": {
            metric: metric_comparison(primary, control, metric)
            for metric in ("accuracy", "macro_f1")
        },
        "paired": accuracy,
        "finite_evaluation": {
            "accuracy": accuracy,
            "macro_f1": paired_macro_f1_bootstrap(
                primary,
                control,
                seed=bootstrap_seed,
            ),
        },
    }


def producer_gate_met(
    comparisons: Mapping[str, Any], retention_gate: bool
) -> tuple[bool, bool, bool]:
    required = (
        "input_access_vs_downstream_only",
        "input_access_vs_no_intervention",
    )
    variance_gate = all(
        comparisons[name]["metrics"][metric]["clears_positive_gate"]
        for name in required
        for metric in ("accuracy", "macro_f1")
    )
    finite_evaluation_gate = all(
        comparisons[name]["finite_evaluation"][metric][
            "clears_finite_uncertainty_gate"
        ]
        for name in required
        for metric in ("accuracy", "macro_f1")
    )
    return (
        variance_gate,
        finite_evaluation_gate,
        variance_gate and finite_evaluation_gate and retention_gate,
    )


def run_campaign(args: argparse.Namespace) -> dict[str, Any]:
    validate_preregistered_budget(args)
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
    validate_preregistration(preregistration)
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
    if len(vocab) != EXPECTED_VOCAB_SIZE:
        raise RuntimeError(f"pinned vocabulary size differs: {len(vocab)}")
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
        arms=("no_intervention_adapter", DOWNSTREAM_ONLY, INPUT_ACCESS),
    )
    campaign_identity = {
        "schema": SCHEMA,
        "config": asdict(config),
        "baseline_manifest_sha256": EXPECTED_BASELINE_MANIFEST_SHA256,
        "baseline_result_sha256": EXPECTED_BASELINE_RESULT_SHA256,
        "preregistration_sha256": file_sha256(preregistration),
        "architecture": {
            "vocab_size": EXPECTED_VOCAB_SIZE,
            "trainable_parameters": EXPECTED_TRAINABLE_PARAMETERS,
            "input_embedding_width": INPUT_EMBEDDING_WIDTH,
            "input_recurrent_width": INPUT_RECURRENT_WIDTH,
            "frozen_hidden_width": FROZEN_HIDDEN_WIDTH,
        },
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
        "claim_boundary": "Controlled discovery measurement only; no promotion or overwrite authority.",
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
    by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in TRAINED_ARMS}
    initial_receipts = []
    for seed in EXPECTED_SEEDS:
        parent_dir = baseline / "parents" / f"seed-{seed}"
        parent_result = load_json(parent_dir / "RESULT.json")
        parent_path = parent_dir / "PARENT.pt"
        validate_parent_lineage(
            seed=seed,
            parent_result=parent_result,
            parent_path=parent_path,
            baseline_result=baseline_result,
        )
        parent = torch.load(parent_path, map_location="cpu", weights_only=False)
        if parent["vocab"] != vocab:
            raise RuntimeError(f"parent vocabulary differs for seed {seed}")
        probe = initial_pair_receipt(
            parent=parent,
            seed=seed,
            rows=multiview_pairs,
            stoi=stoi,
            device=config.device,
        )
        atomic_json(output / "initial-probes" / f"seed-{seed}.json", probe)
        initial_receipts.append(probe)
        for arm in TRAINED_ARMS:
            atomic_json(
                output / "PROGRESS.json",
                {
                    "schema": f"{SCHEMA}.progress",
                    "status": "STARTING_ARM",
                    "seed": seed,
                    "arm": arm,
                    "step": 0,
                    "updated_at_utc": utc_now(),
                },
            )
            by_arm[arm].append(
                _train_one_arm(
                    seed=seed,
                    arm=arm,
                    output=output,
                    config=config,
                    campaign_config_hash=config_hash,
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
        "input_access_vs_downstream_only": _comparison(
            by_arm[INPUT_ACCESS],
            by_arm[DOWNSTREAM_ONLY],
            bootstrap_seed=BOOTSTRAP_SEED,
        ),
        "input_access_vs_no_intervention": _comparison(
            by_arm[INPUT_ACCESS],
            no_intervention,
            bootstrap_seed=BOOTSTRAP_SEED + 1,
        ),
        "downstream_only_vs_no_intervention": _comparison(
            by_arm[DOWNSTREAM_ONLY],
            no_intervention,
            bootstrap_seed=BOOTSTRAP_SEED + 2,
        ),
    }
    retention_gate = all(
        row["frozen_core_bit_identical"]
        and row["all_nonselected_tensors_bit_identical"]
        and row["counting_accuracy"] == row["parent_counting_accuracy"]
        for arm in TRAINED_ARMS
        for row in by_arm[arm]
    )
    variance_gate, finite_evaluation_gate, producer_gate = producer_gate_met(
        comparisons,
        retention_gate,
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
        "initial_pair_receipts": initial_receipts,
        "per_arm": {
            "no_intervention_adapter": no_intervention,
            DOWNSTREAM_ONLY: by_arm[DOWNSTREAM_ONLY],
            INPUT_ACCESS: by_arm[INPUT_ACCESS],
        },
        "comparisons": comparisons,
        "variance_gate": "MET" if variance_gate else "NOT_MET",
        "finite_evaluation_gate": (
            "MET" if finite_evaluation_gate else "NOT_MET"
        ),
        "retention_gate": "MET" if retention_gate else "NOT_MET",
        "producer_gate": "MET_PENDING_INDEPENDENT_REPLAY" if producer_gate else "NOT_MET",
        "claim_boundary": (
            "This 2,000-step discovery segment measures the input-access direction. "
            "It cannot promote weights and does not replace a full-budget fresh-seed replication."
        ),
        "completed_at_utc": utc_now(),
    }
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
    parser.add_argument("--steps", type=int, default=EXPECTED_STEPS)
    parser.add_argument("--checkpoint-every", type=int, default=EXPECTED_CHECKPOINT_EVERY)
    parser.add_argument("--batch-size", type=int, default=EXPECTED_BATCH_SIZE)
    parser.add_argument("--threads", type=int, default=EXPECTED_THREADS)
    parser.add_argument("--minimum-free-gib", type=float, default=EXPECTED_MINIMUM_FREE_GIB)
    parser.add_argument("--progress-poll-seconds", type=float, default=2.0)
    parsed = parser.parse_args(arguments)
    parsed.seeds = EXPECTED_SEEDS
    try:
        validate_preregistered_budget(parsed)
    except ValueError as error:
        parser.error(str(error))
    return parsed


def main(arguments: Iterable[str] | None = None) -> int:
    result = run_campaign(parse_args(arguments))
    print(
        json.dumps(
            {
                "status": result["status"],
                "producer_gate": result["producer_gate"],
                "promotion": result["promotion"],
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
