"""Proof suite for MAHSS tangent-rescue keyed search.

This script packages the local benchmark runs used to validate
``polyhedral_edge_k20_w4_tangent_rescue_r4_b40``. It deliberately compares the
new selector against Tang k20, plain w4, and conservative w10/gear settings
across random and structured coupling keys.

The goal is not to prove universal optimality. It proves the current claim:
tangent rescue closes the tested planted-pair recall hole while staying near
plain w4 evaluation cost on the synthetic dual-state keyed-search generator.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.experiments.mahss_dual_state_keyed_search_sim import run_seed_size_sweep


TARGET_METHOD = "polyhedral_edge_k20_w4_tangent_rescue_r4_b40"
BASELINE_METHODS = (
    "tang_cross_k20",
    "polyhedral_edge_k20_w4",
    "polyhedral_edge_k20_w10",
    "polyhedral_edge_gear_k20_w4_w10",
    TARGET_METHOD,
)


@dataclass(frozen=True)
class ProofProfile:
    name: str
    key_mode: str
    sizes: tuple[int, ...]
    seed_count: int


FULL_PROFILES = (
    ProofProfile("random_orthogonal_50seed", "random_orthogonal", (80, 320, 500, 1000, 2000), 50),
    ProofProfile("random_orthogonal_n5000_20seed", "random_orthogonal", (5000,), 20),
    ProofProfile("identity_20seed", "identity", (500, 1000, 2000), 20),
    ProofProfile("signed_permutation_20seed", "signed_permutation", (500, 1000, 2000), 20),
    ProofProfile("hadamard_20seed", "hadamard", (500, 1000, 2000), 20),
    ProofProfile("block_rotation_20seed", "block_rotation", (500, 1000, 2000), 20),
)

QUICK_PROFILES = (
    ProofProfile("quick_random_orthogonal", "random_orthogonal", (80, 320, 1000), 10),
    ProofProfile("quick_hadamard", "hadamard", (500, 1000), 10),
)


def _method_row(report: dict[str, object], method: str) -> dict[str, object]:
    aggregate = report["aggregate"]
    if not isinstance(aggregate, dict):
        raise TypeError("report aggregate must be a dict")
    row = aggregate[method]
    if not isinstance(row, dict):
        raise TypeError(f"aggregate row for {method} must be a dict")
    return row


def _compact_report(profile: ProofProfile, report: dict[str, object]) -> dict[str, object]:
    methods: dict[str, dict[str, object]] = {}
    for method in BASELINE_METHODS:
        row = _method_row(report, method)
        methods[method] = {
            "full_recall_runs": row["full_recall_runs"],
            "zero_regret_runs": row["zero_regret_runs"],
            "runs": row["runs"],
            "median_evaluations": row["median_evaluations"],
        }
    speedups = report["speedup_vs_tang_median"]
    if not isinstance(speedups, dict):
        raise TypeError("speedup_vs_tang_median must be a dict")
    return {
        "profile": profile.name,
        "key_mode": profile.key_mode,
        "sizes": list(profile.sizes),
        "seed_count": profile.seed_count,
        "methods": methods,
        "target_speedup_vs_tang_median": speedups[TARGET_METHOD],
    }


def run_profiles(profiles: Sequence[ProofProfile]) -> dict[str, object]:
    started = time.time()
    profile_reports = []
    for profile in profiles:
        print(
            f"\n=== {profile.name}: key={profile.key_mode} "
            f"sizes={list(profile.sizes)} seeds={profile.seed_count} ==="
        )
        report = run_seed_size_sweep(
            sizes=profile.sizes,
            seeds=range(profile.seed_count),
            budget_pairs=8,
            n_diamond_pairs=4,
            key_mode=profile.key_mode,
        )
        compact = _compact_report(profile, report)
        profile_reports.append(compact)
        target = compact["methods"][TARGET_METHOD]
        tang = compact["methods"]["tang_cross_k20"]
        print(
            f"  target full_recall={target['full_recall_runs']}/{target['runs']} "
            f"zero_regret={target['zero_regret_runs']}/{target['runs']} "
            f"median_evals={target['median_evaluations']} "
            f"speedup_vs_tang={compact['target_speedup_vs_tang_median']}"
        )
        print(
            f"  tang   full_recall={tang['full_recall_runs']}/{tang['runs']} "
            f"median_evals={tang['median_evaluations']}"
        )
    return {
        "schema_version": "scbe_mahss_tangent_rescue_proof_suite_v1",
        "target_method": TARGET_METHOD,
        "profiles": profile_reports,
        "elapsed_s": round(time.time() - started, 2),
        "claim_boundary": (
            "Synthetic dual-state keyed-search generator only. This suite does not "
            "cover the black-box adversarial parameter optimizer, real attention "
            "matrices, or a literature-faithful dequantized Tang sampler."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="Run a smaller smoke suite.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/mahss_dual_state/tangent_rescue_proof_suite_v1.json"),
    )
    parser.add_argument("--json", action="store_true", help="Print the output JSON after writing it.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_profiles(QUICK_PROFILES if args.quick else FULL_PROFILES)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nwrote {args.output}")
    print(f"elapsed_s={payload['elapsed_s']}")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
