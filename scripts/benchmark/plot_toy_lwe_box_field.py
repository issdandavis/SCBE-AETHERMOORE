"""Render the toy-LWE box-field benchmark as a reviewable SVG chart."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    rows = report["rows"]

    labels = ("Exhaustive", "Exact bounds", "Bounds + four anchors")
    totals = (
        sum(row["evaluated_candidates"]["exhaustive"] for row in rows),
        sum(row["evaluated_candidates"]["bound_only"] for row in rows),
        sum(row["evaluated_candidates"]["multiscale"] for row in rows),
    )
    count = len(rows)
    means = tuple(total / count for total in totals)
    differences = [
        row["evaluated_candidates"]["bound_only"] - row["evaluated_candidates"]["multiscale"] for row in rows
    ]

    figure, (left, right) = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    bars = left.bar(labels, means, color=("#6f7782", "#2f7d6d", "#8b5e3c"))
    left.set_yscale("log")
    left.set_ylabel("Mean unique candidates evaluated (log scale)")
    left.set_title("Exact box bounds cut toy search about 12.7×")
    left.tick_params(axis="x", rotation=12)
    for bar, value in zip(bars, means, strict=True):
        left.text(bar.get_x() + bar.get_width() / 2, value * 1.08, f"{value:,.2f}", ha="center", va="bottom")

    colors = ["#2f7d6d" if value > 0 else "#b64b4b" if value < 0 else "#6f7782" for value in differences]
    right.scatter(range(len(differences)), differences, s=20, c=colors, alpha=0.85)
    right.axhline(0, color="#20252b", linewidth=1)
    right.set_xlabel("Deterministic seed")
    right.set_ylabel("Candidates saved by four anchors")
    right.set_title("Four-anchor ordering: 12 wins, 1 tie, 87 losses")

    figure.suptitle("Multiscale integer box field on 100 tiny LWE instances", fontsize=14)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, format=args.output.suffix.removeprefix("."), dpi=180)


if __name__ == "__main__":
    main()
