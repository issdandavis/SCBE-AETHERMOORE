"""Compare prime fog search upgrades against frozen gates.

This script adds a small set of standard search-system moves around the
hand-built prime fog channels:

* learned linear/centroid ranker over current-window features
* shallow decision-tree ranker
* tree-leaf branch extraction back into an algebraic gate
* two-stage candidate generation plus reranking
* scan-index diversity spacing

Selection happens on range A (50M -> 100M by default). The validation number is
range B (100M -> 150M), which keeps information asymmetry visible.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.run_field_branch_gate_search import (  # noqa: E402
    GateSpec,
    branch_score,
    build_rows,
    ensure_dynamic_profiles,
    profile_score,
    score_profile,
    score_spec,
)
from scripts.research.run_field_gate_oos_validate import spec_from_report  # noqa: E402
from scripts.research.run_field_gate_threshold_sensitivity import fresh_rows  # noqa: E402


DEFAULT_OUT_DIR = Path("artifacts/prime_search_engine_bench")
DEFAULT_ROW_CACHE_DIR = Path("artifacts/prime_fog_row_cache")
LEADER_PROFILES = ("igct_c3_g6", "igct_c4_g5", "igct_c4_g6")
NEG_INF = -1.0e18

CHANNEL_FEATURES = (
    "foam_channel",
    "rebound_channel",
    "crossing_channel",
    "hidden_channel",
    "wall_channel",
    "depth_channel",
    "depth_flux_channel",
    "charge_flip_channel",
    "phi_channel",
    "prime_ratio_channel",
    "depth_resonance_channel",
    "resonant_soliton_channel",
    "geodesic_trend_channel",
    "cassette_channel",
    "cassette_adj_channel",
    "cassette_triplet_channel",
    "cassette_non_adj_channel",
    "cold_spot_channel",
    "cooling_channel",
    "heating_channel",
    "gradient_abs_channel",
)

DERIVED_FEATURES = (
    "scan_ratio",
    "abs_scan_ratio",
    "positive_scan_ratio",
    "cold_grad_product",
    "thermal_band_005_060",
    "geo_cold_product",
    "profile_igct_c3_g6",
    "profile_igct_c4_g5",
    "profile_igct_c4_g6",
    # Poincaré disk topological type features
    "gravity_score_normalized",
    "topo_score",
    "topo_asymmetry",
    "topo_confidence",
    # Musical mode channels (adaptive tonic + diatonic mode fit)
    "mode_fit_score",
    "mode_shift_channel",
    # Von Mangoldt / PNT lambda shadow channels
    "lambda_shadow_channel",
    "lambda_gradient_channel",
    "lambda_peak_lag",
    # Gap transition graph channels (ticker-tape structure)
    "graph_monotone_ramp",
    "graph_return_rate",
    "graph_edge_variance",
    "graph_attractor_score",
    # Cross-Manifold Phase Shifted Symmetric Zone diagnostics
    "cmpssz_phase_coherence",
    "cmpssz_spectral_anomaly",
    "cmpssz_log_zone_score",
)

FEATURE_NAMES = CHANNEL_FEATURES + DERIVED_FEATURES


@dataclass(frozen=True)
class LinearModel:
    means: list[float]
    scales: list[float]
    weights: list[float]
    bias: float


@dataclass(frozen=True)
class TreeNode:
    value: float
    support: int
    positives: int
    feature_index: int | None = None
    threshold: float | None = None
    left: "TreeNode | None" = None
    right: "TreeNode | None" = None


@dataclass(frozen=True)
class BranchPath:
    path_id: str
    conditions: tuple[tuple[int, str, float], ...]
    train_leaf_rate: float
    support: int
    positives: int


def row_cache_path(cache_dir: Path, limit: int, window: int, history: int, anchor_threshold: float) -> Path:
    threshold = str(anchor_threshold).replace(".", "p")
    return cache_dir / f"field_rows_l{limit}_w{window}_h{history}_a{threshold}.json"


def build_or_load_rows(
    limit: int,
    window: int,
    history: int,
    anchor_threshold: float,
    cache_dir: Path,
    use_cache: bool,
) -> list[dict[str, Any]]:
    cache_path = row_cache_path(cache_dir, limit, window, history, anchor_threshold)
    if use_cache and cache_path.exists():
        print(f"Loading cached rows: {cache_path}", flush=True)
        return json.loads(cache_path.read_text(encoding="utf-8"))
    rows = build_rows(limit, window, history, anchor_threshold)
    if use_cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return rows


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(out) or math.isinf(out):
        return default
    return out


def _log_floor(value: float, floor: float = 0.1) -> float:
    return math.log(max(floor, min(1.0, value)))


def cmpssz_log_zone_score(row: dict[str, Any]) -> float:
    """Stable log score for Cross-Manifold Phase Shifted Symmetric Zones.

    The probe's cached cassette fields already encode the N=3/5/7 idea:
    adjacent inversion density is the strict local trigger, triplet density is
    the zone bridge, and non-adjacent density is the background field.
    """
    adj = safe_float(row.get("cassette_adj_channel", 0.0))
    triplet = safe_float(row.get("cassette_triplet_channel", 0.0))
    non_adj = safe_float(row.get("cassette_non_adj_channel", 0.0))
    phase = safe_float(row.get("cmpssz_phase_coherence", 0.0))
    spectral = min(1.0, safe_float(row.get("cmpssz_spectral_anomaly", 0.0)) / 3.0)
    symmetry = min(1.0, (0.55 * adj) + (0.35 * triplet) + (0.10 * non_adj))
    density = min(1.0, safe_float(row.get("cassette_channel", 0.0)) + (0.35 * adj) + (0.20 * triplet))
    background_penalty = 0.35 * non_adj * max(0.0, 1.0 - adj)
    return (
        _log_floor(symmetry)
        + _log_floor(phase)
        + _log_floor(density)
        + _log_floor(spectral)
        - background_penalty
    )


def cmpssz_lane_score(row: dict[str, Any]) -> float:
    # Convert log product back to a compact positive score for lane ranking.
    return math.exp(cmpssz_log_zone_score(row) / 4.0)


def feature_vector(row: dict[str, Any]) -> list[float]:
    channels = {name: safe_float(row.get(name, 0.0)) for name in CHANNEL_FEATURES}
    scan_ratio = safe_float(row.get("scan_ratio", 0.0))
    cold = channels["cold_spot_channel"]
    grad = channels["gradient_abs_channel"]
    geo = channels["geodesic_trend_channel"]
    derived = {
        "scan_ratio": scan_ratio,
        "abs_scan_ratio": abs(scan_ratio),
        "positive_scan_ratio": 1.0 if scan_ratio >= 0.0 else 0.0,
        "cold_grad_product": cold * grad,
        "thermal_band_005_060": 1.0 if 0.05 <= grad <= 0.60 else 0.0,
        "geo_cold_product": max(0.0, geo) * cold,
        "profile_igct_c3_g6": profile_score(row, "igct_c3_g6"),
        "profile_igct_c4_g5": profile_score(row, "igct_c4_g5"),
        "profile_igct_c4_g6": profile_score(row, "igct_c4_g6"),
        # Poincaré disk topological type features (scale-invariant)
        "gravity_score_normalized": safe_float(row.get("gravity_score_normalized", 0.0)),
        "topo_score": safe_float(row.get("topo_score", 0.0)),
        "topo_asymmetry": safe_float(row.get("topo_asymmetry", 0.0)),
        "topo_confidence": safe_float(row.get("topo_confidence", 0.0)),
        # Musical mode channels (adaptive tonic + diatonic mode fit)
        "mode_fit_score": safe_float(row.get("mode_fit_score", 0.0)),
        "mode_shift_channel": safe_float(row.get("mode_shift_channel", 0.0)),
        # Von Mangoldt / PNT lambda shadow channels
        "lambda_shadow_channel": safe_float(row.get("lambda_shadow_channel", 0.0)),
        "lambda_gradient_channel": safe_float(row.get("lambda_gradient_channel", 0.0)),
        "lambda_peak_lag": safe_float(row.get("lambda_peak_lag", 0.5)),
        # Gap transition graph channels (ticker-tape structure)
        "graph_monotone_ramp": safe_float(row.get("graph_monotone_ramp", 0.0)),
        "graph_return_rate": safe_float(row.get("graph_return_rate", 0.5)),
        "graph_edge_variance": safe_float(row.get("graph_edge_variance", 0.0)),
        "graph_attractor_score": safe_float(row.get("graph_attractor_score", 0.0)),
        # CMPSSZ/cassette diagnostics. The log score keeps weak channels from
        # zeroing the lane while still penalizing background dilution.
        "cmpssz_phase_coherence": safe_float(row.get("cmpssz_phase_coherence", 0.0)),
        "cmpssz_spectral_anomaly": safe_float(row.get("cmpssz_spectral_anomaly", 0.0)),
        "cmpssz_log_zone_score": cmpssz_log_zone_score(row),
    }
    return [channels[name] for name in CHANNEL_FEATURES] + [derived[name] for name in DERIVED_FEATURES]


def matrix(rows: list[dict[str, Any]]) -> list[list[float]]:
    return [feature_vector(row) for row in rows]


def labels(rows: list[dict[str, Any]]) -> list[int]:
    return [1 if row.get("future_anchor") else 0 for row in rows]


def fit_standardizer(x_rows: list[list[float]]) -> tuple[list[float], list[float]]:
    if not x_rows:
        return [], []
    n = len(x_rows)
    width = len(x_rows[0])
    means = [sum(row[j] for row in x_rows) / n for j in range(width)]
    scales = []
    for j, mean in enumerate(means):
        variance = sum((row[j] - mean) ** 2 for row in x_rows) / n
        scales.append(math.sqrt(variance) or 1.0)
    return means, scales


def zrow(row: list[float], means: list[float], scales: list[float]) -> list[float]:
    return [(value - means[index]) / scales[index] for index, value in enumerate(row)]


def fit_centroid_ranker(x_rows: list[list[float]], y_rows: list[int]) -> LinearModel:
    means, scales = fit_standardizer(x_rows)
    z_rows = [zrow(row, means, scales) for row in x_rows]
    width = len(means)
    pos = [row for row, label in zip(z_rows, y_rows) if label]
    neg = [row for row, label in zip(z_rows, y_rows) if not label]
    if not pos or not neg:
        return LinearModel(means, scales, [0.0] * width, 0.0)
    pos_mean = [sum(row[j] for row in pos) / len(pos) for j in range(width)]
    neg_mean = [sum(row[j] for row in neg) / len(neg) for j in range(width)]
    weights = [pos_mean[j] - neg_mean[j] for j in range(width)]
    bias = -0.5 * sum((pos_mean[j] ** 2) - (neg_mean[j] ** 2) for j in range(width))
    return LinearModel(means, scales, weights, bias)


def linear_scores(model: LinearModel, x_rows: list[list[float]]) -> list[float]:
    scores = []
    for raw in x_rows:
        z = zrow(raw, model.means, model.scales)
        scores.append(model.bias + sum(weight * value for weight, value in zip(model.weights, z)))
    return scores


def positive_rate(y_rows: list[int], indexes: list[int]) -> float:
    return sum(y_rows[index] for index in indexes) / len(indexes) if indexes else 0.0


def gini_impurity(y_rows: list[int], indexes: list[int]) -> float:
    if not indexes:
        return 0.0
    p = positive_rate(y_rows, indexes)
    return 1.0 - (p * p) - ((1.0 - p) * (1.0 - p))


def quantile_thresholds(values: list[float], bins: int) -> list[float]:
    unique = sorted(set(values))
    if len(unique) <= 1:
        return []
    thresholds = []
    for q in range(1, bins):
        index = min(len(unique) - 1, max(0, round((len(unique) - 1) * q / bins)))
        thresholds.append(unique[index])
    return sorted(set(thresholds))


def best_split(
    x_rows: list[list[float]],
    y_rows: list[int],
    indexes: list[int],
    min_leaf: int,
    bins: int,
) -> tuple[int, float, list[int], list[int], float] | None:
    parent = gini_impurity(y_rows, indexes)
    best: tuple[int, float, list[int], list[int], float] | None = None
    width = len(x_rows[0]) if x_rows else 0
    for feature_index in range(width):
        thresholds = quantile_thresholds([x_rows[index][feature_index] for index in indexes], bins)
        for threshold in thresholds:
            left = [index for index in indexes if x_rows[index][feature_index] <= threshold]
            right = [index for index in indexes if x_rows[index][feature_index] > threshold]
            if len(left) < min_leaf or len(right) < min_leaf:
                continue
            child_impurity = (len(left) / len(indexes)) * gini_impurity(y_rows, left) + (
                len(right) / len(indexes)
            ) * gini_impurity(y_rows, right)
            gain = parent - child_impurity
            if best is None or gain > best[4]:
                best = (feature_index, threshold, left, right, gain)
    return best


def fit_tree(
    x_rows: list[list[float]],
    y_rows: list[int],
    indexes: list[int],
    depth: int,
    max_depth: int,
    min_leaf: int,
    bins: int,
) -> TreeNode:
    positives = sum(y_rows[index] for index in indexes)
    value = positives / len(indexes) if indexes else 0.0
    if depth >= max_depth or len(indexes) < min_leaf * 2:
        return TreeNode(value=value, support=len(indexes), positives=positives)
    split = best_split(x_rows, y_rows, indexes, min_leaf=min_leaf, bins=bins)
    if split is None or split[4] <= 1.0e-9:
        return TreeNode(value=value, support=len(indexes), positives=positives)
    feature_index, threshold, left_indexes, right_indexes, _gain = split
    return TreeNode(
        value=value,
        support=len(indexes),
        positives=positives,
        feature_index=feature_index,
        threshold=threshold,
        left=fit_tree(x_rows, y_rows, left_indexes, depth + 1, max_depth, min_leaf, bins),
        right=fit_tree(x_rows, y_rows, right_indexes, depth + 1, max_depth, min_leaf, bins),
    )


def predict_tree_one(node: TreeNode, row: list[float]) -> float:
    current = node
    while current.feature_index is not None and current.threshold is not None:
        if row[current.feature_index] <= current.threshold:
            if current.left is None:
                return current.value
            current = current.left
        else:
            if current.right is None:
                return current.value
            current = current.right
    return current.value


def tree_scores(node: TreeNode, x_rows: list[list[float]]) -> list[float]:
    return [predict_tree_one(node, row) for row in x_rows]


def collect_branch_paths(
    node: TreeNode,
    path: tuple[tuple[int, str, float], ...] = (),
) -> list[BranchPath]:
    if node.feature_index is None or node.threshold is None:
        path_id = " AND ".join(
            f"{FEATURE_NAMES[index]} {op} {threshold:.6g}" for index, op, threshold in path
        ) or "TRUE"
        return [
            BranchPath(
                path_id=path_id,
                conditions=path,
                train_leaf_rate=node.value,
                support=node.support,
                positives=node.positives,
            )
        ]
    out: list[BranchPath] = []
    if node.left is not None:
        out.extend(collect_branch_paths(node.left, path + ((node.feature_index, "<=", node.threshold),)))
    if node.right is not None:
        out.extend(collect_branch_paths(node.right, path + ((node.feature_index, ">", node.threshold),)))
    return out


def row_matches_path(row: list[float], branch: BranchPath) -> bool:
    for feature_index, op, threshold in branch.conditions:
        value = row[feature_index]
        if op == "<=":
            if value > threshold:
                return False
        elif value <= threshold:
            return False
    return True


def score_dict(rows: list[dict[str, Any]], scores: list[float]) -> dict[int, float]:
    return {id(row): float(score) for row, score in zip(rows, scores)}


def fit_score_normalizer(scores: list[float]) -> tuple[float, float]:
    clean = [score for score in scores if score > NEG_INF / 10]
    if not clean:
        return 0.0, 1.0
    mean = sum(clean) / len(clean)
    variance = sum((score - mean) ** 2 for score in clean) / len(clean)
    return mean, math.sqrt(variance) or 1.0


def apply_score_normalizer(scores: list[float], mean: float, scale: float) -> list[float]:
    return [NEG_INF if score <= NEG_INF / 10 else (score - mean) / scale for score in scores]


def blend_scores(score_columns: list[list[float]], weights: tuple[float, ...]) -> list[float]:
    blended = []
    for values in zip(*score_columns):
        if any(value <= NEG_INF / 10 for value in values):
            blended.append(NEG_INF)
        else:
            blended.append(sum(weight * value for weight, value in zip(weights, values)))
    return blended


def add_tie_break(scores: list[float], tie_breakers: list[float], scale: float = 1.0e-6) -> list[float]:
    out = []
    for score, tie_breaker in zip(scores, tie_breakers):
        if score <= NEG_INF / 10:
            out.append(NEG_INF)
        else:
            out.append(score + (scale * tie_breaker))
    return out


def top_fraction_mask(scores: list[float], fraction: float) -> set[int]:
    keep = max(1, math.ceil(len(scores) * fraction))
    ranked = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
    return set(ranked[:keep])


def apply_candidate_mask(scores: list[float], mask: set[int]) -> list[float]:
    return [score if index in mask else NEG_INF for index, score in enumerate(scores)]


def selected_top_rows(
    rows: list[dict[str, Any]],
    scores: dict[int, float],
    top_n: int,
    min_scan_gap: int = 0,
    unique_anchors_only: bool = False,
) -> list[dict[str, Any]]:
    ranked = sorted(rows, key=lambda row: (-scores[id(row)], row["scan_idx"]))
    selected: list[dict[str, Any]] = []
    claimed_anchors: set[object] = set()
    for row in ranked:
        if scores[id(row)] <= NEG_INF / 10:
            continue
        if min_scan_gap and any(abs(row["scan_idx"] - prior["scan_idx"]) < min_scan_gap for prior in selected):
            continue
        if unique_anchors_only:
            anchor = row.get("first_anchor_prime")
            if anchor is not None and anchor in claimed_anchors:
                continue
        selected.append(row)
        if unique_anchors_only:
            anchor = row.get("first_anchor_prime")
            if anchor is not None:
                claimed_anchors.add(anchor)
        if len(selected) >= top_n:
            break
    return selected


def metrics_for_scores(
    rows: list[dict[str, Any]],
    scores: dict[int, float],
    top_n: int,
    min_scan_gap: int = 0,
    unique_anchors_only: bool = False,
) -> dict[str, Any]:
    positives = sum(1 for row in rows if row["future_anchor"])
    base_rate = positives / len(rows) if rows else 0.0
    top = selected_top_rows(rows, scores, top_n, min_scan_gap=min_scan_gap, unique_anchors_only=unique_anchors_only)
    top_hits = sum(1 for row in top if row["future_anchor"])

    # Unique anchor counting: how many distinct future numbers are covered by top-N hits.
    _seen_anchors: set[object] = set()
    hidden_numbers: list[dict[str, Any]] = []
    unique_anchor_hits = 0
    duplicate_anchor_hits = 0
    for rank, row in enumerate(top, start=1):
        if row.get("future_anchor"):
            anchor_id = row.get("first_anchor_idx", row.get("first_anchor_prime"))
            if anchor_id is None or anchor_id not in _seen_anchors:
                unique_anchor_hits += 1
                hidden_numbers.append(
                    {
                        "rank": rank,
                        "anchor_idx": row.get("first_anchor_idx"),
                        "anchor_prime": row.get("first_anchor_prime"),
                        "anchor_ratio": row.get("first_anchor_ratio"),
                        "scan_idx": row.get("scan_idx"),
                        "scan_prime": row.get("scan_prime"),
                        "lead_steps": row.get("lead_steps"),
                        "score": round(scores[id(row)], 6),
                    }
                )
            else:
                duplicate_anchor_hits += 1
            if anchor_id is not None:
                _seen_anchors.add(anchor_id)
    # Total distinct anchor events reachable in the full row set
    unique_anchors_total = len(
        {
            r.get("first_anchor_idx", r.get("first_anchor_prime"))
            for r in rows
            if r.get("future_anchor") and r.get("first_anchor_idx", r.get("first_anchor_prime")) is not None
        }
    )

    ranked = sorted(rows, key=lambda row: (-scores[id(row)], row["scan_idx"]))
    hit_count = 0
    precision_sum = 0.0
    for index, row in enumerate(ranked, start=1):
        if scores[id(row)] <= NEG_INF / 10:
            continue
        if row["future_anchor"]:
            hit_count += 1
            precision_sum += hit_count / index
    return {
        "row_count": len(rows),
        "positive_count": positives,
        "base_rate": round(base_rate, 6),
        "top_n": len(top),
        "top_hits": top_hits,
        "top_anchor_rate": round(top_hits / len(top), 6) if top else 0.0,
        "unique_anchor_hits": unique_anchor_hits,
        "unique_anchors_total": unique_anchors_total,
        "duplicate_anchor_hits": duplicate_anchor_hits,
        "unique_anchor_rate": round(unique_anchor_hits / len(top), 6) if top else 0.0,
        "unique_anchor_recall": round(unique_anchor_hits / unique_anchors_total, 6) if unique_anchors_total else 0.0,
        "lift": round((top_hits / len(top)) / base_rate, 6) if top and base_rate else 0.0,
        "average_precision": round(precision_sum / positives, 6) if positives else 0.0,
        "min_scan_gap": min_scan_gap,
        "hidden_numbers": hidden_numbers,
        "top_rows": [
            {
                "rank": index + 1,
                "scan_idx": row["scan_idx"],
                "scan_prime": row.get("scan_prime"),
                "scan_ratio": row["scan_ratio"],
                "score": round(scores[id(row)], 6),
                "future_anchor": row["future_anchor"],
                "first_anchor_prime": row.get("first_anchor_prime"),
                "lead_steps": row["lead_steps"],
                "region_kind": row["region_kind"],
                "cold_spot_channel": row.get("cold_spot_channel"),
                "gradient_abs_channel": row.get("gradient_abs_channel"),
                "geodesic_trend_channel": row.get("geodesic_trend_channel"),
                "cassette_channel": row.get("cassette_channel"),
            }
            for index, row in enumerate(top)
        ],
    }


def evaluate_candidate(
    name: str,
    family: str,
    rows_a: list[dict[str, Any]],
    rows_b: list[dict[str, Any]],
    scores_a: list[float],
    scores_b: list[float],
    top_n: int,
    min_scan_gap: int,
    params: dict[str, Any] | None = None,
    unique_anchors_only: bool = False,
) -> dict[str, Any]:
    return {
        "name": name,
        "family": family,
        "params": params or {},
        "range_a": metrics_for_scores(rows_a, score_dict(rows_a, scores_a), top_n, min_scan_gap=min_scan_gap, unique_anchors_only=unique_anchors_only),
        "range_b": metrics_for_scores(rows_b, score_dict(rows_b, scores_b), top_n, min_scan_gap=min_scan_gap, unique_anchors_only=unique_anchors_only),
    }


def ranked_by_range_a(methods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        methods,
        key=lambda item: (
            -item["range_a"]["top_hits"],
            -item["range_a"]["top_anchor_rate"],
            -item["range_a"]["average_precision"],
            item["range_a"]["min_scan_gap"],
            item["name"],
        ),
    )


def choose_by_range_a(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return ranked_by_range_a(candidates)[0]


def choose_by_range_b(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(
        candidates,
        key=lambda item: (
            -item["range_b"]["top_hits"],
            -item["range_b"]["average_precision"],
            item["range_b"]["min_scan_gap"],
            item["name"],
        ),
    )[0]


def method_family_diverse(methods: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_families: set[str] = set()
    for method in ranked_by_range_a(methods):
        if method["family"] in seen_families:
            continue
        selected.append(method)
        seen_families.add(method["family"])
        if len(selected) >= top_k:
            return selected
    for method in ranked_by_range_a(methods):
        if method in selected:
            continue
        selected.append(method)
        if len(selected) >= top_k:
            break
    return selected


def rrf_scores_from_top_rows(
    rows: list[dict[str, Any]],
    methods: list[dict[str, Any]],
    range_key: str,
    rank_constant: int,
) -> list[float]:
    by_scan_idx = {row["scan_idx"]: index for index, row in enumerate(rows)}
    scores = [NEG_INF for _row in rows]
    for method in methods:
        for top_row in method[range_key].get("top_rows", []):
            index = by_scan_idx.get(top_row["scan_idx"])
            if index is None:
                continue
            if scores[index] <= NEG_INF / 10:
                scores[index] = 0.0
            scores[index] += 1.0 / (rank_constant + top_row["rank"])
    return scores


def evaluate_rrf_ensemble(
    name: str,
    selected_methods: list[dict[str, Any]],
    rows_a: list[dict[str, Any]],
    rows_b: list[dict[str, Any]],
    top_n: int,
    rank_constant: int,
    unique_anchors_only: bool = False,
) -> dict[str, Any]:
    scores_a = rrf_scores_from_top_rows(rows_a, selected_methods, "range_a", rank_constant)
    scores_b = rrf_scores_from_top_rows(rows_b, selected_methods, "range_b", rank_constant)
    return evaluate_candidate(
        name=name,
        family="rrf_ensemble",
        rows_a=rows_a,
        rows_b=rows_b,
        scores_a=scores_a,
        scores_b=scores_b,
        top_n=top_n,
        min_scan_gap=0,
        unique_anchors_only=unique_anchors_only,
        params={
            "rank_constant": rank_constant,
            "selected_methods": [
                {
                    "name": method["name"],
                    "family": method["family"],
                    "range_a_hits": method["range_a"]["top_hits"],
                    "range_b_hits": method["range_b"]["top_hits"],
                }
                for method in selected_methods
            ],
        },
    )


def score_frozen(rows: list[dict[str, Any]], spec: GateSpec) -> list[float]:
    scores = []
    for row in rows:
        score = branch_score(row, spec)
        scores.append(score if score > 0.0 else NEG_INF)
    return scores


def score_lambda_shadow(rows: list[dict[str, Any]]) -> list[float]:
    """Score rows by lambda shadow channels only (flashlight-only lane)."""
    scores = []
    for row in rows:
        shadow = safe_float(row.get("lambda_shadow_channel", 0.0))
        gradient = safe_float(row.get("lambda_gradient_channel", 0.0))
        peak_lag = safe_float(row.get("lambda_peak_lag", 0.5))
        # Positive shadow + upward gradient + recent peak = hot zone
        score = shadow + 0.5 * gradient + 0.3 * peak_lag
        scores.append(score if score > NEG_INF / 10 else NEG_INF)
    return scores


def score_frozen_plus_lambda(
    rows: list[dict[str, Any]],
    spec: "GateSpec",
    lambda_weight: float = 0.3,
) -> list[float]:
    """Blend frozen gate score with lambda shadow score (camera + flashlight)."""
    scores = []
    for row in rows:
        frozen_s = branch_score(row, spec)
        shadow = safe_float(row.get("lambda_shadow_channel", 0.0))
        gradient = safe_float(row.get("lambda_gradient_channel", 0.0))
        peak_lag = safe_float(row.get("lambda_peak_lag", 0.5))
        lambda_s = shadow + 0.5 * gradient + 0.3 * peak_lag
        if frozen_s > 0.0:
            score = (1.0 - lambda_weight) * frozen_s + lambda_weight * lambda_s
        else:
            score = NEG_INF
        scores.append(score)
    return scores


def score_graph_map(rows: list[dict[str, Any]]) -> list[float]:
    """Score rows by gap transition graph channels only (graph-map lane)."""
    scores = []
    for row in rows:
        ramp = safe_float(row.get("graph_monotone_ramp", 0.0))
        ret = safe_float(row.get("graph_return_rate", 0.5))
        edge_var = safe_float(row.get("graph_edge_variance", 0.0))
        attractor = safe_float(row.get("graph_attractor_score", 0.0))
        # Long ramp + low return rate + high variance + strong attractor = trending field
        score = ramp + (1.0 - ret) * 0.5 + edge_var * 0.3 + attractor * 0.4
        scores.append(score)
    return scores


def score_frozen_plus_graph(
    rows: list[dict[str, Any]],
    spec: "GateSpec",
    graph_weight: float = 0.3,
) -> list[float]:
    """Blend frozen gate with graph-map score (camera + ticker structure)."""
    scores = []
    for row in rows:
        frozen_s = branch_score(row, spec)
        ramp = safe_float(row.get("graph_monotone_ramp", 0.0))
        ret = safe_float(row.get("graph_return_rate", 0.5))
        edge_var = safe_float(row.get("graph_edge_variance", 0.0))
        attractor = safe_float(row.get("graph_attractor_score", 0.0))
        graph_s = ramp + (1.0 - ret) * 0.5 + edge_var * 0.3 + attractor * 0.4
        if frozen_s > 0.0:
            score = (1.0 - graph_weight) * frozen_s + graph_weight * graph_s
        else:
            score = NEG_INF
        scores.append(score)
    return scores


def score_cmpssz(rows: list[dict[str, Any]]) -> list[float]:
    """Score rows by CMPSSZ/cassette channels only."""
    return [cmpssz_lane_score(row) for row in rows]


def score_frozen_plus_cmpssz(
    rows: list[dict[str, Any]],
    spec: "GateSpec",
    cmpssz_weight: float = 0.3,
) -> list[float]:
    """Blend frozen gate with CMPSSZ score on the frozen score scale."""
    scores = []
    for row in rows:
        frozen_s = branch_score(row, spec)
        cmpssz_s = cmpssz_lane_score(row) * 22.0
        if frozen_s > 0.0:
            score = (1.0 - cmpssz_weight) * frozen_s + cmpssz_weight * cmpssz_s
        else:
            score = NEG_INF
        scores.append(score)
    return scores


def report_baseline_profile(
    rows_a: list[dict[str, Any]],
    rows_b: list[dict[str, Any]],
    profile: str,
    top_n: int,
) -> dict[str, Any]:
    range_a = score_profile(rows_a, profile, top_n)
    range_b = score_profile(rows_b, profile, top_n)
    range_a["min_scan_gap"] = 0
    range_b["min_scan_gap"] = 0
    return {
        "name": profile,
        "family": "additive_profile",
        "params": {},
        "range_a": range_a,
        "range_b": range_b,
    }


def split_ordered_rows(rows: list[dict[str, Any]], fit_fraction: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda row: row["scan_idx"])
    split_at = max(1, min(len(ordered) - 1, int(len(ordered) * fit_fraction)))
    return ordered[:split_at], ordered[split_at:]


def branch_scores_from_path(
    x_rows: list[list[float]],
    frozen_scores: list[float],
    branch: BranchPath,
) -> list[float]:
    return [
        frozen_score if row_matches_path(x_row, branch) else NEG_INF
        for x_row, frozen_score in zip(x_rows, frozen_scores)
    ]


def condition_payload(branch: BranchPath) -> list[dict[str, Any]]:
    return [
        {"feature": FEATURE_NAMES[index], "op": op, "threshold": round(threshold, 8)}
        for index, op, threshold in branch.conditions
    ]


def build_known_unknown_catalog(
    rows: list[dict[str, Any]],
    hidden_maps: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    catalog: dict[object, dict[str, Any]] = {}
    for row in rows:
        if not row.get("future_anchor"):
            continue
        anchor_id = row.get("first_anchor_idx", row.get("first_anchor_prime"))
        if anchor_id is None:
            continue
        item = catalog.setdefault(
            anchor_id,
            {
                "anchor_idx": row.get("first_anchor_idx"),
                "anchor_prime": row.get("first_anchor_prime"),
                "anchor_ratio": row.get("first_anchor_ratio"),
                "candidate_rows": 0,
                "min_lead_steps": None,
                "max_lead_steps": None,
                "found_by": [],
            },
        )
        item["candidate_rows"] += 1
        lead = row.get("lead_steps")
        if lead is not None:
            if item["min_lead_steps"] is None or lead < item["min_lead_steps"]:
                item["min_lead_steps"] = lead
            if item["max_lead_steps"] is None or lead > item["max_lead_steps"]:
                item["max_lead_steps"] = lead

    found_lookup: dict[str, set[object]] = {}
    for method_name, hidden_numbers in hidden_maps.items():
        found_lookup[method_name] = {
            number.get("anchor_idx", number.get("anchor_prime"))
            for number in hidden_numbers
            if number.get("anchor_idx", number.get("anchor_prime")) is not None
        }
    for anchor_id, item in catalog.items():
        item["found_by"] = [method_name for method_name, found_ids in found_lookup.items() if anchor_id in found_ids]
    return sorted(
        catalog.values(),
        key=lambda item: (
            item["anchor_idx"] if item["anchor_idx"] is not None else 10**18,
            item["anchor_prime"] if item["anchor_prime"] is not None else 10**18,
        ),
    )


def write_markdown(report: dict[str, Any], path: Path) -> None:
    fit_label = report["ranges"]["range_a_fit"]["label"]
    select_label = report["ranges"]["range_a"]["label"]
    validate_label = report["ranges"]["range_b"]["label"]
    lines = [
        "# Prime Search Engine Upgrade Bench",
        "",
        f"Training happens on the early `{fit_label}` split, selection happens on `{select_label}`, and validation is `{validate_label}`.",
        "",
        "## Summary",
        "",
        f"| Method | Family | {select_label} | A-uniq | {validate_label} | B-uniq | Gap |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in report["leaderboard"]:
        lines.append(
            "| {name} | {family} | {a}/{an} ({ar:.1%}) | {au}/{aut} | {b}/{bn} ({br:.1%}) | {bu}/{but_} | {gap} |".format(
                name=item["name"],
                family=item["family"],
                a=item["range_a"]["top_hits"],
                an=item["range_a"]["top_n"],
                ar=item["range_a"]["top_anchor_rate"],
                au=item["range_a"].get("unique_anchor_hits", "?"),
                aut=item["range_a"].get("unique_anchors_total", "?"),
                b=item["range_b"]["top_hits"],
                bn=item["range_b"]["top_n"],
                br=item["range_b"]["top_anchor_rate"],
                bu=item["range_b"].get("unique_anchor_hits", "?"),
                but_=item["range_b"].get("unique_anchors_total", "?"),
                gap=item["range_b"]["min_scan_gap"],
            )
        )
    selected = report["best_selected_on_range_a"]
    oracle = report["best_oracle_on_range_b"]
    lines.extend(
        [
            "",
            "## Selection",
            "",
            "Best selected on {}: `{}` -> {}/{} ({:.1%}) [{} unique events] on {}".format(
                select_label,
                selected["name"],
                selected["range_b"]["top_hits"],
                selected["range_b"]["top_n"],
                selected["range_b"]["top_anchor_rate"],
                selected["range_b"].get("unique_anchor_hits", "?"),
                validate_label,
            ),
            "Oracle best on {}: `{}` -> {}/{} ({:.1%}) [{} unique events]".format(
                validate_label,
                oracle["name"],
                oracle["range_b"]["top_hits"],
                oracle["range_b"]["top_n"],
                oracle["range_b"]["top_anchor_rate"],
                oracle["range_b"].get("unique_anchor_hits", "?"),
            ),
            "",
            "## Current Proof Baseline",
            "",
            "Frozen gate: `{}` -> {}/{} ({:.1%}) [{} unique events] on {}".format(
                report["frozen_spec"]["spec_id"],
                report["frozen_gate"]["range_b"]["top_hits"],
                report["frozen_gate"]["range_b"]["top_n"],
                report["frozen_gate"]["range_b"]["top_anchor_rate"],
                report["frozen_gate"]["range_b"].get("unique_anchor_hits", "?"),
                validate_label,
            ),
            "",
            "## Notes",
            "",
            report["claim_boundary"],
        ]
    )
    lines.extend(["", "## Hidden Numbers", ""])
    for title, key in (
        ("Frozen gate", "frozen_gate"),
        ("Best selected", "best_selected_on_range_a"),
        ("Oracle", "best_oracle_on_range_b"),
    ):
        item = report[key]
        lines.extend(
            [
                f"### {title}",
                "",
                "| Rank | Anchor idx | Anchor prime | Anchor ratio | Scan idx | Lead | Score |",
                "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        hidden_numbers = item["range_b"].get("hidden_numbers", [])[: report["config"]["top_n"]]
        if not hidden_numbers:
            lines.append("| - | - | - | - | - | - | - |")
        for number in hidden_numbers:
            lines.append(
                "| {rank} | {anchor_idx} | {anchor_prime} | {anchor_ratio} | {scan_idx} | {lead_steps} | {score} |".format(
                    rank=number.get("rank"),
                    anchor_idx=number.get("anchor_idx"),
                    anchor_prime=number.get("anchor_prime"),
                    anchor_ratio=number.get("anchor_ratio"),
                    scan_idx=number.get("scan_idx"),
                    lead_steps=number.get("lead_steps"),
                    score=number.get("score"),
                )
            )
        lines.append("")
    lines.extend(
        [
            "## Known Unknown Catalog",
            "",
            f"Validation hidden anchor numbers: {len(report.get('known_unknown_catalog', []))}",
            "",
            "| Anchor idx | Anchor prime | Ratio | Candidate rows | Lead range | Found by |",
            "| ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for item in report.get("known_unknown_catalog", [])[: min(40, len(report.get("known_unknown_catalog", [])))]:
        lead_range = f"{item.get('min_lead_steps')}..{item.get('max_lead_steps')}"
        lines.append(
            "| {anchor_idx} | {anchor_prime} | {anchor_ratio} | {candidate_rows} | {lead_range} | {found_by} |".format(
                anchor_idx=item.get("anchor_idx"),
                anchor_prime=item.get("anchor_prime"),
                anchor_ratio=item.get("anchor_ratio"),
                candidate_rows=item.get("candidate_rows"),
                lead_range=lead_range,
                found_by=", ".join(item.get("found_by", [])) or "-",
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    ensure_dynamic_profiles()
    out_dir = Path(args.out_dir)
    cache_dir = Path(args.row_cache_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    _ua: bool = getattr(args, "unique_anchors_only", False)

    frozen_spec = spec_from_report(Path(args.report), args.selector)
    rows_50 = build_or_load_rows(
        args.limit_a_boundary,
        args.window,
        args.history,
        args.anchor_threshold,
        cache_dir,
        not args.no_row_cache,
    )
    rows_100 = build_or_load_rows(
        args.limit_a_test,
        args.window,
        args.history,
        args.anchor_threshold,
        cache_dir,
        not args.no_row_cache,
    )
    rows_150 = build_or_load_rows(
        args.limit_b_test,
        args.window,
        args.history,
        args.anchor_threshold,
        cache_dir,
        not args.no_row_cache,
    )
    range_a_all = fresh_rows(rows_50, rows_100)
    range_b = fresh_rows(rows_100, rows_150)
    if not range_a_all or not range_b:
        raise RuntimeError("empty benchmark range; increase limits")
    fit_a, range_a = split_ordered_rows(range_a_all, args.fit_fraction)
    range_a_full_label = f"{args.limit_a_boundary // 1_000_000}M-{args.limit_a_test // 1_000_000}M"
    range_b_label = f"{args.limit_a_test // 1_000_000}M-{args.limit_b_test // 1_000_000}M"

    print(
        f"Range A fit rows: {len(fit_a):,}; Range A select rows: {len(range_a):,}; Range B rows: {len(range_b):,}",
        flush=True,
    )
    x_fit = matrix(fit_a)
    x_a = matrix(range_a)
    x_b = matrix(range_b)
    y_fit = labels(fit_a)

    frozen_fit = score_frozen(fit_a, frozen_spec)
    frozen_a = score_frozen(range_a, frozen_spec)
    frozen_b = score_frozen(range_b, frozen_spec)
    frozen_mean, frozen_scale = fit_score_normalizer(frozen_fit)
    frozen_a_z = apply_score_normalizer(frozen_a, frozen_mean, frozen_scale)
    frozen_b_z = apply_score_normalizer(frozen_b, frozen_mean, frozen_scale)

    candidates: list[dict[str, Any]] = []
    gap_values = tuple(int(value) for value in args.scan_gaps.split(",") if value.strip())

    for gap in gap_values:
        candidates.append(
            evaluate_candidate(
                name=f"frozen_gate_gap{gap}",
                family="frozen_gate",
                rows_a=range_a,
                rows_b=range_b,
                scores_a=frozen_a,
                scores_b=frozen_b,
                top_n=args.top_n,
                min_scan_gap=gap,
                unique_anchors_only=_ua,
                params={"scan_gap": gap},
            )
        )

    model = fit_centroid_ranker(x_fit, y_fit)
    centroid_fit = linear_scores(model, x_fit)
    centroid_a = linear_scores(model, x_a)
    centroid_b = linear_scores(model, x_b)
    centroid_mean, centroid_scale = fit_score_normalizer(centroid_fit)
    centroid_a_z = apply_score_normalizer(centroid_a, centroid_mean, centroid_scale)
    centroid_b_z = apply_score_normalizer(centroid_b, centroid_mean, centroid_scale)
    for gap in gap_values:
        candidates.append(
            evaluate_candidate(
                name=f"centroid_ranker_gap{gap}",
                family="centroid_ranker",
                rows_a=range_a,
                rows_b=range_b,
                scores_a=centroid_a,
                scores_b=centroid_b,
                top_n=args.top_n,
                min_scan_gap=gap,
                unique_anchors_only=_ua,
                params={"scan_gap": gap},
            )
        )

    tree_candidates: list[tuple[str, TreeNode, dict[str, Any]]] = []
    for max_depth in (1, 2, 3, 4):
        for min_leaf in (50, 200, 500):
            tree = fit_tree(
                x_fit,
                y_fit,
                list(range(len(x_fit))),
                depth=0,
                max_depth=max_depth,
                min_leaf=min_leaf,
                bins=args.tree_bins,
            )
            tree_candidates.append(
                (
                    f"tree_d{max_depth}_leaf{min_leaf}",
                    tree,
                    {"max_depth": max_depth, "min_leaf": min_leaf, "bins": args.tree_bins},
                )
            )

    tree_score_columns: list[tuple[str, list[float], list[float], dict[str, Any], TreeNode]] = []
    for name, tree, params in tree_candidates:
        scores_fit = tree_scores(tree, x_fit)
        scores_a = tree_scores(tree, x_a)
        scores_b = tree_scores(tree, x_b)
        mean, scale = fit_score_normalizer(scores_fit)
        scores_a_z = apply_score_normalizer(scores_a, mean, scale)
        scores_b_z = apply_score_normalizer(scores_b, mean, scale)
        tree_score_columns.append((name, scores_a_z, scores_b_z, params, tree))
        ranked_scores_a = add_tie_break(scores_a, frozen_a_z)
        ranked_scores_b = add_tie_break(scores_b, frozen_b_z)
        for gap in gap_values:
            candidates.append(
                evaluate_candidate(
                    name=f"{name}_gap{gap}",
                    family="decision_tree",
                    rows_a=range_a,
                    rows_b=range_b,
                    scores_a=ranked_scores_a,
                    scores_b=ranked_scores_b,
                    top_n=args.top_n,
                    min_scan_gap=gap,
                unique_anchors_only=_ua,
                    params={**params, "scan_gap": gap},
                )
            )

    # Blend the interpretable frozen gate with learned vector/tree scores.
    blend_weights = (
        (0.75, 0.25, 0.0),
        (0.50, 0.50, 0.0),
        (0.75, 0.0, 0.25),
        (0.50, 0.0, 0.50),
        (0.50, 0.25, 0.25),
        (0.34, 0.33, 0.33),
        (0.25, 0.50, 0.25),
    )
    for tree_name, tree_a_z, tree_b_z, tree_params, _tree in tree_score_columns:
        for weights in blend_weights:
            blend_a = blend_scores([frozen_a_z, centroid_a_z, tree_a_z], weights)
            blend_b = blend_scores([frozen_b_z, centroid_b_z, tree_b_z], weights)
            for gap in gap_values:
                candidates.append(
                    evaluate_candidate(
                        name=f"blend_f{weights[0]:g}_c{weights[1]:g}_t{weights[2]:g}_{tree_name}_gap{gap}",
                        family="blend_reranker",
                        rows_a=range_a,
                        rows_b=range_b,
                        scores_a=blend_a,
                        scores_b=blend_b,
                        top_n=args.top_n,
                        min_scan_gap=gap,
                unique_anchors_only=_ua,
                        params={"weights": weights, "tree": tree_params, "scan_gap": gap},
                    )
                )

    # Two-stage retrieval: candidate generator first, frozen gate reranker second.
    candidate_fractions = tuple(float(value) for value in args.candidate_fractions.split(",") if value.strip())
    for fraction in candidate_fractions:
        mask_a = top_fraction_mask(centroid_a, fraction)
        mask_b = top_fraction_mask(centroid_b, fraction)
        rerank_a = apply_candidate_mask(frozen_a, mask_a)
        rerank_b = apply_candidate_mask(frozen_b, mask_b)
        for gap in gap_values:
            candidates.append(
                evaluate_candidate(
                    name=f"centroid_candidates_{fraction:g}_frozen_rerank_gap{gap}",
                    family="two_stage_retrieval",
                    rows_a=range_a,
                    rows_b=range_b,
                    scores_a=rerank_a,
                    scores_b=rerank_b,
                    top_n=args.top_n,
                    min_scan_gap=gap,
                unique_anchors_only=_ua,
                    params={"candidate_fraction": fraction, "reranker": "frozen_gate", "scan_gap": gap},
                )
            )

    # Tree leaf -> algebraic branch: if leaf conditions hold, score by frozen gate; else exclude.
    for tree_name, _tree_a_z, _tree_b_z, tree_params, tree in tree_score_columns:
        leaves = sorted(
            collect_branch_paths(tree),
            key=lambda leaf: (-leaf.train_leaf_rate, -leaf.support, leaf.path_id),
        )[: args.keep_tree_leaves]
        for leaf_index, branch in enumerate(leaves, start=1):
            branch_a = branch_scores_from_path(x_a, frozen_a, branch)
            branch_b = branch_scores_from_path(x_b, frozen_b, branch)
            for gap in gap_values:
                candidates.append(
                    evaluate_candidate(
                        name=f"tree_branch_{tree_name}_leaf{leaf_index}_gap{gap}",
                        family="tree_branch_algebra",
                        rows_a=range_a,
                        rows_b=range_b,
                        scores_a=branch_a,
                        scores_b=branch_b,
                        top_n=args.top_n,
                        min_scan_gap=gap,
                unique_anchors_only=_ua,
                        params={
                            "tree": tree_params,
                            "scan_gap": gap,
                            "leaf_rate": round(branch.train_leaf_rate, 6),
                            "support": branch.support,
                            "conditions": condition_payload(branch),
                        },
                    )
                )

    baseline_methods = [
        report_baseline_profile(range_a, range_b, profile, args.top_n) for profile in LEADER_PROFILES
    ]
    frozen_gate = evaluate_candidate(
        name="frozen_gate",
        family="proof_baseline",
        rows_a=range_a,
        rows_b=range_b,
        scores_a=frozen_a,
        scores_b=frozen_b,
        top_n=args.top_n,
        min_scan_gap=0,
        unique_anchors_only=_ua,
        params={"spec_id": frozen_spec.spec_id},
    )

    # ── Lambda shadow lanes (flashlight) ──────────────────────────────────────
    lambda_a = score_lambda_shadow(range_a)
    lambda_b = score_lambda_shadow(range_b)
    lambda_shadow_only = evaluate_candidate(
        name="lambda_shadow_only",
        family="lambda_shadow",
        rows_a=range_a,
        rows_b=range_b,
        scores_a=lambda_a,
        scores_b=lambda_b,
        top_n=args.top_n,
        min_scan_gap=0,
        unique_anchors_only=_ua,
        params={"channels": "shadow+gradient+peak_lag"},
    )
    frozen_plus_lambda_a = score_frozen_plus_lambda(range_a, frozen_spec, lambda_weight=0.3)
    frozen_plus_lambda_b = score_frozen_plus_lambda(range_b, frozen_spec, lambda_weight=0.3)
    frozen_plus_lambda = evaluate_candidate(
        name="frozen_plus_lambda_w0.3",
        family="lambda_shadow",
        rows_a=range_a,
        rows_b=range_b,
        scores_a=frozen_plus_lambda_a,
        scores_b=frozen_plus_lambda_b,
        top_n=args.top_n,
        min_scan_gap=0,
        unique_anchors_only=_ua,
        params={"lambda_weight": 0.3},
    )
    candidates.extend([lambda_shadow_only, frozen_plus_lambda])

    # ── Graph-map lanes (ticker-tape structure) ────────────────────────────────
    graph_a = score_graph_map(range_a)
    graph_b = score_graph_map(range_b)
    graph_map_only = evaluate_candidate(
        name="graph_map_only",
        family="graph_map",
        rows_a=range_a,
        rows_b=range_b,
        scores_a=graph_a,
        scores_b=graph_b,
        top_n=args.top_n,
        min_scan_gap=0,
        unique_anchors_only=_ua,
        params={"channels": "ramp+return+edge_var+attractor"},
    )
    frozen_plus_graph_a = score_frozen_plus_graph(range_a, frozen_spec, graph_weight=0.3)
    frozen_plus_graph_b = score_frozen_plus_graph(range_b, frozen_spec, graph_weight=0.3)
    frozen_plus_graph = evaluate_candidate(
        name="frozen_plus_graph_w0.3",
        family="graph_map",
        rows_a=range_a,
        rows_b=range_b,
        scores_a=frozen_plus_graph_a,
        scores_b=frozen_plus_graph_b,
        top_n=args.top_n,
        min_scan_gap=0,
        unique_anchors_only=_ua,
        params={"graph_weight": 0.3},
    )
    candidates.extend([graph_map_only, frozen_plus_graph])

    # ── CMPSSZ lanes (cross-manifold shell inversion resonance) ───────────────
    cmpssz_a = score_cmpssz(range_a)
    cmpssz_b = score_cmpssz(range_b)
    cmpssz_only = evaluate_candidate(
        name="cmpssz_only",
        family="cmpssz",
        rows_a=range_a,
        rows_b=range_b,
        scores_a=cmpssz_a,
        scores_b=cmpssz_b,
        top_n=args.top_n,
        min_scan_gap=0,
        unique_anchors_only=_ua,
        params={"score": "log_floor(symmetry,phase,density,spectral)-background_n7"},
    )
    frozen_plus_cmpssz_a = score_frozen_plus_cmpssz(range_a, frozen_spec, cmpssz_weight=0.3)
    frozen_plus_cmpssz_b = score_frozen_plus_cmpssz(range_b, frozen_spec, cmpssz_weight=0.3)
    frozen_plus_cmpssz = evaluate_candidate(
        name="frozen_plus_cmpssz_w0.3",
        family="cmpssz",
        rows_a=range_a,
        rows_b=range_b,
        scores_a=frozen_plus_cmpssz_a,
        scores_b=frozen_plus_cmpssz_b,
        top_n=args.top_n,
        min_scan_gap=0,
        unique_anchors_only=_ua,
        params={"cmpssz_weight": 0.3},
    )
    candidates.extend([cmpssz_only, frozen_plus_cmpssz])

    pre_ensemble_methods = [frozen_gate, *baseline_methods, *candidates]
    ensemble_candidates: list[dict[str, Any]] = []
    ensemble_top_k = tuple(int(value) for value in args.ensemble_top_k.split(",") if value.strip())
    rrf_constants = tuple(int(value) for value in args.rrf_constants.split(",") if value.strip())
    ranked_methods = ranked_by_range_a(pre_ensemble_methods)
    for top_k in ensemble_top_k:
        selected_plain = ranked_methods[: max(1, min(top_k, len(ranked_methods)))]
        selected_diverse = method_family_diverse(pre_ensemble_methods, max(1, min(top_k, len(pre_ensemble_methods))))
        for rank_constant in rrf_constants:
            ensemble_candidates.append(
                evaluate_rrf_ensemble(
                    name=f"rrf_top{top_k}_c{rank_constant}",
                    selected_methods=selected_plain,
                    rows_a=range_a,
                    rows_b=range_b,
                    top_n=args.top_n,
                    rank_constant=rank_constant,
                )
            )
            ensemble_candidates.append(
                evaluate_rrf_ensemble(
                    name=f"rrf_family_top{top_k}_c{rank_constant}",
                    selected_methods=selected_diverse,
                    rows_a=range_a,
                    rows_b=range_b,
                    top_n=args.top_n,
                    rank_constant=rank_constant,
                )
            )

    candidates.extend(ensemble_candidates)
    all_methods = [frozen_gate, *baseline_methods, *candidates]
    leaderboard = sorted(
        all_methods,
        key=lambda item: (
            -item["range_b"]["top_hits"],
            -item["range_b"]["average_precision"],
            item["range_b"]["min_scan_gap"],
            item["name"],
        ),
    )[: args.keep_top]
    selectable_methods = [frozen_gate, *baseline_methods, *candidates]
    by_range_a = choose_by_range_a(selectable_methods)
    by_range_b = choose_by_range_b(selectable_methods)

    hidden_number_maps = {
        "frozen_gate": frozen_gate["range_b"].get("hidden_numbers", []),
        "best_selected_on_range_a": by_range_a["range_b"].get("hidden_numbers", []),
        "best_oracle_on_range_b": by_range_b["range_b"].get("hidden_numbers", []),
    }
    known_unknown_catalog = build_known_unknown_catalog(range_b, hidden_number_maps)

    report = {
        "schema_version": "prime_search_engine_bench_v1",
        "config": {
            "limit_a_boundary": args.limit_a_boundary,
            "limit_a_test": args.limit_a_test,
            "limit_b_test": args.limit_b_test,
            "window": args.window,
            "history": args.history,
            "top_n": args.top_n,
            "anchor_threshold": args.anchor_threshold,
            "fit_fraction": args.fit_fraction,
            "candidate_count": len(candidates),
            "ensemble_candidate_count": len(ensemble_candidates),
            "ensemble_top_k": list(ensemble_top_k),
            "rrf_constants": list(rrf_constants),
            "scan_gaps": list(gap_values),
            "candidate_fractions": list(candidate_fractions),
        },
        "ranges": {
            "range_a_fit": {
                "label": f"{range_a_full_label} fit",
                "row_count": len(fit_a),
                "base_rate": round(sum(labels(fit_a)) / len(fit_a), 6),
            },
            "range_a": {
                "label": f"{range_a_full_label} selection holdout",
                "row_count": len(range_a),
                "base_rate": round(sum(labels(range_a)) / len(range_a), 6),
            },
            "range_b": {
                "label": range_b_label,
                "row_count": len(range_b),
                "base_rate": round(sum(labels(range_b)) / len(range_b), 6),
            },
        },
        "frozen_spec": frozen_spec.__dict__,
        "frozen_gate": frozen_gate,
        "baselines": baseline_methods,
        "best_selected_on_range_a": by_range_a,
        "best_oracle_on_range_b": by_range_b,
        "hidden_number_maps": hidden_number_maps,
        "known_unknown_catalog": known_unknown_catalog,
        "leaderboard": leaderboard,
        "all_candidates": sorted(
            candidates,
            key=lambda item: (
                -item["range_a"]["top_hits"],
                -item["range_a"]["average_precision"],
                item["range_a"]["min_scan_gap"],
                item["name"],
            ),
        )[: args.keep_all_candidates],
        "claim_boundary": (
            "Methods selected by range_a are adaptive and only count as evidence on range_b. "
            "The oracle row is diagnostic and not a blind result."
        ),
    }
    (out_dir / "latest_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (out_dir / "hidden_numbers_latest.json").write_text(
        json.dumps(report["hidden_number_maps"], indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "known_unknown_catalog_latest.json").write_text(
        json.dumps(report["known_unknown_catalog"], indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, out_dir / "LATEST.md")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="artifacts/prime_fog_branch_gate/latest_report.json")
    parser.add_argument("--selector", choices=["holdout", "train", "full"], default="holdout")
    parser.add_argument("--limit-a-boundary", type=int, default=50_000_000)
    parser.add_argument("--limit-a-test", type=int, default=100_000_000)
    parser.add_argument("--limit-b-test", type=int, default=150_000_000)
    parser.add_argument("--window", type=int, default=36)
    parser.add_argument("--history", type=int, default=12)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--anchor-threshold", type=float, default=4.0)
    parser.add_argument("--fit-fraction", type=float, default=0.60)
    parser.add_argument("--scan-gaps", default="0,4,8,12,16,24,36")
    parser.add_argument("--candidate-fractions", default="0.02,0.05,0.10,0.20,0.50")
    parser.add_argument("--ensemble-top-k", default="3,5,8,12")
    parser.add_argument("--rrf-constants", default="10,60")
    parser.add_argument("--tree-bins", type=int, default=10)
    parser.add_argument("--keep-tree-leaves", type=int, default=8)
    parser.add_argument("--keep-top", type=int, default=25)
    parser.add_argument("--keep-all-candidates", type=int, default=80)
    parser.add_argument("--row-cache-dir", default=str(DEFAULT_ROW_CACHE_DIR))
    parser.add_argument("--no-row-cache", action="store_true")
    parser.add_argument("--unique-anchors", dest="unique_anchors_only", action="store_true", default=False)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    report = run(args)
    selected = report["best_selected_on_range_a"]
    oracle = report["best_oracle_on_range_b"]
    frozen = report["frozen_gate"]
    print(
        "selected_on_A={name} A={ah}/{an} B={bh}/{bn} (B-uniq={bu}/{bua}); frozen_B={fh}/{fn} (uniq={fu}/{fua}); oracle_B={oh}/{on} (uniq={ou}/{oua})".format(
            name=selected["name"],
            ah=selected["range_a"]["top_hits"],
            an=selected["range_a"]["top_n"],
            bh=selected["range_b"]["top_hits"],
            bn=selected["range_b"]["top_n"],
            bu=selected["range_b"].get("unique_anchor_hits", "?"),
            bua=selected["range_b"].get("unique_anchors_total", "?"),
            fh=frozen["range_b"]["top_hits"],
            fn=frozen["range_b"]["top_n"],
            fu=frozen["range_b"].get("unique_anchor_hits", "?"),
            fua=frozen["range_b"].get("unique_anchors_total", "?"),
            oh=oracle["range_b"]["top_hits"],
            on=oracle["range_b"]["top_n"],
            ou=oracle["range_b"].get("unique_anchor_hits", "?"),
            oua=oracle["range_b"].get("unique_anchors_total", "?"),
        ),
        flush=True,
    )
    print(Path(args.out_dir) / "LATEST.md", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
