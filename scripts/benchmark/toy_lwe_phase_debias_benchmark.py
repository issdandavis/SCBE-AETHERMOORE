"""Measure phase-orbit debiasing and a fully charged algebraic handoff."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python.scbe import torus as TORUS
from scripts.benchmark import toy_lwe_dual_trit_torus_benchmark as BASE
from src.crypto import integer_phase_shards as PHASE_SHARDS
from src.crypto import toy_lwe_box_field as BOX
from src.crypto import toy_lwe_phase_debias as DEBIAS
from src.crypto import toy_lwe_phase_search as PHASE
from src.crypto import toy_lwe_seeded_bound as SEEDED
from src.symphonic_cipher.scbe_aethermoore.ai_brain import dual_ternary as DUAL_TERNARY

METHODS = (
    "legacy_phase",
    "orbit_cover_phase",
    "uniform_random",
    "orbit_cover_phase_then_torus",
    "random_then_torus",
)
BOUND_METHODS = ("bound_only", "orbit_cover_seeded_bound", "random_seeded_bound")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ratio(values: list[int]) -> dict[str, int]:
    return {"numerator": sum(values), "denominator": len(values)}


def _paired_values(preferred: list[int], control: list[int], *, lower_is_better: bool) -> dict[str, object]:
    if len(preferred) != len(control) or not preferred:
        raise ValueError("paired panels must be nonempty and equally sized")
    differences = [
        right - left if lower_is_better else left - right for left, right in zip(preferred, control, strict=True)
    ]
    count = len(differences)
    difference_sum = sum(differences)
    scaled_squared_deviations = sum((count * value - difference_sum) ** 2 for value in differences)
    exceeds = difference_sum * difference_sum * count > 4 * scaled_squared_deviations
    return {
        "mean_improvement": {"numerator": difference_sum, "denominator": count},
        "wins": sum(value > 0 for value in differences),
        "ties": sum(value == 0 for value in differences),
        "losses": sum(value < 0 for value in differences),
        "effect_exceeds_two_population_sd": exceeds,
        "improvement_exceeds_two_population_sd": difference_sum > 0 and exceeds,
        "scaled_squared_deviations_sum": scaled_squared_deviations,
        "scaled_deviation_denominator": count**3,
    }


def _candidate_prefix(batch: PHASE.CandidateBatch, count: int, strategy: str) -> PHASE.CandidateBatch:
    return PHASE.CandidateBatch(
        candidates=batch.candidates[:count],
        proposals=batch.proposals,
        duplicate_proposals=batch.duplicate_proposals,
        strategy=strategy,
    )


def _coverage_report(
    legacy: PHASE.CandidateBatch,
    corrected: PHASE.CandidateBatch,
    *,
    dimension: int,
    budget: int,
    random_controls: int,
) -> dict[str, object]:
    legacy_stats = asdict(DEBIAS.orbit_cover_stats(legacy))
    corrected_stats = asdict(DEBIAS.orbit_cover_stats(corrected))
    random_stats = [
        asdict(DEBIAS.orbit_cover_stats(PHASE.random_candidates(dimension, count=budget, seed=4_000_000 + control)))
        for control in range(random_controls)
    ]
    metrics = (
        "nearest_distance_sum",
        "max_coordinate_discrepancy_scaled_by_three",
        "max_pair_cell_discrepancy_scaled_by_nine",
    )
    effects = {
        metric: _paired_values(
            [int(corrected_stats[metric])] * random_controls,
            [int(value[metric]) for value in random_stats],
            lower_is_better=True,
        )
        for metric in metrics
    }
    return {
        "legacy_phase": legacy_stats,
        "orbit_cover_phase": corrected_stats,
        "uniform_random": {metric: _ratio([int(value[metric]) for value in random_stats]) for metric in metrics},
        "random_control_sets": random_controls,
        "orbit_cover_vs_random_effects": effects,
    }


def _bound_aggregate(rows: list[dict[str, object]], method: str) -> dict[str, object]:
    values = [row["bounds"][method] for row in rows]
    return {
        "exact_results": sum(bool(value["exact"]) for value in values),
        "mean_total_objective_evaluations": _ratio([int(value["total_objective_evaluations"]) for value in values]),
        "mean_initial_unique_evaluations": _ratio([int(value["initial_unique_evaluations"]) for value in values]),
        "mean_post_seed_objective_evaluations": _ratio(
            [int(value["post_seed_objective_evaluations"]) for value in values]
        ),
        "mean_boxes_opened": _ratio([int(value["boxes_opened"]) for value in values]),
        "mean_boxes_pruned": _ratio([int(value["boxes_pruned"]) for value in values]),
    }


def _source_receipts() -> dict[str, dict[str, str]]:
    paths = {
        "benchmark_driver": Path(__file__).resolve(),
        "phase_debias": Path(DEBIAS.__file__).resolve(),
        "seeded_bound": Path(SEEDED.__file__).resolve(),
        "legacy_phase_search": Path(PHASE.__file__).resolve(),
        "toy_lwe_bounds": Path(BOX.__file__).resolve(),
        "exact_30_degree_rotation": Path(PHASE_SHARDS.__file__).resolve(),
        "dual_ternary_state_space": Path(DUAL_TERNARY.__file__).resolve(),
        "hypercube_neighbors": Path(TORUS.__file__).resolve(),
    }
    return {name: {"path": str(path), "sha256": _sha256(path)} for name, path in paths.items()}


def run(
    *,
    seed_start: int,
    seeds: int,
    dimension: int,
    samples: int,
    budget: int,
    bound_seeds: int,
    random_coverage_controls: int,
    exhaustive_audit_seeds: int,
    output: Path,
) -> dict[str, object]:
    if seeds < 3 or seed_start < 0:
        raise ValueError("benchmark requires at least three nonnegative paired seeds")
    if not 0 < bound_seeds < budget <= 3**dimension:
        raise ValueError("seed and objective budgets are inconsistent")
    if random_coverage_controls < 3:
        raise ValueError("coverage comparison requires at least three random controls")
    if not 0 <= exhaustive_audit_seeds <= seeds:
        raise ValueError("exhaustive audit count is outside the benchmark panel")

    legacy = PHASE.phase_wheel_candidates(dimension, count=budget)
    corrected = DEBIAS.phase_orbit_cover_candidates(dimension, count=budget)
    corrected_starts = _candidate_prefix(corrected, bound_seeds, "orbit-cover-prefix")
    coverage = _coverage_report(
        legacy,
        corrected,
        dimension=dimension,
        budget=budget,
        random_controls=random_coverage_controls,
    )
    rows: list[dict[str, object]] = []

    for offset in range(seeds):
        seed = seed_start + offset
        instance = BOX.generate_toy_lwe(seed, dimension=dimension, samples=samples, modulus=97)
        truth = BOX.box_field_search(instance, strategy="bound-only")
        if truth.candidate != instance.planted_secret:
            raise RuntimeError("exact bound did not recover the planted toy secret")
        exhaustive_audited = offset < exhaustive_audit_seeds
        if exhaustive_audited:
            exhaustive = BOX.exhaustive_search(instance)
            if (truth.score, truth.candidate) != (exhaustive.score, exhaustive.candidate):
                raise RuntimeError("exact bound disagreed with exhaustive audit")

        random_probes = PHASE.random_candidates(dimension, count=budget, seed=2_700_000 + seed)
        random_starts = _candidate_prefix(random_probes, bound_seeds, "uniform-random-prefix")
        methods = {
            "legacy_phase": PHASE.evaluate_candidates(instance, legacy),
            "orbit_cover_phase": PHASE.evaluate_candidates(instance, corrected),
            "uniform_random": PHASE.evaluate_candidates(instance, random_probes),
            "orbit_cover_phase_then_torus": PHASE.foothold_search(instance, corrected_starts, max_evaluations=budget),
            "random_then_torus": PHASE.foothold_search(instance, random_starts, max_evaluations=budget),
        }
        if any(result.evaluated_candidates != budget for result in methods.values()):
            raise RuntimeError("a heuristic escaped its matched objective budget")

        corrected_bound = SEEDED.seeded_box_field_search(instance, corrected_starts.candidates)
        random_bound = SEEDED.seeded_box_field_search(instance, random_starts.candidates)
        if any(
            (value.score, value.candidate) != (truth.score, truth.candidate)
            for value in (corrected_bound, random_bound)
        ):
            raise RuntimeError("a seeded interval search lost exactness")
        bounds = {
            "bound_only": {
                "exact": True,
                "total_objective_evaluations": truth.evaluated_candidates,
                "initial_unique_evaluations": 0,
                "post_seed_objective_evaluations": truth.evaluated_candidates,
                "boxes_opened": truth.boxes_opened,
                "boxes_pruned": truth.boxes_pruned,
            },
            "orbit_cover_seeded_bound": {
                "exact": True,
                "total_objective_evaluations": corrected_bound.total_objective_evaluations,
                "initial_unique_evaluations": corrected_bound.initial_unique_evaluations,
                "post_seed_objective_evaluations": corrected_bound.post_seed_objective_evaluations,
                "boxes_opened": corrected_bound.boxes_opened,
                "boxes_pruned": corrected_bound.boxes_pruned,
            },
            "random_seeded_bound": {
                "exact": True,
                "total_objective_evaluations": random_bound.total_objective_evaluations,
                "initial_unique_evaluations": random_bound.initial_unique_evaluations,
                "post_seed_objective_evaluations": random_bound.post_seed_objective_evaluations,
                "boxes_opened": random_bound.boxes_opened,
                "boxes_pruned": random_bound.boxes_pruned,
            },
        }
        rows.append(
            {
                "seed": seed,
                "exhaustive_audited": exhaustive_audited,
                "optimum": {"candidate": list(truth.candidate), "score": truth.score},
                "methods": {name: BASE._diagnose(result, truth) for name, result in methods.items()},
                "bounds": bounds,
            }
        )

    aggregates = {method: BASE._aggregate(rows, method) for method in METHODS}
    objective_effects = {
        "orbit_cover_vs_random_score": BASE._paired_effect(
            rows, "orbit_cover_phase", "uniform_random", "score_gap", lower_is_better=True
        ),
        "orbit_cover_vs_random_hits": BASE._paired_effect(
            rows, "orbit_cover_phase", "uniform_random", "exact_optimum_hit", lower_is_better=False
        ),
        "orbit_torus_vs_random_torus_score": BASE._paired_effect(
            rows, "orbit_cover_phase_then_torus", "random_then_torus", "score_gap", lower_is_better=True
        ),
    }
    bound_aggregates = {method: _bound_aggregate(rows, method) for method in BOUND_METHODS}
    bound_effects = {
        "orbit_seeded_vs_bound_only_total": _paired_values(
            [int(row["bounds"]["orbit_cover_seeded_bound"]["total_objective_evaluations"]) for row in rows],
            [int(row["bounds"]["bound_only"]["total_objective_evaluations"]) for row in rows],
            lower_is_better=True,
        ),
        "orbit_seeded_vs_random_seeded_total": _paired_values(
            [int(row["bounds"]["orbit_cover_seeded_bound"]["total_objective_evaluations"]) for row in rows],
            [int(row["bounds"]["random_seeded_bound"]["total_objective_evaluations"]) for row in rows],
            lower_is_better=True,
        ),
    }
    coverage_advantage = all(
        effect["improvement_exceeds_two_population_sd"] for effect in coverage["orbit_cover_vs_random_effects"].values()
    )
    objective_advantage = objective_effects["orbit_cover_vs_random_score"]["improvement_exceeds_two_population_sd"]
    bound_speedup = bound_effects["orbit_seeded_vs_bound_only_total"]["improvement_exceeds_two_population_sd"]
    report = {
        "schema": "scbe.toy-lwe-phase-debias-benchmark.v1",
        "status": (
            "INTERFERENCE_REMOVED_MEASURED_END_TO_END_ADVANTAGE"
            if coverage_advantage and objective_advantage and bound_speedup
            else "INTERFERENCE_REMOVED_OBJECTIVE_UNDERPOWERED"
        ),
        "claim_boundary": "finite_balanced_trit_geometry_and_toy_LWE_only",
        "parameters": {
            "seed_start": seed_start,
            "seeds": seeds,
            "dimension": dimension,
            "samples": samples,
            "modulus": 97,
            "heuristic_objective_budget": budget,
            "fully_charged_bound_seed_count": bound_seeds,
            "random_coverage_controls": random_coverage_controls,
            "exhaustive_audit_seeds": exhaustive_audit_seeds,
        },
        "coverage": coverage,
        "heuristic_aggregates": aggregates,
        "heuristic_paired_effects": objective_effects,
        "bound_aggregates": bound_aggregates,
        "bound_paired_effects": bound_effects,
        "decisions": {
            "phase_projection_interference_removed": coverage_advantage,
            "measured_LWE_objective_advantage": objective_advantage,
            "measured_total_exact_bound_speedup": bound_speedup,
            "deploy_phase_as_LWE_prepass": objective_advantage and bound_speedup,
        },
        "source_receipts": _source_receipts(),
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=10_000)
    parser.add_argument("--seeds", type=int, default=300)
    parser.add_argument("--dimension", type=int, default=8)
    parser.add_argument("--samples", type=int, default=14)
    parser.add_argument("--budget", type=int, default=360)
    parser.add_argument("--bound-seeds", type=int, default=60)
    parser.add_argument("--random-coverage-controls", type=int, default=100)
    parser.add_argument("--exhaustive-audit-seeds", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(
        seed_start=args.seed_start,
        seeds=args.seeds,
        dimension=args.dimension,
        samples=args.samples,
        budget=args.budget,
        bound_seeds=args.bound_seeds,
        random_coverage_controls=args.random_coverage_controls,
        exhaustive_audit_seeds=args.exhaustive_audit_seeds,
        output=args.output,
    )
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))


if __name__ == "__main__":
    main()
