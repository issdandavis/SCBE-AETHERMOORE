"""Seed and size sweep for the dual-state keyed-search winners.

Runs `run_compare` across a grid of (n, seed) pairs and aggregates
recall + total_evaluations per method. Targets the four direct-mode
selectors that achieved 4/4 recall on the seed=19 default:

  - polyhedral_edge_k20_w4     (current winner, sign-facet hypercube)
  - polyhedral_edge_k20_w10    (conservative torque gear)
  - polyhedral_edge_gear_k20_w4_w10 (adaptive speed/torque selector)
  - polyhedral_edge_k20_w4_tangent_rescue_r4_b40 (fast edge + tangent sidecars)
  - polyhedral_edge_k20_w10_weighted (weighted hybrid edge diagnostic)
  - constructive_oscillation_k8_o4_w3 (Lyapunov-derivative oscillation)
  - polyhedral_edge_k30_w6     (parameter-bumped sign-facet)
  - tang_cross_k20             (top-K-by-norm baseline)

For each method we report:
  - recall@full count: how many seeds (out of N) achieved full diamond recall
  - mean total_evaluations conditional on full recall
  - std of total_evaluations conditional on full recall
  - recall failure mode (mean recall when not full)

Two regimes:
  1. SEED STABILITY at fixed n=80, n_diamonds=4 over many seeds
  2. SIZE SCALING over n in {40, 80, 160, 320}, using a small seed block

Output: artifacts/mahss_dual_state/sweep_v1.json + console summary.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.experiments.mahss_dual_state_keyed_search_sim import (  # noqa: E402
    DualStateSpec,
    run_compare,
)

TRACKED_METHODS = (
    "polyhedral_edge_k20_w4",
    "polyhedral_edge_k20_w10",
    "polyhedral_edge_gear_k20_w4_w10",
    "polyhedral_edge_k20_w4_tangent_rescue_r4_b40",
    "polyhedral_edge_k20_w10_weighted",
    "constructive_oscillation_k8_o4_w3",
    "polyhedral_edge_k30_w6",
    "tang_cross_k20",
    "resonance_cross_a1",
    "multigrid_cross_c30_k10",
)


@dataclass
class TrialResult:
    n_a: int
    n_b: int
    seed: int
    method: str
    diamond_recall: float
    diamonds_caught: int
    n_diamond_pairs: int
    regret_log_amp: float
    total_evaluations: int


def run_one(n: int, seed: int, n_diamonds: int = 4, budget_pairs: int = 8) -> list[TrialResult]:
    spec = DualStateSpec(
        n_a=n,
        n_b=n,
        n_diamond_pairs=n_diamonds,
        n_decoys_per_side=12,
        seed=seed,
    )
    report = run_compare(spec, budget_pairs=budget_pairs)
    summary = report["summary"]
    out: list[TrialResult] = []
    for method in TRACKED_METHODS:
        if method not in summary:
            continue
        row = summary[method]
        out.append(
            TrialResult(
                n_a=n,
                n_b=n,
                seed=seed,
                method=method,
                diamond_recall=float(row["diamond_recall"]),
                diamonds_caught=int(row["diamonds_caught"]),
                n_diamond_pairs=int(row["n_diamond_pairs"]),
                regret_log_amp=float(row["regret_log_amp"]),
                total_evaluations=int(row["total_evaluations"]),
            )
        )
    return out


def _summarize(rows: list[TrialResult]) -> dict[str, dict[str, object]]:
    by_method: dict[str, list[TrialResult]] = {}
    for r in rows:
        by_method.setdefault(r.method, []).append(r)

    summary: dict[str, dict[str, object]] = {}
    for method, trials in by_method.items():
        full_recall = [t for t in trials if t.diamond_recall >= 1.0 and t.regret_log_amp == 0.0]
        partial = [t for t in trials if t not in full_recall]
        full_evals = [t.total_evaluations for t in full_recall]
        partial_recalls = [t.diamond_recall for t in partial]
        summary[method] = {
            "n_trials": len(trials),
            "full_recall_count": len(full_recall),
            "full_recall_rate": round(len(full_recall) / max(1, len(trials)), 4),
            "evals_when_full_mean": round(statistics.fmean(full_evals), 2) if full_evals else None,
            "evals_when_full_stdev": round(statistics.pstdev(full_evals), 2) if len(full_evals) > 1 else None,
            "evals_when_full_min": min(full_evals) if full_evals else None,
            "evals_when_full_max": max(full_evals) if full_evals else None,
            "partial_recall_mean": (
                round(statistics.fmean(partial_recalls), 4) if partial_recalls else None
            ),
        }
    return summary


def run_seed_stability(seeds: list[int], n: int = 80) -> dict[str, object]:
    print(f"\n=== Seed stability at n_a=n_b={n}, {len(seeds)} seeds ===")
    rows: list[TrialResult] = []
    t0 = time.time()
    for seed in seeds:
        rows.extend(run_one(n, seed))
    elapsed = time.time() - t0
    summary = _summarize(rows)
    print(f"  ran {len(seeds)} seeds in {elapsed:.1f}s")
    print(f"  {'method':<42} {'full_recall':>13} {'evals_mean':>10} {'evals_std':>9} {'evals_range':>14}")
    for method, row in summary.items():
        rate = row["full_recall_rate"]
        evals_mean = row["evals_when_full_mean"]
        evals_std = row["evals_when_full_stdev"]
        evals_min = row["evals_when_full_min"]
        evals_max = row["evals_when_full_max"]
        rng = f"[{evals_min}, {evals_max}]" if evals_min is not None else "n/a"
        evals_str = f"{evals_mean:>10}" if evals_mean is not None else f"{'n/a':>10}"
        std_str = f"{evals_std:>9}" if evals_std is not None else f"{'n/a':>9}"
        print(
            f"  {method:<42} {row['full_recall_count']:>3}/{row['n_trials']:<3} ({rate:>5.0%}) {evals_str} {std_str} {rng:>14}"
        )
    return {"n": n, "seeds": seeds, "summary": summary, "rows": [asdict(r) for r in rows]}


def run_size_scaling(sizes: list[int], seed: int = 19, n_seeds_per_size: int = 5) -> dict[str, object]:
    print(f"\n=== Size scaling, seeds {seed}..{seed + n_seeds_per_size - 1} per size ===")
    by_size: dict[int, list[TrialResult]] = {n: [] for n in sizes}
    for n in sizes:
        for s in range(seed, seed + n_seeds_per_size):
            by_size[n].extend(run_one(n, s))
    print(
        f"  {'method':<42} "
        + " ".join(f"n={n:>4}".rjust(13) for n in sizes)
    )
    out: dict[str, dict[int, dict[str, object]]] = {}
    for method in TRACKED_METHODS:
        line = f"  {method:<42} "
        out[method] = {}
        for n in sizes:
            method_rows = [r for r in by_size[n] if r.method == method]
            if not method_rows:
                line += "  ----        "
                continue
            sub = _summarize(method_rows)[method]
            rate = sub["full_recall_rate"]
            evals = sub["evals_when_full_mean"]
            evals_str = f"{int(evals)}" if evals is not None else "fail"
            line += f"  {evals_str:>5}@{rate:.0%}    "
            out[method][n] = sub
        print(line)
    return {"sizes": sizes, "n_seeds_per_size": n_seeds_per_size, "summary": out}


def main() -> int:
    t_start = time.time()
    seeds = list(range(11, 61))  # 50 seeds: 11..60
    seed_block = run_seed_stability(seeds, n=80)
    sizes = [40, 80, 160, 320]
    size_block = run_size_scaling(sizes, seed=11, n_seeds_per_size=5)

    out_path = Path("artifacts/mahss_dual_state/sweep_v1.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "scbe_mahss_dual_state_sweep_v1",
        "seed_stability": seed_block,
        "size_scaling": size_block,
        "elapsed_s": round(time.time() - t_start, 2),
    }
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nwrote {out_path}")
    print(f"total time: {payload['elapsed_s']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
