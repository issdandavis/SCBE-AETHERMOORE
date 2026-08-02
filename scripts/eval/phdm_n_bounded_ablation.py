"""Control-complete ablation for the additive PHDM n-bounded projection.

This is a representation test, not a language-model benchmark. It builds the
complete binary tree at depths 1..4, gives every arm the same seeded path
directions, and measures how well pairwise distances preserve the known tree
metric in the six dimensions used by PHDM.

The candidate must beat both the untouched clamp and a size-matched Euclidean
depth control by more than two pooled standard deviations. Local parent and
sibling retrieval are reported separately so a global-distance gain cannot
hide a zero local gain.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import time
from pathlib import Path
from typing import Callable

import numpy as np

from python.scbe.phdm_embedding import PoincareBall

Distance = Callable[[np.ndarray, np.ndarray], float]
METRICS = (
    "tree_distance_spearman",
    "normalized_stress",
    "parent_top1_accuracy",
    "sibling_top1_accuracy",
)


def binary_tree_paths(max_depth: int) -> list[str]:
    if max_depth < 2:
        raise ValueError("max_depth must be at least 2")
    return [
        "".join(bits)
        for depth in range(1, max_depth + 1)
        for bits in itertools.product(".-", repeat=depth)
    ]


def tree_distance(left: str, right: str) -> int:
    shared = 0
    while shared < min(len(left), len(right)) and left[shared] == right[shared]:
        shared += 1
    return len(left) + len(right) - 2 * shared


def path_directions(
    paths: list[str], dimensions: int, seed: int
) -> tuple[np.ndarray, np.random.Generator]:
    if dimensions < 2:
        raise ValueError("dimensions must be at least 2")
    rng = np.random.default_rng(seed)
    edge_directions: dict[str, np.ndarray] = {}
    directions: list[np.ndarray] = []

    for path in paths:
        direction = np.zeros(dimensions, dtype=np.float64)
        for depth in range(1, len(path) + 1):
            edge = path[:depth]
            if edge not in edge_directions:
                sample = rng.standard_normal(dimensions)
                edge_directions[edge] = sample / np.linalg.norm(sample)
            direction += edge_directions[edge] / depth
        directions.append(direction / np.linalg.norm(direction))

    return np.asarray(directions), rng


def euclidean_distance(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right))


def poincare_distance(left: np.ndarray, right: np.ndarray) -> float:
    left_sq = float(left @ left)
    right_sq = float(right @ right)
    difference_sq = float((left - right) @ (left - right))
    denominator = max((1.0 - left_sq) * (1.0 - right_sq), np.finfo(np.float64).tiny)
    return float(np.arccosh(1.0 + 2.0 * difference_sq / denominator))


def rankdata(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = (start + end - 1) / 2.0 + 1.0
        start = end
    return ranks


def spearman(left: np.ndarray, right: np.ndarray) -> float:
    left_rank = rankdata(left)
    right_rank = rankdata(right)
    left_rank -= left_rank.mean()
    right_rank -= right_rank.mean()
    denominator = math.sqrt(
        float(left_rank @ left_rank) * float(right_rank @ right_rank)
    )
    return float((left_rank @ right_rank) / denominator)


def evaluate(
    paths: list[str],
    points: np.ndarray,
    distance: Distance,
) -> dict[str, float]:
    depths = np.asarray([len(path) for path in paths])
    predicted: list[float] = []
    expected: list[float] = []

    for left in range(len(paths)):
        for right in range(left + 1, len(paths)):
            predicted.append(distance(points[left], points[right]))
            expected.append(float(tree_distance(paths[left], paths[right])))

    predicted_array = np.asarray(predicted)
    expected_array = np.asarray(expected)
    scale = float(
        (predicted_array @ expected_array) / (predicted_array @ predicted_array)
    )
    stress = math.sqrt(
        float(np.sum((scale * predicted_array - expected_array) ** 2))
        / float(np.sum(expected_array**2))
    )

    parent_hits: list[bool] = []
    sibling_hits: list[bool] = []
    path_index = {path: index for index, path in enumerate(paths)}

    for index, path in enumerate(paths):
        if len(path) > 1:
            parent_candidates = np.flatnonzero(depths == len(path) - 1)
            nearest_parent = min(
                parent_candidates,
                key=lambda candidate: (
                    distance(points[index], points[candidate]),
                    paths[candidate],
                ),
            )
            parent_hits.append(paths[nearest_parent] == path[:-1])

        if len(path) > 1:
            sibling = path[:-1] + ("-" if path[-1] == "." else ".")
            same_depth = [
                candidate
                for candidate in np.flatnonzero(depths == len(path))
                if candidate != index
            ]
            nearest_peer = min(
                same_depth,
                key=lambda candidate: (
                    distance(points[index], points[candidate]),
                    paths[candidate],
                ),
            )
            sibling_hits.append(nearest_peer == path_index[sibling])

    return {
        "tree_distance_spearman": spearman(expected_array, predicted_array),
        "normalized_stress": float(stress),
        "parent_top1_accuracy": float(np.mean(parent_hits)),
        "sibling_top1_accuracy": float(np.mean(sibling_hits)),
    }


def build_arms(
    paths: list[str],
    directions: np.ndarray,
    rng: np.random.Generator,
    ball: PoincareBall,
) -> dict[str, tuple[np.ndarray, Distance]]:
    depths = np.asarray([len(path) for path in paths], dtype=np.float64)
    mean_depth = float(depths.mean())
    shuffled_depths = rng.permutation(depths)

    n_bounded = np.asarray(
        [
            ball.embed_n_bounded(direction, depth)
            for direction, depth in zip(directions, depths, strict=True)
        ]
    )

    return {
        "primary_clamp_hyperbolic": (
            np.asarray([ball.embed(direction * 2.0) for direction in directions]),
            poincare_distance,
        ),
        "matched_fixed_hyperbolic": (
            directions * ball.n_bounded_radius(mean_depth),
            poincare_distance,
        ),
        "n_bounded_hyperbolic": (n_bounded, poincare_distance),
        "n_bounded_euclidean": (n_bounded, euclidean_distance),
        "linear_depth_euclidean": (
            directions * (depths[:, None] / (depths.max() + 1.0)),
            euclidean_distance,
        ),
        "shuffled_depth_hyperbolic": (
            np.asarray(
                [
                    ball.embed_n_bounded(direction, depth)
                    for direction, depth in zip(
                        directions, shuffled_depths, strict=True
                    )
                ]
            ),
            poincare_distance,
        ),
    }


def summarize(rows: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    return {
        metric: {
            "mean": float(np.mean([row[metric] for row in rows])),
            "sample_sd": float(np.std([row[metric] for row in rows], ddof=1)),
        }
        for metric in METRICS
    }


def gate(
    candidate: dict[str, dict[str, float]],
    control: dict[str, dict[str, float]],
    metric: str,
) -> dict[str, float | str]:
    higher_is_better = metric != "normalized_stress"
    candidate_mean = candidate[metric]["mean"]
    control_mean = control[metric]["mean"]
    gain = candidate_mean - control_mean
    if not higher_is_better:
        gain = -gain

    pooled_sd = math.sqrt(
        (candidate[metric]["sample_sd"] ** 2 + control[metric]["sample_sd"] ** 2) / 2.0
    )
    threshold = 2.0 * pooled_sd
    if gain > threshold:
        verdict = "PASS"
    elif gain < 0.0:
        verdict = "REGRESSION"
    else:
        verdict = "UNDERPOWERED"
    return {
        "gain": float(gain),
        "two_pooled_sd": float(threshold),
        "verdict": verdict,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_ablation(
    *,
    seeds: int = 100,
    seed_start: int = 0,
    dimensions: int = 6,
    max_depth: int = 4,
) -> dict:
    if seeds < 3:
        raise ValueError("at least three seeds are required")

    started = time.perf_counter()
    paths = binary_tree_paths(max_depth)
    ball = PoincareBall()
    raw: dict[str, list[dict[str, float]]] = {}

    for seed in range(seed_start, seed_start + seeds):
        directions, rng = path_directions(paths, dimensions, seed)
        for arm, (points, distance) in build_arms(paths, directions, rng, ball).items():
            raw.setdefault(arm, []).append(evaluate(paths, points, distance))

    summaries = {arm: summarize(rows) for arm, rows in raw.items()}
    candidate = summaries["n_bounded_hyperbolic"]
    controls = (
        "primary_clamp_hyperbolic",
        "matched_fixed_hyperbolic",
        "n_bounded_euclidean",
        "linear_depth_euclidean",
        "shuffled_depth_hyperbolic",
    )
    comparisons = {
        control: {
            metric: gate(candidate, summaries[control], metric) for metric in METRICS
        }
        for control in controls
    }

    script_path = Path(__file__).resolve()
    projection_path = Path(PoincareBall.__module__.replace(".", "/") + ".py")
    if not projection_path.exists():
        projection_path = (
            script_path.parents[2] / "python" / "scbe" / "phdm_embedding.py"
        )

    return {
        "schema": "scbe.phdm-n-bounded-additive-ablation.v1",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": {
            "seeds": seeds,
            "seed_start": seed_start,
            "dimensions": dimensions,
            "max_depth": max_depth,
            "nodes": len(paths),
            "gate": "gain > 2 * pooled sample standard deviation",
        },
        "source": {
            "dataset": "complete synthetic binary tree; no Morse labels or task labels",
            "script": str(script_path),
            "script_sha256": sha256_file(script_path),
            "projection_module": str(projection_path.resolve()),
            "projection_sha256": sha256_file(projection_path),
        },
        "arms": summaries,
        "comparisons": comparisons,
        "boundaries": [
            "This measures representation geometry, not Clay language-model capability.",
            "Every arm receives identical seeded path directions.",
            "Depth is structural input; tasks without an honest depth source cannot use the candidate without leakage.",
            "Parent and sibling retrieval are reported separately from global tree-distance preservation.",
        ],
        "elapsed_seconds": float(time.perf_counter() - started),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--dimensions", type=int, default=6)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = run_ablation(
        seeds=args.seeds,
        seed_start=args.seed_start,
        dimensions=args.dimensions,
        max_depth=args.max_depth,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(args.output)
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
