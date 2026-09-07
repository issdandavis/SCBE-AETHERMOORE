"""Plot the geometric correction separately from toy-LWE outcomes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def ratio(value: dict[str, int]) -> float:
    return value["numerator"] / value["denominator"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = json.loads(args.source.read_text(encoding="utf-8"))
    coverage = report["coverage"]
    legacy = coverage["legacy_phase"]
    corrected = coverage["orbit_cover_phase"]
    random = coverage["uniform_random"]
    heuristics = report["heuristic_aggregates"]
    bounds = report["bound_aggregates"]

    geometric_labels = ["legacy phase", "orbit cover", "random mean"]
    nearest = [
        legacy["nearest_distance_sum"] / legacy["total_space"],
        corrected["nearest_distance_sum"] / corrected["total_space"],
        ratio(random["nearest_distance_sum"]) / corrected["total_space"],
    ]
    coordinate = [
        legacy["max_coordinate_discrepancy_scaled_by_three"] / 3,
        corrected["max_coordinate_discrepancy_scaled_by_three"] / 3,
        ratio(random["max_coordinate_discrepancy_scaled_by_three"]) / 3,
    ]
    pair = [
        legacy["max_pair_cell_discrepancy_scaled_by_nine"] / 9,
        corrected["max_pair_cell_discrepancy_scaled_by_nine"] / 9,
        ratio(random["max_pair_cell_discrepancy_scaled_by_nine"]) / 9,
    ]

    figure, axes = plt.subplots(2, 2, figsize=(12, 8.2))
    figure.suptitle("Dual-trit phase debiasing: geometry improved, toy-LWE speed did not", fontsize=15, weight="bold")
    colors = ["#a64b3c", "#287a6a", "#6382a8"]

    axes[0, 0].bar(geometric_labels, nearest, color=colors)
    axes[0, 0].set_title("Whole-space mean nearest Hamming distance")
    axes[0, 0].set_ylabel("lower is better")
    axes[0, 0].bar_label(axes[0, 0].containers[0], fmt="%.3f")

    positions = range(len(geometric_labels))
    width = 0.36
    axes[0, 1].bar([value - width / 2 for value in positions], coordinate, width, label="coordinate", color="#8064a2")
    axes[0, 1].bar([value + width / 2 for value in positions], pair, width, label="pair cell", color="#d28c3c")
    axes[0, 1].set_xticks(list(positions), geometric_labels)
    axes[0, 1].set_title("Maximum count deviation from uniform")
    axes[0, 1].set_ylabel("lower is better")
    axes[0, 1].legend(frameon=False)

    hit_labels = ["legacy phase", "orbit cover", "random", "orbit + torus", "random + torus"]
    hit_keys = [
        "legacy_phase",
        "orbit_cover_phase",
        "uniform_random",
        "orbit_cover_phase_then_torus",
        "random_then_torus",
    ]
    hits = [heuristics[key]["exact_optimum_hits"] for key in hit_keys]
    axes[1, 0].bar(hit_labels, hits, color=[colors[0], colors[1], colors[2], "#4b927f", "#7895b7"])
    axes[1, 0].set_title("Exact optimum hits on 300 fresh toy-LWE seeds")
    axes[1, 0].set_ylabel("higher is better")
    axes[1, 0].tick_params(axis="x", rotation=18)
    axes[1, 0].bar_label(axes[1, 0].containers[0])

    bound_labels = ["algebraic bound", "+ 60 orbit probes", "+ 60 random probes"]
    bound_keys = ["bound_only", "orbit_cover_seeded_bound", "random_seeded_bound"]
    evaluations = [ratio(bounds[key]["mean_total_objective_evaluations"]) for key in bound_keys]
    axes[1, 1].bar(bound_labels, evaluations, color=["#3d6b8f", colors[1], colors[2]])
    axes[1, 1].set_title("Exact solve: total objective evaluations")
    axes[1, 1].set_ylabel("lower is better")
    axes[1, 1].tick_params(axis="x", rotation=12)
    axes[1, 1].bar_label(axes[1, 1].containers[0], fmt="%.1f")

    figure.text(
        0.5,
        0.012,
        "Complete phase orbits remove lossy sign/prefix bias. Algebraic bounds remain the only pruning authority.",
        ha="center",
        fontsize=10,
    )
    figure.tight_layout(rect=(0, 0.04, 1, 0.95))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180)


if __name__ == "__main__":
    main()
