"""Independent full-held-out replay for the persistent operand-context campaign."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import random
import statistics
import sys
from typing import Any, Iterable, Mapping, Sequence

import torch


HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "source" / "kernel" / "run_cap_then_grow_kaggle.py"
SUCCESSOR_PATH = HERE / "source" / "successor" / "run_persistent_operand_context.py"
SEEDS = (20261134, 20261135, 20261136)
ARMS = ("candidate", "context_permuted", "target_shuffle", "zero_update")
OPCODES = {"add": 0, "subtract": 1, "multiply": 2}
CONTEXT_WIDTH = 6
MAX_POSITION = 7
EXPECTED_DATASET_SHA256 = "c9945f6b8037557e72e167117a58adb2b4bb51bfdcb63da50e56150f49495ad0"


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


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(path)
    return value


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BASE = load_module("clay_operand_context_replay_base", BASE_PATH)
SUCCESSOR = load_module("clay_operand_context_replay_model", SUCCESSOR_PATH)


@dataclass(frozen=True, slots=True)
class ReplayRow:
    operation: str
    opcode: int
    x: int
    y: int
    split: str
    result: int
    prompt: str
    target: str
    identity_sha256: str


def make_row(operation: str, x: int, y: int, split: str) -> ReplayRow:
    if operation == "add":
        result = x + y
    elif operation == "subtract":
        result = x - y
    elif operation == "multiply":
        result = x * y
    else:
        raise ValueError(operation)
    opcode = OPCODES[operation]
    raw = bytes((opcode, (x >> 8) & 255, x & 255, (y >> 8) & 255, y & 255))
    prompt = "K :" + "".join(chr(0xE100 + value) for value in raw) + " =>"
    target = " " + str(result)[::-1]
    identity = stable_hash(
        {
            "opcode": opcode,
            "operation": operation,
            "x": x,
            "y": y,
            "target": target,
            "split": split,
        }
    )
    return ReplayRow(operation, opcode, x, y, split, result, prompt, target, identity)


def build_rows() -> tuple[list[ReplayRow], list[ReplayRow], str]:
    train: list[ReplayRow] = []
    held: list[ReplayRow] = []
    train.extend(make_row("add", x, y, "train") for x in range(30) for y in range(30))
    train.extend(
        make_row("subtract", x, y, "train") for x in range(30) for y in range(x + 1)
    )
    train.extend(make_row("multiply", x, y, "train") for x in range(13) for y in range(13))
    held.extend(make_row("add", x, y, "held_out") for x in range(30, 60) for y in range(30, 60))
    held.extend(
        make_row("subtract", x, y, "held_out")
        for x in range(30, 60)
        for y in range(30, x + 1)
    )
    held.extend(
        make_row("multiply", x, y, "held_out")
        for x in range(13, 25)
        for y in range(13, 25)
    )
    return train, held, stable_hash([row.identity_sha256 for row in (*train, *held)])


def independent_context_rows(
    rows: Sequence[ReplayRow], seed: int, arm: str
) -> tuple[tuple[ReplayRow, ...], str]:
    if arm != "context_permuted":
        contexts = tuple(rows)
        if arm == "target_shuffle":
            # The producer's held target assignment is receipted even though
            # evaluation uses correct targets and identity context. Rebuild it.
            targets = [row.target for row in rows]
            groups: dict[tuple[str, int], list[int]] = {}
            for index, row in enumerate(rows):
                groups.setdefault((row.operation, len(str(row.result))), []).append(index)
            for group_index, key in enumerate(sorted(groups)):
                indices = groups[key]
                values = [targets[index] for index in indices]
                rng = random.Random(seed + 1_000_003 * (group_index + 1))
                rng.shuffle(values)
                original = [targets[index] for index in indices]
                if len(values) > 1 and values == original:
                    values = values[1:] + values[:1]
                for index, target in zip(indices, values, strict=True):
                    targets[index] = target
            assignment = stable_hash(
                [
                    stable_hash({"prompt": row.prompt, "target": target})
                    for row, target in zip(rows, targets, strict=True)
                ]
            )
        else:
            assignment = stable_hash(
                [
                    {
                        "prompt": row.identity_sha256,
                        "context": row.identity_sha256,
                        "target": row.target,
                    }
                    for row in rows
                ]
            )
        return contexts, assignment

    groups: dict[tuple[str, int, str], list[int]] = {}
    for index, row in enumerate(rows):
        groups.setdefault((row.operation, len(str(row.result)), row.split), []).append(index)
    mapping = list(range(len(rows)))
    receipt_rows: list[dict[str, object]] = []
    for group_number, key in enumerate(sorted(groups)):
        indices = list(groups[key])
        if len(indices) < 2:
            raise RuntimeError(f"cannot derange {key}")
        rng = random.Random(seed + 2_000_003 * (group_number + 1))
        rng.shuffle(indices)
        shift = rng.randrange(1, len(indices))
        for position, destination in enumerate(indices):
            source = indices[(position + shift) % len(indices)]
            if source == destination:
                raise RuntimeError(f"fixed point in {key}")
            mapping[destination] = source
            receipt_rows.append(
                {
                    "destination": rows[destination].identity_sha256,
                    "source": rows[source].identity_sha256,
                    "stratum": list(key),
                }
            )
    if sorted(mapping) != list(range(len(rows))):
        raise RuntimeError("context mapping is not bijective")
    return tuple(rows[index] for index in mapping), stable_hash(receipt_rows)


def context_values(row: ReplayRow, position: int) -> tuple[float, ...]:
    return (
        row.opcode / 2.0,
        ((row.x >> 8) & 255) / 255.0,
        (row.x & 255) / 255.0,
        ((row.y >> 8) & 255) / 255.0,
        (row.y & 255) / 255.0,
        min(position, MAX_POSITION) / float(MAX_POSITION),
    )


@torch.inference_mode()
def generate(
    core: Any,
    model: torch.nn.Module,
    prompt_row: ReplayRow,
    context_row: ReplayRow,
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    max_tokens: int = 8,
) -> str:
    model.eval()
    ids = [stoi[core.BOS], *(stoi[character] for character in prompt_row.prompt), stoi[core.SEP]]
    first = torch.tensor(context_values(context_row, 0), dtype=torch.float32).view(
        1, 1, CONTEXT_WIDTH
    )
    logits, state = model(
        torch.tensor([ids], dtype=torch.long),
        "action",
        context=first.expand(1, len(ids), CONTEXT_WIDTH),
    )
    token = int(logits[0, -1].argmax())
    output: list[str] = []
    for step in range(max_tokens):
        if token == stoi[core.EOS]:
            break
        output.append(itos[token])
        context = torch.tensor(
            context_values(context_row, step + 1), dtype=torch.float32
        ).view(1, 1, CONTEXT_WIDTH)
        logits, state = model(
            torch.tensor([[token]], dtype=torch.long),
            "action",
            state,
            context=context,
        )
        token = int(logits[0, -1].argmax())
    return "".join(output)


def evaluate(
    core: Any,
    model: torch.nn.Module,
    rows: Sequence[ReplayRow],
    contexts: Sequence[ReplayRow],
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    predictions: list[dict[str, object]] = []
    per_operation: dict[str, list[bool]] = {name: [] for name in OPCODES}
    for index, (row, context_row) in enumerate(zip(rows, contexts, strict=True)):
        predicted = generate(core, model, row, context_row, stoi, itos)
        correct = predicted == row.target
        per_operation[row.operation].append(correct)
        predictions.append(
            {
                "index": index,
                "operation": row.operation,
                "prompt_identity_sha256": row.identity_sha256,
                "context_identity_sha256": context_row.identity_sha256,
                "target": row.target,
                "prediction": predicted,
                "correct": correct,
            }
        )
    operation_accuracy = {
        operation: statistics.fmean(values) if values else 0.0
        for operation, values in per_operation.items()
    }
    metrics = {
        "exact_accuracy": statistics.fmean(bool(row["correct"]) for row in predictions),
        "macro_operation_accuracy": statistics.fmean(operation_accuracy.values()),
        "per_operation": operation_accuracy,
    }
    return predictions, metrics


def replay(args: argparse.Namespace) -> dict[str, Any]:
    torch.set_num_threads(min(4, max(1, os.cpu_count() or 1)))
    torch.use_deterministic_algorithms(True)
    result = load_json(args.result)
    train_rows, held_rows, dataset_sha256 = build_rows()
    if dataset_sha256 != EXPECTED_DATASET_SHA256 or result["dataset"]["identity_sha256"] != dataset_sha256:
        raise RuntimeError("independent dataset identity differs")
    if (len(train_rows), len(held_rows)) != (1534, 1509):
        raise RuntimeError("independent row count differs")
    scbe_root = args.runtime_root / "scbe_repo"
    sys.path.insert(0, str(scbe_root))
    from python.scbe import clay_frozen_multiview_adapter as core

    vocab = list(result["vocab"])
    stoi = {character: index for index, character in enumerate(vocab)}
    itos = {index: character for index, character in enumerate(vocab)}
    model_type = SUCCESSOR.persistent_model_class(core)
    checks: list[dict[str, object]] = []
    indexed = {(int(run["seed"]), str(run["arm"])): run for run in result["runs"]}
    if set(indexed) != {(seed, arm) for seed in SEEDS for arm in ARMS}:
        raise RuntimeError("run matrix differs")
    for seed in SEEDS:
        for arm in ARMS:
            run = indexed[(seed, arm)]
            model_path = args.output_root / str(run["model_relative_path"])
            if sha256_file(model_path) != str(run["model_sha256"]):
                raise RuntimeError(f"model hash differs: {seed}/{arm}")
            payload = torch.load(model_path, map_location="cpu", weights_only=False)
            if payload.get("seed") != seed or payload.get("arm") != arm:
                raise RuntimeError(f"model identity differs: {seed}/{arm}")
            model = model_type(len(vocab))
            model.load_state_dict(payload["model_state"])
            contexts, assignment = independent_context_rows(held_rows, seed, arm)
            if assignment != str(run["held_context_assignment_sha256"]):
                raise RuntimeError(f"held assignment differs: {seed}/{arm}")
            predictions, metrics = evaluate(core, model, held_rows, contexts, stoi, itos)
            if predictions != run["predictions"] or metrics != run["metrics"]:
                raise RuntimeError(f"held replay differs: {seed}/{arm}")
            count_score = core.counting_accuracy(
                model=model,
                rows=core.counting_rows(True),
                stoi=stoi,
                itos=itos,
                device="cpu",
            )
            if count_score != float(run["counting_accuracy"]):
                raise RuntimeError(f"counting replay differs: {seed}/{arm}")
            checks.append(
                {
                    "seed": seed,
                    "arm": arm,
                    "held_predictions": len(predictions),
                    "held_assignment_sha256": assignment,
                    "model_sha256": str(run["model_sha256"]),
                    "counting_accuracy": count_score,
                }
            )
    return {
        "schema": "clay.persistent-operand-context.independent-replay.v1",
        "status": "PASS",
        "dataset_identity_sha256": dataset_sha256,
        "checks": checks,
        "promotion": "NONE",
    }


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    args = parse_args(arguments)
    receipt = replay(args)
    pending = args.output.with_suffix(args.output.suffix + ".pending")
    pending.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(pending, args.output)
    print(json.dumps({"status": "PASS", "checks": len(receipt["checks"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
