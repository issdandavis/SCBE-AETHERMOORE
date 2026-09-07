"""Plot exact-work and locality results from the fractional-route benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def _mean(ratio: dict[str, int]) -> float:
    return ratio["numerator"] / ratio["denominator"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))

    labels = ["Exact bound", "Fractional route", "Random route"]
    evaluations = [
        _mean(report["baseline"]["mean_total_objective_evaluations"]),
        _mean(report["method_aggregates"]["fractional_zero_last"]["mean_total_objective_evaluations"]),
        _mean(report["method_aggregates"]["random_acquisition"]["mean_total_objective_evaluations"]),
    ]
    locality = report["matrix_locality_diagnostic"]["pair_order_association"]
    locality_labels = ["Matrix to\nhidden target", "Matrix to\npublic foothold", "Raw Hamming to\nhidden target"]
    gammas = [
        _mean(locality["matrix_to_hidden_target"]["gamma"]),
        _mean(locality["matrix_to_public_foothold"]["gamma"]),
        _mean(locality["hamming_to_hidden_target"]["gamma"]),
    ]

    figure, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].bar(labels, evaluations, color=["#264653", "#e76f51", "#8d99ae"])
    axes[0].set_ylabel("Mean unique objective evaluations")
    axes[0].set_title("Acquire, then certify exact optimum")
    axes[0].tick_params(axis="x", rotation=12)
    for index, value in enumerate(evaluations):
        axes[0].text(index, value + max(evaluations) * 0.015, f"{value:.2f}", ha="center")

    axes[1].bar(locality_labels, gammas, color=["#2a9d8f", "#457b9d", "#e9c46a"])
    axes[1].axhline(0, color="black", linewidth=0.8)
    axes[1].set_ylim(-1, 1)
    axes[1].set_ylabel("Pair-order gamma")
    axes[1].set_title("Diagnostic locality to hidden target")
    for index, value in enumerate(gammas):
        axes[1].text(index, value + (0.04 if value >= 0 else -0.08), f"{value:.3f}", ha="center")

    figure.suptitle("Exact integer toy-LWE fractional route test")
    figure.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180)


if __name__ == "__main__":
    main()
