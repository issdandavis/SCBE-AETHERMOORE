"""Validate the exact oriented-zero automaton and its toy-search boundary.

The benchmark separates two claims:

1. the automaton is a deterministic, anti-chatter control primitive; and
2. compiling a multiscale toy-LWE schedule through that automaton preserves
   the schedule exactly but does not create search information by itself.

All decisions and objective scores use integers or ``Fraction``.  Floating
point is used only by matplotlib at the presentation boundary.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
import hashlib
from itertools import product
import json
from pathlib import Path
import random
import sys
from typing import Callable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.crypto import oriented_zero_hybrid as H
from src.crypto import toy_lwe_box_field as BOX

Candidate = tuple[int, ...]


@dataclass(frozen=True)
class SearchResult:
    candidate: Candidate
    score: int
    objective_evaluations: int
    route: tuple[str, ...]
    receipt_head_sha256: str | None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ratio(values: Sequence[int]) -> dict[str, int]:
    if not values:
        raise ValueError("ratio input must be nonempty")
    return {"numerator": sum(values), "denominator": len(values)}


def _paired_effect(preferred: Sequence[int], control: Sequence[int]) -> dict[str, object]:
    """Exact paired lower-is-better effect and the repository's 2-SD gate."""

    if len(preferred) != len(control) or not preferred:
        raise ValueError("paired panels must be nonempty and equally sized")
    differences = [right - left for left, right in zip(preferred, control, strict=True)]
    count = len(differences)
    difference_sum = sum(differences)
    scaled_squared_deviations = sum((count * value - difference_sum) ** 2 for value in differences)
    exceeds = difference_sum * difference_sum * count > 4 * scaled_squared_deviations
    return {
        "mean_control_minus_preferred": {"numerator": difference_sum, "denominator": count},
        "wins": sum(value > 0 for value in differences),
        "ties": sum(value == 0 for value in differences),
        "losses": sum(value < 0 for value in differences),
        "effect_exceeds_two_population_sd": exceeds,
        "improvement_exceeds_two_population_sd": difference_sum > 0 and exceeds,
        "harm_exceeds_two_population_sd": difference_sum < 0 and exceeds,
        "scaled_squared_deviations_sum": scaled_squared_deviations,
        "scaled_deviation_denominator": count**3,
    }


def _control_graph(*, episodes: int) -> H.RegionGraph:
    chart = H.CeilingMap(Fraction(7), Fraction(1, 4))
    regions = tuple(H.Region(name, Fraction(1, 16), Fraction(1, 8), chart) for name in ("root", "positive", "negative"))
    edges = tuple(
        H.RegionEdge(source, side, "default", "positive" if side > 0 else "negative", Fraction(1, 4))
        for source in ("root", "positive", "negative")
        for side in (-1, 1)
    )
    return H.RegionGraph(regions, edges, jump_budget=episodes, minimum_dwell_steps=2)


def _boundary_trace(seed: int, *, episodes: int, jitter_steps: int) -> tuple[H.OrientedObservation, ...]:
    rng = random.Random(seed)
    trace: list[H.OrientedObservation] = []
    low_radii = (Fraction(0), Fraction(1, 128), Fraction(1, 64), Fraction(1, 32), Fraction(1, 16))
    for _ in range(episodes):
        side = rng.choice((-1, 1))
        trace.append(H.OrientedObservation(Fraction(side, 4), side))
        trace.append(H.OrientedObservation(Fraction(side, 16), side))
        for _ in range(jitter_steps):
            radius = rng.choice(low_radii)
            trace.append(H.OrientedObservation(radius * side, side))
        trace.append(H.OrientedObservation(Fraction(side, 8), side))
    return tuple(trace)


def _naive_boundary_events(graph: H.RegionGraph, trace: Sequence[H.OrientedObservation]) -> int:
    """Threshold-only control with no armed state or hysteresis."""

    region = graph.region("root")
    return sum(observation.side != 0 and observation.radius <= region.enter_radius for observation in trace)


def _finite_model_check(*, depth: int) -> dict[str, int]:
    graph = _control_graph(episodes=3)
    initial = H.HybridState("root", Fraction(1), side=1)
    alphabet = (
        H.OrientedObservation(Fraction(1, 4), 1),
        H.OrientedObservation(Fraction(-1, 4), -1),
        H.OrientedObservation(Fraction(1, 32), 1),
        H.OrientedObservation(Fraction(-1, 32), -1),
        H.OrientedObservation(Fraction(0), 0),
    )
    traces = failures = steps = 0
    for observations in product(alphabet, repeat=depth):
        result = H.run_trace(graph, initial, observations)
        traces += 1
        steps += len(result.receipts)
        outcomes = [receipt.outcome for receipt in result.receipts]
        valid = (
            result.state.jumps <= graph.jump_budget
            and H.replay_matches(graph, initial, observations, result.receipts)
            and all(not (left == right == "JUMP") for left, right in zip(outcomes, outcomes[1:]))
            and all(
                receipt.ceiling_coordinate + receipt.ceiling_gap == graph.region(receipt.source_region).chart.ceiling
                for receipt in result.receipts
            )
        )
        failures += not valid
    return {"depth": depth, "alphabet": len(alphabet), "traces": traces, "steps": steps, "invariant_failures": failures}


def _search_graph(scales: tuple[int, ...]) -> H.RegionGraph:
    names = tuple(f"scale-{scale}" for scale in scales) + ("done",)
    chart = H.CeilingMap(Fraction(1), Fraction(1))
    regions = tuple(H.Region(name, Fraction(0), Fraction(1), chart) for name in names)
    edges = tuple(
        H.RegionEdge(names[index], side, "refine", names[index + 1], Fraction(2))
        for index in range(len(scales))
        for side in (-1, 1)
    )
    return H.RegionGraph(regions, edges, jump_budget=len(scales), minimum_dwell_steps=2)


def _coordinate_stage(
    instance: BOX.ToyLWEInstance,
    candidate: Candidate,
    step_size: int,
    measure: Callable[[Candidate], int],
) -> tuple[Candidate, int]:
    """Run deterministic best-improvement coordinate descent at one scale."""

    current = candidate
    remembered_side = 1
    while True:
        current_score = measure(current)
        alternatives: list[tuple[int, Candidate, int]] = []
        for index in range(instance.dimension):
            for side in (-1, 1):
                proposed = list(current)
                proposed[index] = max(
                    instance.secret_low,
                    min(instance.secret_high, proposed[index] + side * step_size),
                )
                point = tuple(proposed)
                if point != current:
                    alternatives.append((measure(point), point, side))
        if not alternatives:
            return current, remembered_side
        best_score, best_candidate, best_side = min(alternatives)
        if best_score >= current_score:
            return current, remembered_side
        current = best_candidate
        remembered_side = best_side


def _multiscale_search(instance: BOX.ToyLWEInstance, *, through_graph: bool) -> SearchResult:
    BOX.validate_instance(instance)
    scales = tuple(range(instance.secret_high - instance.secret_low, 0, -1))
    candidate = (0,) * instance.dimension
    cache: dict[Candidate, int] = {}

    def measure(point: Candidate) -> int:
        if point not in cache:
            cache[point] = BOX.exact_score(instance, point)
        return cache[point]

    graph = _search_graph(scales)
    state = H.HybridState(f"scale-{scales[0]}", Fraction(1), side=1)
    observations: list[H.OrientedObservation] = []
    receipts: list[H.TransitionReceipt] = []
    route = tuple(f"scale-{scale}" for scale in scales) + ("done",)
    remembered_side = 1
    for index, scale in enumerate(scales):
        if through_graph and index:
            rearm = H.OrientedObservation(Fraction(remembered_side), remembered_side, "refine")
            result = H.advance(graph, state, rearm)
            if result.receipt.outcome != "REARM":
                raise RuntimeError("graph schedule did not rearm at its exact exit guard")
            state = result.state
            observations.append(rearm)
            receipts.append(result.receipt)
        candidate, remembered_side = _coordinate_stage(instance, candidate, scale, measure)
        if through_graph:
            boundary = H.OrientedObservation(Fraction(0), remembered_side, "refine")
            result = H.advance(graph, state, boundary)
            if result.receipt.outcome != "JUMP":
                raise RuntimeError("graph schedule did not refine at its oriented zero")
            state = result.state
            observations.append(boundary)
            receipts.append(result.receipt)

    if through_graph:
        if not H.replay_matches(
            graph, H.HybridState(f"scale-{scales[0]}", Fraction(1), side=1), observations, receipts
        ):
            raise RuntimeError("graph schedule receipts failed deterministic replay")
        if H.linearized_jump_route(graph, receipts) != route:
            raise RuntimeError("graph schedule did not linearize to the explicit scale route")
        head: str | None = state.receipt_head_sha256
    else:
        head = None
    return SearchResult(candidate, measure(candidate), len(cache), route, head)


def _single_scale_search(instance: BOX.ToyLWEInstance) -> SearchResult:
    cache: dict[Candidate, int] = {}

    def measure(point: Candidate) -> int:
        if point not in cache:
            cache[point] = BOX.exact_score(instance, point)
        return cache[point]

    candidate, _ = _coordinate_stage(instance, (0,) * instance.dimension, 1, measure)
    return SearchResult(candidate, measure(candidate), len(cache), ("scale-1", "done"), None)


def _random_search(instance: BOX.ToyLWEInstance, *, budget: int, seed: int) -> SearchResult:
    candidates = list(product(range(instance.secret_low, instance.secret_high + 1), repeat=instance.dimension))
    random.Random(seed).shuffle(candidates)
    measured = [(BOX.exact_score(instance, candidate), candidate) for candidate in candidates[:budget]]
    if not measured:
        raise ValueError("random search requires a positive budget")
    score, candidate = min(measured)
    return SearchResult(candidate, score, len(measured), ("random",), None)


def _source_receipts() -> dict[str, dict[str, str]]:
    paths = {
        "benchmark_driver": Path(__file__).resolve(),
        "oriented_zero_hybrid": Path(H.__file__).resolve(),
        "toy_lwe_objective": Path(BOX.__file__).resolve(),
        "prior_signed_zero_limits": Path(r"C:\dev\loom\signed_zero_division.py"),
        "existing_fsgs_hybrid": PROJECT_ROOT / "src/symphonic_cipher/scbe_aethermoore/ai_brain/fsgs.py",
        "existing_hysteresis": PROJECT_ROOT / "src/spiralverse/proximity_optimizer.py",
        "existing_topological_cfi": PROJECT_ROOT / "src/symphonic_cipher/topological_cfi.py",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"source receipt inputs are missing: {missing}")
    return {name: {"path": str(path), "sha256": _sha256(path)} for name, path in paths.items()}


def _write_plot(report: dict[str, object], output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    chatter_rows = report["chatter_control"]["rows"]
    search_rows = report["toy_search"]["rows"]
    seeds = [row["seed"] for row in chatter_rows]
    naive = [row["naive_events"] for row in chatter_rows]
    hybrid = [row["hybrid_jumps"] for row in chatter_rows]
    methods = ("graph_gap", "direct_gap", "single_scale_gap", "random_gap")
    means = [sum(row[name] for row in search_rows) / len(search_rows) for name in methods]

    figure, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].plot(seeds, naive, label="threshold only", linewidth=1)
    axes[0].plot(seeds, hybrid, label="oriented + hysteresis", linewidth=1)
    axes[0].set_title("Boundary events per paired trace")
    axes[0].set_xlabel("seed")
    axes[0].set_ylabel("events")
    axes[0].legend()
    axes[1].bar(("graph", "direct", "single", "random"), means)
    axes[1].set_title("Toy-LWE mean score gap (lower is better)")
    axes[1].set_ylabel("exact integer objective gap")
    figure.suptitle(report["status"])
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


def run(
    *,
    seed_start: int,
    seeds: int,
    dimension: int,
    samples: int,
    secret_radius: int,
    chatter_episodes: int,
    jitter_steps: int,
    finite_depth: int,
    output: Path,
    plot: Path | None = None,
) -> dict[str, object]:
    if seed_start < 0 or seeds < 3:
        raise ValueError("benchmark requires at least three nonnegative paired seeds")
    if dimension < 1 or samples < 1 or secret_radius < 1:
        raise ValueError("toy-LWE dimensions, samples, and radius must be positive")
    if chatter_episodes < 1 or jitter_steps < 1:
        raise ValueError("chatter panel must contain positive episodes and jitter")
    if not 1 <= finite_depth <= 7:
        raise ValueError("finite model-check depth must be in [1, 7]")

    chatter_rows: list[dict[str, object]] = []
    for offset in range(seeds):
        seed = seed_start + offset
        graph = _control_graph(episodes=chatter_episodes)
        trace = _boundary_trace(seed, episodes=chatter_episodes, jitter_steps=jitter_steps)
        initial = H.HybridState("root", Fraction(1), side=1)
        result = H.run_trace(graph, initial, trace)
        jumps = sum(receipt.outcome == "JUMP" for receipt in result.receipts)
        chatter_rows.append(
            {
                "seed": seed,
                "observations": len(trace),
                "naive_events": _naive_boundary_events(graph, trace),
                "hybrid_jumps": jumps,
                "expected_episodes": chatter_episodes,
                "replay_verified": H.replay_matches(graph, initial, trace, result.receipts),
                "receipt_head_sha256": result.state.receipt_head_sha256,
            }
        )

    search_rows: list[dict[str, object]] = []
    for offset in range(seeds):
        seed = seed_start + offset
        instance = BOX.generate_toy_lwe(
            seed,
            dimension=dimension,
            samples=samples,
            modulus=97,
            secret_radius=secret_radius,
            error_radius=1,
        )
        truth = BOX.exhaustive_search(instance)
        graph_result = _multiscale_search(instance, through_graph=True)
        direct_result = _multiscale_search(instance, through_graph=False)
        if graph_result.candidate != direct_result.candidate or graph_result.score != direct_result.score:
            raise RuntimeError("graph compilation changed the direct search result")
        if graph_result.objective_evaluations != direct_result.objective_evaluations:
            raise RuntimeError("graph compilation changed objective accounting")
        single_result = _single_scale_search(instance)
        random_result = _random_search(instance, budget=graph_result.objective_evaluations, seed=91_000_000 + seed)
        search_rows.append(
            {
                "seed": seed,
                "optimum_score": truth.score,
                "graph_candidate": list(graph_result.candidate),
                "graph_score": graph_result.score,
                "graph_gap": graph_result.score - truth.score,
                "graph_evaluations": graph_result.objective_evaluations,
                "graph_receipt_head_sha256": graph_result.receipt_head_sha256,
                "direct_candidate": list(direct_result.candidate),
                "direct_score": direct_result.score,
                "direct_gap": direct_result.score - truth.score,
                "direct_evaluations": direct_result.objective_evaluations,
                "single_scale_gap": single_result.score - truth.score,
                "single_scale_evaluations": single_result.objective_evaluations,
                "random_gap": random_result.score - truth.score,
                "random_evaluations": random_result.objective_evaluations,
                "graph_exact_score_hit": graph_result.score == truth.score,
                "single_scale_exact_score_hit": single_result.score == truth.score,
                "random_exact_score_hit": random_result.score == truth.score,
            }
        )

    finite_check = _finite_model_check(depth=finite_depth)
    naive_events = [int(row["naive_events"]) for row in chatter_rows]
    hybrid_jumps = [int(row["hybrid_jumps"]) for row in chatter_rows]
    graph_gaps = [int(row["graph_gap"]) for row in search_rows]
    direct_gaps = [int(row["direct_gap"]) for row in search_rows]
    single_gaps = [int(row["single_scale_gap"]) for row in search_rows]
    random_gaps = [int(row["random_gap"]) for row in search_rows]
    parity = all(
        row["graph_candidate"] == row["direct_candidate"]
        and row["graph_score"] == row["direct_score"]
        and row["graph_evaluations"] == row["direct_evaluations"]
        for row in search_rows
    )
    control_valid = (
        finite_check["invariant_failures"] == 0
        and all(bool(row["replay_verified"]) for row in chatter_rows)
        and all(int(row["hybrid_jumps"]) == chatter_episodes for row in chatter_rows)
        and parity
    )
    chatter_effect = _paired_effect(hybrid_jumps, naive_events)
    if not control_valid:
        status = "ORIENTED_ZERO_HYBRID_FAILED_VALIDATION"
    elif not chatter_effect["improvement_exceeds_two_population_sd"]:
        status = "ORIENTED_ZERO_HYBRID_UNDERPOWERED"
    else:
        status = "ORIENTED_ZERO_CONTROL_VALIDATED_NO_INDEPENDENT_SEARCH_GAIN"

    report: dict[str, object] = {
        "schema": "scbe.oriented-zero-hybrid-benchmark.v1",
        "status": status,
        "claim_boundary": "exact_hybrid_control_and_tiny_integer_toy_LWE_only",
        "interpretation": (
            "The ceiling/guard/graph construction is a valid deterministic control and audit primitive. "
            "Graph compilation exactly matches its direct multiscale scheduler, so the graph itself supplies no "
            "new target information or cryptanalytic speedup."
        ),
        "parameters": {
            "seed_start": seed_start,
            "seeds": seeds,
            "dimension": dimension,
            "samples": samples,
            "secret_radius": secret_radius,
            "chatter_episodes": chatter_episodes,
            "jitter_steps": jitter_steps,
            "finite_depth": finite_depth,
            "arithmetic": "integer objectives and Fraction guards; float only for plotting",
        },
        "finite_model_check": finite_check,
        "chatter_control": {
            "rows": chatter_rows,
            "mean_naive_events": _ratio(naive_events),
            "mean_hybrid_jumps": _ratio(hybrid_jumps),
            "paired_effect": chatter_effect,
        },
        "toy_search": {
            "rows": search_rows,
            "graph_direct_exact_parity": parity,
            "graph_mean_gap": _ratio(graph_gaps),
            "direct_mean_gap": _ratio(direct_gaps),
            "single_scale_mean_gap": _ratio(single_gaps),
            "random_mean_gap": _ratio(random_gaps),
            "graph_exact_score_hits": sum(bool(row["graph_exact_score_hit"]) for row in search_rows),
            "single_scale_exact_score_hits": sum(bool(row["single_scale_exact_score_hit"]) for row in search_rows),
            "random_exact_score_hits": sum(bool(row["random_exact_score_hit"]) for row in search_rows),
            "graph_vs_direct": _paired_effect(graph_gaps, direct_gaps),
            "graph_vs_single_scale": _paired_effect(graph_gaps, single_gaps),
            "graph_vs_size_matched_random": _paired_effect(graph_gaps, random_gaps),
        },
        "security_boundaries": [
            "unoriented exact zero quarantines rather than inventing a side",
            "missing or duplicate regional routes fail closed",
            "hysteresis, reset, dwell, and jump budget bound repeated transitions",
            "hash linkage is tamper evident and still needs an external signature for authentication",
            "no result here applies directly to ML-KEM, ML-DSA, or production key recovery",
        ],
        "source_receipts": _source_receipts(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    if plot is not None:
        plot.parent.mkdir(parents=True, exist_ok=True)
        _write_plot(report, plot)
    receipt = {
        "schema": "scbe.oriented-zero-hybrid-artifact-receipt.v1",
        "report": {"path": str(output.resolve()), "sha256": _sha256(output)},
        "plot": None if plot is None else {"path": str(plot.resolve()), "sha256": _sha256(plot)},
        "sources": report["source_receipts"],
    }
    receipt_path = output.with_name(f"{output.stem}_RECEIPT.json")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=30_000)
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--dimension", type=int, default=4)
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument("--secret-radius", type=int, default=2)
    parser.add_argument("--chatter-episodes", type=int, default=12)
    parser.add_argument("--jitter-steps", type=int, default=10)
    parser.add_argument("--finite-depth", type=int, default=6)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "docs/research/evidence/oriented_zero_hybrid_20260907.json",
    )
    parser.add_argument(
        "--plot",
        type=Path,
        default=PROJECT_ROOT / "docs/research/evidence/oriented_zero_hybrid_20260907.png",
    )
    args = parser.parse_args()
    report = run(
        seed_start=args.seed_start,
        seeds=args.seeds,
        dimension=args.dimension,
        samples=args.samples,
        secret_radius=args.secret_radius,
        chatter_episodes=args.chatter_episodes,
        jitter_steps=args.jitter_steps,
        finite_depth=args.finite_depth,
        output=args.output,
        plot=args.plot,
    )
    print(json.dumps({"status": report["status"], "output": str(args.output), "plot": str(args.plot)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
