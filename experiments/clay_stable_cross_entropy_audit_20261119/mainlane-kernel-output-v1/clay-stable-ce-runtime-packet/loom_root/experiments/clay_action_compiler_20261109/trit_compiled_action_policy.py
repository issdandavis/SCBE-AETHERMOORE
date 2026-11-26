"""Trit-derived action policy for Clay's deterministic developmental sandbox.

The model is deliberately action-first rather than text-generative.  A state
vector is mapped to a query and scored against an immutable table of exact
action-token rows.  Every frozen base matrix is derived from signed bytes,
balanced trits, radial method coordinates, and the Six Tongues.  Training may
change only zero-initialized residual matrices; it cannot rewrite the token
registry or the compiler table.

This module proposes a token ID only.  The exact sandbox/compiler remains the
execution and reward authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
import hashlib
import json
import math
import random
from typing import Any, Iterable

import torch
from torch import Tensor, nn
from torch.nn import functional as F

from developmental_game_sandbox import (
    ACTION_NAMES,
    AgentStats,
    DevelopmentalGameSandbox,
    LifecycleSchedule,
    MEMORY_SLOTS,
    SandboxConfig,
    SandboxState,
)
from regional_breathing_field import (
    RegionalBreathingSandbox,
    holdout_field_config,
    training_field_config,
)
from trit_token_weight_bank import TONGUES, TokenWeightBank, build_weight_bank


SCHEMA = "clay.trit-compiled-action-policy.v1"
DATASET_SCHEMA = "clay.trit-action-policy-dataset.v1"
MOTOR_ACTIONS = ACTION_NAMES[:5]
ARMS = ("authority", "random_fixed", "shuffled_binding")

FEATURE_NAMES = (
    "position_x",
    "position_y",
    "velocity_x",
    "velocity_y",
    "presented_position_x",
    "presented_position_y",
    "presented_target_x",
    "presented_target_y",
    "frame_offset_x",
    "frame_offset_y",
    "geometry_00",
    "geometry_01",
    "geometry_10",
    "geometry_11",
    "scope_dx",
    "scope_dy",
    "scope_margin_x",
    "scope_margin_y",
    "scope_speed",
    "phase_crawl",
    "phase_play",
    "phase_swaddle",
    "phase_release",
    "drive_negative",
    "drive_neutral",
    "drive_positive",
    "target_phase_0",
    "target_phase_1",
    "target_phase_2",
    "target_phase_3",
    "memory_occupancy",
    "stagnation",
    "outburst",
    "mobility",
    "curiosity",
    "stability",
    "bias",
)


def canonical_json(value: Any) -> str:
    def encode_extra(item: Any) -> str:
        if isinstance(item, Decimal):
            return format(item, "f")
        raise TypeError(f"unsupported canonical JSON value: {type(item).__name__}")

    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=encode_extra,
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def tensor_sha256(value: Tensor) -> str:
    cpu = value.detach().cpu().contiguous()
    header = f"{cpu.dtype}|{tuple(cpu.shape)}|".encode("ascii")
    return hashlib.sha256(header + cpu.numpy().tobytes()).hexdigest()


def _float_list(values: Iterable[str]) -> list[float]:
    return [float(value) for value in values]


def vectorize_state(sandbox: DevelopmentalGameSandbox, state: SandboxState) -> Tensor:
    """Return the declared cross-vector view without replacing canonical state."""

    observation = sandbox.observation(state)
    phase = str(observation["phase"])
    presented_position = _float_list(observation["presented_position"])
    presented_target = _float_list(observation["presented_target"])
    frame_offset = _float_list(observation["frame_offset"])
    geometry = [float(value) for row in observation["geometry_matrix"] for value in row]
    scope = _float_list(observation["scope_vector"])
    world = float(sandbox.config.world_limit)
    target_phase = state.target_index % 4
    values = (
        float(state.position[0]) / world,
        float(state.position[1]) / world,
        float(state.velocity[0]) / 2.0,
        float(state.velocity[1]) / 2.0,
        presented_position[0] / world,
        presented_position[1] / world,
        presented_target[0] / world,
        presented_target[1] / world,
        frame_offset[0] / world,
        frame_offset[1] / world,
        *geometry,
        scope[0] / (2.0 * world),
        scope[1] / (2.0 * world),
        scope[2] / world,
        scope[3] / world,
        scope[4] / 2.0,
        *(1.0 if phase == name else 0.0 for name in ("crawl", "play", "swaddle", "release")),
        *(1.0 if state.drive_trit == drive else 0.0 for drive in (-1, 0, 1)),
        *(1.0 if target_phase == index else 0.0 for index in range(4)),
        sum(value is not None for value in state.memory) / MEMORY_SLOTS,
        min(1.0, state.stagnation_ticks / max(1, sandbox.config.outcry_trigger_ticks)),
        min(1.0, state.outburst_ticks_remaining / max(1, sandbox.config.outcry_duration_ticks)),
        float(state.stats.mobility) / 10.0,
        float(state.stats.curiosity) / 10.0,
        float(state.stats.stability) / 10.0,
        1.0,
    )
    if len(values) != len(FEATURE_NAMES) or any(not math.isfinite(value) for value in values):
        raise ValueError("policy feature vector violates its declared schema")
    return torch.tensor(values, dtype=torch.float32)


def _decimal_from_milli(value: int) -> Decimal:
    return Decimal(value) / Decimal(1000)


def sample_state(sandbox: DevelopmentalGameSandbox, rng: random.Random) -> SandboxState:
    """Sample one bounded state using integer draws for replay stability."""

    limit_milli = int(sandbox.config.world_limit * 1000)
    tick = rng.randrange(0, sandbox.config.schedule.cycle_ticks * 64)
    position = (
        _decimal_from_milli(rng.randint(-limit_milli, limit_milli)),
        _decimal_from_milli(rng.randint(-limit_milli, limit_milli)),
    )
    velocity = (
        _decimal_from_milli(rng.randint(-1250, 1250)),
        _decimal_from_milli(rng.randint(-1250, 1250)),
    )
    drive = rng.choice((-1, 0, 1))
    occupied = rng.randrange(0, 3)
    memory: list[int | None] = [None] * MEMORY_SLOTS
    for slot in rng.sample(range(MEMORY_SLOTS), occupied):
        memory[slot] = rng.randint(-64, 64)
    return SandboxState(
        tick=tick,
        position=position,
        velocity=velocity,
        target_index=rng.randrange(0, len(sandbox.config.targets)),
        memory=tuple(memory),
        stats=AgentStats(
            _decimal_from_milli(rng.randint(0, 10_000)),
            _decimal_from_milli(rng.randint(0, 10_000)),
            _decimal_from_milli(rng.randint(0, 10_000)),
        ),
        drive_trit=drive,
        stagnation_ticks=rng.randrange(0, sandbox.config.outcry_trigger_ticks),
        outburst_ticks_remaining=rng.randrange(0, sandbox.config.outcry_duration_ticks + 1),
    )


@dataclass(frozen=True, slots=True)
class PolicyDataset:
    features: Tensor
    labels: Tensor
    split: str
    source_family: str
    config_sha256: str
    tensor_sha256: str

    def verify(self) -> bool:
        if self.features.ndim != 2 or self.labels.ndim != 1:
            return False
        if self.features.shape[0] != self.labels.shape[0] or self.features.shape[1] != len(FEATURE_NAMES):
            return False
        if self.labels.dtype != torch.long or bool(torch.any((self.labels < 0) | (self.labels >= len(MOTOR_ACTIONS))).item()):
            return False
        return self.tensor_sha256 == sha256_json(
            {
                "features": tensor_sha256(self.features),
                "labels": tensor_sha256(self.labels),
                "split": self.split,
                "source_family": self.source_family,
                "config_sha256": self.config_sha256,
            }
        )


def build_policy_dataset(
    sandbox: DevelopmentalGameSandbox,
    *,
    count: int,
    seed: int,
    split: str,
    source_family: str,
) -> PolicyDataset:
    if count < 1 or not split or not source_family:
        raise ValueError("dataset count/split/source family must be declared")
    rng = random.Random(seed)
    features: list[Tensor] = []
    labels: list[int] = []
    for _ in range(count):
        state = sample_state(sandbox, rng)
        selected, _ = sandbox.sieve_actions(state)
        features.append(vectorize_state(sandbox, state))
        labels.append(selected.token_id)
    feature_tensor = torch.stack(features)
    label_tensor = torch.tensor(labels, dtype=torch.long)
    config_record = asdict(sandbox.config)
    config_hash = sha256_json(config_record)
    body = {
        "features": tensor_sha256(feature_tensor),
        "labels": tensor_sha256(label_tensor),
        "split": split,
        "source_family": source_family,
        "config_sha256": config_hash,
    }
    return PolicyDataset(feature_tensor, label_tensor, split, source_family, config_hash, sha256_json(body))


def training_sandbox() -> DevelopmentalGameSandbox:
    return DevelopmentalGameSandbox()


def training_curriculum_sandboxes() -> tuple[DevelopmentalGameSandbox, ...]:
    """Return bounded sectors that bracket, but do not include, the holdout.

    The parent remains trained on the cardinal sandbox.  Reinforcement cycles
    the world around a continuous agent state through cardinal, +22.5 degree,
    and -22.5 degree sectors.  The evaluation diagonals at 45 degrees remain
    unseen so transfer is still measured rather than trained directly.
    """

    positive = SandboxConfig(
        gravity=(Decimal("0.05"), Decimal("-0.23")),
        restoring_strength=Decimal("0.13"),
        targets=(
            (Decimal("1.385819"), Decimal("0.574025")),
            (Decimal("-0.574025"), Decimal("1.385819")),
            (Decimal("-1.385819"), Decimal("-0.574025")),
            (Decimal("0.574025"), Decimal("-1.385819")),
        ),
        schedule=LifecycleSchedule(11, 19, 7, 9),
    )
    negative = SandboxConfig(
        gravity=(Decimal("-0.05"), Decimal("-0.22")),
        restoring_strength=Decimal("0.14"),
        targets=(
            (Decimal("1.385819"), Decimal("-0.574025")),
            (Decimal("0.574025"), Decimal("1.385819")),
            (Decimal("-1.385819"), Decimal("0.574025")),
            (Decimal("-0.574025"), Decimal("-1.385819")),
        ),
        schedule=LifecycleSchedule(13, 17, 9, 7),
    )
    result = (
        training_sandbox(),
        DevelopmentalGameSandbox(positive),
        DevelopmentalGameSandbox(negative),
    )
    held_targets = set(holdout_sandbox().config.targets)
    if any(held_targets.intersection(sandbox.config.targets) for sandbox in result):
        raise RuntimeError("training curriculum leaked an exact holdout target")
    return result


def holdout_sandbox() -> DevelopmentalGameSandbox:
    return DevelopmentalGameSandbox(
        SandboxConfig(
            gravity=(Decimal("0.10"), Decimal("-0.20")),
            restoring_strength=Decimal("0.15"),
            targets=(
                (Decimal("1.25"), Decimal("1.25")),
                (Decimal("-1.25"), Decimal("1.25")),
                (Decimal("-1.25"), Decimal("-1.25")),
                (Decimal("1.25"), Decimal("-1.25")),
            ),
            schedule=LifecycleSchedule(10, 18, 7, 9),
        )
    )


def training_regional_breathing_sandbox() -> RegionalBreathingSandbox:
    """Cardinal objective with the causal twelve-sector training membrane."""

    return RegionalBreathingSandbox(
        training_sandbox().config,
        training_field_config(),
    )


def holdout_regional_breathing_sandbox() -> RegionalBreathingSandbox:
    """Direction-disjoint objective and source-disjoint membrane phase."""

    return RegionalBreathingSandbox(
        holdout_sandbox().config,
        holdout_field_config(),
    )


def _feature_trit_matrix(rows: int, columns: int, domain: str) -> Tensor:
    values = torch.empty((rows, columns), dtype=torch.float32)
    for row in range(rows):
        for column in range(columns):
            digest = hashlib.sha256(f"{domain}|{row}|{column}".encode("utf-8")).digest()
            values[row, column] = (-1.0, 0.0, 1.0)[digest[0] % 3]
    return values


def canonical_compiler_table(bank: TokenWeightBank | None = None) -> Tensor:
    """Concatenate all Six-Tongue rows for each exact motor token."""

    selected = bank or build_weight_bank(width=64)
    if not selected.verify():
        raise ValueError("action token bank failed verification")
    rows = []
    for token_id in range(len(MOTOR_ACTIONS)):
        values: list[int] = []
        for tongue in TONGUES:
            values.extend(selected.row("developmental-action", token_id, tongue).weights)
        rows.append(values)
    table = torch.tensor(rows, dtype=torch.float32)
    if set(table.unique().tolist()) - {-1.0, 0.0, 1.0}:
        raise RuntimeError("compiler table escaped balanced ternary")
    return table


def compiler_table_for_arm(arm: str, bank: TokenWeightBank | None = None) -> Tensor:
    canonical = canonical_compiler_table(bank)
    if arm == "authority":
        return canonical
    if arm == "shuffled_binding":
        return canonical[torch.arange(canonical.shape[0] - 1, -1, -1)]
    if arm == "random_fixed":
        rows = []
        for row_index, row in enumerate(canonical):
            generator = torch.Generator(device="cpu")
            generator.manual_seed(20261111 + row_index)
            rows.append(row[torch.randperm(row.numel(), generator=generator)])
        return torch.stack(rows)
    raise ValueError(f"unknown controlled compiler arm: {arm}")


class TritCompiledActionPolicy(nn.Module):
    """Residual learner over immutable trit-derived feature and compiler planes."""

    def __init__(self, *, arm: str, hidden_width: int = 96, bank: TokenWeightBank | None = None) -> None:
        super().__init__()
        if arm not in ARMS or hidden_width < 8:
            raise ValueError("policy arm/hidden width is invalid")
        compiler = compiler_table_for_arm(arm, bank)
        query_width = compiler.shape[1]
        self.arm = arm
        self.hidden_width = hidden_width
        self.query_width = query_width
        base_input = _feature_trit_matrix(hidden_width, len(FEATURE_NAMES), "clay-feature-trits")
        base_query = _feature_trit_matrix(query_width, hidden_width, "clay-query-trits")
        self.register_buffer("base_input", base_input)
        self.register_buffer("base_query", base_query)
        self.register_buffer("compiler_table", compiler)
        self.input_residual = nn.Parameter(torch.zeros_like(base_input))
        self.query_residual = nn.Parameter(torch.zeros_like(base_query))
        self.input_gain = nn.Parameter(torch.zeros(hidden_width))

    def forward(self, features: Tensor, *, return_activations: bool = False):
        if features.ndim != 2 or features.shape[1] != len(FEATURE_NAMES):
            raise ValueError("policy expects [batch, declared_features]")
        input_weight = self.base_input + self.input_residual
        hidden = torch.tanh(
            F.linear(features, input_weight / math.sqrt(len(FEATURE_NAMES)))
            * (1.0 + 0.1 * torch.tanh(self.input_gain))
        )
        query_weight = self.base_query + self.query_residual
        query = torch.tanh(F.linear(hidden, query_weight / math.sqrt(self.hidden_width)))
        logits = F.linear(query, self.compiler_table / math.sqrt(self.query_width))
        if return_activations:
            return logits, {"hidden": hidden, "query": query}
        return logits

    def base_receipt(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "arm": self.arm,
            "feature_names_sha256": sha256_json(FEATURE_NAMES),
            "base_input_sha256": tensor_sha256(self.base_input),
            "base_query_sha256": tensor_sha256(self.base_query),
            "compiler_table_sha256": tensor_sha256(self.compiler_table),
            "compiler_values": sorted(self.compiler_table.unique().tolist()),
            "trainable_parameters": sum(value.numel() for value in self.parameters()),
            "execution_authority": False,
        }

    def residual_receipt(self) -> dict[str, Any]:
        rows = {
            "input_residual": self.input_residual,
            "query_residual": self.query_residual,
            "input_gain": self.input_gain,
        }
        return {
            name: {
                "sha256": tensor_sha256(value),
                "l2": float(torch.linalg.vector_norm(value.detach()).cpu()),
                "maximum_absolute": float(value.detach().abs().max().cpu()),
                "changed_values": int((value.detach().abs() > 1e-12).sum().cpu()),
                "values": value.numel(),
            }
            for name, value in rows.items()
        }


def evaluate_policy(model: TritCompiledActionPolicy, dataset: PolicyDataset, *, device: torch.device) -> dict[str, Any]:
    if not dataset.verify():
        raise ValueError("cannot evaluate an invalid policy dataset")
    model.eval()
    with torch.no_grad():
        logits, activations = model(dataset.features.to(device), return_activations=True)
        labels = dataset.labels.to(device)
        probabilities = logits.softmax(dim=-1)
        predictions = logits.argmax(dim=-1)
        loss = F.cross_entropy(logits, labels)
        one_hot = F.one_hot(labels, num_classes=len(MOTOR_ACTIONS)).to(probabilities.dtype)
        brier = ((probabilities - one_hot) ** 2).sum(dim=-1).mean()
        confidence = probabilities.max(dim=-1).values
        accuracy = (predictions == labels).float().mean()
        ece = torch.zeros((), device=device)
        for lower in torch.linspace(0.0, 0.9, 10, device=device):
            upper = lower + 0.1
            mask = (confidence >= lower) & (confidence < upper if upper < 1 else confidence <= upper)
            if bool(mask.any()):
                ece += mask.float().mean() * (confidence[mask].mean() - (predictions[mask] == labels[mask]).float().mean()).abs()
        confusion = torch.zeros((len(MOTOR_ACTIONS), len(MOTOR_ACTIONS)), dtype=torch.int64, device=device)
        for truth, predicted in zip(labels, predictions):
            confusion[truth, predicted] += 1
        f1_values = []
        per_class_accuracy = []
        for index in range(len(MOTOR_ACTIONS)):
            tp = confusion[index, index].float()
            fp = confusion[:, index].sum().float() - tp
            fn = confusion[index, :].sum().float() - tp
            denominator = 2 * tp + fp + fn
            f1_values.append(float((2 * tp / denominator).cpu()) if denominator else 0.0)
            count = confusion[index, :].sum()
            per_class_accuracy.append(float((tp / count).cpu()) if count else 0.0)
        ordered = logits.sort(dim=-1, descending=True).values
        margin = (ordered[:, 0] - ordered[:, 1]).mean()
    return {
        "records": len(dataset.labels),
        "loss": float(loss.cpu()),
        "accuracy": float(accuracy.cpu()),
        "macro_f1": sum(f1_values) / len(f1_values),
        "brier": float(brier.cpu()),
        "ece": float(ece.cpu()),
        "mean_margin": float(margin.cpu()),
        "hidden_mean_abs": float(activations["hidden"].abs().mean().cpu()),
        "hidden_saturation": float((activations["hidden"].abs() > 0.95).float().mean().cpu()),
        "query_mean_abs": float(activations["query"].abs().mean().cpu()),
        "query_saturation": float((activations["query"].abs() > 0.95).float().mean().cpu()),
        "per_class_accuracy": dict(zip(MOTOR_ACTIONS, per_class_accuracy, strict=True)),
        "confusion": confusion.cpu().tolist(),
        "prediction_sha256": tensor_sha256(predictions),
        "logits_sha256": tensor_sha256(logits),
    }


def feature_connection_strengths(model: TritCompiledActionPolicy, *, limit: int = 12) -> list[dict[str, Any]]:
    strengths = torch.linalg.vector_norm(model.input_residual.detach(), dim=0).cpu().tolist()
    rows = [
        {"feature": name, "residual_l2": float(value)}
        for name, value in zip(FEATURE_NAMES, strengths, strict=True)
    ]
    return sorted(rows, key=lambda row: (-row["residual_l2"], row["feature"]))[:limit]


__all__ = [
    "ARMS",
    "DATASET_SCHEMA",
    "FEATURE_NAMES",
    "MOTOR_ACTIONS",
    "PolicyDataset",
    "SCHEMA",
    "TritCompiledActionPolicy",
    "build_policy_dataset",
    "canonical_compiler_table",
    "compiler_table_for_arm",
    "evaluate_policy",
    "feature_connection_strengths",
    "holdout_sandbox",
    "holdout_regional_breathing_sandbox",
    "sample_state",
    "tensor_sha256",
    "training_sandbox",
    "training_regional_breathing_sandbox",
    "vectorize_state",
]
