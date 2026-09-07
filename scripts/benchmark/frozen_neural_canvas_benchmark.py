#!/usr/bin/env python3
"""Measure a fixed untrained canvas on exact toy-LWE coordinate probes.

This benchmark does not train a model and does not attack production keys.  It
projects the same complete central-difference bank through two canvases that
share frozen ternary weights:

* an affine identity-activation control;
* a bounded nonlinear clip activation.

The direct exact residual and a matched random guess remain controls.  Every
coordinate emits three predeclared points (-1, 0, +1); no result determines
which telemetry is collected next.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import statistics
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.crypto import frozen_neural_canvas as C
from src.crypto import toy_lwe_box_field as B

DEFAULT_OUTPUT = Path("docs/research/evidence/frozen_neural_canvas_20260907.json")
CANVAS_SEEDS = (11, 29, 47)


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _basis(width: int) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(int(index == active) for index in range(width)) for active in range(width))


def _energy(layer: tuple[int, ...]) -> int:
    return sum(value * value for value in layer)


def _unique_minimum(scores: dict[int, int]) -> int | None:
    minimum = min(scores.values())
    winners = [candidate for candidate, score in scores.items() if score == minimum]
    return winners[0] if len(winners) == 1 else None


def _candidate(dimension: int, index: int, value: int) -> tuple[int, ...]:
    return tuple(value if coordinate == index else 0 for coordinate in range(dimension))


def _probe_inputs(instance: B.ToyLWEInstance):
    base_candidate = (0,) * instance.dimension
    directions = _basis(instance.dimension)
    positive = tuple(
        B.residual_vector(instance, _candidate(instance.dimension, index, 1)) for index in range(instance.dimension)
    )
    negative = tuple(
        B.residual_vector(instance, _candidate(instance.dimension, index, -1)) for index in range(instance.dimension)
    )
    return directions, B.residual_vector(instance, base_candidate), positive, negative


def _method_row() -> dict[str, int]:
    return {"correct": 0, "emitted": 0, "total": 0}


def _record(bucket: dict[str, int], prediction: int | None, target: int) -> None:
    bucket["total"] += 1
    if prediction is not None:
        bucket["emitted"] += 1
        bucket["correct"] += int(prediction == target)


def _ratio(numerator: int, denominator: int) -> dict[str, int | float | None]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "decimal": numerator / denominator if denominator else None,
    }


def _stats(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(values),
        "population_sd": statistics.pstdev(values),
    }


def run(*, instance_start: int = 10_000, instances: int = 300) -> dict[str, object]:
    if type(instance_start) is not int or instance_start < 0:
        raise ValueError("instance start must be a nonnegative integer")
    if type(instances) is not int or instances < 1:
        raise ValueError("instance count must be a positive integer")

    started = time.perf_counter()
    rows: list[dict[str, object]] = []
    for canvas_seed in CANVAS_SEEDS:
        clipped = C.build_canvas(14, (24, 24), seed=canvas_seed, activation="clip", clip_limit=97)
        linear = C.build_canvas(14, (24, 24), seed=canvas_seed, activation="identity", clip_limit=97)
        if clipped.weight_sha256 != linear.weight_sha256 or clipped.layers != linear.layers:
            raise RuntimeError("matched canvas controls do not share weights")

        methods = {name: _method_row() for name in ("direct_residual", "linear_canvas", "clipped_canvas", "random")}
        random_control = random.Random(canvas_seed + 1_000_003)
        slope_rank = [0] * len(clipped.layers)
        curvature_rank = [0] * len(clipped.layers)
        dead_nodes = [0] * len(clipped.layers)
        state_counts = [Counter() for _ in clipped.layers]
        fixed_forward_calls = 0

        for instance_seed in range(instance_start, instance_start + instances):
            instance = B.generate_toy_lwe(instance_seed, dimension=8, samples=14, modulus=97)
            directions, base_input, positive_inputs, negative_inputs = _probe_inputs(instance)
            receipt = C.probe_triplets(clipped, base_input, directions, positive_inputs, negative_inputs)
            if not C.verify_receipt(receipt):
                raise RuntimeError("canvas response receipt failed verification")
            fixed_forward_calls += receipt.forward_calls

            linear_base = C.forward(linear, base_input)
            linear_positive = tuple(C.forward(linear, value) for value in positive_inputs)
            linear_negative = tuple(C.forward(linear, value) for value in negative_inputs)
            fixed_forward_calls += 1 + len(linear_positive) + len(linear_negative)

            for layer_index, summary in enumerate(receipt.layer_summaries):
                slope_rank[layer_index] += summary.slope_rank
                curvature_rank[layer_index] += summary.curvature_rank
                dead_nodes[layer_index] += summary.dead_nodes
                state_counts[layer_index].update(dict(summary.state_counts))

            for coordinate, target in enumerate(instance.planted_secret or ()):
                candidates = {value: _candidate(instance.dimension, coordinate, value) for value in C.TRITS}
                direct_scores = {value: B.exact_score(instance, candidate) for value, candidate in candidates.items()}
                linear_scores = {
                    -1: _energy(linear_negative[coordinate][-1]),
                    0: _energy(linear_base[-1]),
                    1: _energy(linear_positive[coordinate][-1]),
                }
                clipped_scores = {
                    -1: _energy(receipt.responses[coordinate].negative_layers[-1]),
                    0: _energy(receipt.baseline_layers[-1]),
                    1: _energy(receipt.responses[coordinate].positive_layers[-1]),
                }
                _record(methods["direct_residual"], _unique_minimum(direct_scores), target)
                _record(methods["linear_canvas"], _unique_minimum(linear_scores), target)
                _record(methods["clipped_canvas"], _unique_minimum(clipped_scores), target)
                _record(methods["random"], random_control.choice(C.TRITS), target)

        normalized_methods = {}
        for name, counts in methods.items():
            normalized_methods[name] = {
                **counts,
                "accuracy_all": _ratio(counts["correct"], counts["total"]),
                "accuracy_when_emitted": _ratio(counts["correct"], counts["emitted"]),
                "coverage": _ratio(counts["emitted"], counts["total"]),
            }
        rows.append(
            {
                "canvas_seed": canvas_seed,
                "weight_sha256": clipped.weight_sha256,
                "clipped_canvas_sha256": clipped.canvas_sha256,
                "linear_canvas_sha256": linear.canvas_sha256,
                "instances": instances,
                "coordinate_targets": instances * 8,
                "methods": normalized_methods,
                "mean_slope_rank": [_ratio(value, instances) for value in slope_rank],
                "mean_curvature_rank": [_ratio(value, instances) for value in curvature_rank],
                "mean_dead_nodes": [_ratio(value, instances) for value in dead_nodes],
                "dual_trit_state_counts": [
                    [{"state": state, "count": counts[state]} for state in C.DUAL_TRIT_STATES]
                    for counts in state_counts
                ],
                "fixed_forward_calls": fixed_forward_calls,
            }
        )

    method_names = ("direct_residual", "linear_canvas", "clipped_canvas", "random")
    method_stats = {
        name: _stats([row["methods"][name]["accuracy_all"]["decimal"] for row in rows]) for name in method_names
    }
    clipped = method_stats["clipped_canvas"]
    comparisons = {}
    for control in ("direct_residual", "linear_canvas", "random"):
        reference = method_stats[control]
        pooled_sd = ((clipped["population_sd"] ** 2 + reference["population_sd"] ** 2) / 2) ** 0.5
        difference = clipped["mean"] - reference["mean"]
        comparisons[control] = {
            "mean_accuracy_difference": difference,
            "two_pooled_population_sd": 2 * pooled_sd,
            "exceeds_required_effect": difference > 2 * pooled_sd,
            "wins_every_canvas_seed": all(
                row["methods"]["clipped_canvas"]["accuracy_all"]["decimal"]
                > row["methods"][control]["accuracy_all"]["decimal"]
                for row in rows
            ),
        }
    qualified = all(
        value["exceeds_required_effect"] and value["wins_every_canvas_seed"] for value in comparisons.values()
    )
    strongest_control = max(method_stats[name]["mean"] for name in ("direct_residual", "linear_canvas", "random"))
    if qualified:
        verdict = "CANDIDATE_ADVANTAGE"
    elif clipped["mean"] <= strongest_control:
        verdict = "NO_ADVANTAGE"
    else:
        verdict = "UNDERPOWERED"

    return {
        "schema": "scbe.frozen-neural-canvas-toy-lwe-benchmark.v1",
        "status": verdict,
        "scope": "Fixed untrained response mapping on synthetic toy LWE; no production keys or training.",
        "instance_start": instance_start,
        "instances_per_canvas_seed": instances,
        "canvas_seeds": CANVAS_SEEDS,
        "probe_policy": "all eight coordinate directions, baseline and both signs, fixed before any response",
        "network": {
            "input_width": 14,
            "layer_widths": (24, 24),
            "weights": "deterministic balanced ternary",
            "nonlinear_activation": "integer clip at +/-97",
            "matched_control": "same weights and biases with identity activation",
            "optimizer_steps": 0,
            "learned_readout": False,
            "adaptive_selection": False,
        },
        "rows": rows,
        "aggregate_accuracy": method_stats,
        "comparisons": comparisons,
        "conclusion": (
            "The blank canvas produced a reproducible node-response tensor but did not beat every direct, linear, "
            "and random control under the registered effect rule."
            if not qualified
            else "The blank canvas met the candidate effect gate; independent replication is still required."
        ),
        "elapsed_seconds": time.perf_counter() - started,
        "sources": {
            str(Path(C.__file__).resolve()): _sha256(C.__file__),
            str(Path(B.__file__).resolve()): _sha256(B.__file__),
            str(Path(__file__).resolve()): _sha256(__file__),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-start", type=int, default=10_000)
    parser.add_argument("--instances", type=int, default=300)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(instance_start=args.instance_start, instances=args.instances)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "status": result["status"],
                "aggregate": result["aggregate_accuracy"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
