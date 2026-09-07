"""Render the bounded dual-trit/torus toy-LWE benchmark summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

METHODS = (
    ("dual_trit_phase", "Phase"),
    ("uniform_random", "Random"),
    ("dual_trit_phase_then_torus", "Phase + torus"),
    ("random_then_torus", "Random + torus"),
    ("center_then_torus", "Center + torus"),
)


def _mean(value: dict[str, int]) -> float:
    return value["numerator"] / value["denominator"]


def plot(source: Path, output: Path) -> None:
    report = json.loads(source.read_text(encoding="utf-8"))
    aggregates = report["aggregates"]
    budget = report["parameters"]["objective_budget_per_heuristic"]
    labels = [f"{label} {budget}" if key in {"dual_trit_phase", "uniform_random"} else label for key, label in METHODS]
    hits = [aggregates[key]["exact_optimum_hits"] for key, _ in METHODS]
    gaps = [_mean(aggregates[key]["mean_score_gap"]) for key, _ in METHODS]
    selected = [_mean(aggregates[key]["mean_selected_hamming_to_optimum"]) for key, _ in METHODS]
    nearest = [_mean(aggregates[key]["mean_nearest_evaluated_hamming_to_optimum"]) for key, _ in METHODS]

    figure, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    colors = ["#5a4fcf", "#999999", "#2f7d6d", "#c28e2c", "#6c6c6c"]
    axes[0].bar(labels, hits, color=colors)
    axes[0].set_title("Exact optimum hits")
    axes[0].set_ylabel(f"seeds out of {report['parameters']['seeds']}")
    axes[1].bar(labels, gaps, color=colors)
    axes[1].set_title("Mean objective gap (lower is better)")
    width = 0.38
    positions = list(range(len(labels)))
    axes[2].bar(
        [value - width / 2 for value in positions],
        selected,
        width,
        label="selected",
        color="#a34f79",
    )
    axes[2].bar(
        [value + width / 2 for value in positions],
        nearest,
        width,
        label="nearest sampled",
        color="#4f86a3",
    )
    axes[2].set_xticks(positions, labels)
    axes[2].set_title("Hamming distance to optimum")
    axes[2].legend()
    for axis in axes:
        axis.tick_params(axis="x", rotation=28)
        axis.grid(axis="y", alpha=0.2)
    exact_mean = _mean(report["controls"]["exact_interval_bound_mean_objective_evaluations"])
    seeds = report["parameters"]["seeds"]
    figure.suptitle(f"Dual-trit phase / torus toy-LWE test — {report['status']}")
    figure.text(
        0.5,
        0.01,
        f"Exact interval-bound control: {seeds}/{seeds} optima at {exact_mean:.2f} mean objective evaluations.",
        ha="center",
    )
    figure.tight_layout(rect=(0, 0.05, 1, 1))
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    plot(args.source, args.output)


if __name__ == "__main__":
    main()
