"""Matched-control benchmark for Kaprekar mirror topology features.

The primary task is route consistency. Given a source state and a destination
at a lower convergence depth, predict whether the destination is on the
source's future Kaprekar path. Positive and negative destinations are matched
by basin and depth.

This is a shadow-lane measurement. It does not promote features into Clay.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Iterable, Sequence

import numpy as np

from .kaprekar_mirror_dataset import build_records

CONDITIONS = (
    "raw",
    "digit_stats",
    "random_shell",
    "shuffled_depth",
    "primary",
    "primary_random_pad",
    "mirror",
)
DEFAULT_SEEDS = (7, 2024, 6174)
FEATURE_DIM = 20
PAIR_FEATURE_DIM = FEATURE_DIM * 4
RIDGE_ALPHA = 1.0
MIN_RELATIVE_GAIN = 0.05


def _stable_digest(seed: int, namespace: str, value: str) -> bytes:
    return hashlib.sha256(f"{seed}:{namespace}:{value}".encode("ascii")).digest()


def _stable_index(seed: int, namespace: str, value: str, size: int) -> int:
    if size < 1:
        raise ValueError("size must be positive")
    return int.from_bytes(_stable_digest(seed, namespace, value)[:8], "big") % size


def _stable_unit(seed: int, namespace: str, value: str) -> float:
    numerator = int.from_bytes(_stable_digest(seed, namespace, value)[:8], "big")
    return 2.0 * numerator / float((1 << 64) - 1) - 1.0


class FeatureBuilder:
    """Build fixed-width feature arms without reading record labels."""

    def __init__(self, records: Sequence[dict[str, Any]], *, seed: int) -> None:
        if any(int(record["width"]) != 4 for record in records):
            raise ValueError("the benchmark feature contract requires four-digit records")
        self.records = tuple(records)
        self.seed = seed
        self.by_state = {str(record["state"]): record for record in records}
        self.depth_donors = self._build_depth_donors()

    def _build_depth_donors(self) -> dict[str, str]:
        by_split: dict[str, list[str]] = defaultdict(list)
        for record in self.records:
            by_split[str(record["split"])].append(str(record["state"]))

        donors: dict[str, str] = {}
        for split, states in sorted(by_split.items()):
            ordered = sorted(
                states,
                key=lambda state: _stable_digest(self.seed, f"depth-donor:{split}", state),
            )
            rotated = ordered[1:] + ordered[:1]
            donors.update(zip(ordered, rotated))
        return donors

    def vector(self, record: dict[str, Any], condition: str) -> np.ndarray:
        if condition not in CONDITIONS:
            raise ValueError(f"unknown condition: {condition}")

        state = str(record["state"])
        digits = [int(char) for char in state]
        sorted_digits = sorted(digits)
        vector = np.zeros(FEATURE_DIM, dtype=float)
        vector[0:4] = np.asarray(digits, dtype=float) / 9.0

        if condition == "raw":
            return vector

        vector[4:8] = np.asarray(sorted_digits, dtype=float) / 9.0
        vector[8] = sum(digits) / 36.0
        vector[9] = len(set(digits)) / 4.0
        if condition == "digit_stats":
            return vector

        view = record["auxiliary_view"]
        if condition == "random_shell":
            shell = _stable_index(self.seed, "random-shell", state, 8)
            vector[10] = shell / 7.0
            vector[11] = 0.75 * math.tanh(0.5 * shell / 2.0)
            for index in range(12, FEATURE_DIM):
                vector[index] = _stable_unit(
                    self.seed,
                    f"random-feature:{index}",
                    state,
                )
            return vector

        if condition == "shuffled_depth":
            donor = self.by_state[self.depth_donors[state]]
            donor_view = donor["auxiliary_view"]
            vector[10] = float(donor_view["primary_depth"]) / 7.0
            vector[11] = float(donor_view["primary_radial_depth"])
            return vector

        vector[10] = float(view["primary_depth"]) / 7.0
        vector[11] = float(view["primary_radial_depth"])
        vector[12:15] = np.asarray(view["primary_point"], dtype=float)
        if condition == "primary":
            return vector
        if condition == "primary_random_pad":
            for index in range(15, FEATURE_DIM):
                vector[index] = _stable_unit(
                    self.seed,
                    f"primary-random-pad:{index}",
                    state,
                )
            return vector

        vector[15:18] = np.asarray(view["mirror_point"], dtype=float)
        vector[18] = float(bool(view["is_mirror_seam"]))
        vector[19] = int(str(view["mirror_pair_id"])) / 9_999.0
        return vector


def _pair_vector(
    builder: FeatureBuilder,
    source: dict[str, Any],
    destination: dict[str, Any],
    condition: str,
) -> np.ndarray:
    source_vector = builder.vector(source, condition)
    destination_vector = builder.vector(destination, condition)
    return np.concatenate(
        (
            source_vector,
            destination_vector,
            np.abs(source_vector - destination_vector),
            source_vector * destination_vector,
        )
    )


def build_route_pairs(
    records: Sequence[dict[str, Any]],
    *,
    seed: int,
) -> list[dict[str, Any]]:
    """Build balanced path-membership pairs matched on basin and depth."""

    by_state = {str(record["state"]): record for record in records}
    by_depth: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record["is_repdigit"]:
            continue
        view = record["auxiliary_view"]
        by_depth[(str(view["primary_bottom"]), int(view["primary_depth"]))].append(record)

    pairs: list[dict[str, Any]] = []
    for source in records:
        if source["is_repdigit"]:
            continue

        path = tuple(str(state) for state in source["audit"]["primary_path"])
        source_depth = int(source["auxiliary_view"]["primary_depth"])
        if source_depth < 2:
            continue

        offset = 1 + _stable_index(
            seed,
            "positive-offset",
            str(source["state"]),
            source_depth - 1,
        )
        positive_state = path[offset]
        positive = by_state[positive_state]
        target_depth = int(positive["auxiliary_view"]["primary_depth"])
        basin = str(positive["auxiliary_view"]["primary_bottom"])
        negative_candidates = [
            candidate
            for candidate in by_depth[(basin, target_depth)]
            if str(candidate["state"]) not in path and str(candidate["family_id"]) != str(source["family_id"])
        ]
        if not negative_candidates:
            continue
        negative = negative_candidates[
            _stable_index(
                seed,
                "negative-destination",
                str(source["state"]),
                len(negative_candidates),
            )
        ]

        common = {
            "source": source,
            "source_family": str(source["family_id"]),
            "split": str(source["split"]),
            "target_depth": target_depth,
            "basin": basin,
        }
        pairs.append({**common, "destination": positive, "label": 1})
        pairs.append({**common, "destination": negative, "label": 0})

    return pairs


def assert_route_pair_contract(pairs: Iterable[dict[str, Any]]) -> None:
    """Check balance, family grouping, and matched negative construction."""

    labels_by_source: dict[str, list[int]] = defaultdict(list)
    destinations_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in pairs:
        source = pair["source"]
        destination = pair["destination"]
        assert str(pair["source_family"]) == str(source["family_id"])
        assert str(pair["split"]) == str(source["split"])
        assert int(pair["target_depth"]) == int(destination["auxiliary_view"]["primary_depth"])
        assert str(pair["basin"]) == str(destination["auxiliary_view"]["primary_bottom"])
        state = str(source["state"])
        labels_by_source[state].append(int(pair["label"]))
        destinations_by_source[state].append(destination)

    if not labels_by_source:
        raise ValueError("route-pair builder produced no examples")
    if any(sorted(labels) != [0, 1] for labels in labels_by_source.values()):
        raise ValueError("each route source must have one positive and one negative")
    if any(len(destinations) != 2 for destinations in destinations_by_source.values()):
        raise ValueError("each route source must have two destinations")


def _fit_ridge(
    train_x: np.ndarray,
    train_y: np.ndarray,
    *,
    alpha: float = RIDGE_ALPHA,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    feature_mean = train_x.mean(axis=0)
    feature_scale = train_x.std(axis=0)
    feature_scale = np.where(feature_scale < 1e-12, 1.0, feature_scale)
    normalized = (train_x - feature_mean) / feature_scale
    design = np.column_stack((normalized, np.ones(len(normalized))))
    gram = design.T @ design
    regularizer = np.eye(gram.shape[0], dtype=float) * alpha
    regularizer[-1, -1] = 0.0
    weights = np.linalg.solve(gram + regularizer, design.T @ train_y)
    return weights, feature_mean, feature_scale


def _predict_ridge(
    test_x: np.ndarray,
    model: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> np.ndarray:
    weights, feature_mean, feature_scale = model
    normalized = (test_x - feature_mean) / feature_scale
    design = np.column_stack((normalized, np.ones(len(normalized))))
    return design @ weights


def _f1_score(labels: np.ndarray, predictions: np.ndarray) -> float:
    true_positive = int(np.sum((labels == 1) & (predictions == 1)))
    false_positive = int(np.sum((labels == 0) & (predictions == 1)))
    false_negative = int(np.sum((labels == 1) & (predictions == 0)))
    denominator = 2 * true_positive + false_positive + false_negative
    return 0.0 if denominator == 0 else 2.0 * true_positive / denominator


def _condition_metrics(
    records: Sequence[dict[str, Any]],
    route_pairs: Sequence[dict[str, Any]],
    *,
    seed: int,
    condition: str,
) -> dict[str, float | int | str]:
    builder = FeatureBuilder(records, seed=seed)
    train_pairs = [pair for pair in route_pairs if pair["split"] == "train"]
    test_pairs = [pair for pair in route_pairs if pair["split"] == "test"]
    if not train_pairs or not test_pairs:
        raise ValueError("family split produced an empty route train or test set")

    train_route_x = np.vstack(
        [_pair_vector(builder, pair["source"], pair["destination"], condition) for pair in train_pairs]
    )
    test_route_x = np.vstack(
        [_pair_vector(builder, pair["source"], pair["destination"], condition) for pair in test_pairs]
    )
    train_route_y = np.asarray([pair["label"] for pair in train_pairs], dtype=float)
    test_route_y = np.asarray([pair["label"] for pair in test_pairs], dtype=int)
    route_model = _fit_ridge(train_route_x, train_route_y)
    route_scores = _predict_ridge(test_route_x, route_model)
    route_predictions = (route_scores >= 0.5).astype(int)

    train_records = [record for record in records if record["split"] == "train" and not record["is_repdigit"]]
    test_records = [record for record in records if record["split"] == "test" and not record["is_repdigit"]]
    train_transition_x = np.vstack([builder.vector(record, condition) for record in train_records])
    test_transition_x = np.vstack([builder.vector(record, condition) for record in test_records])
    denominator = float(10 ** int(records[0]["width"]) - 1)
    train_transition_y = np.asarray(
        [int(record["labels"]["primary_next_state"]) / denominator for record in train_records],
        dtype=float,
    )
    test_transition_y = np.asarray(
        [int(record["labels"]["primary_next_state"]) / denominator for record in test_records],
        dtype=float,
    )
    transition_model = _fit_ridge(train_transition_x, train_transition_y)
    transition_predictions = np.clip(
        _predict_ridge(test_transition_x, transition_model),
        0.0,
        1.0,
    )
    transition_exact = np.rint(transition_predictions * denominator).astype(int) == np.rint(
        test_transition_y * denominator
    ).astype(int)

    return {
        "seed": seed,
        "condition": condition,
        "feature_dim": FEATURE_DIM,
        "pair_feature_dim": PAIR_FEATURE_DIM,
        "route_train_rows": len(train_pairs),
        "route_test_rows": len(test_pairs),
        "route_accuracy": float(np.mean(route_predictions == test_route_y)),
        "route_f1": _f1_score(test_route_y, route_predictions),
        "transition_test_rows": len(test_records),
        "transition_mae": float(np.mean(np.abs(transition_predictions - test_transition_y))),
        "transition_exact": float(np.mean(transition_exact)),
    }


def _aggregate(
    results: Sequence[dict[str, float | int | str]],
) -> dict[str, dict[str, dict[str, Any]]]:
    aggregate: dict[str, dict[str, dict[str, Any]]] = {}
    for condition in CONDITIONS:
        rows = [result for result in results if result["condition"] == condition]
        condition_metrics: dict[str, dict[str, Any]] = {}
        for metric in (
            "route_accuracy",
            "route_f1",
            "transition_mae",
            "transition_exact",
        ):
            values = [float(row[metric]) for row in rows]
            condition_metrics[metric] = {
                "values": values,
                "mean": mean(values),
                "sd": stdev(values) if len(values) > 1 else 0.0,
            }
        aggregate[condition] = condition_metrics
    return aggregate


def _pooled_sd(left: Sequence[float], right: Sequence[float]) -> float:
    left_sd = stdev(left) if len(left) > 1 else 0.0
    right_sd = stdev(right) if len(right) > 1 else 0.0
    return math.sqrt((left_sd * left_sd + right_sd * right_sd) / 2.0)


def _lower_is_better_gate(
    candidate: Sequence[float],
    control: Sequence[float],
) -> dict[str, Any]:
    candidate_mean = mean(candidate)
    control_mean = mean(control)
    delta = control_mean - candidate_mean
    pooled_sd = _pooled_sd(candidate, control)
    relative_bar = MIN_RELATIVE_GAIN * abs(control_mean)
    noise_bar = 2.0 * pooled_sd
    binding_bar = max(relative_bar, noise_bar)
    paired_improvements = [
        control_value - candidate_value for candidate_value, control_value in zip(candidate, control)
    ]
    return {
        "candidate_mean": candidate_mean,
        "control_mean": control_mean,
        "absolute_improvement": delta,
        "relative_improvement": (0.0 if control_mean == 0.0 else delta / abs(control_mean)),
        "pooled_sd": pooled_sd,
        "relative_bar": relative_bar,
        "noise_bar": noise_bar,
        "binding_bar": binding_bar,
        "all_seeds_improve": all(value > 0.0 for value in paired_improvements),
        "paired_improvements": paired_improvements,
        "passed": delta >= binding_bar and all(value > 0.0 for value in paired_improvements),
    }


def apply_promotion_gate(
    aggregate: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    """Require mirror route-error lift over no-topology and strongest controls."""

    candidate_errors = [1.0 - value for value in aggregate["mirror"]["route_f1"]["values"]]
    control_names = (
        "raw",
        "digit_stats",
        "random_shell",
        "shuffled_depth",
        "primary",
        "primary_random_pad",
    )
    control_errors = {
        condition: [1.0 - value for value in aggregate[condition]["route_f1"]["values"]] for condition in control_names
    }
    strongest_control = min(control_names, key=lambda name: mean(control_errors[name]))
    comparisons = {
        "digit_stats": _lower_is_better_gate(
            candidate_errors,
            control_errors["digit_stats"],
        ),
        "strongest_control": {
            "name": strongest_control,
            **_lower_is_better_gate(
                candidate_errors,
                control_errors[strongest_control],
            ),
        },
    }

    candidate_transition = aggregate["mirror"]["transition_mae"]["values"]
    baseline_transition = aggregate["digit_stats"]["transition_mae"]["values"]
    transition_pooled_sd = _pooled_sd(candidate_transition, baseline_transition)
    transition_degradation = mean(candidate_transition) - mean(baseline_transition)
    transition_tolerance = max(
        0.01 * abs(mean(baseline_transition)),
        2.0 * transition_pooled_sd,
    )
    transition_guard = {
        "candidate_mean": mean(candidate_transition),
        "baseline_mean": mean(baseline_transition),
        "degradation": transition_degradation,
        "tolerance": transition_tolerance,
        "passed": transition_degradation <= transition_tolerance,
    }

    qualified = (
        comparisons["digit_stats"]["passed"]
        and comparisons["strongest_control"]["passed"]
        and transition_guard["passed"]
    )
    positive_lift = (
        comparisons["digit_stats"]["absolute_improvement"] > 0.0
        and comparisons["strongest_control"]["absolute_improvement"] > 0.0
    )
    status = "QUALIFIED" if qualified else ("UNDERPOWERED" if positive_lift else "NO_LIFT")
    return {
        "status": status,
        "qualified": qualified,
        "primary_metric": "route_error = 1 - route_f1",
        "minimum_relative_gain": MIN_RELATIVE_GAIN,
        "comparisons": comparisons,
        "transition_guard": transition_guard,
        "consistency_note": ("All-seed direction is a consistency filter only; it is not significance evidence."),
    }


def run_benchmark(
    *,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    width: int = 4,
) -> dict[str, Any]:
    if len(seeds) < 3:
        raise ValueError("at least three seeds are required")
    if width != 4:
        raise ValueError("the 6174 benchmark is defined only for four-digit states")

    results: list[dict[str, float | int | str]] = []
    pair_counts: dict[str, int] = {}
    for seed in seeds:
        records = build_records(
            width=width,
            split_seed=seed,
            include_repdigits=True,
        )
        route_pairs = build_route_pairs(records, seed=seed)
        assert_route_pair_contract(route_pairs)
        pair_counts[str(seed)] = len(route_pairs)
        for condition in CONDITIONS:
            results.append(
                _condition_metrics(
                    records,
                    route_pairs,
                    seed=seed,
                    condition=condition,
                )
            )

    aggregate = _aggregate(results)
    gate = apply_promotion_gate(aggregate)
    return {
        "schema_version": "kaprekar_mirror_benchmark_report_v1",
        "seeds": list(seeds),
        "width": width,
        "conditions": list(CONDITIONS),
        "feature_dim": FEATURE_DIM,
        "pair_feature_dim": PAIR_FEATURE_DIM,
        "ridge_alpha": RIDGE_ALPHA,
        "split_contract": "source permutation families are disjoint across train/validation/test",
        "feature_access_contract": (
            "features use state and auxiliary_view only; labels and audit trajectories are excluded"
        ),
        "route_pair_contract": ("one positive and one negative per source; destination basin and depth are matched"),
        "pair_counts": pair_counts,
        "results": results,
        "aggregate": aggregate,
        "promotion_gate": gate,
        "claim_boundary": (
            "Synthetic fixed-width decimal benchmark only. Qualification permits a Clay shadow "
            "auxiliary view, not governance authority or a general topology claim."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="7,2024,6174")
    parser.add_argument("--width", type=int, default=4)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    seeds = tuple(int(part.strip()) for part in args.seeds.split(",") if part.strip())
    report = run_benchmark(seeds=seeds, width=args.width)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.output is None:
        print(payload)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8", newline="\n")
    return 0 if report["promotion_gate"]["qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
