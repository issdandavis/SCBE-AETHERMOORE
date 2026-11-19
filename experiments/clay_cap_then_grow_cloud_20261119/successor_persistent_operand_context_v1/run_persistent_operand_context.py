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
import os
from pathlib import Path
import random
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
    row: Row,
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    *,
    max_tokens: int = 8,
) -> str:
    model.eval()
    ids = [stoi[core.BOS], *(stoi[character] for character in row.prompt), stoi[core.SEP]]
    first = torch.tensor(context_values(row, 0), dtype=torch.float32).view(1, 1, CONTEXT_WIDTH)
    prompt_context = first.expand(1, len(ids), CONTEXT_WIDTH)
    logits, state = model(torch.tensor([ids], dtype=torch.long), "action", context=prompt_context)
    token = int(logits[0, -1].argmax())
    output: list[str] = []
    for step in range(max_tokens):
        if token == stoi[core.EOS]:
            break
        output.append(itos[token])
        next_context = torch.tensor(
            context_values(row, min(step + 1, MAX_DECODE_POSITION)), dtype=torch.float32
        ).view(1, 1, CONTEXT_WIDTH)
        logits, state = model(
            torch.tensor([[token]], dtype=torch.long), "action", state, context=next_context
        )
        token = int(logits[0, -1].argmax())
    return "".join(output)


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
