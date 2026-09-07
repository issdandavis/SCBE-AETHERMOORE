#!/usr/bin/env python3
"""Plot the frozen-canvas target estimate and response-rank measurements."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

DEFAULT_INPUT = Path("docs/research/evidence/frozen_neural_canvas_20260907.json")
DEFAULT_OUTPUT = Path("docs/research/evidence/frozen_neural_canvas_20260907.png")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = json.loads(args.input.read_text(encoding="utf-8"))

    methods = ("direct_residual", "linear_canvas", "clipped_canvas", "random")
    labels = ("Direct residual", "Linear canvas", "Clipped canvas", "Random")
    means = [100 * result["aggregate_accuracy"][name]["mean"] for name in methods]
    errors = [100 * result["aggregate_accuracy"][name]["population_sd"] for name in methods]

    rows = result["rows"]
    layers = range(len(rows[0]["mean_slope_rank"]))
    slope = [sum(row["mean_slope_rank"][layer]["decimal"] for row in rows) / len(rows) for layer in layers]
    curvature = [sum(row["mean_curvature_rank"][layer]["decimal"] for row in rows) / len(rows) for layer in layers]

    figure, axes = plt.subplots(1, 2, figsize=(11, 4.3), constrained_layout=True)
    axes[0].bar(labels, means, yerr=errors, capsize=5, color=("#315f72", "#8299a4", "#b36b3f", "#888888"))
    axes[0].axhline(100 / 3, color="#222222", linestyle="--", linewidth=1, label="1/3 chance")
    axes[0].set_ylabel("Coordinate estimate accuracy (%)")
    axes[0].set_ylim(28, 36)
    axes[0].tick_params(axis="x", rotation=18)
    axes[0].legend(frameon=False)
    axes[0].set_title("No target-estimation advantage")

    positions = list(layers)
    axes[1].bar([value - 0.18 for value in positions], slope, width=0.36, label="Slope rank", color="#315f72")
    axes[1].bar(
        [value + 0.18 for value in positions],
        curvature,
        width=0.36,
        label="Curvature rank",
        color="#b36b3f",
    )
    axes[1].axhline(8, color="#222222", linestyle="--", linewidth=1, label="Maximum")
    axes[1].set_xticks(positions, [f"Layer {value + 1}" for value in positions])
    axes[1].set_ylabel("Exact response-matrix rank")
    axes[1].set_ylim(0, 8.8)
    axes[1].legend(frameon=False)
    axes[1].set_title("Untouched response spans all 8 probes")

    figure.suptitle("Frozen neural canvas: rich fingerprint, no new search information", fontsize=13)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180)
    plt.close(figure)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
