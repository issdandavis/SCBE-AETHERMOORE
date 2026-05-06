"""Adversarial optimizer for the MAHSS tangent-rescue selector.

The proof suite shows tangent rescue works across fixed random and structured
key families. This script tries to break that result. It samples landscape
parameters that can make the target selector fail while keeping Tang k20 as a
fair reference. Counterexamples are preserved in JSON instead of filtered out.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.experiments.mahss_dual_state_keyed_search_sim import (  # noqa: E402
    DualStateSpec,
    amplitude_matrix,
    build_landscape,
    evaluate_selection,
    select_polyhedral_edge_gear_cross,
    select_polyhedral_edge_tangent_rescue_cross,
    select_polyhedral_edge_walk_cross,
    select_tang_cross,
)


TARGET_METHOD = "polyhedral_edge_k20_w4_tangent_rescue_r4_b40"


@dataclass(frozen=True)
class AdversarialCase:
    n: int
    seed: int
    key_mode: str
    n_decoys_per_side: int
    decoy_norm: float
    diamond_alignment: float


def _parse_ints(raw: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in raw.split(",") if part.strip())


def _parse_floats(raw: str) -> tuple[float, ...]:
    return tuple(float(part.strip()) for part in raw.split(",") if part.strip())


def _parse_strings(raw: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _select_methods(spec: DualStateSpec, *, budget_pairs: int) -> dict[str, dict[str, object]]:
    landscape = build_landscape(spec)
    A = landscape["A"]
    B = landscape["B"]
    M = landscape["M"]
    assert isinstance(A, np.ndarray) and isinstance(B, np.ndarray) and isinstance(M, np.ndarray)
    log_amp = amplitude_matrix(A, B, M)
    runs = {
        "tang_cross_k20": select_tang_cross(A, B, M, k_per_side=20, budget_pairs=budget_pairs),
        "polyhedral_edge_k20_w4": select_polyhedral_edge_walk_cross(
            A, B, M, seed_count=20, edge_width=4, budget_pairs=budget_pairs
        ),
        "polyhedral_edge_k20_w10": select_polyhedral_edge_walk_cross(
            A, B, M, seed_count=20, edge_width=10, budget_pairs=budget_pairs
        ),
        "polyhedral_edge_gear_k20_w4_w10": select_polyhedral_edge_gear_cross(
            A,
            B,
            M,
            seed_count=20,
            fast_width=4,
            torque_width=10,
            shift_threshold=80_000,
            budget_pairs=budget_pairs,
        )[:2],
        TARGET_METHOD: select_polyhedral_edge_tangent_rescue_cross(
            A,
            B,
            M,
            seed_count=20,
            edge_width=4,
            tangent_planes=4,
            rescue_budget=40,
            budget_pairs=budget_pairs,
        )[:2],
    }
    out: dict[str, dict[str, object]] = {}
    for method, (pairs, evaluations) in runs.items():
        row = evaluate_selection(pairs, landscape, log_amp)
        row["total_evaluations"] = int(evaluations)
        out[method] = row
    return out


def _case_score(methods: dict[str, dict[str, object]]) -> float:
    """Higher score means worse for tangent rescue under a fair Tang baseline."""

    target = methods[TARGET_METHOD]
    tang = methods["tang_cross_k20"]
    if float(tang["diamond_recall"]) < 1.0 or float(tang["regret_log_amp"]) != 0.0:
        return -1.0
    recall_gap = 1.0 - float(target["diamond_recall"])
    regret = float(target["regret_log_amp"])
    eval_ratio = float(target["total_evaluations"]) / max(1.0, float(tang["total_evaluations"]))
    return 1000.0 * recall_gap + 10.0 * regret + max(0.0, eval_ratio - 0.45)


def _sample_cases(
    *,
    rng: random.Random,
    trials: int,
    sizes: Sequence[int],
    seeds: Sequence[int],
    key_modes: Sequence[str],
    decoys: Sequence[int],
    decoy_norms: Sequence[float],
    alignments: Sequence[float],
) -> list[AdversarialCase]:
    cases: list[AdversarialCase] = []
    for _ in range(trials):
        cases.append(
            AdversarialCase(
                n=int(rng.choice(sizes)),
                seed=int(rng.choice(seeds)),
                key_mode=str(rng.choice(key_modes)),
                n_decoys_per_side=int(rng.choice(decoys)),
                decoy_norm=float(rng.choice(decoy_norms)),
                diamond_alignment=float(rng.choice(alignments)),
            )
        )
    return cases


def run_adversarial_search(
    *,
    trials: int,
    sizes: Sequence[int],
    seeds: Sequence[int],
    key_modes: Sequence[str],
    decoys: Sequence[int],
    decoy_norms: Sequence[float],
    alignments: Sequence[float],
    random_seed: int,
    budget_pairs: int,
) -> dict[str, object]:
    started = time.time()
    rng = random.Random(random_seed)
    cases = _sample_cases(
        rng=rng,
        trials=trials,
        sizes=sizes,
        seeds=seeds,
        key_modes=key_modes,
        decoys=decoys,
        decoy_norms=decoy_norms,
        alignments=alignments,
    )
    scored: list[dict[str, object]] = []
    fair_count = 0
    target_fail_count = 0
    for idx, case in enumerate(cases):
        spec = DualStateSpec(
            n_a=case.n,
            n_b=case.n,
            n_diamond_pairs=4,
            n_decoys_per_side=case.n_decoys_per_side,
            decoy_norm=case.decoy_norm,
            diamond_alignment=case.diamond_alignment,
            seed=case.seed,
            key_mode=case.key_mode,
        )
        methods = _select_methods(spec, budget_pairs=budget_pairs)
        score = _case_score(methods)
        fair = score >= 0.0
        if fair:
            fair_count += 1
            if float(methods[TARGET_METHOD]["diamond_recall"]) < 1.0:
                target_fail_count += 1
        scored.append(
            {
                "trial": idx,
                "case": asdict(case),
                "fair_tang_baseline": fair,
                "adversarial_score": round(score, 6),
                "methods": methods,
            }
        )

    fair_cases = [row for row in scored if bool(row["fair_tang_baseline"])]
    fair_cases.sort(key=lambda row: float(row["adversarial_score"]), reverse=True)
    all_cases = sorted(scored, key=lambda row: float(row["adversarial_score"]), reverse=True)
    return {
        "schema_version": "scbe_mahss_tangent_rescue_adversarial_v1",
        "target_method": TARGET_METHOD,
        "trials": int(trials),
        "fair_tang_cases": int(fair_count),
        "target_failures_under_fair_tang": int(target_fail_count),
        "random_seed": int(random_seed),
        "budget_pairs": int(budget_pairs),
        "search_space": {
            "sizes": [int(n) for n in sizes],
            "seeds": [int(seed) for seed in seeds],
            "key_modes": list(key_modes),
            "decoys": [int(value) for value in decoys],
            "decoy_norms": [float(value) for value in decoy_norms],
            "diamond_alignments": [float(value) for value in alignments],
        },
        "worst_fair_cases": fair_cases[:20],
        "worst_all_cases": all_cases[:20],
        "elapsed_s": round(time.time() - started, 2),
        "interpretation": (
            "A counterexample requires target_failures_under_fair_tang > 0. "
            "Unfair cases where Tang also fails are tracked but do not refute the speed claim."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=500)
    parser.add_argument("--random-seed", type=int, default=20260506)
    parser.add_argument("--sizes", default="80,320,500,1000,2000")
    parser.add_argument("--seeds", default="0:100", help="Comma list or start:end range.")
    parser.add_argument(
        "--key-modes",
        default="random_orthogonal,identity,signed_permutation,hadamard,block_rotation",
    )
    parser.add_argument("--decoys", default="12,16,20,24,32")
    parser.add_argument("--decoy-norms", default="5.5,6.0,6.5,7.0")
    parser.add_argument("--alignments", default="0.82,0.88,0.92,0.96")
    parser.add_argument("--budget-pairs", type=int, default=8)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/mahss_dual_state/tangent_rescue_adversarial_v1.json"),
    )
    parser.add_argument("--json", action="store_true")
    return parser


def _parse_seed_spec(raw: str) -> tuple[int, ...]:
    if ":" in raw:
        start, end = raw.split(":", 1)
        return tuple(range(int(start), int(end)))
    return _parse_ints(raw)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_adversarial_search(
        trials=args.trials,
        sizes=_parse_ints(args.sizes),
        seeds=_parse_seed_spec(args.seeds),
        key_modes=_parse_strings(args.key_modes),
        decoys=_parse_ints(args.decoys),
        decoy_norms=_parse_floats(args.decoy_norms),
        alignments=_parse_floats(args.alignments),
        random_seed=args.random_seed,
        budget_pairs=args.budget_pairs,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(
        f"trials={payload['trials']} fair_tang={payload['fair_tang_cases']} "
        f"target_failures_under_fair_tang={payload['target_failures_under_fair_tang']} "
        f"elapsed_s={payload['elapsed_s']}"
    )
    worst = payload["worst_fair_cases"]
    if isinstance(worst, list) and worst:
        top = worst[0]
        print(f"worst_fair_case={json.dumps(top['case'], sort_keys=True)}")
        methods = top["methods"]
        if isinstance(methods, dict):
            target = methods[TARGET_METHOD]
            print(
                f"target recall={target['diamond_recall']} regret={target['regret_log_amp']} "
                f"evals={target['total_evaluations']}"
            )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
