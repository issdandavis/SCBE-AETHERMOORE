#!/usr/bin/env python3
"""Probe whether SCBE inner embedding dimensions carry governance signal.

This is a Zone-4 eval around the phdm-21d context-broker embedding:

    dims 0-5   observed tongue projection
    dims 6-20  inner/non-defined channels

The question is not whether an isotropic random vector obeys k/n. It does.
The question is whether the repo's real 21D embedding uses the inner channels
for decision-relevant signal, or whether those channels are mostly noise.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from typing import Any, Iterable

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.mcp.context_broker_mcp import _classify_tongue, _embed_text

OBSERVED_SLICE = slice(0, 6)
INNER_SLICE = slice(6, 21)
GOVERNANCE_INNER_SLICE = slice(12, 21)
TONGUE_KEYS = ("KO", "AV", "RU", "CA", "UM", "DR")


def _norm_sq(row: np.ndarray) -> float:
    return float(np.dot(row, row))


def _records_from_adversarial_corpus() -> list[dict[str, Any]]:
    from tests.adversarial.attack_corpus import BASELINE_CLEAN, get_all_attacks

    rows: list[dict[str, Any]] = []
    for item in BASELINE_CLEAN:
        rows.append(
            {
                "id": str(item.get("id", f"clean_{len(rows)}")),
                "text": str(item["prompt"]),
                "attack": 0,
                "family": "clean",
            }
        )
    for item in get_all_attacks():
        rows.append(
            {
                "id": str(item.get("id", f"attack_{len(rows)}")),
                "text": str(item["prompt"]),
                "attack": 1,
                "family": str(item.get("class", "attack")),
            }
        )
    return rows


def _tool_family(name: str) -> str:
    if name.startswith("research-"):
        return "research"
    if name.startswith("geoseal-"):
        return "geoseal"
    if name.startswith("scbe-cli-"):
        return "cli_bench"
    if name.startswith("scbe-"):
        return "scbe_system"
    if name.startswith("video-"):
        return "video"
    return name.split("-", 1)[0]


def _records_from_tool_registry() -> list[dict[str, Any]]:
    path = REPO_ROOT / "packages" / "agent-bus" / "tools.json"
    tools = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for tool in tools:
        name = str(tool.get("name", "unknown"))
        desc = str(tool.get("description", ""))
        args = " ".join(str(arg) for arg in tool.get("args", []))
        text = f"{name}. {desc}. {tool.get('command', '')} {args}"
        rows.append(
            {
                "id": name,
                "text": text,
                "family": _tool_family(name),
                "tier": int(_classify_tongue(text)["tier"]),
            }
        )
    return rows


def _embedding_matrix(records: list[dict[str, Any]]) -> np.ndarray:
    return np.vstack([_embed_text(record["text"]) for record in records])


def _energy_report(matrix: np.ndarray) -> dict[str, float]:
    observed = matrix[:, OBSERVED_SLICE]
    inner = matrix[:, INNER_SLICE]
    full_norm = np.sum(matrix * matrix, axis=1)
    observed_norm = np.sum(observed * observed, axis=1)
    inner_norm = np.sum(inner * inner, axis=1)
    point_shares = observed_norm / np.maximum(full_norm, 1e-12)

    pair_shares: list[float] = []
    full_dists: list[float] = []
    observed_dists: list[float] = []
    inner_dists: list[float] = []
    for i in range(len(matrix)):
        for j in range(i + 1, len(matrix)):
            diff = matrix[i] - matrix[j]
            obs_diff = observed[i] - observed[j]
            inner_diff = inner[i] - inner[j]
            full_d = _norm_sq(diff)
            if full_d <= 1e-12:
                continue
            obs_d = _norm_sq(obs_diff)
            inner_d = _norm_sq(inner_diff)
            pair_shares.append(obs_d / full_d)
            full_dists.append(math.sqrt(full_d))
            observed_dists.append(math.sqrt(obs_d))
            inner_dists.append(math.sqrt(inner_d))

    return {
        "dimension_count_share": round(6 / 21, 6),
        "point_observed_share_mean": round(float(np.mean(point_shares)), 6),
        "point_inner_share_mean": round(
            float(np.mean(inner_norm / np.maximum(full_norm, 1e-12))), 6
        ),
        "pair_observed_share_mean": round(float(np.mean(pair_shares)), 6),
        "pair_inner_share_mean": round(1.0 - float(np.mean(pair_shares)), 6),
        "pair_observed_vs_full_corr": round(_pearson(observed_dists, full_dists), 6),
        "pair_inner_vs_full_corr": round(_pearson(inner_dists, full_dists), 6),
    }


def _pearson(a: Iterable[float], b: Iterable[float]) -> float:
    av = np.asarray(list(a), dtype=np.float64)
    bv = np.asarray(list(b), dtype=np.float64)
    if len(av) < 2 or float(np.std(av)) == 0.0 or float(np.std(bv)) == 0.0:
        return 0.0
    return float(np.corrcoef(av, bv)[0, 1])


def _binary_auc(labels: list[int], scores: list[float]) -> float:
    pairs = sorted(zip(scores, labels), key=lambda item: item[0])
    pos = sum(labels)
    neg = len(labels) - pos
    if pos == 0 or neg == 0:
        return float("nan")

    rank_sum_pos = 0.0
    rank = 1
    idx = 0
    while idx < len(pairs):
        j = idx + 1
        while j < len(pairs) and pairs[j][0] == pairs[idx][0]:
            j += 1
        avg_rank = (rank + rank + (j - idx) - 1) / 2.0
        for k in range(idx, j):
            if pairs[k][1] == 1:
                rank_sum_pos += avg_rank
        rank += j - idx
        idx = j

    return float((rank_sum_pos - pos * (pos + 1) / 2.0) / (pos * neg))


def _auc_with_null(
    labels: list[int], scores: list[float], *, seed: int, rounds: int
) -> dict[str, float]:
    rng = random.Random(seed)
    auc = _binary_auc(labels, scores)
    nulls = []
    for _ in range(rounds):
        shuffled = labels[:]
        rng.shuffle(shuffled)
        nulls.append(_binary_auc(shuffled, scores))
    return {
        "auc": round(auc, 6),
        "null_mean": round(float(np.mean(nulls)), 6),
        "null_p95": round(float(np.quantile(nulls, 0.95)), 6),
        "beats_null95": bool(auc > float(np.quantile(nulls, 0.95))),
    }


def _leave_one_out_nn_accuracy(matrix: np.ndarray, labels: list[str]) -> float:
    if len(matrix) < 2:
        return 0.0
    correct = 0
    total = 0
    for i in range(len(matrix)):
        best_j = None
        best_dist = float("inf")
        for j in range(len(matrix)):
            if i == j:
                continue
            dist = _norm_sq(matrix[i] - matrix[j])
            if dist < best_dist:
                best_dist = dist
                best_j = j
        if best_j is None:
            continue
        total += 1
        if labels[i] == labels[best_j]:
            correct += 1
    return correct / max(total, 1)


def _knn_with_null(
    matrix: np.ndarray,
    labels: list[str],
    *,
    seed: int,
    rounds: int,
) -> dict[str, float]:
    rng = random.Random(seed)
    acc = _leave_one_out_nn_accuracy(matrix, labels)
    nulls = []
    for _ in range(rounds):
        shuffled = labels[:]
        rng.shuffle(shuffled)
        nulls.append(_leave_one_out_nn_accuracy(matrix, shuffled))
    return {
        "accuracy": round(acc, 6),
        "null_mean": round(float(np.mean(nulls)), 6),
        "null_p95": round(float(np.quantile(nulls, 0.95)), 6),
        "beats_null95": bool(acc > float(np.quantile(nulls, 0.95))),
    }


def _score_report(
    matrix: np.ndarray, labels: list[int], *, seed: int, rounds: int
) -> dict[str, dict[str, float]]:
    observed_radius = np.linalg.norm(matrix[:, OBSERVED_SLICE], axis=1).tolist()
    inner_radius = np.linalg.norm(matrix[:, INNER_SLICE], axis=1).tolist()
    governance_inner_radius = np.linalg.norm(
        matrix[:, GOVERNANCE_INNER_SLICE], axis=1
    ).tolist()
    full_radius = np.linalg.norm(matrix, axis=1).tolist()
    return {
        "observed_tongue_radius": _auc_with_null(
            labels, observed_radius, seed=seed, rounds=rounds
        ),
        "inner_all_radius": _auc_with_null(
            labels, inner_radius, seed=seed + 1, rounds=rounds
        ),
        "inner_governance_radius": _auc_with_null(
            labels, governance_inner_radius, seed=seed + 2, rounds=rounds
        ),
        "full_radius": _auc_with_null(
            labels, full_radius, seed=seed + 3, rounds=rounds
        ),
    }


def _centroid_distance_report(
    matrix: np.ndarray,
    labels: list[int],
    *,
    seed: int,
    rounds: int,
) -> dict[str, dict[str, float]]:
    negative_rows = matrix[np.asarray(labels, dtype=int) == 0]
    if len(negative_rows) == 0:
        raise ValueError("centroid distance needs at least one negative/control row")

    def distances(view: slice) -> list[float]:
        subset = matrix[:, view]
        centroid = negative_rows[:, view].mean(axis=0)
        return np.linalg.norm(subset - centroid, axis=1).tolist()

    return {
        "observed_tongue_from_control_centroid": _auc_with_null(
            labels,
            distances(OBSERVED_SLICE),
            seed=seed,
            rounds=rounds,
        ),
        "inner_all_from_control_centroid": _auc_with_null(
            labels,
            distances(INNER_SLICE),
            seed=seed + 1,
            rounds=rounds,
        ),
        "inner_governance_from_control_centroid": _auc_with_null(
            labels,
            distances(GOVERNANCE_INNER_SLICE),
            seed=seed + 2,
            rounds=rounds,
        ),
        "full_from_control_centroid": _auc_with_null(
            labels,
            distances(slice(0, matrix.shape[1])),
            seed=seed + 3,
            rounds=rounds,
        ),
    }


def run_probe(*, seed: int = 1337, rounds: int = 400) -> dict[str, Any]:
    adversarial = _records_from_adversarial_corpus()
    adv_matrix = _embedding_matrix(adversarial)
    adv_labels = [int(row["attack"]) for row in adversarial]

    tools = _records_from_tool_registry()
    tool_matrix = _embedding_matrix(tools)
    tool_families = [str(row["family"]) for row in tools]
    tool_tier_labels = [1 if int(row["tier"]) >= 3 else 0 for row in tools]

    report = {
        "schema_version": "scbe_inner_dimension_signal_probe_v1",
        "embedding": "src.mcp.context_broker_mcp._embed_text phdm-21d",
        "dimension_split": {
            "observed": "dims 0-5 tongue domain",
            "inner": "dims 6-20 semantic hash + risk + clarity + pattern channels",
            "inner_governance": "dims 12-20 risk + clarity + attack-pattern channels",
        },
        "rounds": rounds,
        "seed": seed,
        "adversarial_corpus": {
            "records": len(adversarial),
            "positive_attacks": sum(adv_labels),
            "energy": _energy_report(adv_matrix),
            "attack_auc_radius": _score_report(
                adv_matrix, adv_labels, seed=seed, rounds=rounds
            ),
            "attack_auc_from_clean_centroid": _centroid_distance_report(
                adv_matrix,
                adv_labels,
                seed=seed + 100,
                rounds=rounds,
            ),
        },
        "tool_registry": {
            "records": len(tools),
            "families": sorted(set(tool_families)),
            "high_tier_records": sum(tool_tier_labels),
            "energy": _energy_report(tool_matrix),
            "tier_auc_radius": _score_report(
                tool_matrix, tool_tier_labels, seed=seed + 10, rounds=rounds
            ),
            "tier_auc_from_low_tier_centroid": _centroid_distance_report(
                tool_matrix,
                tool_tier_labels,
                seed=seed + 110,
                rounds=rounds,
            ),
            "family_knn": {
                "observed_tongue": _knn_with_null(
                    tool_matrix[:, OBSERVED_SLICE],
                    tool_families,
                    seed=seed + 20,
                    rounds=rounds,
                ),
                "inner": _knn_with_null(
                    tool_matrix[:, INNER_SLICE],
                    tool_families,
                    seed=seed + 21,
                    rounds=rounds,
                ),
                "full": _knn_with_null(
                    tool_matrix, tool_families, seed=seed + 22, rounds=rounds
                ),
            },
        },
        "verdict": {},
    }

    adv_auc = report["adversarial_corpus"]["attack_auc_from_clean_centroid"]
    tool_auc = report["tool_registry"]["tier_auc_from_low_tier_centroid"]
    report["verdict"] = {
        "inner_all_carries_attack_signal": bool(
            adv_auc["inner_all_from_control_centroid"]["beats_null95"]
        ),
        "inner_governance_subblock_carries_attack_signal": bool(
            adv_auc["inner_governance_from_control_centroid"]["beats_null95"]
        ),
        "observed_tongue_carries_attack_signal": bool(
            adv_auc["observed_tongue_from_control_centroid"]["beats_null95"]
        ),
        "inner_all_carries_tool_tier_signal": bool(
            tool_auc["inner_all_from_control_centroid"]["beats_null95"]
        ),
        "inner_governance_subblock_carries_tool_tier_signal": bool(
            tool_auc["inner_governance_from_control_centroid"]["beats_null95"]
        ),
        "observed_tongue_carries_tool_tier_signal": bool(
            tool_auc["observed_tongue_from_control_centroid"]["beats_null95"]
        ),
        "claim_boundary": (
            "This validates the current phdm-21d read-side split only. The all-inner "
            "block includes deterministic semantic hash channels, so inner_all signal "
            "does not by itself prove the risk subblock is sufficient or semantic."
        ),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--rounds", type=int, default=400)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    report = run_probe(seed=args.seed, rounds=args.rounds)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
