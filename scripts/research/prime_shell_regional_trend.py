"""Prime shell regional trend extractor.

The prime shell is useful as a calibration/compression surface for known primes.
It should not be promoted as a prime finder unless a residual trend survives a
null. This script identifies the regional trend lines on the shell:

    compass region = p mod 30 admissible lane
    height         = log(p)
    field 1        = gap_after / log(p)  (parallelity divergence)
    field 2        = BigOmega(p+1)       (additive boundary density)

The core question: do the regional lanes have field trends beyond shuffled
assignments, or are the trends just the wheel made visible?
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research.prime_boundary_spectrum_null import (
    factorize,
    first_n_primes,
    simple_sieve,
)

DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "prime_shell_regional_trend"
ADMISSIBLE_MOD_30 = (1, 7, 11, 13, 17, 19, 23, 29)


@dataclass(frozen=True)
class PrimeShellPoint:
    prime_index: int
    prime: int
    residue_mod_30: int
    log_prime: float
    gap_after: int
    gap_divergence: float
    boundary_big_omega: int
    boundary_omega: int
    shell_theta: float
    shell_radius: float
    shell_x: float
    shell_y: float
    shell_z: float


@dataclass(frozen=True)
class LaneTrend:
    residue_mod_30: int
    count: int
    mean_log_prime: float
    mean_gap_divergence: float
    gap_slope_per_log: float
    gap_r2: float
    mean_boundary_big_omega: float
    boundary_slope_per_log: float
    boundary_r2: float
    flare_count: int


def linear_fit(xs: Sequence[float], ys: Sequence[float]) -> tuple[float, float, float]:
    """Return slope, intercept, r2 for y = slope*x + intercept."""
    if len(xs) != len(ys):
        raise ValueError("xs and ys must have the same length")
    if len(xs) < 2:
        return 0.0, ys[0] if ys else 0.0, 0.0
    x_mean = statistics.fmean(xs)
    y_mean = statistics.fmean(ys)
    ss_x = sum((x - x_mean) ** 2 for x in xs)
    if ss_x == 0:
        return 0.0, y_mean, 0.0
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / ss_x
    intercept = y_mean - slope * x_mean
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    if ss_tot == 0:
        return slope, intercept, 1.0
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    return slope, intercept, max(0.0, 1.0 - ss_res / ss_tot)


def _big_omega(factors: dict[int, int]) -> int:
    return sum(factors.values())


def build_shell_points(
    n_primes: int = 20_000, turns_per_log: float = 0.75
) -> list[PrimeShellPoint]:
    if n_primes < 10:
        raise ValueError("n_primes must be at least 10")

    primes = first_n_primes(n_primes + 1)
    factor_primes = simple_sieve(int(math.sqrt(primes[-1] + 1)) + 8)
    points: list[PrimeShellPoint] = []
    for index, prime in enumerate(primes[:-1]):
        residue = prime % 30
        if residue not in ADMISSIBLE_MOD_30:
            continue
        log_prime = math.log(prime)
        gap_after = primes[index + 1] - prime
        gap_divergence = gap_after / max(log_prime, 1e-12)
        boundary_factors = factorize(prime + 1, factor_primes)
        boundary_big_omega = _big_omega(boundary_factors)
        boundary_omega = len(boundary_factors)

        regional_bearing = 2.0 * math.pi * (residue / 30.0)
        theta = regional_bearing + turns_per_log * log_prime
        radius = 1.0 + 0.025 * log_prime + 0.035 * boundary_big_omega
        points.append(
            PrimeShellPoint(
                prime_index=index,
                prime=prime,
                residue_mod_30=residue,
                log_prime=log_prime,
                gap_after=gap_after,
                gap_divergence=gap_divergence,
                boundary_big_omega=boundary_big_omega,
                boundary_omega=boundary_omega,
                shell_theta=theta,
                shell_radius=radius,
                shell_x=radius * math.cos(theta),
                shell_y=radius * math.sin(theta),
                shell_z=log_prime,
            )
        )
    return points


def lane_trends(points: Sequence[PrimeShellPoint]) -> list[LaneTrend]:
    if not points:
        return []
    global_gap_values = sorted(point.gap_divergence for point in points)
    flare_threshold = global_gap_values[int(0.95 * (len(global_gap_values) - 1))]
    by_residue: dict[int, list[PrimeShellPoint]] = defaultdict(list)
    for point in points:
        by_residue[point.residue_mod_30].append(point)

    trends: list[LaneTrend] = []
    for residue in sorted(by_residue):
        lane = by_residue[residue]
        xs = [point.log_prime for point in lane]
        gap_values = [point.gap_divergence for point in lane]
        boundary_values = [float(point.boundary_big_omega) for point in lane]
        gap_slope, _gap_intercept, gap_r2 = linear_fit(xs, gap_values)
        boundary_slope, _boundary_intercept, boundary_r2 = linear_fit(
            xs, boundary_values
        )
        trends.append(
            LaneTrend(
                residue_mod_30=residue,
                count=len(lane),
                mean_log_prime=statistics.fmean(xs),
                mean_gap_divergence=statistics.fmean(gap_values),
                gap_slope_per_log=gap_slope,
                gap_r2=gap_r2,
                mean_boundary_big_omega=statistics.fmean(boundary_values),
                boundary_slope_per_log=boundary_slope,
                boundary_r2=boundary_r2,
                flare_count=sum(
                    point.gap_divergence >= flare_threshold for point in lane
                ),
            )
        )
    return trends


def regional_spread(points: Sequence[PrimeShellPoint], metric_name: str) -> float:
    by_residue: dict[int, list[float]] = defaultdict(list)
    for point in points:
        by_residue[point.residue_mod_30].append(float(getattr(point, metric_name)))
    means = [statistics.fmean(values) for values in by_residue.values() if values]
    if len(means) < 2:
        return 0.0
    return statistics.pstdev(means)


def null_spread_p95(
    points: Sequence[PrimeShellPoint],
    metric_name: str,
    trials: int = 200,
    seed: int = 23,
) -> float:
    rng = random.Random(seed)
    residues = [point.residue_mod_30 for point in points]
    values = [float(getattr(point, metric_name)) for point in points]
    spreads: list[float] = []
    for _trial in range(trials):
        shuffled = list(values)
        rng.shuffle(shuffled)
        by_residue: dict[int, list[float]] = defaultdict(list)
        for residue, value in zip(residues, shuffled):
            by_residue[residue].append(value)
        means = [statistics.fmean(items) for items in by_residue.values() if items]
        spreads.append(statistics.pstdev(means) if len(means) >= 2 else 0.0)
    return sorted(spreads)[int(math.ceil(0.95 * len(spreads))) - 1]


def run_probe(
    n_primes: int = 20_000,
    null_trials: int = 200,
    seed: int = 23,
    render: bool = False,
    out_dir: Path | None = None,
) -> dict[str, object]:
    points = build_shell_points(n_primes=n_primes)
    trends = lane_trends(points)
    gap_spread = regional_spread(points, "gap_divergence")
    gap_null95 = null_spread_p95(
        points, "gap_divergence", trials=null_trials, seed=seed
    )
    boundary_spread = regional_spread(points, "boundary_big_omega")
    boundary_null95 = null_spread_p95(
        points, "boundary_big_omega", trials=null_trials, seed=seed + 1000
    )

    strongest_gap_lane = max(trends, key=lambda trend: abs(trend.gap_slope_per_log))
    strongest_boundary_lane = max(
        trends, key=lambda trend: abs(trend.boundary_slope_per_log)
    )
    gap_survives = gap_spread > gap_null95
    boundary_survives = boundary_spread > boundary_null95
    verdict = (
        "REGIONAL_TREND_SURVIVES_NULL"
        if gap_survives or boundary_survives
        else "WHEEL_LANES_ONLY"
    )

    summary: dict[str, object] = {
        "n_points": len(points),
        "n_lanes": len(trends),
        "admissible_mod_30": ADMISSIBLE_MOD_30,
        "metrics": {
            "gap_regional_spread": gap_spread,
            "gap_spread_null95": gap_null95,
            "gap_spread_margin": gap_spread - gap_null95,
            "boundary_regional_spread": boundary_spread,
            "boundary_spread_null95": boundary_null95,
            "boundary_spread_margin": boundary_spread - boundary_null95,
        },
        "strongest_lanes": {
            "gap_slope": asdict(strongest_gap_lane),
            "boundary_slope": asdict(strongest_boundary_lane),
        },
        "lane_trends": [asdict(trend) for trend in trends],
        "decision_record": {
            "promotion": "QUARANTINE_RESEARCH_ONLY",
            "verdict": verdict,
            "gap_survives_null": gap_survives,
            "boundary_survives_null": boundary_survives,
            "claim_boundary": (
                "Identifies trend lines on known-prime shell lanes. It is a compression and "
                "diagnostic surface, not a prime finder unless residual trends survive stronger nulls."
            ),
        },
    }
    if out_dir is not None:
        write_artifacts(points, trends, summary, out_dir=out_dir, render=render)
    return summary


def write_artifacts(
    points: Sequence[PrimeShellPoint],
    trends: Sequence[LaneTrend],
    summary: dict[str, object],
    out_dir: Path,
    render: bool = False,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    with (out_dir / "lane_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(trends[0]).keys()))
        writer.writeheader()
        for trend in trends:
            writer.writerow(asdict(trend))
    with (out_dir / "shell_points.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(points[0]).keys()))
        writer.writeheader()
        for point in points:
            writer.writerow(asdict(point))
    if render:
        render_trends(trends, out_dir / "prime_shell_regional_trends.png")


def render_trends(trends: Sequence[LaneTrend], out_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return

    residues = [trend.residue_mod_30 for trend in trends]
    gap_means = [trend.mean_gap_divergence for trend in trends]
    boundary_means = [trend.mean_boundary_big_omega for trend in trends]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), facecolor="#0b0d10")
    for axis in axes:
        axis.set_facecolor("#0b0d10")
        axis.tick_params(colors="white")
        axis.grid(color="#2b3340", alpha=0.45)
    axes[0].bar([str(residue) for residue in residues], gap_means, color="#ffb02e")
    axes[0].set_title("Mean gap / log(p) by mod-30 lane", color="white")
    axes[0].set_xlabel("Residue lane", color="white")
    axes[0].set_ylabel("Parallelity divergence", color="white")
    axes[1].bar([str(residue) for residue in residues], boundary_means, color="#33c4ff")
    axes[1].set_title("Mean BigOmega(p+1) by mod-30 lane", color="white")
    axes[1].set_xlabel("Residue lane", color="white")
    axes[1].set_ylabel("Boundary density", color="white")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-primes", type=int, default=20_000)
    parser.add_argument("--null-trials", type=int, default=200)
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--render", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_probe(
        n_primes=args.n_primes,
        null_trials=args.null_trials,
        seed=args.seed,
        render=args.render,
        out_dir=args.out_dir,
    )
    print(json.dumps(summary["metrics"], indent=2, sort_keys=True))
    print(json.dumps(summary["decision_record"], indent=2, sort_keys=True))
    print(json.dumps(summary["strongest_lanes"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
