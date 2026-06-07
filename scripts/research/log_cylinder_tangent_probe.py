"""Log-cylinder tangent probe.

This tests the user's offset frame:

    start  = log(n)
    left   = log(n) - log(n - 1)
    right  = log(n + 2) - log(n)
    angle  = 0 if Liouville lambda(n)=+1 else pi if lambda(n)=-1

The +2 offset bypasses the trivial n -> n+1 parity flip. The question is whether
the +2 tangent vectors flow in parallel lanes or mix chaotically on the
Liouville-parity log cylinder.

This is a finite-window, research-only probe.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research.prime_boundary_spectrum_null import factorize, simple_sieve

DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "log_cylinder_tangent_probe"
WHEEL_MODULUS = 30
WHEEL_RESIDUES = (1, 7, 11, 13, 17, 19, 23, 29)


@dataclass(frozen=True)
class CylinderPoint:
    n: int
    log_n: float
    liouville: int
    angle: float
    left_tangent: float
    right_tangent: float
    delta_angle_plus2: float
    residue_mod_30: int
    is_prime: bool
    boundary_left_big_omega: int
    horizon_plus2_big_omega: int


def big_omega(value: int, factor_primes: Sequence[int]) -> int:
    return sum(factorize(value, factor_primes).values())


def liouville_lambda(value: int, factor_primes: Sequence[int]) -> int:
    omega_total = big_omega(value, factor_primes)
    return 1 if omega_total % 2 == 0 else -1


def is_prime_from_factors(value: int, factor_primes: Sequence[int]) -> bool:
    return value >= 2 and factorize(value, factor_primes) == {value: 1}


def build_points(limit: int = 50_000) -> list[CylinderPoint]:
    if limit < 10:
        raise ValueError("limit must be at least 10")
    factor_primes = simple_sieve(int(math.sqrt(limit + 2)) + 8)
    points: list[CylinderPoint] = []
    for n in range(3, limit - 2):
        lam = liouville_lambda(n, factor_primes)
        lam_plus2 = liouville_lambda(n + 2, factor_primes)
        angle = 0.0 if lam > 0 else math.pi
        angle_plus2 = 0.0 if lam_plus2 > 0 else math.pi
        points.append(
            CylinderPoint(
                n=n,
                log_n=math.log(n),
                liouville=lam,
                angle=angle,
                left_tangent=math.log(n) - math.log(n - 1),
                right_tangent=math.log(n + 2) - math.log(n),
                delta_angle_plus2=abs(angle_plus2 - angle),
                residue_mod_30=n % WHEEL_MODULUS,
                is_prime=is_prime_from_factors(n, factor_primes),
                boundary_left_big_omega=big_omega(n - 1, factor_primes),
                horizon_plus2_big_omega=big_omega(n + 2, factor_primes),
            )
        )
    return points


def lane_flip_rates(points: Sequence[CylinderPoint]) -> dict[str, object]:
    by_residue: dict[int, list[CylinderPoint]] = defaultdict(list)
    for point in points:
        by_residue[point.residue_mod_30].append(point)

    residue_rates = {}
    for residue, lane in sorted(by_residue.items()):
        if not lane:
            continue
        flips = sum(point.delta_angle_plus2 > 0.0 for point in lane)
        residue_rates[str(residue)] = flips / len(lane)

    admissible = [point for point in points if point.residue_mod_30 in WHEEL_RESIDUES]
    non_admissible = [
        point for point in points if point.residue_mod_30 not in WHEEL_RESIDUES
    ]

    def rate(items: Sequence[CylinderPoint]) -> float:
        return sum(point.delta_angle_plus2 > 0.0 for point in items) / max(
            len(items), 1
        )

    return {
        "overall_flip_rate": rate(points),
        "admissible_flip_rate": rate(admissible),
        "non_admissible_flip_rate": rate(non_admissible),
        "residue_flip_rates": residue_rates,
        "residue_rate_spread": max(residue_rates.values())
        - min(residue_rates.values()),
    }


def tangent_parallelism(points: Sequence[CylinderPoint]) -> dict[str, float]:
    ratios = [point.right_tangent / max(point.left_tangent, 1e-12) for point in points]
    mean = sum(ratios) / len(ratios)
    variance = sum((value - mean) ** 2 for value in ratios) / len(ratios)
    return {
        "right_left_ratio_mean": mean,
        "right_left_ratio_std": math.sqrt(variance),
        "right_left_ratio_min": min(ratios),
        "right_left_ratio_max": max(ratios),
    }


def shuffled_angle_null_spread(
    points: Sequence[CylinderPoint], trials: int = 200, seed: int = 67
) -> float:
    rng = random.Random(seed)
    residues = [point.residue_mod_30 for point in points]
    lambdas = [point.liouville for point in points]
    spreads: list[float] = []
    for _trial in range(trials):
        shuffled = list(lambdas)
        rng.shuffle(shuffled)
        by_residue: dict[int, list[int]] = defaultdict(list)
        for residue, lam in zip(residues, shuffled):
            by_residue[residue].append(lam)
        rates = []
        for residue in sorted(by_residue):
            lane = by_residue[residue]
            # Randomized proxy for plus2 flips under destroyed local order.
            flips = sum(1 for idx in range(len(lane) - 1) if lane[idx] != lane[idx + 1])
            rates.append(flips / max(len(lane) - 1, 1))
        spreads.append(max(rates) - min(rates))
    return sorted(spreads)[int(math.ceil(0.95 * len(spreads))) - 1]


def run_probe(
    limit: int = 50_000,
    null_trials: int = 200,
    seed: int = 67,
    out_dir: Path | None = None,
) -> dict[str, object]:
    points = build_points(limit=limit)
    lane_metrics = lane_flip_rates(points)
    parallel_metrics = tangent_parallelism(points)
    null_spread95 = shuffled_angle_null_spread(points, trials=null_trials, seed=seed)
    residue_spread = float(lane_metrics["residue_rate_spread"])
    survives = residue_spread > null_spread95
    verdict = (
        "PLUS2_TANGENT_RESIDUE_LANES" if survives else "PLUS2_TANGENT_PARITY_MIXED"
    )

    summary: dict[str, object] = {
        "limit": limit,
        "n_points": len(points),
        "lane_metrics": lane_metrics,
        "parallel_metrics": parallel_metrics,
        "nulls": {
            "shuffled_angle_residue_spread_p95": null_spread95,
            "residue_spread_margin": residue_spread - null_spread95,
        },
        "decision_record": {
            "promotion": "QUARANTINE_RESEARCH_ONLY",
            "verdict": verdict,
            "survives_shuffled_angle_null": survives,
            "claim_boundary": (
                "Finite Liouville-parity log-cylinder probe with offsets -1 and +2. "
                "Does not prove asymptotic lane behavior."
            ),
        },
    }
    if out_dir is not None:
        write_artifacts(points, summary, out_dir)
    return summary


def write_artifacts(
    points: Sequence[CylinderPoint],
    summary: dict[str, object],
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    sample = [asdict(point) for point in points[: min(len(points), 10_000)]]
    (out_dir / "points_sample.json").write_text(
        json.dumps(sample, indent=2), encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=50_000)
    parser.add_argument("--null-trials", type=int, default=200)
    parser.add_argument("--seed", type=int, default=67)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_probe(
        limit=args.limit,
        null_trials=args.null_trials,
        seed=args.seed,
        out_dir=args.out_dir,
    )
    print(json.dumps(summary["lane_metrics"], indent=2, sort_keys=True))
    print(json.dumps(summary["parallel_metrics"], indent=2, sort_keys=True))
    print(json.dumps(summary["nulls"], indent=2, sort_keys=True))
    print(json.dumps(summary["decision_record"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
