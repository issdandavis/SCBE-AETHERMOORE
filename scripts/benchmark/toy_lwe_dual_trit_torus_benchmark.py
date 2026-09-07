"""Compare the existing dual-trit phase wheel with matched toy-LWE controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.crypto import integer_phase_shards as PHASE_SHARDS
from src.crypto import toy_lwe_box_field as B
from src.crypto import toy_lwe_phase_search as P
from src.symphonic_cipher.scbe_aethermoore.ai_brain import dual_ternary as D
from python.scbe import torus as T

METHODS = (
    "dual_trit_phase",
    "uniform_random",
    "dual_trit_phase_then_torus",
    "random_then_torus",
    "center_then_torus",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _trace_sha256(result: P.ProbeResult) -> str:
    payload = [[list(candidate), score] for candidate, score in result.evaluated]
    canonical = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _score_distance_correlation(result: P.ProbeResult, optimum: P.Candidate) -> float:
    scores = [score for _, score in result.evaluated]
    distances = [P.hamming_distance(candidate, optimum) for candidate, _ in result.evaluated]
    count = len(scores)
    score_sum = sum(scores)
    distance_sum = sum(distances)
    numerator = count * sum(score * distance for score, distance in zip(scores, distances, strict=True))
    numerator -= score_sum * distance_sum
    score_term = count * sum(score * score for score in scores) - score_sum * score_sum
    distance_term = count * sum(distance * distance for distance in distances) - distance_sum * distance_sum
    if score_term <= 0 or distance_term <= 0:
        return 0.0
    return numerator / math.sqrt(score_term * distance_term)


def _diagnose(result: P.ProbeResult, truth: B.SearchResult) -> dict[str, object]:
    distances = [P.hamming_distance(candidate, truth.candidate) for candidate, _ in result.evaluated]
    selected_distance = P.hamming_distance(result.candidate, truth.candidate)
    return {
        "candidate": list(result.candidate),
        "score": result.score,
        "score_gap": result.score - truth.score,
        "exact_optimum_hit": result.candidate == truth.candidate,
        "selected_hamming_to_optimum": selected_distance,
        "nearest_evaluated_hamming_to_optimum": min(distances),
        "evaluated_optimum_footholds": sum(distance == 1 for distance in distances),
        "selected_is_nearest_evaluated": selected_distance == min(distances),
        "score_distance_correlation": _score_distance_correlation(result, truth.candidate),
        "objective_evaluations": result.evaluated_candidates,
        "candidate_proposals": result.candidate_proposals,
        "duplicate_proposals": result.duplicate_proposals,
        "frontier_expansions": result.frontier_expansions,
        "strategy": result.strategy,
        "trace_sha256": _trace_sha256(result),
    }


def _aggregate(rows: list[dict[str, object]], method: str) -> dict[str, object]:
    entries = [row["methods"][method] for row in rows]
    count = len(entries)

    def ratio(key: str) -> dict[str, int]:
        return {
            "numerator": sum(int(entry[key]) for entry in entries),
            "denominator": count,
        }

    correlations = [float(entry["score_distance_correlation"]) for entry in entries]
    return {
        "exact_optimum_hits": sum(bool(entry["exact_optimum_hit"]) for entry in entries),
        "mean_score_gap": ratio("score_gap"),
        "mean_selected_hamming_to_optimum": ratio("selected_hamming_to_optimum"),
        "mean_nearest_evaluated_hamming_to_optimum": ratio("nearest_evaluated_hamming_to_optimum"),
        "mean_evaluated_optimum_footholds": ratio("evaluated_optimum_footholds"),
        "selected_is_nearest_count": sum(bool(entry["selected_is_nearest_evaluated"]) for entry in entries),
        "mean_score_distance_correlation": sum(correlations) / count,
        "mean_objective_evaluations": ratio("objective_evaluations"),
        "mean_candidate_proposals": ratio("candidate_proposals"),
        "mean_duplicate_proposals": ratio("duplicate_proposals"),
        "mean_frontier_expansions": ratio("frontier_expansions"),
    }


def _paired_effect(
    rows: list[dict[str, object]],
    preferred: str,
    control: str,
    metric: str,
    *,
    lower_is_better: bool,
) -> dict[str, object]:
    differences = []
    for row in rows:
        preferred_value = int(row["methods"][preferred][metric])
        control_value = int(row["methods"][control][metric])
        differences.append(control_value - preferred_value if lower_is_better else preferred_value - control_value)
    count = len(differences)
    difference_sum = sum(differences)
    scaled_squared_deviations = sum((count * value - difference_sum) ** 2 for value in differences)
    return {
        "preferred": preferred,
        "control": control,
        "metric": metric,
        "positive_means_preferred_is_better": True,
        "mean_improvement": {"numerator": difference_sum, "denominator": count},
        "wins": sum(value > 0 for value in differences),
        "ties": sum(value == 0 for value in differences),
        "losses": sum(value < 0 for value in differences),
        "effect_exceeds_two_population_sd": difference_sum * difference_sum * count > 4 * scaled_squared_deviations,
        "improvement_exceeds_two_population_sd": difference_sum > 0
        and difference_sum * difference_sum * count > 4 * scaled_squared_deviations,
        "scaled_squared_deviations_sum": scaled_squared_deviations,
        "scaled_deviation_denominator": count**3,
    }


def _source_receipts(loom_relation_source: Path | None) -> dict[str, dict[str, str]]:
    paths = {
        "benchmark_driver": Path(__file__).resolve(),
        "phase_search": Path(P.__file__).resolve(),
        "exact_30_degree_rotation": Path(PHASE_SHARDS.__file__).resolve(),
        "dual_ternary_state_space": Path(D.__file__).resolve(),
        "hypercube_neighbors": Path(T.__file__).resolve(),
        "toy_lwe_objective_and_bounds": Path(B.__file__).resolve(),
    }
    if loom_relation_source is not None:
        resolved = loom_relation_source.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(resolved)
        paths["loom_dual_trit_D4_relation"] = resolved
    return {name: {"path": str(path), "sha256": _sha256(path)} for name, path in paths.items()}


def run(
    *,
    seeds: int,
    dimension: int,
    samples: int,
    budget: int,
    foothold_seeds: int,
    output: Path,
    loom_relation_source: Path | None = None,
) -> dict[str, object]:
    if seeds < 3:
        raise ValueError("benchmark requires at least three paired seeds")
    if foothold_seeds < 1 or foothold_seeds >= budget:
        raise ValueError("foothold seed count must lie between one and the objective budget")
    if budget > 3**dimension:
        raise ValueError("objective budget exceeds the finite candidate space")

    phase_probes = P.phase_wheel_candidates(dimension, count=budget)
    phase_starts = P.phase_wheel_candidates(dimension, count=foothold_seeds)
    center = P.CandidateBatch((tuple(0 for _ in range(dimension)),), 1, 0, "center-control")
    rows: list[dict[str, object]] = []

    for seed in range(seeds):
        instance = B.generate_toy_lwe(seed, dimension=dimension, samples=samples, modulus=97)
        truth = B.exhaustive_search(instance)
        bound = B.box_field_search(instance, strategy="bound-only")
        if (bound.score, bound.candidate) != (truth.score, truth.candidate):
            raise RuntimeError("exact interval search disagreed with exhaustive ground truth")

        random_probes = P.random_candidates(dimension, count=budget, seed=700_000 + seed)
        random_starts = P.random_candidates(dimension, count=foothold_seeds, seed=700_000 + seed)
        results = {
            "dual_trit_phase": P.evaluate_candidates(instance, phase_probes),
            "uniform_random": P.evaluate_candidates(instance, random_probes),
            "dual_trit_phase_then_torus": P.foothold_search(instance, phase_starts, max_evaluations=budget),
            "random_then_torus": P.foothold_search(instance, random_starts, max_evaluations=budget),
            "center_then_torus": P.foothold_search(instance, center, max_evaluations=budget),
        }
        if any(result.evaluated_candidates != budget for result in results.values()):
            raise RuntimeError("a matched probe escaped its exact objective budget")
        rows.append(
            {
                "seed": seed,
                "planted_secret": list(instance.planted_secret or ()),
                "planted_is_optimum": instance.planted_secret == truth.candidate,
                "optimum": {"candidate": list(truth.candidate), "score": truth.score},
                "exact_bound": {
                    "candidate": list(bound.candidate),
                    "score": bound.score,
                    "objective_evaluations": bound.evaluated_candidates,
                    "boxes_opened": bound.boxes_opened,
                    "boxes_pruned": bound.boxes_pruned,
                },
                "methods": {name: _diagnose(result, truth) for name, result in results.items()},
            }
        )

    aggregates = {method: _aggregate(rows, method) for method in METHODS}
    effects = {
        "phase_wheel_vs_uniform_random_score": _paired_effect(
            rows,
            "dual_trit_phase",
            "uniform_random",
            "score_gap",
            lower_is_better=True,
        ),
        "phase_wheel_vs_uniform_random_hits": _paired_effect(
            rows,
            "dual_trit_phase",
            "uniform_random",
            "exact_optimum_hit",
            lower_is_better=False,
        ),
        "phase_torus_vs_random_torus_score": _paired_effect(
            rows,
            "dual_trit_phase_then_torus",
            "random_then_torus",
            "score_gap",
            lower_is_better=True,
        ),
        "phase_torus_vs_random_torus_hits": _paired_effect(
            rows,
            "dual_trit_phase_then_torus",
            "random_then_torus",
            "exact_optimum_hit",
            lower_is_better=False,
        ),
        "phase_torus_vs_center_torus_score": _paired_effect(
            rows,
            "dual_trit_phase_then_torus",
            "center_then_torus",
            "score_gap",
            lower_is_better=True,
        ),
    }
    measured_advantage = (
        effects["phase_wheel_vs_uniform_random_score"]["improvement_exceeds_two_population_sd"]
        and effects["phase_torus_vs_random_torus_score"]["improvement_exceeds_two_population_sd"]
        and aggregates["dual_trit_phase"]["exact_optimum_hits"] >= aggregates["uniform_random"]["exact_optimum_hits"]
        and aggregates["dual_trit_phase_then_torus"]["exact_optimum_hits"]
        >= aggregates["random_then_torus"]["exact_optimum_hits"]
    )
    exact_bound_evaluations = [int(row["exact_bound"]["objective_evaluations"]) for row in rows]
    report = {
        "schema": "scbe.toy-lwe-dual-trit-torus-benchmark.v1",
        "status": "MEASURED_ADVANTAGE" if measured_advantage else "UNDERPOWERED",
        "claim_boundary": "toy_balanced_ternary_LWE_only_not_ML_KEM_or_ML_DSA",
        "integer_search_core": True,
        "parameters": {
            "seeds": seeds,
            "dimension": dimension,
            "samples": samples,
            "modulus": 97,
            "secret_values": [-1, 0, 1],
            "objective_budget_per_heuristic": budget,
            "foothold_seed_candidates": foothold_seeds,
            "phase_slots": budget,
        },
        "controls": {
            "exhaustive_candidates_per_seed": 3**dimension,
            "exact_interval_bound_ground_truth_agreement": True,
            "exact_interval_bound_mean_objective_evaluations": {
                "numerator": sum(exact_bound_evaluations),
                "denominator": seeds,
            },
            "all_heuristic_objective_budgets_matched": True,
            "candidate_generation_and_duplicates_counted": True,
        },
        "phase_wheel_construction": {
            "unique_candidates": len(phase_probes.candidates),
            "candidate_proposals": phase_probes.proposals,
            "duplicate_proposals": phase_probes.duplicate_proposals,
            "meaning": (
                "360 exact labelled probes from mirrored cyclotomic phase orbits; "
                "not a claim of 360 equal Euclidean angles in eight dimensions"
            ),
        },
        "aggregates": aggregates,
        "paired_effects": effects,
        "source_receipts": _source_receipts(loom_relation_source),
        "interpretation": (
            "A phase or torus heuristic is useful only if it beats matched random controls and the "
            "unstructured center start at the declared effect threshold. Safe exact bounds remain separate."
        ),
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--dimension", type=int, default=8)
    parser.add_argument("--samples", type=int, default=14)
    parser.add_argument("--budget", type=int, default=360)
    parser.add_argument("--foothold-seeds", type=int, default=64)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--loom-relation-source", type=Path)
    args = parser.parse_args()
    report = run(
        seeds=args.seeds,
        dimension=args.dimension,
        samples=args.samples,
        budget=args.budget,
        foothold_seeds=args.foothold_seeds,
        output=args.output,
        loom_relation_source=args.loom_relation_source,
    )
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))


if __name__ == "__main__":
    main()
