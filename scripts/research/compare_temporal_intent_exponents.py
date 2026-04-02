#!/usr/bin/env python3
"""
Compare temporal-intent harmonic exponents on the live SCBE governance surface.

This script does not alter the current production formula. It evaluates the
current temporal-intent wall

    H_eff(d, R, x) = R ** (d ** alpha * x)

across multiple candidate exponents while preserving the production constants:

    R = 1.5
    x = temporal intent persistence factor

The goal is to show where each exponent is stricter, where each one separates
threshold crossings more sharply, and how that interacts with the governed
loop's intent-over-time semantics.

Outputs:
    - JSON summary with threshold crossings and sharpness integrals
    - layered PNG plots under artifacts/research/

Important:
    `src/harmonic/driftTracker.ts` thresholds are included as downstream drift
    diagnostics. They are not the same axis as the temporal-intent wall, so
    this script reports them in metadata rather than forcing a fake overlay.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from spiralverse.temporal_intent import R_HARMONIC, TemporalSecurityGate, harmonic_wall_temporal


PHI = (1.0 + math.sqrt(5.0)) / 2.0
EXPONENTS: Dict[str, float] = {
    "1.5": 1.5,
    "phi": PHI,
    "sqrt2": math.sqrt(2.0),
    "2": 2.0,  # current production baseline
    "e": math.e,
}


@dataclass(frozen=True)
class DriftThresholds:
    synthetic_cv_threshold: float
    genuine_fractal_min: float


@dataclass(frozen=True)
class ThresholdPoint:
    x_factor: float
    crossing_distance: float
    sharpness: float


@dataclass(frozen=True)
class ExponentSummary:
    alpha_name: str
    alpha_value: float
    allow_curve: List[ThresholdPoint]
    quarantine_curve: List[ThresholdPoint]
    integrated_allow_sharpness: float
    integrated_quarantine_sharpness: float
    mean_allow_crossing: float
    mean_quarantine_crossing: float


def linspace(start: float, stop: float, steps: int) -> List[float]:
    if steps <= 1:
        return [start]
    width = stop - start
    return [start + width * (idx / (steps - 1)) for idx in range(steps)]


def load_drift_thresholds(path: Path | None = None) -> DriftThresholds:
    source = path or (REPO_ROOT / "src" / "harmonic" / "driftTracker.ts")
    text = source.read_text(encoding="utf-8")
    synthetic_match = re.search(r"const SYNTHETIC_CV_THRESHOLD = ([0-9.]+);", text)
    fractal_match = re.search(r"const GENUINE_FRACTAL_MIN = ([0-9.]+);", text)
    if synthetic_match is None or fractal_match is None:
        raise ValueError(f"Could not parse drift thresholds from {source}")
    return DriftThresholds(
        synthetic_cv_threshold=float(synthetic_match.group(1)),
        genuine_fractal_min=float(fractal_match.group(1)),
    )


def temporal_harmonic_wall(d: float, x_factor: float, alpha: float, r_base: float = R_HARMONIC) -> float:
    if alpha == 2.0:
        return harmonic_wall_temporal(d=d, x=x_factor, R=r_base)
    return r_base ** (d**alpha * x_factor)


def temporal_harm_score(d: float, x_factor: float, alpha: float, r_base: float = R_HARMONIC) -> float:
    h_temporal = temporal_harmonic_wall(d=d, x_factor=x_factor, alpha=alpha, r_base=r_base)
    return 1.0 / (1.0 + math.log(max(1.0, h_temporal)))


def temporal_decision(
    score: float,
    allow_threshold: float = TemporalSecurityGate.ALLOW_THRESHOLD,
    quarantine_threshold: float = TemporalSecurityGate.QUARANTINE_THRESHOLD,
) -> str:
    if score > allow_threshold:
        return "ALLOW"
    if score > quarantine_threshold:
        return "QUARANTINE"
    return "DENY"


def crossing_distance(
    alpha: float,
    x_factor: float,
    threshold: float,
    r_base: float = R_HARMONIC,
) -> float:
    if x_factor <= 0.0:
        return float("nan")
    if threshold <= 0.0 or threshold >= 1.0:
        raise ValueError("Threshold must be in (0, 1)")
    coefficient = (1.0 / threshold - 1.0) / (math.log(r_base) * x_factor)
    if coefficient < 0.0:
        return float("nan")
    return coefficient ** (1.0 / alpha)


def crossing_sharpness(
    alpha: float,
    x_factor: float,
    threshold: float,
    r_base: float = R_HARMONIC,
) -> float:
    d_cross = crossing_distance(alpha=alpha, x_factor=x_factor, threshold=threshold, r_base=r_base)
    if math.isnan(d_cross):
        return float("nan")
    return threshold**2 * math.log(r_base) * x_factor * alpha * (d_cross ** (alpha - 1.0))


def integrate(points: Sequence[float], dx: float) -> float:
    return sum(points) * dx


def build_summary(
    alpha_name: str,
    alpha_value: float,
    x_values: Sequence[float],
    allow_threshold: float,
    quarantine_threshold: float,
    r_base: float,
) -> ExponentSummary:
    allow_curve = [
        ThresholdPoint(
            x_factor=x,
            crossing_distance=crossing_distance(alpha_value, x, allow_threshold, r_base),
            sharpness=crossing_sharpness(alpha_value, x, allow_threshold, r_base),
        )
        for x in x_values
    ]
    quarantine_curve = [
        ThresholdPoint(
            x_factor=x,
            crossing_distance=crossing_distance(alpha_value, x, quarantine_threshold, r_base),
            sharpness=crossing_sharpness(alpha_value, x, quarantine_threshold, r_base),
        )
        for x in x_values
    ]
    dx = x_values[1] - x_values[0] if len(x_values) > 1 else 1.0
    return ExponentSummary(
        alpha_name=alpha_name,
        alpha_value=alpha_value,
        allow_curve=allow_curve,
        quarantine_curve=quarantine_curve,
        integrated_allow_sharpness=integrate([point.sharpness for point in allow_curve], dx),
        integrated_quarantine_sharpness=integrate([point.sharpness for point in quarantine_curve], dx),
        mean_allow_crossing=sum(point.crossing_distance for point in allow_curve) / len(allow_curve),
        mean_quarantine_crossing=sum(point.crossing_distance for point in quarantine_curve) / len(quarantine_curve),
    )


def plot_harm_score_overlays(
    output_path: Path,
    x_panels: Sequence[float],
    alphas: Dict[str, float],
    d_values: Sequence[float],
    allow_threshold: float,
    quarantine_threshold: float,
    r_base: float,
) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharex=True, sharey=True)
    for axis, x_factor in zip(axes.flatten(), x_panels):
        for alpha_name, alpha_value in alphas.items():
            scores = [temporal_harm_score(d=d, x_factor=x_factor, alpha=alpha_value, r_base=r_base) for d in d_values]
            axis.plot(d_values, scores, label=alpha_name, linewidth=2)
        axis.axhline(allow_threshold, color="green", linestyle="--", linewidth=1.0, label="allow threshold")
        axis.axhline(quarantine_threshold, color="orange", linestyle="--", linewidth=1.0, label="quarantine threshold")
        axis.set_title(f"x = {x_factor:.2f}")
        axis.set_xlabel("distance d")
        axis.set_ylabel("harm score / omega")
        axis.grid(alpha=0.25)
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=7, frameon=False)
    fig.suptitle("Temporal intent harmonic score overlays")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_threshold_curves(
    output_path: Path,
    summaries: Sequence[ExponentSummary],
    allow_threshold: float,
    quarantine_threshold: float,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharex=True)
    for summary in summaries:
        axes[0].plot(
            [point.x_factor for point in summary.allow_curve],
            [point.crossing_distance for point in summary.allow_curve],
            label=summary.alpha_name,
            linewidth=2,
        )
        axes[1].plot(
            [point.x_factor for point in summary.quarantine_curve],
            [point.crossing_distance for point in summary.quarantine_curve],
            label=summary.alpha_name,
            linewidth=2,
        )
    axes[0].set_title(f"ALLOW crossing distance (score={allow_threshold:.2f})")
    axes[1].set_title(f"QUARANTINE crossing distance (score={quarantine_threshold:.2f})")
    for axis in axes:
        axis.set_xlabel("temporal intent factor x")
        axis.set_ylabel("crossing distance d")
        axis.grid(alpha=0.25)
    axes[0].legend(frameon=False)
    fig.suptitle("Threshold crossing curves by exponent")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_sharpness_curves(output_path: Path, summaries: Sequence[ExponentSummary]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharex=True)
    for summary in summaries:
        axes[0].plot(
            [point.x_factor for point in summary.allow_curve],
            [point.sharpness for point in summary.allow_curve],
            label=summary.alpha_name,
            linewidth=2,
        )
        axes[1].plot(
            [point.x_factor for point in summary.quarantine_curve],
            [point.sharpness for point in summary.quarantine_curve],
            label=summary.alpha_name,
            linewidth=2,
        )
    axes[0].set_title("ALLOW threshold sharpness")
    axes[1].set_title("QUARANTINE threshold sharpness")
    for axis in axes:
        axis.set_xlabel("temporal intent factor x")
        axis.set_ylabel("|d score / dd| at threshold")
        axis.grid(alpha=0.25)
    axes[0].legend(frameon=False)
    fig.suptitle("Threshold discrimination sharpness by exponent")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def format_report(
    summaries: Sequence[ExponentSummary],
    drift_thresholds: DriftThresholds,
    allow_threshold: float,
    quarantine_threshold: float,
    x_min: float,
    x_max: float,
    r_base: float,
) -> str:
    lines = [
        "Temporal Intent Exponent Comparison",
        "==================================",
        f"Production baseline: H_eff(d, R, x) = R^(d^2 * x), R={r_base:.3f}",
        f"Temporal thresholds: ALLOW>{allow_threshold:.2f}, QUARANTINE>{quarantine_threshold:.2f}, else DENY",
        f"x-range: [{x_min:.2f}, {x_max:.2f}]",
        (
            "Downstream drift diagnostics (separate layer): "
            f"SYNTHETIC_CV_THRESHOLD={drift_thresholds.synthetic_cv_threshold:.2f}, "
            f"GENUINE_FRACTAL_MIN={drift_thresholds.genuine_fractal_min:.2f}"
        ),
        "",
        f"{'alpha':<8} {'allow_mean_d':>12} {'quarantine_mean_d':>18} {'allow_sharp':>14} {'quarantine_sharp':>18}",
    ]
    for summary in summaries:
        lines.append(
            f"{summary.alpha_name:<8} "
            f"{summary.mean_allow_crossing:>12.4f} "
            f"{summary.mean_quarantine_crossing:>18.4f} "
            f"{summary.integrated_allow_sharpness:>14.4f} "
            f"{summary.integrated_quarantine_sharpness:>18.4f}"
        )
    strongest_allow = max(summaries, key=lambda item: item.integrated_allow_sharpness)
    strongest_quarantine = max(summaries, key=lambda item: item.integrated_quarantine_sharpness)
    lines.extend(
        [
            "",
            f"Best ALLOW-boundary discriminator over x-range: {strongest_allow.alpha_name}",
            f"Best QUARANTINE-boundary discriminator over x-range: {strongest_quarantine.alpha_name}",
            "Interpretation: lower crossing distance means a stricter wall; higher sharpness means cleaner threshold separation.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--x-min", type=float, default=0.5)
    parser.add_argument("--x-max", type=float, default=3.0)
    parser.add_argument("--x-steps", type=int, default=26)
    parser.add_argument("--d-max", type=float, default=1.0)
    parser.add_argument("--d-steps", type=int, default=201)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "artifacts" / "research" / "temporal_intent")
    parser.add_argument("--json", action="store_true", help="print JSON instead of the human report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    allow_threshold = TemporalSecurityGate.ALLOW_THRESHOLD
    quarantine_threshold = TemporalSecurityGate.QUARANTINE_THRESHOLD
    drift_thresholds = load_drift_thresholds()

    x_values = linspace(args.x_min, args.x_max, args.x_steps)
    d_values = linspace(0.0, args.d_max, args.d_steps)

    summaries = [
        build_summary(
            alpha_name=name,
            alpha_value=value,
            x_values=x_values,
            allow_threshold=allow_threshold,
            quarantine_threshold=quarantine_threshold,
            r_base=R_HARMONIC,
        )
        for name, value in EXPONENTS.items()
    ]

    plot_harm_score_overlays(
        output_path=args.output_dir / "harm_score_overlays.png",
        x_panels=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
        alphas=EXPONENTS,
        d_values=d_values,
        allow_threshold=allow_threshold,
        quarantine_threshold=quarantine_threshold,
        r_base=R_HARMONIC,
    )
    plot_threshold_curves(
        output_path=args.output_dir / "threshold_crossings.png",
        summaries=summaries,
        allow_threshold=allow_threshold,
        quarantine_threshold=quarantine_threshold,
    )
    plot_sharpness_curves(output_path=args.output_dir / "threshold_sharpness.png", summaries=summaries)

    payload = {
        "r_base": R_HARMONIC,
        "allow_threshold": allow_threshold,
        "quarantine_threshold": quarantine_threshold,
        "drift_thresholds": asdict(drift_thresholds),
        "output_dir": str(args.output_dir),
        "summaries": [asdict(summary) for summary in summaries],
    }
    (args.output_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            format_report(
                summaries=summaries,
                drift_thresholds=drift_thresholds,
                allow_threshold=allow_threshold,
                quarantine_threshold=quarantine_threshold,
                x_min=args.x_min,
                x_max=args.x_max,
                r_base=R_HARMONIC,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
