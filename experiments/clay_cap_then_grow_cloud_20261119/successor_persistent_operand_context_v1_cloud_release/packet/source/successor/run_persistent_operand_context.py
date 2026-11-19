"""Prototype runner for the preregistered persistent operand-context bypass.

This module implements the mechanism and its exact parameter-matched controls.
Its command line exposes a bounded no-parent/no-cloud smoke only. A full campaign
remains fail-closed until a separately hashed independent verifier exists.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys
from types import SimpleNamespace
from typing import Any, Iterable, Mapping, Sequence

import torch
from torch import Tensor, nn
import torch.nn.functional as F


HERE = Path(__file__).resolve().parent
BASE_RUNNER_PATH = HERE.parent / "kernel" / "run_cap_then_grow_kaggle.py"
SCHEMA = "clay.persistent-operand-context.v1"
SEEDS = (20261134, 20261135, 20261136)
ARMS = ("candidate", "context_permuted", "target_shuffle", "zero_update")
TRAINED_ARMS = ARMS[:-1]
CONTEXT_WIDTH = 6
HIDDEN_WIDTH = 192
MAX_DECODE_POSITION = 7
BASE_TRAINABLE_PARAMETERS = 140_820
CONTEXT_PROJECTION_PARAMETERS = CONTEXT_WIDTH * HIDDEN_WIDTH + HIDDEN_WIDTH
EXPECTED_TRAINABLE_PARAMETERS = BASE_TRAINABLE_PARAMETERS + CONTEXT_PROJECTION_PARAMETERS
EXPECTED_DATASET_SHA256 = "c9945f6b8037557e72e167117a58adb2b4bb51bfdcb63da50e56150f49495ad0"
AUTHORITY = "PROTOTYPE_AND_SMOKE_ONLY_NO_CLOUD_EXECUTION_NO_PROMOTION"


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def stable_hash(value: object) -> str:
    return sha256(canonical_json(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_bytes(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    os.replace(pending, path)


def load_base_runner() -> Any:
    name = "clay_cap_then_grow_base_runner_for_context_successor"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, BASE_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load base runner: {BASE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BASE = load_base_runner()
Row = BASE.Row


def context_values(row: Row, decode_position: int) -> tuple[float, ...]:
    if not 0 <= decode_position <= MAX_DECODE_POSITION:
        raise ValueError(f"decode position outside 0..{MAX_DECODE_POSITION}: {decode_position}")
    return (
        row.opcode / 2.0,
        ((row.x >> 8) & 255) / 255.0,
        (row.x & 255) / 255.0,
        ((row.y >> 8) & 255) / 255.0,
        (row.y & 255) / 255.0,
        decode_position / float(MAX_DECODE_POSITION),
    )


def context_assignment(rows: Sequence[Row], seed: int) -> tuple[tuple[int, ...], str]:
    """Derange context sources inside operation/length/split strata."""

    groups: dict[tuple[str, int, str], list[int]] = {}
    for index, row in enumerate(rows):
        groups.setdefault((row.operation, len(str(row.result)), row.split), []).append(index)
    mapping = list(range(len(rows)))
    receipt_rows: list[dict[str, object]] = []
    for group_number, key in enumerate(sorted(groups)):
        indices = list(groups[key])
        if len(indices) < 2:
            raise RuntimeError(f"context stratum cannot be deranged: {key}")
        rng = random.Random(seed + 2_000_003 * (group_number + 1))
        rng.shuffle(indices)
        shift = rng.randrange(1, len(indices))
        for position, destination in enumerate(indices):
            source = indices[(position + shift) % len(indices)]
            if source == destination:
                raise RuntimeError(f"context derangement retained a fixed point: {key}")
            mapping[destination] = source
            receipt_rows.append(
                {
                    "destination": rows[destination].identity_sha256,
                    "source": rows[source].identity_sha256,
                    "stratum": list(key),
                }
            )
    if sorted(mapping) != list(range(len(rows))):
        raise RuntimeError("context assignment is not a permutation")
    return tuple(mapping), stable_hash(receipt_rows)


@dataclass(frozen=True, slots=True)
class ArmRows:
    arm: str
    pairs: tuple[tuple[str, str], ...]
    context_rows: tuple[Row, ...]
    assignment_sha256: str


def build_arm_rows(rows: Sequence[Row], seed: int, arm: str) -> ArmRows:
    rows = tuple(rows)
    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    if arm == "context_permuted":
        mapping, assignment_sha256 = context_assignment(rows, seed)
        contexts = tuple(rows[index] for index in mapping)
        pairs = tuple((row.prompt, row.target) for row in rows)
    elif arm == "target_shuffle":
        shuffled, assignment_sha256 = BASE.shuffled_pairs(rows, seed)
        pairs = tuple(shuffled)
        contexts = rows
    else:
        contexts = rows
        pairs = tuple((row.prompt, row.target) for row in rows)
        assignment_sha256 = stable_hash(
            [
                {
                    "prompt": row.identity_sha256,
                    "context": row.identity_sha256,
                    "target": target,
                }
                for row, (_, target) in zip(rows, pairs, strict=True)
            ]
        )
    return ArmRows(arm, pairs, contexts, assignment_sha256)


def make_context_batch(
    core: Any,
    arm_rows: ArmRows,
    indices: Iterable[int],
    stoi: Mapping[str, int],
    device: str,
) -> tuple[Tensor, Tensor, Tensor, Tensor]:
    indices = tuple(indices)
    inputs, labels, masks = core.make_batch(arm_rows.pairs, indices, stoi, device)
    features = torch.zeros((*inputs.shape, CONTEXT_WIDTH), dtype=torch.float32, device=device)
    for batch_index, row_index in enumerate(indices):
        row = arm_rows.context_rows[row_index]
        base = context_values(row, 0)[:5]
        features[batch_index, :, :5] = torch.tensor(base, dtype=torch.float32, device=device)
        positions = (masks[batch_index].cumsum(dim=0) - 1).clamp(0, MAX_DECODE_POSITION)
        features[batch_index, :, 5] = positions / float(MAX_DECODE_POSITION)
    return inputs, labels, masks, features


def persistent_model_class(core: Any) -> type[nn.Module]:
    class PersistentOperandContextModel(core.FrozenActionModel):
        def __init__(self, vocab_size: int) -> None:
            super().__init__(vocab_size)
            self.context_projection = nn.Linear(CONTEXT_WIDTH, HIDDEN_WIDTH)

        def forward(
            self,
            inputs: Tensor,
            head: str,
            state: Any = None,
            *,
            context: Tensor | None = None,
        ) -> tuple[Tensor, Any]:
            core_state = state[0] if isinstance(state, tuple) else state
            hidden, core_state = self.g(self.e(inputs), core_state)
            if head == "count":
                return self.count_head(hidden), core_state
            if context is None or context.shape != (*hidden.shape[:-1], CONTEXT_WIDTH):
                raise ValueError(
                    f"action context must have shape {(*hidden.shape[:-1], CONTEXT_WIDTH)}, "
                    f"got {None if context is None else tuple(context.shape)}"
                )
            carrier = hidden + F.gelu(self.context_projection(context))
            return self.adapter_head(self.adapter(carrier)), (core_state, None)

    PersistentOperandContextModel.__name__ = "PersistentOperandContextModel"
    return PersistentOperandContextModel


def load_parent_state(model: nn.Module, parent_state: Mapping[str, Tensor]) -> None:
    missing, unexpected = model.load_state_dict(parent_state, strict=False)
    expected_missing = {"context_projection.weight", "context_projection.bias"}
    if set(missing) != expected_missing or unexpected:
        raise RuntimeError(f"parent state mismatch: missing={missing}, unexpected={unexpected}")


def selected_trainable(model: nn.Module, *, enforce_campaign_count: bool = True) -> list[nn.Parameter]:
    for parameter in model.parameters():
        parameter.requires_grad = False
    selected = [
        *model.context_projection.parameters(),
        *model.adapter.parameters(),
        *model.adapter_head.parameters(),
    ]
    for parameter in selected:
        parameter.requires_grad = True
    count = sum(parameter.numel() for parameter in selected)
    if enforce_campaign_count and count != EXPECTED_TRAINABLE_PARAMETERS:
        raise RuntimeError(f"trainable parameter count differs: {count}")
    return selected


def action_loss(model: nn.Module, inputs: Tensor, labels: Tensor, masks: Tensor, context: Tensor) -> Tensor:
    logits, _ = model(inputs, "action", context=context)
    token_loss = F.cross_entropy(
        logits.reshape(-1, logits.size(-1)), labels.reshape(-1), reduction="none"
    ).reshape(labels.shape)
    denominators = masks.sum(dim=1).clamp(min=1)
    return ((token_loss * masks).sum(dim=1) / denominators).mean()


@torch.inference_mode()
def generate_text(
    core: Any,
    model: nn.Module,
    prompt_row: Row,
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    *,
    context_row: Row | None = None,
    max_tokens: int = 8,
) -> str:
    """Generate for ``prompt_row`` while allowing an independent context source.

    Candidate and target-shuffle arms use the prompt row as their context.  The
    matched context-permuted control must instead pass its sealed context row;
    silently falling back to the prompt would invalidate that control.
    """

    model.eval()
    context_source = prompt_row if context_row is None else context_row
    ids = [stoi[core.BOS], *(stoi[character] for character in prompt_row.prompt), stoi[core.SEP]]
    first = torch.tensor(context_values(context_source, 0), dtype=torch.float32).view(
        1, 1, CONTEXT_WIDTH
    )
    prompt_context = first.expand(1, len(ids), CONTEXT_WIDTH)
    logits, state = model(torch.tensor([ids], dtype=torch.long), "action", context=prompt_context)
    token = int(logits[0, -1].argmax())
    output: list[str] = []
    for step in range(max_tokens):
        if token == stoi[core.EOS]:
            break
        output.append(itos[token])
        next_context = torch.tensor(
            context_values(context_source, min(step + 1, MAX_DECODE_POSITION)),
            dtype=torch.float32,
        ).view(1, 1, CONTEXT_WIDTH)
        logits, state = model(
            torch.tensor([[token]], dtype=torch.long), "action", state, context=next_context
        )
        token = int(logits[0, -1].argmax())
    return "".join(output)


@torch.inference_mode()
def evaluate_rows(
    core: Any,
    model: nn.Module,
    prompt_rows: Sequence[Row],
    context_rows: Sequence[Row],
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    *,
    max_tokens: int = 8,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Evaluate one sealed prompt/context pairing with per-example receipts."""

    if len(prompt_rows) != len(context_rows):
        raise ValueError("prompt/context row counts differ")
    predictions: list[dict[str, object]] = []
    per_operation: dict[str, list[bool]] = {name: [] for name in BASE.OPCODES}
    for index, (prompt_row, context_row) in enumerate(
        zip(prompt_rows, context_rows, strict=True)
    ):
        predicted = generate_text(
            core,
            model,
            prompt_row,
            stoi,
            itos,
            context_row=context_row,
            max_tokens=max_tokens,
        )
        correct = predicted == prompt_row.target
        per_operation[prompt_row.operation].append(correct)
        predictions.append(
            {
                "index": index,
                "operation": prompt_row.operation,
                "prompt_identity_sha256": prompt_row.identity_sha256,
                "context_identity_sha256": context_row.identity_sha256,
                "target": prompt_row.target,
                "prediction": predicted,
                "correct": correct,
            }
        )
    exact = sum(bool(row["correct"]) for row in predictions) / max(1, len(predictions))
    operation_accuracy = {
        operation: sum(values) / len(values) if values else 0.0
        for operation, values in per_operation.items()
    }
    metrics: dict[str, object] = {
        "exact_accuracy": exact,
        "macro_operation_accuracy": sum(operation_accuracy.values()) / len(operation_accuracy),
        "per_operation": operation_accuracy,
    }
    return predictions, metrics


def paired_bootstrap_delta(
    candidate_correct: Sequence[bool],
    control_correct: Sequence[bool],
    *,
    seed: int,
    strata: Sequence[str] | None = None,
    draws: int = 4096,
    alpha: float = 0.05,
) -> dict[str, object]:
    """Deterministic paired finite-evaluation bound.

    With ``strata=None`` this bootstraps held-out exact accuracy.  Supplying the
    operation label for every example bootstraps the equal-weight macro of the
    per-operation accuracy deltas.  A campaign gate passes only when the
    one-sided lower confidence bound is strictly positive, in addition to the
    unchanged seed-level two-pooled-SD and 3/3-win requirements.
    """

    if len(candidate_correct) != len(control_correct) or not candidate_correct:
        raise ValueError("paired correctness ledgers must have the same nonzero length")
    if draws < 100:
        raise ValueError("paired bootstrap requires at least 100 draws")
    if not 0.0 < alpha < 0.5:
        raise ValueError("alpha must lie strictly between zero and one half")
    if strata is None:
        labels = ("all",) * len(candidate_correct)
    else:
        if len(strata) != len(candidate_correct):
            raise ValueError("strata length differs from correctness ledgers")
        labels = tuple(str(value) for value in strata)
    groups: dict[str, list[int]] = {}
    for index, label in enumerate(labels):
        groups.setdefault(label, []).append(index)
    ordered_groups = [groups[label] for label in sorted(groups)]

    differences = [int(left) - int(right) for left, right in zip(candidate_correct, control_correct)]
    point = sum(sum(differences[index] for index in group) / len(group) for group in ordered_groups)
    point /= len(ordered_groups)
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(draws):
        group_means = []
        for group in ordered_groups:
            total = sum(differences[group[rng.randrange(len(group))]] for _ in group)
            group_means.append(total / len(group))
        samples.append(sum(group_means) / len(group_means))
    samples.sort()
    lower_index = max(0, min(draws - 1, math.floor(alpha * draws)))
    lower = samples[lower_index]
    return {
        "point_delta": point,
        "lower_one_sided": lower,
        "alpha": alpha,
        "draws": draws,
        "strata": sorted(groups),
        "passes": lower > 0.0,
    }


def _operation_accuracy(run: Mapping[str, object], operation: str) -> float:
    per_operation = run["metrics"]["per_operation"]  # type: ignore[index]
    value = per_operation[operation]  # type: ignore[index]
    if isinstance(value, Mapping):
        value = value["exact_accuracy"]
    return float(value)


def _seed_comparison(
    candidate: Sequence[Mapping[str, object]],
    control: Sequence[Mapping[str, object]],
    metric: str,
) -> dict[str, object]:
    left = [float(run["metrics"][metric]) for run in candidate]  # type: ignore[index]
    right = [float(run["metrics"][metric]) for run in control]  # type: ignore[index]
    left_sd = statistics.stdev(left)
    right_sd = statistics.stdev(right)
    pooled = math.sqrt((left_sd * left_sd + right_sd * right_sd) / 2.0)
    delta = statistics.fmean(left) - statistics.fmean(right)
    wins = [a > b for a, b in zip(left, right, strict=True)]
    return {
        "candidate_mean": statistics.fmean(left),
        "control_mean": statistics.fmean(right),
        "mean_delta": delta,
        "two_pooled_sd": 2.0 * pooled,
        "matched_seed_wins": sum(wins),
        "passes": delta > 2.0 * pooled and all(wins),
    }


def _paired_prediction_bootstrap(
    candidate: Sequence[Mapping[str, object]],
    control: Sequence[Mapping[str, object]],
    *,
    seed: int,
    macro_operation: bool,
    draws: int,
) -> dict[str, object]:
    """Bootstrap held-out rows after averaging each paired row over seeds."""

    candidate_by_seed = {int(run["seed"]): run for run in candidate}
    control_by_seed = {int(run["seed"]): run for run in control}
    row_differences: list[float] | None = None
    row_operations: list[str] | None = None
    row_identities: list[str] | None = None
    for campaign_seed in SEEDS:
        candidate_rows = candidate_by_seed[campaign_seed]["predictions"]
        control_rows = control_by_seed[campaign_seed]["predictions"]
        if len(candidate_rows) != len(control_rows):  # type: ignore[arg-type]
            raise ValueError("candidate/control prediction counts differ")
        identities: list[str] = []
        operations: list[str] = []
        differences: list[float] = []
        for left, right in zip(candidate_rows, control_rows, strict=True):  # type: ignore[arg-type]
            left_identity = str(
                left.get("identity_sha256", left.get("prompt_identity_sha256", ""))
            )
            right_identity = str(
                right.get("identity_sha256", right.get("prompt_identity_sha256", ""))
            )
            if not left_identity or left_identity != right_identity:
                raise ValueError("candidate/control prediction identities differ")
            if str(left["operation"]) != str(right["operation"]):
                raise ValueError("candidate/control prediction operations differ")
            identities.append(left_identity)
            operations.append(str(left["operation"]))
            differences.append(float(bool(left["correct"])) - float(bool(right["correct"])))
        if row_identities is None:
            row_identities = identities
            row_operations = operations
            row_differences = [0.0] * len(differences)
        elif identities != row_identities or operations != row_operations:
            raise ValueError("held-out prediction rows differ across seeds")
        assert row_differences is not None
        row_differences = [
            total + value / len(SEEDS)
            for total, value in zip(row_differences, differences, strict=True)
        ]
    assert row_differences is not None and row_operations is not None
    labels = row_operations if macro_operation else ["all"] * len(row_differences)
    groups: dict[str, list[int]] = {}
    for index, label in enumerate(labels):
        groups.setdefault(label, []).append(index)
    ordered_groups = [groups[label] for label in sorted(groups)]
    point = statistics.fmean(
        statistics.fmean(row_differences[index] for index in group)
        for group in ordered_groups
    )
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(draws):
        means = []
        for group in ordered_groups:
            means.append(
                statistics.fmean(
                    row_differences[group[rng.randrange(len(group))]] for _ in group
                )
            )
        samples.append(statistics.fmean(means))
    samples.sort()
    lower = samples[max(0, min(draws - 1, math.floor(0.05 * draws)))]
    return {
        "point_delta": point,
        "lower_one_sided_95": lower,
        "draws": draws,
        "strata": sorted(groups),
        "passes": lower > 0.0,
    }


def admission_gate(
    candidate: Sequence[Mapping[str, object]],
    controls: Mapping[str, Sequence[Mapping[str, object]]],
    *,
    independent_replay: bool,
    bootstrap_seed: int,
    bootstrap_draws: int = 4096,
) -> dict[str, object]:
    """Fail-closed measurement gate for the preregistered successor campaign."""

    required_controls = {"context_permuted", "target_shuffle", "zero_update"}
    if set(controls) != required_controls:
        raise ValueError(f"controls must be exactly {sorted(required_controls)}")

    def ordered(runs: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
        result = sorted(runs, key=lambda run: int(run["seed"]))
        if [int(run["seed"]) for run in result] != list(SEEDS):
            raise ValueError(f"runs must contain exactly the sealed seeds {SEEDS}")
        return result

    candidate_runs = ordered(candidate)
    control_runs = {name: ordered(runs) for name, runs in controls.items()}
    comparisons: dict[str, object] = {}
    comparison_passes: list[bool] = []
    for control_index, name in enumerate(sorted(control_runs)):
        metric_results: dict[str, object] = {}
        for metric_index, metric in enumerate(("exact_accuracy", "macro_operation_accuracy")):
            seed_result = _seed_comparison(candidate_runs, control_runs[name], metric)
            finite_result = _paired_prediction_bootstrap(
                candidate_runs,
                control_runs[name],
                seed=bootstrap_seed + 1009 * control_index + metric_index,
                macro_operation=metric == "macro_operation_accuracy",
                draws=bootstrap_draws,
            )
            passes = bool(seed_result["passes"] and finite_result["passes"])
            metric_results[metric] = {
                "seed_effect": seed_result,
                "finite_evaluation": finite_result,
                "passes": passes,
            }
            comparison_passes.append(passes)
        comparisons[name] = metric_results

    candidate_nonzero = all(
        _operation_accuracy(run, operation) > 0.0
        for run in candidate_runs
        for operation in BASE.OPCODES
    )
    out_of_support = all(
        _operation_accuracy(candidate_run, operation)
        > _operation_accuracy(control_runs[control_name][seed_index], operation)
        for seed_index, candidate_run in enumerate(candidate_runs)
        for control_name in ("context_permuted", "target_shuffle")
        for operation in ("add", "multiply")
    )
    all_runs = [*candidate_runs, *(run for runs in control_runs.values() for run in runs)]
    retention = all(
        bool(run["retention_exact"])
        and bool(run["training"]["frozen_core_bit_identical"])  # type: ignore[index]
        for run in all_runs
    )
    gates = {
        "three_seed_two_sd_three_of_three_and_finite_evaluation": all(comparison_passes),
        "candidate_per_operation_nonzero": candidate_nonzero,
        "out_of_support_add_multiply": out_of_support,
        "retention_and_frozen_identity": retention,
        "independent_replay": bool(independent_replay),
    }
    return {
        "comparisons": comparisons,
        "gates": gates,
        "all_measurement_gates": all(gates.values()),
        "promotion": "NONE",
    }


class _ToyFrozenActionModel(nn.Module):
    """Small synthetic core used only by the bounded smoke; no checkpoint is loaded."""

    def __init__(self, vocab_size: int) -> None:
        super().__init__()
        self.e = nn.Embedding(vocab_size, 8)
        self.g = nn.GRU(8, HIDDEN_WIDTH, 1, batch_first=True)
        self.adapter = nn.Sequential(nn.Linear(HIDDEN_WIDTH, 16), nn.GELU(), nn.Linear(16, HIDDEN_WIDTH))
        self.count_head = nn.Linear(HIDDEN_WIDTH, vocab_size)
        self.adapter_head = nn.Linear(HIDDEN_WIDTH, vocab_size)


def _tensor_hash(state: Mapping[str, Tensor], prefixes: Sequence[str]) -> str:
    digest = sha256()
    for name in sorted(state):
        if not name.startswith(tuple(prefixes)):
            continue
        tensor = state[name].detach().cpu().contiguous()
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(tensor.numpy().tobytes(order="C"))
    return digest.hexdigest()


def run_smoke() -> dict[str, object]:
    train, held, dataset_sha256 = BASE.build_rows()
    if dataset_sha256 != EXPECTED_DATASET_SHA256:
        raise RuntimeError("dataset identity differs")
    assignments: dict[str, dict[str, str]] = {}
    for seed in SEEDS:
        assignments[str(seed)] = {}
        for split, rows in (("train", train), ("held_out", held)):
            arm = build_arm_rows(rows, seed, "context_permuted")
            for destination, source in zip(rows, arm.context_rows, strict=True):
                if destination.identity_sha256 == source.identity_sha256:
                    raise RuntimeError("context smoke found a fixed point")
                if (destination.operation, len(str(destination.result)), destination.split) != (
                    source.operation,
                    len(str(source.result)),
                    source.split,
                ):
                    raise RuntimeError("context smoke crossed a stratum")
            assignments[str(seed)][split] = arm.assignment_sha256

    torch.manual_seed(91)
    toy_core = SimpleNamespace(FrozenActionModel=_ToyFrozenActionModel)
    model_type = persistent_model_class(toy_core)
    candidate = model_type(vocab_size=32)
    control = model_type(vocab_size=32)
    control.load_state_dict(candidate.state_dict())
    if any(
        not torch.equal(left, right)
        for left, right in zip(candidate.state_dict().values(), control.state_dict().values(), strict=True)
    ):
        raise RuntimeError("matched arms did not start bit-identically")
    projection_count = sum(parameter.numel() for parameter in candidate.context_projection.parameters())
    if projection_count != CONTEXT_PROJECTION_PARAMETERS:
        raise RuntimeError("context projection parameter count differs")
    selected_trainable(candidate, enforce_campaign_count=False)
    frozen_before = _tensor_hash(candidate.state_dict(), ("e.", "g.", "count_head."))
    inputs = torch.tensor([[1, 2, 3], [3, 2, 1]], dtype=torch.long)
    labels = torch.tensor([[2, 3, 4], [2, 1, 0]], dtype=torch.long)
    masks = torch.ones_like(inputs, dtype=torch.float32)
    context = torch.tensor(
        [
            [context_values(train[0], position) for position in range(3)],
            [context_values(train[-1], position) for position in range(3)],
        ],
        dtype=torch.float32,
    )
    optimizer = torch.optim.Adam(selected_trainable(candidate, enforce_campaign_count=False), lr=0.002)
    loss = action_loss(candidate, inputs, labels, masks, context)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    frozen_after = _tensor_hash(candidate.state_dict(), ("e.", "g.", "count_head."))
    if frozen_before != frozen_after:
        raise RuntimeError("synthetic smoke changed frozen tensors")
    if not torch.isfinite(loss):
        raise RuntimeError("synthetic smoke loss is nonfinite")

    train_add = {row.result for row in train if row.operation == "add"}
    held_add = {row.result for row in held if row.operation == "add"}
    train_subtract = {row.result for row in train if row.operation == "subtract"}
    held_subtract = {row.result for row in held if row.operation == "subtract"}
    train_multiply = {row.result for row in train if row.operation == "multiply"}
    held_multiply = {row.result for row in held if row.operation == "multiply"}
    if not train_add.isdisjoint(held_add) or not train_multiply.isdisjoint(held_multiply):
        raise RuntimeError("out-of-support split differs")
    if train_subtract != held_subtract:
        raise RuntimeError("subtraction overlap diagnostic differs")

    return {
        "schema": f"{SCHEMA}.smoke",
        "status": "PASS_NO_PARENT_LOAD_NO_CLOUD_EXECUTION",
        "authority": AUTHORITY,
        "dataset_identity_sha256": dataset_sha256,
        "train_rows": len(train),
        "held_out_rows": len(held),
        "context_projection_parameters": projection_count,
        "campaign_trainable_parameters": EXPECTED_TRAINABLE_PARAMETERS,
        "matched_initialization": True,
        "frozen_tensors_bit_identical_after_synthetic_update": True,
        "synthetic_loss": float(loss.detach()),
        "context_assignment_sha256": assignments,
        "split_checks": {
            "add_result_support_disjoint": True,
            "multiply_result_support_disjoint": True,
            "subtract_result_support_equal": True,
        },
        "runner_sha256": sha256_file(Path(__file__)),
        "promotion": "NONE",
    }


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-output", type=Path, required=True)
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    args = parse_args(arguments)
    receipt = run_smoke()
    atomic_json(args.smoke_output, receipt)
    print(json.dumps({"status": receipt["status"], "promotion": "NONE"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
