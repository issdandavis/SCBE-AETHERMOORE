"""Benchmark matrix locality and exact fractional acquire-then-certify search."""

from __future__ import annotations

import argparse
import hashlib
from itertools import combinations
import json
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.crypto import toy_lwe_box_field as BOX
from src.crypto import toy_lwe_fractional_route as ROUTE
from src.crypto import toy_lwe_phase_search as PHASE

METHODS = (
    "lower_bound_acquisition",
    "midpoint_acquisition",
    "fractional_zero_first",
    "fractional_zero_last",
    "random_acquisition",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ratio(values: list[int]) -> dict[str, int]:
    return {"numerator": sum(values), "denominator": len(values)}


def _paired_effect(preferred: list[int], control: list[int]) -> dict[str, object]:
    """Measure saved work for a lower-is-better preferred method."""

    if len(preferred) != len(control) or not preferred:
        raise ValueError("paired panels must be nonempty and equally sized")
    differences = [right - left for left, right in zip(preferred, control, strict=True)]
    count = len(differences)
    difference_sum = sum(differences)
    scaled_squared_deviations = sum((count * value - difference_sum) ** 2 for value in differences)
    exceeds = difference_sum * difference_sum * count > 4 * scaled_squared_deviations
    return {
        "mean_saved_objective_evaluations": {"numerator": difference_sum, "denominator": count},
        "wins": sum(value > 0 for value in differences),
        "ties": sum(value == 0 for value in differences),
        "losses": sum(value < 0 for value in differences),
        "effect_exceeds_two_population_sd": exceeds,
        "improvement_exceeds_two_population_sd": difference_sum > 0 and exceeds,
        "harm_exceeds_two_population_sd": difference_sum < 0 and exceeds,
        "scaled_squared_deviations_sum": scaled_squared_deviations,
        "scaled_deviation_denominator": count**3,
    }


def _association(metric: list[int], objective: list[int]) -> dict[str, object]:
    """Return an exact pair-order association without floating-point math."""

    if len(metric) != len(objective) or len(metric) < 2:
        raise ValueError("association vectors must have the same nontrivial length")
    concordant = 0
    discordant = 0
    ties = 0
    for left, right in combinations(range(len(metric)), 2):
        product = (metric[left] - metric[right]) * (objective[left] - objective[right])
        if product > 0:
            concordant += 1
        elif product < 0:
            discordant += 1
        else:
            ties += 1
    return {
        "concordant": concordant,
        "discordant": discordant,
        "ties": ties,
        "gamma": {
            "numerator": concordant - discordant,
            "denominator": concordant + discordant,
        },
    }


def _method_arguments(name: str, seed: int) -> dict[str, object]:
    if name == "lower_bound_acquisition":
        return {"policy": "lower-bound"}
    if name == "midpoint_acquisition":
        return {"policy": "midpoint"}
    if name == "fractional_zero_first":
        return {"policy": "fractional-space", "zero_policy": "first"}
    if name == "fractional_zero_last":
        return {"policy": "fractional-space", "zero_policy": "last"}
    if name == "random_acquisition":
        return {"policy": "random", "random_seed": 19_000_000 + seed}
    raise ValueError(name)


def _source_receipts() -> dict[str, dict[str, str]]:
    paths = {
        "benchmark_driver": Path(__file__).resolve(),
        "fractional_route": Path(ROUTE.__file__).resolve(),
        "exact_box_bounds": Path(BOX.__file__).resolve(),
        "finite_trit_controls": Path(PHASE.__file__).resolve(),
        "prior_directional_zero_notes": Path(r"C:\dev\loom\signed_zero_division.py"),
        "prior_fractional_pole_notes": Path(r"C:\dev\loom\fractional_degree_well.py"),
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"source receipt inputs are missing: {missing}")
    return {name: {"path": str(path), "sha256": _sha256(path)} for name, path in paths.items()}


def run(
    *,
    seed_start: int,
    seeds: int,
    dimension: int,
    samples: int,
    locality_candidates: int,
    exhaustive_audit_seeds: int,
    output: Path,
) -> dict[str, object]:
    if seed_start < 0 or seeds < 3:
        raise ValueError("benchmark requires at least three nonnegative paired seeds")
    if not 2 <= locality_candidates <= 3**dimension:
        raise ValueError("locality panel is outside the finite candidate space")
    if not 0 <= exhaustive_audit_seeds <= seeds:
        raise ValueError("exhaustive audit count is outside the benchmark panel")

    rows: list[dict[str, object]] = []
    locality_totals = {
        "matrix_to_hidden_target": {"concordant": 0, "discordant": 0, "ties": 0},
        "matrix_to_public_foothold": {"concordant": 0, "discordant": 0, "ties": 0},
        "matrix_to_zero_anchor": {"concordant": 0, "discordant": 0, "ties": 0},
        "hamming_to_hidden_target": {"concordant": 0, "discordant": 0, "ties": 0},
    }
    for offset in range(seeds):
        seed = seed_start + offset
        instance = BOX.generate_toy_lwe(seed, dimension=dimension, samples=samples, modulus=97)
        baseline_started = time.perf_counter_ns()
        truth = BOX.box_field_search(instance, strategy="bound-only")
        baseline_elapsed_ns = time.perf_counter_ns() - baseline_started
        if truth.candidate != instance.planted_secret:
            raise RuntimeError("exact bound did not recover the planted toy secret")
        exhaustive_audited = offset < exhaustive_audit_seeds
        if exhaustive_audited:
            exhaustive = BOX.exhaustive_search(instance)
            if (truth.score, truth.candidate) != (exhaustive.score, exhaustive.candidate):
                raise RuntimeError("exact bound disagreed with exhaustive audit")

        method_rows: dict[str, object] = {}
        rotated_methods = METHODS[offset % len(METHODS) :] + METHODS[: offset % len(METHODS)]
        for name in rotated_methods:
            started = time.perf_counter_ns()
            result = ROUTE.acquire_then_certify(instance, **_method_arguments(name, seed))
            elapsed_ns = time.perf_counter_ns() - started
            if (result.score, result.candidate) != (truth.score, truth.candidate):
                raise RuntimeError(f"{name} lost exactness")
            method_rows[name] = {
                "total_objective_evaluations": result.total_objective_evaluations,
                "acquisition_objective_evaluations": result.acquisition_objective_evaluations,
                "certification_objective_evaluations": result.certification_objective_evaluations,
                "acquired_exact_optimum": result.acquired_candidate == truth.candidate,
                "acquired_candidate": list(result.acquired_candidate),
                "acquired_score_gap": result.acquired_score - truth.score,
                "acquired_matrix_distance_to_optimum": ROUTE.matrix_displacement_squared(
                    instance, result.acquired_candidate, truth.candidate
                ),
                "acquired_hamming_distance_to_optimum": PHASE.hamming_distance(
                    result.acquired_candidate, truth.candidate
                ),
                "route_steps": len(result.route),
                "boxes_opened": result.boxes_opened,
                "boxes_pruned": result.boxes_pruned,
                "resolved_zero_states": result.resolved_zero_states,
                "kernel_pocket_states": result.kernel_pocket_states,
                "elapsed_ns": elapsed_ns,
            }

        assert instance.planted_secret is not None
        candidates = PHASE.random_candidates(
            dimension,
            count=locality_candidates,
            seed=31_000_000 + seed,
        ).candidates
        objectives = [BOX.exact_score(instance, candidate) for candidate in candidates]
        hidden_matrix_distances = [
            ROUTE.matrix_displacement_squared(instance, candidate, instance.planted_secret) for candidate in candidates
        ]
        public_foothold = tuple(method_rows["fractional_zero_last"]["acquired_candidate"])
        public_matrix_distances = [
            ROUTE.matrix_displacement_squared(instance, candidate, public_foothold) for candidate in candidates
        ]
        zero_anchor = (0,) * dimension
        zero_matrix_distances = [
            ROUTE.matrix_displacement_squared(instance, candidate, zero_anchor) for candidate in candidates
        ]
        hidden_hamming_distances = [
            PHASE.hamming_distance(candidate, instance.planted_secret) for candidate in candidates
        ]
        associations = {
            "matrix_to_hidden_target": _association(hidden_matrix_distances, objectives),
            "matrix_to_public_foothold": _association(public_matrix_distances, objectives),
            "matrix_to_zero_anchor": _association(zero_matrix_distances, objectives),
            "hamming_to_hidden_target": _association(hidden_hamming_distances, objectives),
        }
        for metric in locality_totals:
            for key in locality_totals[metric]:
                locality_totals[metric][key] += int(associations[metric][key])

        rows.append(
            {
                "seed": seed,
                "exhaustive_audited": exhaustive_audited,
                "optimum": {"candidate": list(truth.candidate), "score": truth.score},
                "baseline": {
                    "total_objective_evaluations": truth.evaluated_candidates,
                    "boxes_opened": truth.boxes_opened,
                    "boxes_pruned": truth.boxes_pruned,
                    "elapsed_ns": baseline_elapsed_ns,
                },
                "methods": method_rows,
                "locality": associations,
            }
        )

    baseline_counts = [int(row["baseline"]["total_objective_evaluations"]) for row in rows]
    method_counts = {
        name: [int(row["methods"][name]["total_objective_evaluations"]) for row in rows] for name in METHODS
    }
    method_aggregates = {
        name: {
            "mean_total_objective_evaluations": _ratio(method_counts[name]),
            "mean_acquisition_objective_evaluations": _ratio(
                [int(row["methods"][name]["acquisition_objective_evaluations"]) for row in rows]
            ),
            "exact_acquisition_hits": sum(bool(row["methods"][name]["acquired_exact_optimum"]) for row in rows),
            "mean_acquired_score_gap": _ratio([int(row["methods"][name]["acquired_score_gap"]) for row in rows]),
            "mean_elapsed_ns": _ratio([int(row["methods"][name]["elapsed_ns"]) for row in rows]),
            "kernel_pocket_states": sum(int(row["methods"][name]["kernel_pocket_states"]) for row in rows),
        }
        for name in METHODS
    }
    fractional_counts = method_counts["fractional_zero_last"]
    effects = {
        "fractional_vs_exact_bound": _paired_effect(fractional_counts, baseline_counts),
        "fractional_vs_random_acquisition": _paired_effect(fractional_counts, method_counts["random_acquisition"]),
        "exact_bound_vs_fractional": _paired_effect(baseline_counts, fractional_counts),
        "zero_first_vs_zero_last": _paired_effect(method_counts["fractional_zero_first"], fractional_counts),
    }
    for values in locality_totals.values():
        values["gamma"] = {
            "numerator": values["concordant"] - values["discordant"],
            "denominator": values["concordant"] + values["discordant"],
        }
    fraction_advantage = (
        effects["fractional_vs_exact_bound"]["improvement_exceeds_two_population_sd"]
        and effects["fractional_vs_random_acquisition"]["improvement_exceeds_two_population_sd"]
    )
    fraction_interference = effects["exact_bound_vs_fractional"]["improvement_exceeds_two_population_sd"]
    report = {
        "schema": "scbe.toy-lwe-fractional-route-benchmark.v1",
        "status": (
            "FRACTIONAL_ROUTE_MEASURED_ADVANTAGE"
            if fraction_advantage
            else (
                "MATRIX_LOCALITY_WITH_FRACTIONAL_INTERFERENCE"
                if fraction_interference
                else "FRACTIONAL_ROUTE_UNDERPOWERED"
            )
        ),
        "claim_boundary": "exact_integer_toy_LWE_only",
        "parameters": {
            "seed_start": seed_start,
            "seeds": seeds,
            "dimension": dimension,
            "samples": samples,
            "modulus": 97,
            "secret_values": [-1, 0, 1],
            "locality_candidates_per_seed": locality_candidates,
            "exhaustive_audit_seeds": exhaustive_audit_seeds,
        },
        "arithmetic": {
            "search_uses_floating_point": False,
            "finite_ratios": "fractions.Fraction exact integer cross-products",
            "zero_denominator": "tagged resolved or kernel-pocket; never evaluated as a scalar",
            "entropy_boundary": "state-count metadata only; no Shannon entropy without probabilities",
        },
        "baseline": {
            "exact_results": seeds,
            "mean_total_objective_evaluations": _ratio(baseline_counts),
            "mean_elapsed_ns": _ratio([int(row["baseline"]["elapsed_ns"]) for row in rows]),
        },
        "method_aggregates": method_aggregates,
        "paired_effects": effects,
        "matrix_locality_diagnostic": {
            "uses_hidden_planted_secret": True,
            "therefore_available_to_search": False,
            "pair_order_association": locality_totals,
        },
        "decisions": {
            "matrix_induced_hidden_target_locality_observed": locality_totals["matrix_to_hidden_target"]["gamma"][
                "numerator"
            ]
            > 0,
            "public_foothold_locality_observed": locality_totals["matrix_to_public_foothold"]["gamma"]["numerator"] > 0,
            "fractional_route_beats_exact_bound_and_random": fraction_advantage,
            "fractional_route_adds_measured_interference": fraction_interference,
            "deploy_fractional_route": fraction_advantage,
        },
        "source_receipts": _source_receipts(),
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=20_000)
    parser.add_argument("--seeds", type=int, default=300)
    parser.add_argument("--dimension", type=int, default=8)
    parser.add_argument("--samples", type=int, default=14)
    parser.add_argument("--locality-candidates", type=int, default=128)
    parser.add_argument("--exhaustive-audit-seeds", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(
        seed_start=args.seed_start,
        seeds=args.seeds,
        dimension=args.dimension,
        samples=args.samples,
        locality_candidates=args.locality_candidates,
        exhaustive_audit_seeds=args.exhaustive_audit_seeds,
        output=args.output,
    )
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))


if __name__ == "__main__":
    main()
