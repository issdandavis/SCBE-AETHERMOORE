#!/usr/bin/env python3
"""Run one explicitly released frozen prime-token reader lineage.

The runtime factory is project-local code that returns the already-admitted
model and examples.  This command owns only release enforcement, lineage
isolation, exact resume, reader-only optimization, and checkpoint receipts.
It never dispatches tools or changes promotion/unfreeze authority.
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
from pathlib import Path
import sys
from typing import Callable

import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.prime_token_input_access import (
    CONTROL_MODES,
    FullSystemPrimeTokenInputAccessLM,
)
from python.scbe.prime_token_training import (
    PrimeTrainingExample,
    admit_material_launch,
    atomic_json,
    load_adapter_checkpoint,
    module_state_sha256,
    new_training_state,
    save_adapter_checkpoint,
    sha256_file,
    train_steps,
)

REQUIRED_IDENTITY_FIELDS = (
    "arm",
    "seed",
    "parent_sha256",
    "source_manifest_sha256",
    "split_manifest_sha256",
)
ALL_ARMS = ("no_intervention", *CONTROL_MODES)
REQUIRED_EVALUATION_METRICS = (
    "accuracy",
    "relationship",
    "function",
    "ordinary_false_activation",
    "frozen_parent_retention",
    "throughput",
    "peak_memory",
)


def _factory(spec: str) -> Callable:
    if spec.count(":") != 1:
        raise ValueError("runtime factory must use module:function syntax")
    module_name, function_name = spec.split(":", 1)
    function = getattr(importlib.import_module(module_name), function_name)
    if not callable(function):
        raise TypeError("runtime factory target is not callable")
    return function


def validate_evaluation_result(value: object) -> dict[str, object]:
    """Require raw outcomes and every preregistered non-storage measure."""

    if not isinstance(value, dict):
        raise TypeError("runtime evaluator must return a dictionary")
    metrics = value.get("metrics")
    outcomes = value.get("per_example")
    if not isinstance(metrics, dict):
        raise TypeError("runtime evaluator omitted its metrics dictionary")
    missing = [name for name in REQUIRED_EVALUATION_METRICS if name not in metrics]
    if missing:
        raise ValueError(f"runtime evaluator omitted required metrics: {missing}")
    for name in REQUIRED_EVALUATION_METRICS:
        number = metrics[name]
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise TypeError(f"runtime metric {name} must be numeric")
        if not math.isfinite(float(number)):
            raise ValueError(f"runtime metric {name} must be finite")
    if not isinstance(outcomes, list) or not outcomes:
        raise ValueError("runtime evaluator must retain non-empty per-example outcomes")
    if not all(isinstance(row, dict) for row in outcomes):
        raise TypeError("runtime per-example outcomes must be dictionaries")
    return {"metrics": dict(metrics), "per_example": outcomes}


def run(args: argparse.Namespace) -> dict[str, object]:
    release = admit_material_launch(args.audit, args.authorization)
    runtime_file = args.runtime_config.resolve(strict=True)
    runtime_config = json.loads(runtime_file.read_text(encoding="utf-8"))
    if not isinstance(runtime_config, dict):
        raise ValueError("runtime config must be a JSON object")
    payload = _factory(args.runtime_factory)(runtime_config)
    if not isinstance(payload, dict):
        raise TypeError("runtime factory must return a dictionary")
    model = payload.get("model")
    examples = payload.get("examples")
    identity = payload.get("identity")
    evaluator = payload.get("evaluate")
    if not isinstance(model, FullSystemPrimeTokenInputAccessLM):
        raise TypeError("runtime factory returned the wrong model type")
    if not isinstance(examples, list) or not all(isinstance(item, PrimeTrainingExample) for item in examples):
        raise TypeError("runtime factory returned invalid examples")
    if not isinstance(identity, dict):
        raise TypeError("runtime factory returned invalid lineage identity")
    if not callable(evaluator):
        raise TypeError("runtime factory omitted its independent evaluation callable")
    missing = [field for field in REQUIRED_IDENTITY_FIELDS if not identity.get(field)]
    if missing:
        raise ValueError(f"lineage identity is missing required fields: {missing}")
    if identity["arm"] != args.arm or str(identity["seed"]) != str(args.seed):
        raise ValueError("runtime lineage arm/seed differs from command")
    if identity["parent_sha256"] != module_state_sha256(model.core):
        raise ValueError("runtime lineage parent hash differs from loaded core")
    if args.arm != "no_intervention" and any(example.packet.mode != args.arm for example in examples):
        raise ValueError("runtime examples contain another control arm")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    unexpected = [path for path in output.iterdir() if path.name != "LATEST.json"]
    if unexpected and not (output / "LATEST.json").is_file():
        raise RuntimeError("new lineage output directory is not empty")
    start_step = 0
    history: list[dict[str, object]] = []
    pointer: dict[str, object] | None = None
    if args.arm == "no_intervention":
        if args.steps != 0:
            raise ValueError("no_intervention is evaluation-only and requires zero steps")
        final_step = 0
    else:
        if args.steps <= 0:
            raise ValueError("learned arms require positive training steps")
        optimizer, sampler = new_training_state(model, learning_rate=args.learning_rate, seed=args.seed)
        if (output / "LATEST.json").is_file():
            checkpoint, _ = load_adapter_checkpoint(
                output,
                model=model,
                optimizer=optimizer,
                sampler=sampler,
                expected_identity=identity,
            )
            start_step = int(checkpoint["step"])

        def checkpoint_step(step, current_optimizer, current_sampler, metrics):
            if step % args.save_every == 0:
                save_adapter_checkpoint(
                    output,
                    model=model,
                    optimizer=current_optimizer,
                    sampler=current_sampler,
                    step=step,
                    save_every=args.save_every,
                    identity=identity,
                    metrics=metrics,
                )

        optimizer, sampler, history = train_steps(
            model,
            examples,
            steps=args.steps,
            learning_rate=args.learning_rate,
            seed=args.seed,
            device=torch.device(args.device),
            optimizer=optimizer,
            sampler=sampler,
            start_step=start_step,
            on_step=checkpoint_step,
        )
        final_step = start_step + args.steps
        pointer = save_adapter_checkpoint(
            output,
            model=model,
            optimizer=optimizer,
            sampler=sampler,
            step=final_step,
            save_every=args.save_every,
            identity=identity,
            metrics=history[-1],
        )
    evaluation = validate_evaluation_result(evaluator(model, examples, args.arm))
    checkpoint_bytes = 0 if pointer is None else (output / str(pointer["file"])).stat().st_size
    evaluation["metrics"]["checkpoint_bytes"] = checkpoint_bytes
    atomic_json(output / "EVALUATION.json", evaluation)
    result = {
        "schema": "scbe.prime-token-reader-run.v1",
        "status": "COMPLETE_NO_PROMOTION",
        "contract_id": release["contract_id"],
        "release": release,
        "runtime_config": str(runtime_file),
        "runtime_config_sha256": sha256_file(runtime_file),
        "identity": identity,
        "start_step": start_step,
        "final_step": final_step,
        "checkpoint": pointer,
        "last_training_metrics": history[-1] if history else None,
        "evaluation": evaluation,
        "tool_dispatch": False,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    atomic_json(output / "RUN_RESULT.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--authorization", required=True, type=Path)
    parser.add_argument("--runtime-factory", required=True)
    parser.add_argument("--runtime-config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--arm", required=True, choices=ALL_ARMS)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--steps", required=True, type=int)
    parser.add_argument("--save-every", type=int, default=100)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--device", default="cpu")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.steps < 0 or args.save_every <= 0:
        raise ValueError("steps must be non-negative and save-every positive")
    result = run(args)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
