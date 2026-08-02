"""Additive PHDM projection ablation on real SCBE Python ASTs.

Depth comes from Python AST traversal, not a risk label or expected decision.
Node direction excludes depth, parent, path, source location, and child index.
It is built from node type, six face trits, and a token digest, then projected
to the six dimensions used by PHDM. Small seeded noise prevents duplicate
feature rows from inheriting a favorable pre-order tie break.

Task: rank the true parent of every non-root node against every other node in
the same bounded file prefix. Report MRR, Recall@1, and Recall@5. The candidate
must beat the untouched clamp, no-depth flat baseline, shuffled-depth control,
and size-matched Euclidean depth control by more than two pooled sample standard
deviations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np

from python.scbe.cube_stereo import stereo_encode
from python.scbe.phdm_embedding import PoincareBall
from scripts.eval.phdm_n_bounded_ablation import gate, sha256_file

ROOT = Path(__file__).resolve().parents[2]
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
METRICS = ("parent_mrr", "parent_recall_at_1", "parent_recall_at_5")


def corpus(file_limit: int = 20) -> list[Path]:
    files = sorted((ROOT / "python" / "scbe").glob("*.py"))
    files = [path for path in files if path.name != "__init__.py"]
    return files[:file_limit]


def digest_features(token: object, width: int = 8) -> np.ndarray:
    digest = hashlib.sha256(str(token).encode("utf-8", "replace")).digest()[:width]
    return np.asarray(list(digest), dtype=np.float64) / 127.5 - 1.0


def load_nodes(files: list[Path], node_cap: int) -> list[dict]:
    loaded: list[dict] = []
    for path in files:
        source = path.read_text(encoding="utf-8", errors="surrogatepass")
        tokens = stereo_encode(source)["tokens"][:node_cap]
        loaded.append(
            {
                "path": path,
                "tokens": tokens,
                "sha256": sha256_file(path),
            }
        )
    return loaded


def feature_matrix(
    tokens: list[dict], type_index: dict[str, int]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    type_width = len(type_index)
    matrix = np.zeros((len(tokens), type_width + len(TONGUES) + 8), dtype=np.float64)
    parents: list[int] = []
    depths: list[float] = []

    for index, token in enumerate(tokens):
        matrix[index, type_index[token["node_type"]]] = 1.0
        matrix[index, type_width : type_width + len(TONGUES)] = [
            token["lens_b_faces"][tongue] for tongue in TONGUES
        ]
        matrix[index, type_width + len(TONGUES) :] = digest_features(token["token"])
        parent = token["lens_a_relation"]["parent"]
        parents.append(-1 if parent is None else int(parent))
        depths.append(float(token["lens_a_relation"]["depth"]))

    return matrix, np.asarray(parents), np.asarray(depths)


def pairwise_euclidean(points: np.ndarray) -> np.ndarray:
    norms = np.sum(points * points, axis=1)
    squared = np.maximum(norms[:, None] + norms[None, :] - 2.0 * points @ points.T, 0.0)
    return np.sqrt(squared)


def pairwise_poincare(points: np.ndarray) -> np.ndarray:
    norms = np.sum(points * points, axis=1)
    differences = np.maximum(
        norms[:, None] + norms[None, :] - 2.0 * points @ points.T, 0.0
    )
    denominator = np.maximum(
        (1.0 - norms)[:, None] * (1.0 - norms)[None, :],
        np.finfo(np.float64).tiny,
    )
    return np.arccosh(1.0 + 2.0 * differences / denominator)


def parent_metrics(distances: np.ndarray, parents: np.ndarray) -> dict[str, float]:
    ranks: list[int] = []
    for child, parent in enumerate(parents):
        if parent < 0 or parent >= len(parents):
            continue
        row = distances[child].copy()
        row[child] = np.inf
        target = row[parent]
        lower = int(np.sum(row < target))
        tied_before = int(
            np.sum(
                (row == target)
                & (np.arange(len(row)) < parent)
                & (np.arange(len(row)) != child)
            )
        )
        ranks.append(1 + lower + tied_before)

    rank_array = np.asarray(ranks)
    return {
        "parent_mrr": float(np.mean(1.0 / rank_array)),
        "parent_recall_at_1": float(np.mean(rank_array <= 1)),
        "parent_recall_at_5": float(np.mean(rank_array <= 5)),
    }


def summarize(rows: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    return {
        metric: {
            "mean": float(np.mean([row[metric] for row in rows])),
            "sample_sd": float(np.std([row[metric] for row in rows], ddof=1)),
        }
        for metric in METRICS
    }


def run_ablation(
    *,
    seeds: int = 20,
    seed_start: int = 0,
    dimensions: int = 6,
    file_limit: int = 20,
    node_cap: int = 256,
    noise_scale: float = 0.01,
) -> dict:
    if seeds < 3:
        raise ValueError("at least three seeds are required")
    if dimensions != 6:
        raise ValueError("this ablation is pinned to PHDM's six hyperbolic dimensions")
    if file_limit < 1 or node_cap < 2:
        raise ValueError("file_limit must be positive and node_cap must be at least 2")

    started = time.perf_counter()
    files = corpus(file_limit)
    loaded = load_nodes(files, node_cap)
    node_types = sorted(
        {token["node_type"] for item in loaded for token in item["tokens"]}
    )
    type_index = {node_type: index for index, node_type in enumerate(node_types)}
    feature_width = len(type_index) + len(TONGUES) + 8
    ball = PoincareBall()
    raw: dict[str, list[dict[str, float]]] = {}

    for seed in range(seed_start, seed_start + seeds):
        rng = np.random.default_rng(seed)
        projection = rng.standard_normal((feature_width, dimensions)) / math.sqrt(
            feature_width
        )
        per_file: dict[str, list[dict[str, float]]] = {}

        for item in loaded:
            features, parents, depths = feature_matrix(item["tokens"], type_index)
            directions = features @ projection
            directions += rng.normal(scale=noise_scale, size=directions.shape)
            direction_norms = np.linalg.norm(directions, axis=1, keepdims=True)
            if np.any(direction_norms == 0.0):
                raise ValueError("feature projection produced a zero direction")
            directions /= direction_norms

            shuffled_depths = rng.permutation(depths)
            n_bounded = np.asarray(
                [
                    ball.embed_n_bounded(direction, depth + 1.0)
                    for direction, depth in zip(directions, depths, strict=True)
                ]
            )
            arms = {
                "flat_euclidean": pairwise_euclidean(directions),
                "primary_clamp_hyperbolic": pairwise_poincare(
                    np.asarray(
                        [ball.embed(direction * 2.0) for direction in directions]
                    )
                ),
                "n_bounded_hyperbolic": pairwise_poincare(n_bounded),
                "n_bounded_euclidean": pairwise_euclidean(n_bounded),
                "linear_depth_euclidean": pairwise_euclidean(
                    directions * ((depths + 1.0) / (depths.max() + 2.0))[:, None]
                ),
                "shuffled_depth_hyperbolic": pairwise_poincare(
                    np.asarray(
                        [
                            ball.embed_n_bounded(direction, depth + 1.0)
                            for direction, depth in zip(
                                directions, shuffled_depths, strict=True
                            )
                        ]
                    )
                ),
            }
            for arm, distances in arms.items():
                per_file.setdefault(arm, []).append(parent_metrics(distances, parents))

        for arm, file_rows in per_file.items():
            raw.setdefault(arm, []).append(
                {
                    metric: float(np.mean([row[metric] for row in file_rows]))
                    for metric in METRICS
                }
            )

    summaries = {arm: summarize(rows) for arm, rows in raw.items()}
    candidate = summaries["n_bounded_hyperbolic"]
    controls = (
        "flat_euclidean",
        "primary_clamp_hyperbolic",
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

    random_rows = []
    for item in loaded:
        candidates = max(len(item["tokens"]) - 1, 1)
        harmonic = sum(1.0 / rank for rank in range(1, candidates + 1))
        random_rows.append(
            {
                "parent_mrr": harmonic / candidates,
                "parent_recall_at_1": 1.0 / candidates,
                "parent_recall_at_5": min(5.0 / candidates, 1.0),
            }
        )

    return {
        "schema": "scbe.phdm-ast-parent-additive-ablation.v1",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": {
            "seeds": seeds,
            "seed_start": seed_start,
            "dimensions": dimensions,
            "file_limit": file_limit,
            "node_cap_per_file": node_cap,
            "noise_scale": noise_scale,
            "feature_width": feature_width,
            "gate": "gain > 2 * pooled sample standard deviation",
        },
        "corpus": [
            {
                "path": str(item["path"].relative_to(ROOT)),
                "sha256": item["sha256"],
                "nodes": len(item["tokens"]),
            }
            for item in loaded
        ],
        "features": {
            "included": [
                "node_type_one_hot",
                "six_face_trits",
                "token_sha256_first_8_bytes",
            ],
            "excluded": [
                "depth",
                "parent",
                "path",
                "location",
                "child_index",
                "source_index",
            ],
        },
        "random_rank_baseline": {
            metric: float(np.mean([row[metric] for row in random_rows]))
            for metric in METRICS
        },
        "arms": summaries,
        "comparisons": comparisons,
        "boundaries": [
            "This is structural-address retrieval, not a Clay language-model or governance benchmark.",
            "Absolute retrieval scores remain visible; relative gain does not imply useful standalone accuracy.",
            "AST traversal supplies honest depth. GitHub PR text currently has no equivalent non-leaking depth source.",
            "All arms receive the same feature directions and seeded perturbations.",
        ],
        "source": {
            "script": str(Path(__file__).resolve()),
            "script_sha256": sha256_file(Path(__file__).resolve()),
            "projection_module": str(
                (ROOT / "python" / "scbe" / "phdm_embedding.py").resolve()
            ),
            "projection_sha256": sha256_file(
                ROOT / "python" / "scbe" / "phdm_embedding.py"
            ),
        },
        "elapsed_seconds": float(time.perf_counter() - started),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--dimensions", type=int, default=6)
    parser.add_argument("--file-limit", type=int, default=20)
    parser.add_argument("--node-cap", type=int, default=256)
    parser.add_argument("--noise-scale", type=float, default=0.01)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = run_ablation(
        seeds=args.seeds,
        seed_start=args.seed_start,
        dimensions=args.dimensions,
        file_limit=args.file_limit,
        node_cap=args.node_cap,
        noise_scale=args.noise_scale,
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
