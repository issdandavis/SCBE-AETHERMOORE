#!/usr/bin/env python3
"""Null-gate the spin-voxel field topology claim.

The tautological test is "does the cost formula increase when its spin penalty
is higher?" This probe asks the sharper question: can the vector-field term
separate a smooth local field from a boundary field when both carry the exact
same vector inventory?

The null shuffles each sample's vectors before scoring. That preserves vector
magnitudes and inventory while destroying the neighborhood topology that
``spin_disorder`` claims to read.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import random
import sys
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.storage.spin_voxel import (  # noqa: E402
    SpinVector,
    SpinVoxelConfig,
    build_ring_edges,
    harmonic_scaling_spin_voxel,
    normalize_spin,
    t_phase_factor,
)


@dataclass(frozen=True)
class FieldSample:
    label: int
    lane: str
    pair_id: int
    spins: list[SpinVector]


def _unit_xy(theta: float) -> SpinVector:
    return normalize_spin((math.cos(theta), math.sin(theta), 0.0))


def _rotate(values: Sequence[SpinVector], offset: int) -> list[SpinVector]:
    if not values:
        return []
    n = len(values)
    k = offset % n
    return list(values[k:]) + list(values[:k])


def _alternating_half_turn_order(spins: Sequence[SpinVector]) -> list[SpinVector]:
    if len(spins) % 2 != 0:
        raise ValueError("spin_count must be even for the same-inventory boundary pair")
    half = len(spins) // 2
    ordered: list[SpinVector] = []
    for i in range(half):
        ordered.append(spins[i])
        ordered.append(spins[i + half])
    return ordered


def build_same_inventory_samples(
    *, sample_pairs: int, spin_count: int, seed: int
) -> list[FieldSample]:
    if sample_pairs < 1:
        raise ValueError("sample_pairs must be >= 1")
    if spin_count < 4 or spin_count % 2 != 0:
        raise ValueError("spin_count must be an even integer >= 4")

    rng = random.Random(seed)
    samples: list[FieldSample] = []
    for pair_id in range(sample_pairs):
        phase = rng.uniform(0.0, 2.0 * math.pi)
        inventory = [
            _unit_xy(phase + ((2.0 * math.pi * i) / spin_count))
            for i in range(spin_count)
        ]
        smooth = _rotate(inventory, rng.randrange(spin_count))
        boundary = _alternating_half_turn_order(smooth)
        samples.append(
            FieldSample(
                label=0, lane="smooth_same_inventory", pair_id=pair_id, spins=smooth
            )
        )
        samples.append(
            FieldSample(
                label=1, lane="boundary_same_inventory", pair_id=pair_id, spins=boundary
            )
        )
    return samples


def _auc(labels: Sequence[int], scores: Sequence[float]) -> float:
    positives = [score for label, score in zip(labels, scores) if label == 1]
    negatives = [score for label, score in zip(labels, scores) if label == 0]
    if not positives or not negatives:
        raise ValueError("AUC requires at least one positive and one negative sample")

    wins = 0.0
    total = len(positives) * len(negatives)
    for pos in positives:
        for neg in negatives:
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5
    return wins / total


def _percentile(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * q
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    fraction = rank - lower
    return (ordered[lower] * (1.0 - fraction)) + (ordered[upper] * fraction)


def _spin_multiplier(
    spins: list[SpinVector],
    *,
    edges: list[tuple[int, int]],
    config: SpinVoxelConfig,
    d: float,
    r: float,
    intent_norm: float,
    phase: str,
) -> float:
    base = (r ** (d**2)) * (t_phase_factor(phase) / max(intent_norm, config.epsilon))
    cost = harmonic_scaling_spin_voxel(
        d=d,
        r=r,
        intent_norm=intent_norm,
        spins=spins,
        phase=phase,  # type: ignore[arg-type]
        edges=edges,
        config=config,
    )
    return cost / base


def _shuffled(spins: Sequence[SpinVector], rng: random.Random) -> list[SpinVector]:
    shuffled = list(spins)
    rng.shuffle(shuffled)
    return shuffled


def run_probe(
    *,
    sample_pairs: int = 48,
    spin_count: int = 64,
    null_trials: int = 200,
    seed: int = 1729,
    margin: float = 0.05,
) -> dict[str, object]:
    if null_trials < 1:
        raise ValueError("null_trials must be >= 1")

    config = SpinVoxelConfig(
        alpha=0.35, exchange_j=0.0, external_field=(0.0, 0.0, 0.0), spin_reference=1.0
    )
    edges = build_ring_edges(spin_count)
    samples = build_same_inventory_samples(
        sample_pairs=sample_pairs, spin_count=spin_count, seed=seed
    )
    labels = [sample.label for sample in samples]

    score_kwargs = {
        "edges": edges,
        "config": config,
        "d": 6.0,
        "r": 1.35,
        "intent_norm": 1.0,
        "phase": "fast",
    }
    real_scores = [_spin_multiplier(sample.spins, **score_kwargs) for sample in samples]
    real_auc = _auc(labels, real_scores)

    null_rng = random.Random(seed + 10_000)
    null_aucs: list[float] = []
    for _ in range(null_trials):
        null_scores = [
            _spin_multiplier(_shuffled(sample.spins, null_rng), **score_kwargs)
            for sample in samples
        ]
        null_aucs.append(_auc(labels, null_scores))

    smooth_scores = [
        score for sample, score in zip(samples, real_scores) if sample.label == 0
    ]
    boundary_scores = [
        score for sample, score in zip(samples, real_scores) if sample.label == 1
    ]
    null95 = _percentile(null_aucs, 0.95)
    delta_vs_null95 = real_auc - null95
    verdict = (
        "FIELD_TOPOLOGY_SIGNAL"
        if real_auc > null95 + margin
        and _percentile(boundary_scores, 0.5) > _percentile(smooth_scores, 0.5)
        else "NULL_MATCHED_DECORATIVE"
    )

    return {
        "schema_version": "scbe_spin_voxel_null_gate_v1",
        "verdict": verdict,
        "claim_boundary": (
            "Controlled same-inventory vector-field topology probe. Validates angular-neighborhood signal only; "
            "does not validate magnetic, topological, quantum, or production security claims."
        ),
        "sample_pairs": sample_pairs,
        "spin_count": spin_count,
        "null_trials": null_trials,
        "seed": seed,
        "metric": {
            "real_auc": round(real_auc, 6),
            "shuffle_inventory_null_auc_mean": round(
                sum(null_aucs) / len(null_aucs), 6
            ),
            "shuffle_inventory_null_auc_p95": round(null95, 6),
            "delta_real_minus_null95": round(delta_vs_null95, 6),
            "margin_required": margin,
        },
        "multipliers": {
            "smooth_median": round(_percentile(smooth_scores, 0.5), 6),
            "boundary_median": round(_percentile(boundary_scores, 0.5), 6),
            "boundary_over_smooth_median": round(
                _percentile(boundary_scores, 0.5)
                / max(_percentile(smooth_scores, 0.5), 1e-12),
                6,
            ),
        },
        "null_auc": {
            "min": round(min(null_aucs), 6),
            "p50": round(_percentile(null_aucs, 0.5), 6),
            "p95": round(null95, 6),
            "max": round(max(null_aucs), 6),
        },
        "control": {
            "null_type": "per-sample spin-order shuffle",
            "preserves": ["spin_count", "unit_magnitudes", "exact_vector_inventory"],
            "destroys": ["ring_neighborhood_topology", "boundary_order"],
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-pairs", type=int, default=48)
    parser.add_argument("--spin-count", type=int, default=64)
    parser.add_argument("--null-trials", type=int, default=200)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--margin", type=float, default=0.05)
    parser.add_argument("--out", type=Path, help="Optional JSON output path.")
    args = parser.parse_args(argv)

    payload = run_probe(
        sample_pairs=args.sample_pairs,
        spin_count=args.spin_count,
        null_trials=args.null_trials,
        seed=args.seed,
        margin=args.margin,
    )
    text = json.dumps(payload, indent=2)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
