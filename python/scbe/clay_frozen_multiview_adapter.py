"""Resume-safe frozen-input-adapter campaign over exact Clay action bytes.

The counting core is trained first and then frozen bit-for-bit.  Three matched
adapter arms receive either one static view, three legal views, or a constant
carrier over the same three-view schedule.  The untouched parent is the fourth
control.  Predictions are measurements only; deterministic Clay labels remain
the sole action authority and no checkpoint may be promoted by this runner.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import statistics
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import torch
from torch import Tensor, nn

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

SCHEMA = "clay.frozen-multiview-adapter-campaign.v1"
AUTHORITY = "MEASUREMENT_ONLY_NO_EXECUTION_NO_PROMOTION_NO_PARTIAL_UNFREEZE"
TRAINED_ARMS = (
    "frozen_adapter_static",
    "frozen_adapter_multiview",
    "frozen_adapter_null",
)
ALL_ARMS = ("no_intervention_adapter",) + TRAINED_ARMS
PRIMARY_ARM = "frozen_adapter_multiview"
CONTROLS = (
    "frozen_adapter_static",
    "frozen_adapter_null",
    "no_intervention_adapter",
)
ARM_SEED_OFFSET = {arm: 701 for arm in TRAINED_ARMS}
FROZEN_PREFIXES = ("e.", "g.", "count_head.")

PAD, BOS, SEP, EOS = "\x00", "\x02", "\x1f", "\x03"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(pending, path)


def atomic_torch(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    torch.save(dict(value), pending)
    os.replace(pending, path)


def counting_rows(holdout: bool) -> list[tuple[str, str]]:
    rows = []
    for step in range(1, 10):
        for start in range(40):
            terms = [start + step * index for index in range(4)]
            target = start + step * 4
            if target > 400 or (start % 7 == 0) != holdout:
                continue
            rows.append(
                (
                    f"C {step} : " + " ".join(map(str, terms)) + " =>",
                    f" {target}",
                )
            )
    return rows


def vocab_of(*rowsets: Sequence[tuple[str, str]]) -> tuple[list[str], dict[str, int]]:
    characters = set(PAD + BOS + SEP + EOS)
    for rows in rowsets:
        for prompt, target in rows:
            characters.update(prompt)
            characters.update(target)
    special = (PAD, BOS, SEP, EOS)
    vocab = list(special) + sorted(char for char in characters if char not in special)
    return vocab, {char: index for index, char in enumerate(vocab)}


def encode(prompt: str, target: str, stoi: Mapping[str, int]) -> tuple[list[int], list[int], list[int]]:
    full = [stoi[BOS], *(stoi[char] for char in prompt), stoi[SEP]]
    separator = len(full) - 1
    full.extend(stoi[char] for char in target)
    full.append(stoi[EOS])
    inputs = full[:-1]
    labels = full[1:]
    mask = [int(index >= separator) for index in range(len(labels))]
    return inputs, labels, mask


def make_batch(
    rows: Sequence[tuple[str, str]],
    indices: Iterable[int],
    stoi: Mapping[str, int],
    device: str,
) -> tuple[Tensor, Tensor, Tensor]:
    encoded = [encode(*rows[index], stoi) for index in indices]
    width = max(len(inputs) for inputs, _, _ in encoded)
    inputs = torch.zeros((len(encoded), width), dtype=torch.long)
    labels = torch.zeros((len(encoded), width), dtype=torch.long)
    masks = torch.zeros((len(encoded), width), dtype=torch.float32)
    for row, (source, target, mask) in enumerate(encoded):
        inputs[row, : len(source)] = torch.tensor(source)
        labels[row, : len(target)] = torch.tensor(target)
        masks[row, : len(mask)] = torch.tensor(mask)
    return inputs.to(device), labels.to(device), masks.to(device)


class DeterministicBatchSampler:
    """Complete shuffled-epoch state, including exact resume position."""

    def __init__(self, row_count: int, batch_size: int, seed: int) -> None:
        if row_count < 1 or batch_size < 1:
            raise ValueError("sampler dimensions must be positive")
        self.row_count = row_count
        self.batch_size = batch_size
        self.rng = random.Random(seed)
        self.order = list(range(row_count))
        self.rng.shuffle(self.order)
        self.position = 0
        self.epoch = 0

    def next_indices(self) -> list[int]:
        if self.position >= self.row_count:
            self.epoch += 1
            self.order = list(range(self.row_count))
            self.rng.shuffle(self.order)
            self.position = 0
        end = min(self.position + self.batch_size, self.row_count)
        result = self.order[self.position : end]
        self.position = end
        return result

    def state_dict(self) -> dict[str, Any]:
        return {
            "row_count": self.row_count,
            "batch_size": self.batch_size,
            "rng_state": self.rng.getstate(),
            "order": self.order,
            "position": self.position,
            "epoch": self.epoch,
        }

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        if (
            int(state["row_count"]) != self.row_count
            or int(state["batch_size"]) != self.batch_size
        ):
            raise ValueError("sampler checkpoint dimensions differ")
        self.rng.setstate(state["rng_state"])
        self.order = [int(value) for value in state["order"]]
        self.position = int(state["position"])
        self.epoch = int(state["epoch"])


class TwoSlotCheckpoint:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.pointer = directory / "latest.json"

    def save(self, payload: Mapping[str, Any], generation: int) -> None:
        slot = self.directory / ("slot-a.pt" if generation % 2 == 0 else "slot-b.pt")
        atomic_torch(slot, payload)
        atomic_json(
            self.pointer,
            {
                "schema": f"{SCHEMA}.checkpoint-pointer",
                "slot": slot.name,
                "sha256": file_sha256(slot),
                "generation": generation,
                "step": int(payload["step"]),
                "updated_at_utc": utc_now(),
            },
        )

    def load(self) -> tuple[dict[str, Any], dict[str, Any]] | None:
        if not self.pointer.is_file():
            return None
        pointer = json.loads(self.pointer.read_text(encoding="utf-8"))
        slot = self.directory / pointer["slot"]
        if not slot.is_file() or file_sha256(slot) != pointer["sha256"]:
            raise RuntimeError("checkpoint pointer does not match its slot")
        return torch.load(slot, map_location="cpu", weights_only=False), pointer


class Adapter(nn.Module):
    def __init__(self, hidden: int = 192, bottleneck: int = 160) -> None:
        super().__init__()
        self.down = nn.Linear(hidden, bottleneck)
        self.mid = nn.Linear(bottleneck, bottleneck)
        self.up = nn.Linear(bottleneck, hidden)
        self.act = nn.GELU()
        nn.init.zeros_(self.up.weight)
        nn.init.zeros_(self.up.bias)

    def forward(self, hidden: Tensor) -> Tensor:
        return hidden + self.up(self.act(self.mid(self.act(self.down(hidden)))))


class FrozenActionModel(nn.Module):
    """Counting core plus a downstream adapter with a matched null carrier."""

    def __init__(self, vocab_size: int) -> None:
        super().__init__()
        self.e = nn.Embedding(vocab_size, 64, padding_idx=0)
        self.g = nn.GRU(64, 192, 2, batch_first=True)
        self.adapter = Adapter()
        self.count_head = nn.Linear(192, vocab_size)
        self.adapter_head = nn.Linear(192, vocab_size)
        self.active_path = "adapter"

    def set_path(self, path: str) -> None:
        if path not in {"adapter", "adapter_null"}:
            raise ValueError(f"unknown path: {path}")
        self.active_path = path

    def forward(
        self, inputs: Tensor, head: str, state: Any = None
    ) -> tuple[Tensor, Any]:
        core_state = state[0] if isinstance(state, tuple) else state
        hidden, core_state = self.g(self.e(inputs), core_state)
        if head == "count":
            return self.count_head(hidden), core_state
        carrier = (
            torch.ones_like(hidden)
            if self.active_path == "adapter_null"
            else hidden
        )
        return self.adapter_head(self.adapter(carrier)), (core_state, None)

    def parameters_for(self, stage: str) -> list[nn.Parameter]:
        if stage == "count_parent":
            modules: tuple[nn.Module, ...] = (self.e, self.g, self.count_head)
        elif stage in TRAINED_ARMS:
            modules = (self.adapter, self.adapter_head)
        else:
            raise ValueError(f"unknown stage: {stage}")
        return [parameter for module in modules for parameter in module.parameters()]


def path_for_arm(arm: str) -> str:
    return "adapter_null" if arm == "frozen_adapter_null" else "adapter"


def set_trainable(model: FrozenActionModel, stage: str) -> list[nn.Parameter]:
    for parameter in model.parameters():
        parameter.requires_grad = False
    selected = model.parameters_for(stage)
    for parameter in selected:
        parameter.requires_grad = True
    return selected


def frozen_state(model: nn.Module) -> dict[str, Tensor]:
    return {
        key: value.detach().cpu().clone()
        for key, value in model.state_dict().items()
        if key.startswith(FROZEN_PREFIXES)
    }


def frozen_state_identical(before: Mapping[str, Tensor], model: nn.Module) -> bool:
    after = frozen_state(model)
    return before.keys() == after.keys() and all(
        torch.equal(before[key], after[key]) for key in before
    )


def flattened_trainable(model: FrozenActionModel, stage: str) -> np.ndarray:
    arrays = [
        parameter.detach().cpu().numpy().reshape(-1)
        for parameter in model.parameters_for(stage)
    ]
    return np.concatenate(arrays).astype(np.float32, copy=False)


@dataclass(frozen=True, slots=True)
class RunConfig:
    seeds: tuple[int, ...]
    data_seed: int
    rows_per_view: int
    holdout_rows: int
    count_steps: int
    grow_steps: int
    checkpoint_every: int
    batch_size: int
    learning_rate: float
    threads: int
    device: str
    source_dir: str
    source_hashes: Mapping[str, str]
    dataset_manifest_sha256: str
    authority: str = AUTHORITY
    arms: tuple[str, ...] = ALL_ARMS


def _checkpoint_payload(
    *,
    model: FrozenActionModel,
    optimizer: torch.optim.Optimizer,
    sampler: DeterministicBatchSampler,
    ledger: ConceptExposureLedger | None,
    step: int,
    generation: int,
    loss: float,
    stage: str,
    seed: int,
    config_hash: str,
) -> dict[str, Any]:
    return {
        "schema": f"{SCHEMA}.checkpoint",
        "stage": stage,
        "seed": seed,
        "config_hash": config_hash,
        "step": step,
        "generation": generation,
        "loss": loss,
        "model_state": model.state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "sampler_state": sampler.state_dict(),
        "ledger_state": ledger.state_dict() if ledger is not None else None,
        "torch_cpu_rng_state": torch.get_rng_state(),
    }


def train_steps(
    *,
    model: FrozenActionModel,
    stage: str,
    seed: int,
    rows: Sequence[tuple[str, str]],
    samples: Sequence[ActionTextRow] | None,
    ledger: ConceptExposureLedger | None,
    stoi: Mapping[str, int],
    config: RunConfig,
    total_steps: int,
    checkpoint_dir: Path,
    config_hash: str,
) -> tuple[int, float, int]:
    if (samples is None) != (ledger is None):
        raise ValueError("samples and exposure ledger must be supplied together")
    if samples is not None and len(samples) != len(rows):
        raise ValueError("exposure sample order differs from training rows")
    model.set_path(path_for_arm(stage))
    trainable = set_trainable(model, stage)
    optimizer = torch.optim.Adam(trainable, lr=config.learning_rate)
    sampler = DeterministicBatchSampler(
        len(rows), config.batch_size, seed + ARM_SEED_OFFSET.get(stage, 0)
    )
    checkpoint = TwoSlotCheckpoint(checkpoint_dir)
    restored = checkpoint.load()
    step = 0
    generation = 0
    last_loss = math.nan
    if restored is not None:
        payload, pointer = restored
        expected = {
            "schema": f"{SCHEMA}.checkpoint",
            "stage": stage,
            "seed": seed,
            "config_hash": config_hash,
        }
        if any(payload.get(key) != value for key, value in expected.items()):
            raise RuntimeError("checkpoint identity differs")
        model.load_state_dict(payload["model_state"])
        optimizer.load_state_dict(payload["optimizer_state"])
        sampler.load_state_dict(payload["sampler_state"])
        if ledger is not None:
            ledger.restore_state(payload["ledger_state"])
        torch.set_rng_state(payload["torch_cpu_rng_state"])
        step = int(payload["step"])
        generation = int(pointer["generation"]) + 1
        last_loss = float(payload["loss"])

    loss_function = nn.CrossEntropyLoss(reduction="none")
    while step < total_steps:
        model.train()
        indices = sampler.next_indices()
        inputs, labels, masks = make_batch(rows, indices, stoi, config.device)
        logits, _ = model(inputs, "count" if stage == "count_parent" else "action")
        token_loss = loss_function(
            logits.reshape(-1, logits.size(-1)), labels.reshape(-1)
        ).reshape(labels.shape)
        denominators = masks.sum(dim=1).clamp(min=1)
        sample_loss = (token_loss * masks).sum(dim=1) / denominators
        loss = sample_loss.mean()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        if ledger is not None and samples is not None:
            ledger.observe_batch(
                [samples[index].sample.sample_id for index in indices],
                sample_loss.detach().cpu().numpy(),
                np.zeros((len(indices), 5), dtype=np.float64),
            )
        step += 1
        last_loss = float(loss.detach().cpu())
        if step % config.checkpoint_every == 0 or step == total_steps:
            checkpoint.save(
                _checkpoint_payload(
                    model=model,
                    optimizer=optimizer,
                    sampler=sampler,
                    ledger=ledger,
                    step=step,
                    generation=generation,
                    loss=last_loss,
                    stage=stage,
                    seed=seed,
                    config_hash=config_hash,
                ),
                generation,
            )
            generation += 1
    return step, last_loss, sum(parameter.numel() for parameter in trainable)


@torch.inference_mode()
def generate_integer(
    model: FrozenActionModel,
    *,
    head: str,
    prompt: str,
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    device: str,
    max_length: int = 5,
) -> int | None:
    model.eval()
    ids = [stoi[BOS], *(stoi[char] for char in prompt), stoi[SEP]]
    logits, state = model(torch.tensor([ids], device=device), head)
    token = int(logits[0, -1].argmax())
    output = []
    for _ in range(max_length):
        if token == stoi[EOS]:
            break
        output.append(itos[token])
        logits, state = model(torch.tensor([[token]], device=device), head, state)
        token = int(logits[0, -1].argmax())
    text = "".join(output).strip()
    try:
        return int(text.split()[0])
    except (ValueError, IndexError):
        return None


@torch.inference_mode()
def predict_action_rows(
    model: FrozenActionModel,
    *,
    path: str,
    rows: Sequence[ActionTextRow],
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    device: str,
) -> list[dict[str, Any]]:
    model.set_path(path)
    predictions = []
    for index, row in enumerate(rows):
        prediction = generate_integer(
            model=model,
            head="action",
            prompt=row.prompt,
            stoi=stoi,
            itos=itos,
            device=device,
            max_length=2,
        )
        predictions.append(
            {
                "example_index": index,
                "sample_id": row.sample.sample_id,
                "payload_sha256": row.sample.payload_sha256,
                "target": row.label,
                "prediction": prediction,
                "correct": prediction == row.label,
                "sector": row.sector,
                "operation_id": row.sample.operation_id,
                "view_id": row.sample.view_id,
                "source_family": row.sample.source_family,
            }
        )
    return predictions


@torch.inference_mode()
def counting_accuracy(
    model: FrozenActionModel,
    *,
    rows: Sequence[tuple[str, str]],
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    device: str,
) -> float:
    correct = 0
    for prompt, target in rows:
        prediction = generate_integer(
            model=model,
            head="count",
            prompt=prompt,
            stoi=stoi,
            itos=itos,
            device=device,
        )
        correct += prediction == int(target.strip())
    return correct / len(rows)


def action_metrics(predictions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    labels = range(5)
    accuracy = statistics.fmean(bool(row["correct"]) for row in predictions)
    recalls = []
    f1s = []
    per_action = {}
    for label in labels:
        relevant = [row for row in predictions if int(row["target"]) == label]
        true_positive = sum(row["prediction"] == label for row in relevant)
        false_negative = len(relevant) - true_positive
        false_positive = sum(
            row["prediction"] == label and int(row["target"]) != label
            for row in predictions
        )
        recall = true_positive / len(relevant) if relevant else 0.0
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0
        )
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        recalls.append(recall)
        f1s.append(f1)
        per_action[str(label)] = {
            "support": len(relevant),
            "accuracy": recall,
            "f1": f1,
            "false_negative": false_negative,
        }
    sectors = sorted({int(row["sector"]) for row in predictions})
    return {
        "accuracy": accuracy,
        "macro_f1": statistics.fmean(f1s),
        "worst_action_accuracy": min(recalls),
        "per_action": per_action,
        "per_sector_accuracy": {
            str(sector): statistics.fmean(
                bool(row["correct"])
                for row in predictions
                if int(row["sector"]) == sector
            )
            for sector in sectors
        },
    }


def paired_exact_p(wins: int, losses: int) -> float:
    discordant = wins + losses
    if not discordant:
        return 1.0
    tail = sum(math.comb(discordant, index) for index in range(min(wins, losses) + 1))
    return min(1.0, 2.0 * tail / (2**discordant))


def paired_prediction_comparison(
    contender: Sequence[Mapping[str, Any]], control: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    left = {
        (int(row["seed"]), int(item["example_index"])): bool(item["correct"])
        for row in contender
        for item in row["predictions"]
    }
    right = {
        (int(row["seed"]), int(item["example_index"])): bool(item["correct"])
        for row in control
        for item in row["predictions"]
    }
    if left.keys() != right.keys():
        raise RuntimeError("paired prediction keys differ")
    wins = sum(left[key] and not right[key] for key in left)
    losses = sum(right[key] and not left[key] for key in left)
    p_value = paired_exact_p(wins, losses)
    return {
        "examples": len(left),
        "wins": wins,
        "losses": losses,
        "ties": len(left) - wins - losses,
        "two_sided_exact_p": p_value,
        "clears_finite_uncertainty_gate": wins > losses and p_value <= 0.05,
    }


def metric_comparison(
    contender: Sequence[Mapping[str, Any]],
    control: Sequence[Mapping[str, Any]],
    metric: str,
) -> dict[str, Any]:
    left = [float(row["metrics"][metric]) for row in contender]
    right = [float(row["metrics"][metric]) for row in control]
    if [int(row["seed"]) for row in contender] != [int(row["seed"]) for row in control]:
        raise RuntimeError("metric comparison seeds differ")
    left_sd = statistics.stdev(left) if len(left) > 1 else 0.0
    right_sd = statistics.stdev(right) if len(right) > 1 else 0.0
    pooled_sd = math.sqrt((left_sd * left_sd + right_sd * right_sd) / 2.0)
    delta = statistics.fmean(left) - statistics.fmean(right)
    threshold = 2.0 * pooled_sd
    return {
        "metric": metric,
        "contender_mean": statistics.fmean(left),
        "control_mean": statistics.fmean(right),
        "mean_delta": delta,
        "pooled_sd": pooled_sd,
        "two_pooled_sd": threshold,
        "clears_positive_gate": delta > threshold,
        "matched_seed_wins": sum(a > b for a, b in zip(left, right, strict=True)),
        "matched_seed_losses": sum(a < b for a, b in zip(left, right, strict=True)),
    }


def _write_status(output: Path, **fields: Any) -> None:
    atomic_json(
        output / "STATUS.json",
        {
            "schema": f"{SCHEMA}.status",
            "status": "RUNNING",
            **fields,
            "updated_at_utc": utc_now(),
        },
    )


def build_parent(
    *,
    seed: int,
    output: Path,
    config: RunConfig,
    config_hash: str,
    vocab: list[str],
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    count_train: Sequence[tuple[str, str]],
    count_holdout: Sequence[tuple[str, str]],
    action_holdout: Sequence[ActionTextRow],
) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = output / "parents" / f"seed-{seed}"
    model_path = directory / "PARENT.pt"
    result_path = directory / "RESULT.json"
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if file_sha256(model_path) != result["parent_sha256"]:
            raise RuntimeError("parent result hash differs")
        return result, torch.load(model_path, map_location="cpu", weights_only=False)
    torch.manual_seed(seed)
    model = FrozenActionModel(len(vocab)).to(config.device)
    steps, loss, trainable = train_steps(
        model=model,
        stage="count_parent",
        seed=seed,
        rows=count_train,
        samples=None,
        ledger=None,
        stoi=stoi,
        config=config,
        total_steps=config.count_steps,
        checkpoint_dir=directory / "checkpoints",
        config_hash=config_hash,
    )
    count_score = counting_accuracy(
        model=model,
        rows=count_holdout,
        stoi=stoi,
        itos=itos,
        device=config.device,
    )
    predictions = predict_action_rows(
        model,
        path="adapter",
        rows=action_holdout,
        stoi=stoi,
        itos=itos,
        device=config.device,
    )
    payload = {
        "schema": f"{SCHEMA}.parent",
        "seed": seed,
        "config_hash": config_hash,
        "model_state": model.state_dict(),
        "vocab": vocab,
    }
    atomic_torch(model_path, payload)
    result = {
        "schema": f"{SCHEMA}.parent-result",
        "status": "COMPLETE",
        "seed": seed,
        "steps": steps,
        "trainable_parameters": trainable,
        "final_loss": loss,
        "counting_accuracy": count_score,
        "metrics": action_metrics(predictions),
        "predictions": predictions,
        "parent_sha256": file_sha256(model_path),
        "completed_at_utc": utc_now(),
    }
    atomic_json(result_path, result)
    return result, payload


def _rows_for_arm(
    arm: str, dataset: FrozenMultiviewDataset
) -> tuple[tuple[ActionTextRow, ...], tuple[tuple[str, str], ...]]:
    records = (
        dataset.static_rows
        if arm == "frozen_adapter_static"
        else dataset.multiview_rows
    )
    return records, tuple(row.pair() for row in records)


def train_arm(
    *,
    arm: str,
    seed: int,
    output: Path,
    config: RunConfig,
    config_hash: str,
    parent: Mapping[str, Any],
    parent_result: Mapping[str, Any],
    dataset: FrozenMultiviewDataset,
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    count_holdout: Sequence[tuple[str, str]],
) -> dict[str, Any]:
    directory = output / "horses" / f"{arm}-seed-{seed}"
    model_path = directory / "MODEL.pt"
    result_path = directory / "RESULT.json"
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if file_sha256(model_path) != result["model_sha256"]:
            raise RuntimeError("horse result hash differs")
        return result
    torch.manual_seed(seed + ARM_SEED_OFFSET[arm])
    model = FrozenActionModel(len(parent["vocab"])).to(config.device)
    model.load_state_dict(parent["model_state"])
    frozen_before = frozen_state(model)
    initial = flattened_trainable(model, arm).copy()
    records, pairs = _rows_for_arm(arm, dataset)
    ledger = ConceptExposureLedger(
        [
            *(row.sample for row in records),
            *(row.sample for row in dataset.holdout_rows),
        ],
        gradient_width=5,
        minimum_exposures_per_concept=max(1, config.grow_steps),
    )
    steps, loss, trainable = train_steps(
        model=model,
        stage=arm,
        seed=seed,
        rows=pairs,
        samples=records,
        ledger=ledger,
        stoi=stoi,
        config=config,
        total_steps=config.grow_steps,
        checkpoint_dir=directory / "checkpoints",
        config_hash=config_hash,
    )
    core_identical = frozen_state_identical(frozen_before, model)
    if not core_identical:
        raise RuntimeError(f"frozen tensors changed for {arm} seed {seed}")
    predictions = predict_action_rows(
        model,
        path=path_for_arm(arm),
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
    final = flattened_trainable(model, arm)
    payload = {
        "schema": f"{SCHEMA}.horse",
        "arm": arm,
        "seed": seed,
        "config_hash": config_hash,
        "parent_sha256": parent_result["parent_sha256"],
        "model_state": model.state_dict(),
        "vocab": parent["vocab"],
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
        "parent_sha256": parent_result["parent_sha256"],
        "frozen_core_bit_identical": core_identical,
        "weight_effect": weight_effect_receipt(initial, final),
        "exposure_report": ledger.report(),
        "model_sha256": file_sha256(model_path),
        "completed_at_utc": utc_now(),
    }
    atomic_json(result_path, result)
    return result


def aggregate_results(
    rows: Sequence[Mapping[str, Any]],
    parents: Sequence[Mapping[str, Any]],
    config: RunConfig,
) -> dict[str, Any]:
    by_arm = {
        arm: sorted(
            (row for row in rows if row["arm"] == arm),
            key=lambda row: int(row["seed"]),
        )
        for arm in ALL_ARMS
    }
    comparisons = {}
    paired = {}
    for control in CONTROLS:
        name = f"{PRIMARY_ARM}_vs_{control}"
        comparisons[name] = {
            metric: metric_comparison(
                by_arm[PRIMARY_ARM], by_arm[control], metric
            )
            for metric in ("accuracy", "macro_f1")
        }
        paired[name] = paired_prediction_comparison(
            by_arm[PRIMARY_ARM], by_arm[control]
        )
    retention = {
        arm: all(
            math.isclose(
                float(row["counting_accuracy"]),
                float(row["parent_counting_accuracy"]),
                abs_tol=1e-12,
            )
            for row in by_arm[arm]
        )
        for arm in TRAINED_ARMS
    }
    parameter_match = len(
        {
            int(row["trainable_parameters"])
            for arm in TRAINED_ARMS
            for row in by_arm[arm]
        }
    ) == 1
    producer_gate = (
        parameter_match
        and all(retention.values())
        and all(
            bool(row["frozen_core_bit_identical"])
            for arm in TRAINED_ARMS
            for row in by_arm[arm]
        )
        and all(
            comparisons[name][metric]["clears_positive_gate"]
            for name in comparisons
            for metric in ("accuracy", "macro_f1")
        )
        and all(value["clears_finite_uncertainty_gate"] for value in paired.values())
    )
    return {
        "schema": f"{SCHEMA}.result",
        "status": "COMPLETE",
        "authority": AUTHORITY,
        "promotion": "NOT_AUTHORIZED",
        "partial_unfreeze": "NONE",
        "producer_gate": "MET_PENDING_INDEPENDENT_REPLAY" if producer_gate else "NOT_MET",
        "config": asdict(config),
        "parameter_count_matched": parameter_match,
        "counting_preserved_exactly": retention,
        "comparisons": comparisons,
        "paired_comparisons": paired,
        "parents": list(parents),
        "per_arm": by_arm,
        "completed_at_utc": utc_now(),
    }


def require_storage(output: Path, minimum_free_gib: float) -> float:
    anchor = Path(output.anchor or "C:/")
    free = shutil.disk_usage(anchor).free / (1024**3)
    if free < minimum_free_gib:
        raise RuntimeError(
            f"storage admission closed: {free:.3f} GiB < {minimum_free_gib:.3f} GiB"
        )
    return free


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--seeds", default="20261131,20261132,20261133")
    parser.add_argument("--data-seed", type=int, default=20261113)
    parser.add_argument("--rows-per-view", type=int, default=1000)
    parser.add_argument("--holdout-rows", type=int, default=1500)
    parser.add_argument("--count-steps", type=int, default=28000)
    parser.add_argument("--grow-steps", type=int, default=18000)
    parser.add_argument("--checkpoint-every", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=0.002)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--minimum-free-gib", type=float, default=25.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    seeds = tuple(int(value) for value in args.seeds.split(",") if value)
    if len(seeds) < 3 or len(set(seeds)) != len(seeds):
        raise ValueError("at least three distinct seeds are required")
    output = args.output_dir.resolve()
    admitted_free_gib = require_storage(output, args.minimum_free_gib)
    preregistration = args.preregistration.resolve(strict=True)
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)

    provider = ClaySourceAdapter(args.source_dir)
    dataset = build_frozen_multiview_dataset(
        provider,
        rows_per_view=args.rows_per_view,
        holdout_rows=args.holdout_rows,
        seed=args.data_seed,
    )
    config = RunConfig(
        seeds=seeds,
        data_seed=args.data_seed,
        rows_per_view=args.rows_per_view,
        holdout_rows=args.holdout_rows,
        count_steps=args.count_steps,
        grow_steps=args.grow_steps,
        checkpoint_every=args.checkpoint_every,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        threads=args.threads,
        device="cpu",
        source_dir=str(Path(args.source_dir).resolve()),
        source_hashes=dict(sorted(provider.source_hashes.items())),
        dataset_manifest_sha256=str(dataset.manifest["manifest_sha256"]),
    )
    config_hash = stable_hash(asdict(config))
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
    manifest = {
        "schema": f"{SCHEMA}.manifest",
        "config": asdict(config),
        "config_hash": config_hash,
        "runner": str(Path(__file__).resolve()),
        "runner_sha256": file_sha256(Path(__file__).resolve()),
        "data_builder": str(Path(build_frozen_multiview_dataset.__code__.co_filename).resolve()),
        "data_builder_sha256": file_sha256(
            Path(build_frozen_multiview_dataset.__code__.co_filename).resolve()
        ),
        "preregistration": str(preregistration),
        "preregistration_sha256": file_sha256(preregistration),
        "dataset": dict(dataset.manifest),
        "vocab_sha256": stable_hash(vocab),
        "vocab_size": len(vocab),
        "admitted_free_gib": admitted_free_gib,
        "minimum_free_gib": args.minimum_free_gib,
    }
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "RUN_MANIFEST.json"
    if manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        comparable = dict(existing)
        comparable["admitted_free_gib"] = manifest["admitted_free_gib"]
        if comparable != manifest:
            raise RuntimeError("existing manifest differs; choose a new output directory")
    else:
        atomic_json(manifest_path, manifest)

    parents = []
    results: list[dict[str, Any]] = []
    for seed in seeds:
        _write_status(output, seed=seed, stage="count_parent")
        parent_result, parent = build_parent(
            seed=seed,
            output=output,
            config=config,
            config_hash=config_hash,
            vocab=vocab,
            stoi=stoi,
            itos=itos,
            count_train=count_train,
            count_holdout=count_holdout,
            action_holdout=dataset.holdout_rows,
        )
        parents.append(parent_result)
        results.append(
            {
                "arm": "no_intervention_adapter",
                "seed": seed,
                "trainable_parameters": 0,
                "metrics": parent_result["metrics"],
                "predictions": parent_result["predictions"],
                "counting_accuracy": parent_result["counting_accuracy"],
                "parent_counting_accuracy": parent_result["counting_accuracy"],
            }
        )
        for arm in TRAINED_ARMS:
            _write_status(output, seed=seed, stage=arm)
            result = train_arm(
                arm=arm,
                seed=seed,
                output=output,
                config=config,
                config_hash=config_hash,
                parent=parent,
                parent_result=parent_result,
                dataset=dataset,
                stoi=stoi,
                itos=itos,
                count_holdout=count_holdout,
            )
            results.append(result)
            print(
                f"{arm:28s} seed={seed} accuracy={result['metrics']['accuracy']:.6f} "
                f"macro_f1={result['metrics']['macro_f1']:.6f} "
                f"count={result['counting_accuracy']:.6f}",
                flush=True,
            )

    aggregate = aggregate_results(results, parents, config)
    atomic_json(output / "RESULT.json", aggregate)
    atomic_json(
        output / "STATUS.json",
        {
            "schema": f"{SCHEMA}.status",
            "status": "COMPLETE",
            "result": str(output / "RESULT.json"),
            "updated_at_utc": utc_now(),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

