"""Reproducible benchmark for the exact-integer toy LWE box-field search."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.crypto import toy_lwe_box_field as B


def run(seeds: int, dimension: int, samples: int, output: Path) -> dict[str, object]:
    if seeds < 2:
        raise ValueError("benchmark needs at least two seeds")
    rows = []
    for seed in range(seeds):
        instance = B.generate_toy_lwe(seed, dimension=dimension, samples=samples, modulus=97)
        exhaustive = B.exhaustive_search(instance)
        bound_only = B.box_field_search(instance, strategy="bound-only")
        multiscale = B.box_field_search(instance, strategy="multiscale")
        if (bound_only.score, bound_only.candidate) != (exhaustive.score, exhaustive.candidate):
            raise RuntimeError("bound-only search disagreed with exhaustive ground truth")
        if (multiscale.score, multiscale.candidate) != (exhaustive.score, exhaustive.candidate):
            raise RuntimeError("multiscale search disagreed with exhaustive ground truth")
        rows.append(
            {
                "seed": seed,
                "planted_recovered": exhaustive.candidate == instance.planted_secret,
                "optimum": {"candidate": exhaustive.candidate, "score": exhaustive.score},
                "evaluated_candidates": {
                    "exhaustive": exhaustive.evaluated_candidates,
                    "bound_only": bound_only.evaluated_candidates,
                    "multiscale": multiscale.evaluated_candidates,
                },
                "boxes_opened": {
                    "bound_only": bound_only.boxes_opened,
                    "multiscale": multiscale.boxes_opened,
                },
                "boxes_pruned": {
                    "bound_only": bound_only.boxes_pruned,
                    "multiscale": multiscale.boxes_pruned,
                },
            }
        )

    exhaustive_counts = [row["evaluated_candidates"]["exhaustive"] for row in rows]
    bound_counts = [row["evaluated_candidates"]["bound_only"] for row in rows]
    multiscale_counts = [row["evaluated_candidates"]["multiscale"] for row in rows]
    differences = [bound - multi for bound, multi in zip(bound_counts, multiscale_counts, strict=True)]
    difference_sum = sum(differences)
    scaled_squared_deviations = sum((seeds * value - difference_sum) ** 2 for value in differences)
    report = {
        "schema": "scbe.toy-lwe-box-field-benchmark.v1",
        "status": "TOY_EXPERIMENT_ONLY",
        "integer_arithmetic_only": True,
        "parameters": {
            "seeds": seeds,
            "dimension": dimension,
            "samples": samples,
            "modulus": 97,
            "secret_values": [-1, 0, 1],
        },
        "ground_truth_agreement": True,
        "planted_secret_recoveries": sum(row["planted_recovered"] for row in rows),
        "mean_evaluated_candidates": {
            "exhaustive": {"numerator": sum(exhaustive_counts), "denominator": seeds},
            "bound_only": {"numerator": sum(bound_counts), "denominator": seeds},
            "multiscale": {"numerator": sum(multiscale_counts), "denominator": seeds},
        },
        "aggregate_candidate_reduction": {
            "exhaustive_over_bound_only": {"numerator": sum(exhaustive_counts), "denominator": sum(bound_counts)},
            "exhaustive_over_multiscale": {"numerator": sum(exhaustive_counts), "denominator": sum(multiscale_counts)},
        },
        "multiscale_minus_bound_only": {
            "mean_saved_candidates": {"numerator": difference_sum, "denominator": seeds},
            "scaled_squared_deviations_sum": scaled_squared_deviations,
            "scaled_deviation_denominator": seeds**3,
            "absolute_effect_exceeds_two_population_sd": difference_sum * difference_sum * seeds
            > 4 * scaled_squared_deviations,
            "wins": sum(value > 0 for value in differences),
            "ties": sum(value == 0 for value in differences),
            "losses": sum(value < 0 for value in differences),
        },
        "interpretation": "Paired exact work counts; no deployed-cryptography claim follows.",
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=30)
    parser.add_argument("--dimension", type=int, default=8)
    parser.add_argument("--samples", type=int, default=14)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.seeds, args.dimension, args.samples, args.output)
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))


if __name__ == "__main__":
    main()
