"""Controlled Clay hybrid input-access efficacy campaign.

The candidate preserves a bounded downstream adapter and adds a causal compact
raw-input reader before the frozen recurrence bottleneck.  It is compared with
the exact-size ordinary downstream adapter and the immutable no-intervention
baseline.  This module has measurement authority only.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import threading
import time
from typing import Any, Iterable, Mapping, Sequence

import torch
import torch.nn.functional as F
from torch import Tensor, nn

from python.scbe.clay_frozen_multiview_adapter import (
    ARM_SEED_OFFSET,
    Adapter,
    FrozenActionModel,
    RunConfig,
    action_metrics,
    atomic_json,
    atomic_torch,
    counting_accuracy,
    counting_rows,
    encode,
    file_sha256,
    flattened_trainable,
    frozen_state,
    frozen_state_identical,
    make_batch,
    path_for_arm,
    predict_action_rows,
    stable_hash,
    train_steps,
    vocab_of,
)
from python.scbe.clay_frozen_multiview_data import build_frozen_multiview_dataset
from python.scbe.clay_input_access_campaign import (
    BOOTSTRAP_SEED,
    DOWNSTREAM_ONLY,
    EXPECTED_BASELINE_MANIFEST_SHA256,
    EXPECTED_BASELINE_RESULT_SHA256,
    EXPECTED_BATCH_SIZE,
    EXPECTED_CHECKPOINT_EVERY,
    EXPECTED_DATASET_MANIFEST_SHA256,
    EXPECTED_MINIMUM_FREE_GIB,
    EXPECTED_SEEDS,
    EXPECTED_STEPS,
    EXPECTED_THREADS,
    EXPECTED_TRAINABLE_PARAMETERS,
    EXPECTED_VOCAB_SIZE,
    TRAIN_STAGE,
    _comparison,
    _progress_monitor,
    load_json,
    nonselected_state,
    producer_gate_met,
    require_storage,
    state_identical,
    trainable_parameter_names,
    validate_parent_lineage,
    validate_preregistered_budget,
)
from python.scbe.clay_paired_orbit_training import ClaySourceAdapter
from python.scbe.clay_stable_cross_entropy import STANDARD
from python.scbe.concept_exposure_ledger import (
    ConceptExposureLedger,
    weight_effect_receipt,
)

SCHEMA = "clay.hybrid-input-access-efficacy-campaign.v1"
PREREGISTRATION_SCHEMA = "clay.hybrid-input-access-efficacy-preregistration.v1"
PREREGISTRATION_SHA256 = (
    "b5de5a9cb4c75585e616ae483f10e6495514eeb17516e659d4901993607c656b"
)
AUTHORITY = "MEASUREMENT_ONLY_NO_EXECUTION_NO_PROMOTION_NO_WEIGHT_OVERWRITE"
HYBRID_INPUT_ACCESS = "hybrid_input_access"
TRAINED_ARMS = (DOWNSTREAM_ONLY, HYBRID_INPUT_ACCESS)

FROZEN_HIDDEN_WIDTH = 192
HYBRID_ADAPTER_BOTTLENECK = 101
COMPACT_INPUT_ROWS = 269
COMPACT_EMBEDDING_WIDTH = 80
COMPACT_RECURRENT_WIDTH = 31
EXPECTED_ABSENT_FULL_IDS = (3, 10, 11, 12, 13, 14, 18)
EXPECTED_COMPACT_FULL_IDS = tuple(
    index
    for index in range(EXPECTED_VOCAB_SIZE)
    if index not in EXPECTED_ABSENT_FULL_IDS
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_preregistration(path: Path) -> dict[str, Any]:
    if file_sha256(path) != PREREGISTRATION_SHA256:
        raise RuntimeError("hybrid preregistration hash differs")
    value = load_json(path)
    if value.get("schema") != PREREGISTRATION_SCHEMA:
        raise RuntimeError("hybrid preregistration schema differs")
    if value.get("status") != "PREREGISTERED_BEFORE_RESULTS":
        raise RuntimeError("hybrid preregistration status differs")
    return value


def derive_compact_input_ids(
    rows: Sequence[tuple[str, str]],
    stoi: Mapping[str, int],
) -> tuple[int, ...]:
    observed = {0}
    for source, target in rows:
        inputs, _, _ = encode(source, target, stoi)
        observed.update(int(index) for index in inputs)
    compact = tuple(sorted(observed))
    if compact != EXPECTED_COMPACT_FULL_IDS:
        raise RuntimeError(
            "actual action-training alphabet differs: "
            f"observed={compact}, expected={EXPECTED_COMPACT_FULL_IDS}"
        )
    return compact


class HybridInputAccessActionModel(FrozenActionModel):
    """Smaller downstream adapter plus a compact causal raw-input residual."""

    def __init__(
        self,
        vocab_size: int,
        compact_input_ids: Sequence[int],
    ) -> None:
        if vocab_size != EXPECTED_VOCAB_SIZE:
            raise ValueError(
                f"hybrid architecture requires vocab {EXPECTED_VOCAB_SIZE}, got {vocab_size}"
            )
        compact = tuple(int(index) for index in compact_input_ids)
        if compact != EXPECTED_COMPACT_FULL_IDS:
            raise ValueError("hybrid compact action alphabet differs")
        super().__init__(vocab_size)
        self.adapter = Adapter(
            hidden=FROZEN_HIDDEN_WIDTH,
            bottleneck=HYBRID_ADAPTER_BOTTLENECK,
        )
        self.input_embedding = nn.Embedding(
            COMPACT_INPUT_ROWS,
            COMPACT_EMBEDDING_WIDTH,
        )
        self.input_recurrence = nn.GRU(
            COMPACT_EMBEDDING_WIDTH,
            COMPACT_RECURRENT_WIDTH,
            batch_first=True,
        )
        self.input_up = nn.Linear(
            COMPACT_RECURRENT_WIDTH,
            FROZEN_HIDDEN_WIDTH,
        )
        nn.init.zeros_(self.input_up.weight)
        nn.init.zeros_(self.input_up.bias)
        remap = torch.full((vocab_size,), -1, dtype=torch.long)
        for compact_index, full_index in enumerate(compact):
            remap[full_index] = compact_index
        self.register_buffer("input_id_remap", remap, persistent=True)

    def set_path(self, path: str) -> None:
        if path != "adapter":
            raise ValueError(f"hybrid arm supports only adapter path, got {path}")
        self.active_path = path

    def compact_inputs(self, inputs: Tensor) -> Tensor:
        if inputs.dtype != torch.long:
            raise TypeError("hybrid action inputs must be torch.long")
        if inputs.numel() and (
            int(inputs.min()) < 0 or int(inputs.max()) >= len(self.input_id_remap)
        ):
            raise RuntimeError("hybrid action input ID lies outside the full vocabulary")
        compact = self.input_id_remap[inputs]
        if bool(torch.any(compact < 0)):
            rejected = sorted({int(value) for value in inputs[compact < 0].tolist()})
            raise RuntimeError(f"unmapped hybrid action input IDs: {rejected}")
        return compact

    def action_logits_from_hidden(
        self,
        inputs: Tensor,
        frozen_hidden: Tensor,
        input_state: Tensor | None = None,
    ) -> tuple[Tensor, Tensor]:
        compact = self.compact_inputs(inputs)
        drop_anchor = input_state is None
        if drop_anchor:
            anchor = torch.full(
                (inputs.shape[0], 1),
                int(self.input_id_remap[0]),
                dtype=torch.long,
                device=inputs.device,
            )
            compact = torch.cat((anchor, compact), dim=1)
        sidecar, input_state = self.input_recurrence(
            self.input_embedding(compact),
            input_state,
        )
        if drop_anchor:
            sidecar = sidecar[:, 1:]
        carrier = self.adapter(frozen_hidden) + self.input_up(sidecar)
        return self.adapter_head(carrier), input_state

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
            raise ValueError(f"unknown hybrid stage: {stage}")
        modules: tuple[nn.Module, ...] = (
            self.adapter,
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
    compact_input_ids: Sequence[int],
    device: str,
) -> FrozenActionModel:
    if arm not in TRAINED_ARMS:
        raise ValueError(f"unknown hybrid campaign arm: {arm}")
    vocab_size = len(parent["vocab"])
    if vocab_size != EXPECTED_VOCAB_SIZE:
        raise RuntimeError(f"pinned parent vocab differs: {vocab_size}")
    torch.manual_seed(seed + ARM_SEED_OFFSET[TRAIN_STAGE])
    if arm == DOWNSTREAM_ONLY:
        model: FrozenActionModel = FrozenActionModel(vocab_size)
        model.load_state_dict(parent["model_state"], strict=True)
    else:
        model = HybridInputAccessActionModel(vocab_size, compact_input_ids)
        compatible_parent = {
            name: value
            for name, value in parent["model_state"].items()
            if not name.startswith("adapter.")
        }
        incompatible = model.load_state_dict(compatible_parent, strict=False)
        expected_missing = {
            "adapter.down.weight",
            "adapter.down.bias",
            "adapter.mid.weight",
            "adapter.mid.bias",
            "adapter.up.weight",
            "adapter.up.bias",
            "input_embedding.weight",
            "input_recurrence.weight_ih_l0",
            "input_recurrence.weight_hh_l0",
            "input_recurrence.bias_ih_l0",
            "input_recurrence.bias_hh_l0",
            "input_up.weight",
            "input_up.bias",
            "input_id_remap",
        }
        if set(incompatible.missing_keys) != expected_missing or incompatible.unexpected_keys:
            raise RuntimeError(f"hybrid parent state differs: {incompatible}")
    model.to(device)
    model.set_path(path_for_arm(TRAIN_STAGE))
    selected = sum(parameter.numel() for parameter in model.parameters_for(TRAIN_STAGE))
    if selected != EXPECTED_TRAINABLE_PARAMETERS:
        raise RuntimeError(
            f"{arm} selected parameter count differs: {selected} != "
            f"{EXPECTED_TRAINABLE_PARAMETERS}"
        )
    return model


@torch.inference_mode()
def initial_pair_receipt(
    *,
    parent: Mapping[str, Any],
    seed: int,
    compact_input_ids: Sequence[int],
    rows: Sequence[tuple[str, str]],
    stoi: Mapping[str, int],
    device: str,
) -> dict[str, Any]:
    indices = list(range(min(8, len(rows))))
    inputs, _, _ = make_batch(rows, indices, stoi, device)
    control = construct_arm_model(
        arm=DOWNSTREAM_ONLY,
        parent=parent,
        seed=seed,
        compact_input_ids=compact_input_ids,
        device=device,
    ).eval()
    candidate = construct_arm_model(
        arm=HYBRID_INPUT_ACCESS,
        parent=parent,
        seed=seed,
        compact_input_ids=compact_input_ids,
        device=device,
    ).eval()
    control_logits, _ = control(inputs, "action")
    candidate_logits, _ = candidate(inputs, "action")
    if not torch.equal(control_logits, candidate_logits):
        raise RuntimeError(f"hybrid initial logits differ for seed {seed}")
    return {
        "schema": f"{SCHEMA}.initial-pair",
        "seed": seed,
        "examples": len(indices),
        "bit_identical_logits": True,
        "control_trainable_parameters": sum(
            parameter.numel() for parameter in control.parameters_for(TRAIN_STAGE)
        ),
        "candidate_trainable_parameters": sum(
            parameter.numel() for parameter in candidate.parameters_for(TRAIN_STAGE)
        ),
        "control_trainable_parameter_names": list(trainable_parameter_names(control)),
        "candidate_trainable_parameter_names": list(
            trainable_parameter_names(candidate)
        ),
    }


def _selected_gradient_support(model: FrozenActionModel) -> tuple[int, int]:
    selected = {id(parameter) for parameter in model.parameters_for(TRAIN_STAGE)}
    nonzero = expected = 0
    for parameter in model.parameters():
        if id(parameter) not in selected:
            continue
        expected += parameter.numel()
        if parameter.grad is not None:
            nonzero += int(torch.count_nonzero(parameter.grad))
    return nonzero, expected


def _masked_action_loss(
    model: FrozenActionModel,
    inputs: Tensor,
    labels: Tensor,
    mask: Tensor,
) -> Tensor:
    logits, _ = model(inputs, "action")
    losses = F.cross_entropy(
        logits.reshape(-1, EXPECTED_VOCAB_SIZE),
        labels.reshape(-1),
        reduction="none",
    ).reshape_as(mask)
    return (losses * mask).sum() / mask.sum()


def _actual_row_cover(
    rows: Sequence[tuple[str, str]],
    stoi: Mapping[str, int],
) -> list[int]:
    uncovered = set(EXPECTED_COMPACT_FULL_IDS)
    uncovered.discard(0)
    selected = []
    for index, (source, target) in enumerate(rows):
        inputs, _, _ = encode(source, target, stoi)
        contribution = uncovered.intersection(inputs)
        if contribution:
            selected.append(index)
            uncovered.difference_update(contribution)
        if not uncovered:
            break
    if uncovered:
        raise RuntimeError(f"actual rows do not cover compact IDs: {sorted(uncovered)}")
    return selected


def effective_capacity_receipt(
    *,
    parent: Mapping[str, Any],
    seed: int,
    compact_input_ids: Sequence[int],
    rows: Sequence[tuple[str, str]],
    stoi: Mapping[str, int],
    device: str,
) -> dict[str, Any]:
    cover = _actual_row_cover(rows, stoi)
    inputs, labels, mask = make_batch(rows, cover, stoi, device)
    arms: dict[str, dict[str, Any]] = {}
    for arm in TRAINED_ARMS:
        gradient_model = construct_arm_model(
            arm=arm,
            parent=parent,
            seed=seed,
            compact_input_ids=compact_input_ids,
            device=device,
        )
        with torch.no_grad():
            gradient_model.adapter.up.weight.copy_(
                torch.linspace(
                    -0.05,
                    0.05,
                    gradient_model.adapter.up.weight.numel(),
                    device=device,
                ).reshape_as(gradient_model.adapter.up.weight)
            )
            gradient_model.adapter.up.bias.copy_(
                torch.linspace(
                    -0.02,
                    0.02,
                    gradient_model.adapter.up.bias.numel(),
                    device=device,
                )
            )
            if isinstance(gradient_model, HybridInputAccessActionModel):
                gradient_model.input_up.weight.copy_(
                    torch.linspace(
                        -0.05,
                        0.05,
                        gradient_model.input_up.weight.numel(),
                        device=device,
                    ).reshape_as(gradient_model.input_up.weight)
                )
                gradient_model.input_up.bias.copy_(
                    torch.linspace(
                        -0.02,
                        0.02,
                        gradient_model.input_up.bias.numel(),
                        device=device,
                    )
                )
        gradient_model.zero_grad(set_to_none=True)
        _masked_action_loss(gradient_model, inputs, labels, mask).backward()
        reachable, selected = _selected_gradient_support(gradient_model)
        if reachable != selected or selected != EXPECTED_TRAINABLE_PARAMETERS:
            raise RuntimeError(
                f"effective gradient reachability differs for {arm}: {reachable}/{selected}"
            )

        change_model = construct_arm_model(
            arm=arm,
            parent=parent,
            seed=seed,
            compact_input_ids=compact_input_ids,
            device=device,
        )
        initial = flattened_trainable(change_model, TRAIN_STAGE).copy()
        change_parameters = change_model.parameters_for(TRAIN_STAGE)
        for witness_step in range(2):
            change_model.zero_grad(set_to_none=True)
            _masked_action_loss(change_model, inputs, labels, mask).backward()
            with torch.no_grad():
                for parameter in change_parameters:
                    if parameter.grad is None:
                        raise RuntimeError(
                            f"two-step witness lost a gradient path for {arm}"
                        )
                    if witness_step == 1 and bool(torch.any(parameter.grad == 0)):
                        raise RuntimeError(
                            f"opened two-step witness retained a zero gradient for {arm}"
                        )
                    # A fixed sign step measures structural changeability without
                    # conflating a tiny but nonzero gradient with Adam epsilon or
                    # float32 ULP rounding.  The real campaign still uses Adam and
                    # separately requires every selected scalar to change.
                    parameter.add_(
                        parameter.grad.sign(),
                        alpha=(-0.001 if witness_step == 0 else -0.0005),
                    )
        effect = weight_effect_receipt(
            initial,
            flattened_trainable(change_model, TRAIN_STAGE),
        )
        if int(effect["changed_scalars"]) != EXPECTED_TRAINABLE_PARAMETERS:
            raise RuntimeError(
                f"two-step effective change differs for {arm}: "
                f"{effect['changed_scalars']}/{EXPECTED_TRAINABLE_PARAMETERS}"
            )
        arms[arm] = {
            "selected_scalars": selected,
            "gradient_reachable_scalars": reachable,
            "two_step_changed_scalars": effect["changed_scalars"],
            "two_step_effect_receipt_sha256": effect["receipt_sha256"],
        }
    return {
        "schema": f"{SCHEMA}.effective-capacity",
        "seed": seed,
        "actual_training_rows_selected": cover,
        "actual_training_row_count": len(cover),
        "compact_full_ids": list(compact_input_ids),
        "compact_rows": len(compact_input_ids),
        "arms": arms,
        "status": "PASS",
    }


def validate_completed_arm_result(
    *,
    result: Mapping[str, Any],
    model_path: Path,
    seed: int,
    arm: str,
    config: RunConfig,
    campaign_config_hash: str,
    arm_config_hash: str,
    compact_input_ids: Sequence[int],
    parent: Mapping[str, Any],
    parent_result: Mapping[str, Any],
    dataset: Any,
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    count_holdout: Sequence[tuple[str, str]],
) -> None:
    initial_model = construct_arm_model(
        arm=arm,
        parent=parent,
        seed=seed,
        compact_input_ids=compact_input_ids,
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
        "compact_input_ids": list(compact_input_ids),
        "effective_changed_scalars": EXPECTED_TRAINABLE_PARAMETERS,
    }
    for key, value in expected.items():
        if result.get(key) != value:
            raise RuntimeError(f"existing hybrid arm field differs: {key}")
    if not math.isfinite(float(result["final_loss"])):
        raise RuntimeError("existing hybrid arm loss is non-finite")
    if not model_path.is_file() or file_sha256(model_path) != result.get("model_sha256"):
        raise RuntimeError("existing hybrid arm model hash differs")

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
        "compact_input_ids": list(compact_input_ids),
    }
    for key, value in payload_expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"existing hybrid model field differs: {key}")
    initial_trainable = flattened_trainable(initial_model, TRAIN_STAGE).copy()
    frozen_before = frozen_state(initial_model)
    nonselected_before = nonselected_state(initial_model)
    initial_model.load_state_dict(payload["model_state"], strict=True)
    if not frozen_state_identical(frozen_before, initial_model):
        raise RuntimeError("existing hybrid model changed frozen tensors")
    if not state_identical(nonselected_before, initial_model):
        raise RuntimeError("existing hybrid model changed non-selected tensors")
    predictions = predict_action_rows(
        initial_model,
        path=path_for_arm(TRAIN_STAGE),
        rows=dataset.holdout_rows,
        stoi=stoi,
        itos=itos,
        device=config.device,
    )
    if result.get("predictions") != predictions:
        raise RuntimeError("existing hybrid arm predictions differ on replay")
    if result.get("metrics") != action_metrics(predictions):
        raise RuntimeError("existing hybrid arm metrics differ on replay")
    count_score = counting_accuracy(
        model=initial_model,
        rows=count_holdout,
        stoi=stoi,
        itos=itos,
        device=config.device,
    )
    if result.get("counting_accuracy") != count_score:
        raise RuntimeError("existing hybrid arm counting score differs on replay")
    if count_score != float(parent_result["counting_accuracy"]):
        raise RuntimeError("existing hybrid arm did not retain parent counting")
    effect = weight_effect_receipt(
        initial_trainable,
        flattened_trainable(initial_model, TRAIN_STAGE),
    )
    if result.get("weight_effect") != effect:
        raise RuntimeError("existing hybrid arm weight effect differs on replay")


def _train_one_arm(
    *,
    seed: int,
    arm: str,
    output: Path,
    config: RunConfig,
    campaign_config_hash: str,
    compact_input_ids: Sequence[int],
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
            compact_input_ids=compact_input_ids,
            parent=parent,
            parent_result=parent_result,
            dataset=dataset,
            stoi=stoi,
            itos=itos,
            count_holdout=count_holdout,
        )
        return result

    model = construct_arm_model(
        arm=arm,
        parent=parent,
        seed=seed,
        compact_input_ids=compact_input_ids,
        device=config.device,
    )
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
    effect = weight_effect_receipt(initial, final)
    if int(effect["changed_scalars"]) != EXPECTED_TRAINABLE_PARAMETERS:
        raise RuntimeError(
            f"effective changed scalars differ for {arm} seed {seed}: "
            f"{effect['changed_scalars']} != {EXPECTED_TRAINABLE_PARAMETERS}"
        )
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
        "compact_input_ids": list(compact_input_ids),
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
        "effective_changed_scalars": effect["changed_scalars"],
        "final_loss": loss,
        "metrics": action_metrics(predictions),
        "predictions": predictions,
        "counting_accuracy": count_score,
        "parent_counting_accuracy": parent_count_score,
        "parent_sha256": parent_result["parent_sha256"],
        "frozen_core_bit_identical": True,
        "all_nonselected_tensors_bit_identical": True,
        "trainable_parameter_names": list(selected_names),
        "compact_input_ids": list(compact_input_ids),
        "weight_effect": effect,
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
    compact_input_ids = derive_compact_input_ids(multiview_pairs, stoi)
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
        arms=("no_intervention_adapter", DOWNSTREAM_ONLY, HYBRID_INPUT_ACCESS),
    )
    campaign_identity = {
        "schema": SCHEMA,
        "config": asdict(config),
        "baseline_manifest_sha256": EXPECTED_BASELINE_MANIFEST_SHA256,
        "baseline_result_sha256": EXPECTED_BASELINE_RESULT_SHA256,
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "architecture": {
            "vocab_size": EXPECTED_VOCAB_SIZE,
            "trainable_parameters": EXPECTED_TRAINABLE_PARAMETERS,
            "hybrid_adapter_bottleneck": HYBRID_ADAPTER_BOTTLENECK,
            "compact_input_rows": COMPACT_INPUT_ROWS,
            "compact_embedding_width": COMPACT_EMBEDDING_WIDTH,
            "compact_recurrent_width": COMPACT_RECURRENT_WIDTH,
            "compact_input_ids": list(compact_input_ids),
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
        "claim_boundary": "Controlled hybrid discovery only; no promotion or overwrite authority.",
    }
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "RUN_MANIFEST.json"
    if manifest_path.is_file():
        existing = load_json(manifest_path)
        comparable = dict(existing)
        comparable["admitted_free_gib"] = admitted_free_gib
        if comparable != manifest:
            raise RuntimeError("existing hybrid campaign manifest differs")
    else:
        atomic_json(manifest_path, manifest)

    no_intervention = sorted(
        baseline_result["per_arm"]["no_intervention_adapter"],
        key=lambda row: int(row["seed"]),
    )
    by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in TRAINED_ARMS}
    initial_receipts = []
    capacity_receipts = []
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
            compact_input_ids=compact_input_ids,
            rows=multiview_pairs,
            stoi=stoi,
            device=config.device,
        )
        atomic_json(output / "initial-probes" / f"seed-{seed}.json", probe)
        initial_receipts.append(probe)
        capacity = effective_capacity_receipt(
            parent=parent,
            seed=seed,
            compact_input_ids=compact_input_ids,
            rows=multiview_pairs,
            stoi=stoi,
            device=config.device,
        )
        atomic_json(output / "capacity-probes" / f"seed-{seed}.json", capacity)
        capacity_receipts.append(capacity)
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
                    compact_input_ids=compact_input_ids,
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
        "hybrid_vs_downstream_only": _comparison(
            by_arm[HYBRID_INPUT_ACCESS],
            by_arm[DOWNSTREAM_ONLY],
            bootstrap_seed=BOOTSTRAP_SEED + 100,
        ),
        "hybrid_vs_no_intervention": _comparison(
            by_arm[HYBRID_INPUT_ACCESS],
            no_intervention,
            bootstrap_seed=BOOTSTRAP_SEED + 101,
        ),
        "downstream_only_vs_no_intervention": _comparison(
            by_arm[DOWNSTREAM_ONLY],
            no_intervention,
            bootstrap_seed=BOOTSTRAP_SEED + 102,
        ),
    }
    retention_gate = all(
        row["frozen_core_bit_identical"]
        and row["all_nonselected_tensors_bit_identical"]
        and row["counting_accuracy"] == row["parent_counting_accuracy"]
        and int(row["effective_changed_scalars"])
        == EXPECTED_TRAINABLE_PARAMETERS
        for arm in TRAINED_ARMS
        for row in by_arm[arm]
    )
    gate_comparisons = {
        "input_access_vs_downstream_only": comparisons[
            "hybrid_vs_downstream_only"
        ],
        "input_access_vs_no_intervention": comparisons[
            "hybrid_vs_no_intervention"
        ],
    }
    variance_gate, finite_evaluation_gate, producer_gate = producer_gate_met(
        gate_comparisons,
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
        "compact_input_ids": list(compact_input_ids),
        "initial_pair_receipts": initial_receipts,
        "effective_capacity_receipts": capacity_receipts,
        "per_arm": {
            "no_intervention_adapter": no_intervention,
            DOWNSTREAM_ONLY: by_arm[DOWNSTREAM_ONLY],
            HYBRID_INPUT_ACCESS: by_arm[HYBRID_INPUT_ACCESS],
        },
        "comparisons": comparisons,
        "variance_gate": "MET" if variance_gate else "NOT_MET",
        "finite_evaluation_gate": "MET" if finite_evaluation_gate else "NOT_MET",
        "retention_and_effective_capacity_gate": (
            "MET" if retention_gate else "NOT_MET"
        ),
        "producer_gate": (
            "MET_PENDING_INDEPENDENT_REPLAY" if producer_gate else "NOT_MET"
        ),
        "claim_boundary": (
            "This 2,000-step discovery segment measures the preregistered hybrid. "
            "It cannot promote weights and requires fresh replication after any pass."
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
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=EXPECTED_CHECKPOINT_EVERY,
    )
    parser.add_argument("--batch-size", type=int, default=EXPECTED_BATCH_SIZE)
    parser.add_argument("--threads", type=int, default=EXPECTED_THREADS)
    parser.add_argument(
        "--minimum-free-gib",
        type=float,
        default=EXPECTED_MINIMUM_FREE_GIB,
    )
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
