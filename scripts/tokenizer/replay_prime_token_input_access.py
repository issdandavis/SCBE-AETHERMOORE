#!/usr/bin/env python3
"""Independently rebuild packets and replay one prime-token adapter lineage."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys

import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.prime_token_independent_replay import (
    load_adapter_read_only,
    reconstruct_packet_independently,
    replay_predictions,
    verify_replay_ledger,
)
from python.scbe.prime_token_input_access import FullSystemPrimeTokenInputAccessLM
from python.scbe.prime_token_training import atomic_json, sha256_file


def _factory(spec: str):
    if spec.count(":") != 1:
        raise ValueError("runtime factory must use module:function syntax")
    module_name, function_name = spec.split(":", 1)
    function = getattr(importlib.import_module(module_name), function_name)
    if not callable(function):
        raise TypeError("runtime factory target is not callable")
    return function


def run(args: argparse.Namespace) -> dict[str, object]:
    runtime_file = args.runtime_config.resolve(strict=True)
    runtime_config = json.loads(runtime_file.read_text(encoding="utf-8"))
    payload = _factory(args.runtime_factory)(runtime_config)
    if not isinstance(payload, dict):
        raise TypeError("replay runtime factory must return a dictionary")
    model = payload.get("model")
    identity = payload.get("identity")
    cases = payload.get("replay_cases")
    if not isinstance(model, FullSystemPrimeTokenInputAccessLM):
        raise TypeError("replay factory returned the wrong model type")
    if not isinstance(identity, dict) or not isinstance(cases, list) or not cases:
        raise TypeError("replay factory omitted identity or replay cases")
    checkpoint = load_adapter_read_only(args.checkpoint_dir, model=model, expected_identity=identity)
    outcomes = []
    for index, case in enumerate(cases):
        packet = reconstruct_packet_independently(
            case["records"],
            case["owner_positions"],
            sequence_length=int(case["sequence_length"]),
            mode=str(case["mode"]),
            frame=str(case.get("frame", "lexical")),
        )
        replay = replay_predictions(
            model,
            torch.as_tensor(case["token_ids"], dtype=torch.long),
            torch.as_tensor(case["targets"], dtype=torch.long),
            packet,
        )
        expected = case.get("producer_ledger")
        if expected:
            verify_replay_ledger(expected, replay)
        outcomes.append({"case": index, **replay})
    total = sum(int(item["example_count"]) for item in outcomes)
    correct = sum(int(item["correct_count"]) for item in outcomes)
    result = {
        "schema": "scbe.prime-token-independent-replay-run.v1",
        "status": "VERIFIED_REPLAY_NO_PROMOTION",
        "runtime_config": str(runtime_file),
        "runtime_config_sha256": sha256_file(runtime_file),
        "checkpoint": checkpoint,
        "case_count": len(outcomes),
        "example_count": total,
        "correct_count": correct,
        "accuracy": correct / total if total else 0.0,
        "cases": outcomes,
        "producer_metrics_ignored": True,
        "tool_dispatch": False,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    atomic_json(args.output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-factory", required=True)
    parser.add_argument("--runtime-config", required=True, type=Path)
    parser.add_argument("--checkpoint-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    result = run(parser.parse_args())
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
