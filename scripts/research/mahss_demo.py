"""MAHSS demo: transparent-paper illumination across K parallel attention mechanisms.

Diagnostic harness against ``python.scbe.mahss``. Runs four cases that probe
where the "transparent paper illuminates the target" claim holds and where it
breaks.

Cases:

1. ``aligned_manual``   — query == sparse_local output, router weights
                          MANUALLY pinned to sparse_local. This mirrors the
                          existing unit test and is the regime in which the
                          peak-illumination claim is known to hold.
2. ``aligned_auto``     — same query, auto-router via query.role inner
                          products. Diagnostic: shows whether random
                          hash-derived role vectors carry enough signal
                          for the router to recover the right mechanism.
3. ``mixed_auto``       — query is a 50/50 blend of dense + sparse, auto
                          router. Diagnostic: shows whether the peaks rank
                          the two source mechanisms above the distractors.
4. ``misaligned_manual``— query at sparse_local, router pinned at dense.
                          Diagnostic for the ΔS strain telemetry: does the
                          current cross_manifold_strain formula rise when
                          the router disagrees with the query, or is it
                          measuring something else?

Findings are printed as PASS/FAIL claim flags so the demo is honest about
which parts of the MAHSS spec are validated and which need follow-up.

Wiring to SCBE layers (comment-only, no new layer code is introduced):

* L1-L2  — each ``attention_outputs`` entry is treated as a candidate output of
           a different attention kernel running in parallel at realification.
* L7     — ``mobius_phase_fold`` provides the bounded isometric "fold" that
           densifies the search space without changing topological invariants.
* L9-L10 — illumination peaks + router_entropy are the spectral / spin-style
           telemetry surface; cross_manifold_strain is the live ΔS readout.

Run::

    python scripts/research/mahss_demo.py
    python scripts/research/mahss_demo.py --json   # machine-readable receipt
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from python.scbe.mahss import (  # noqa: E402
    MAHSSConfig,
    MAHSSResult,
    build_mahss,
    intention_router_via_outputs,
    toy_attention_outputs,
)

DIM = 128
SEED_NOISE = 47


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 0.0 else vector


def _add_distractor(outputs: dict[str, tuple[float, ...]], dim: int = DIM) -> dict[str, tuple[float, ...]]:
    """Add a deterministic noise mechanism so K >= 4 (multi-attention proper)."""

    rng = np.random.default_rng(SEED_NOISE)
    noise = rng.standard_normal(dim) * 0.5
    return {**outputs, "noise_distractor": tuple(noise)}


def _mixed_query(outputs: dict[str, tuple[float, ...]]) -> tuple[float, ...]:
    dense = np.asarray(outputs["dense_global"], dtype=float)
    sparse = np.asarray(outputs["sparse_local"], dtype=float)
    return tuple(_normalize(0.5 * dense + 0.5 * sparse))


def _ranked(illumination: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(illumination.items(), key=lambda item: item[1], reverse=True)


def _format_case(label: str, result: MAHSSResult) -> str:
    lines = [f"=== {label} ==="]
    lines.append(f"  selected_mechanism : {result.selected_mechanism}")
    lines.append(f"  peak_margin        : {result.peak_margin:+.6f}")
    lines.append(f"  cross_manifold_strain : {result.cross_manifold_strain:.6f}")
    lines.append(f"  router_entropy        : {float(result.telemetry['router_entropy']):.6f}")
    lines.append(f"  folded_norm           : {float(result.telemetry['folded_norm']):.6f}")
    lines.append("  illumination ranked:")
    for name, score in _ranked(result.illumination):
        lines.append(f"    {name:>20s}  {score:+.6f}")
    lines.append("  router weights:")
    for name, weight in sorted(result.router_weights.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"    {name:>20s}  {weight:.6f}")
    return "\n".join(lines)


def run_demo(*, dim: int = DIM) -> dict[str, Any]:
    """Run the four diagnostic cases and return a structured receipt."""

    cfg = MAHSSConfig(dim=dim, fold_strength=1.0 / ((1.0 + math.sqrt(5.0)) / 2.0))
    outputs = _add_distractor(toy_attention_outputs(dim=dim), dim=dim)
    receipts: dict[str, MAHSSResult] = {}

    pinned_sparse = {
        "dense_global": 0.05,
        "sparse_local": 0.85,
        "state_space": 0.05,
        "noise_distractor": 0.05,
    }
    pinned_dense = {
        "dense_global": 0.85,
        "sparse_local": 0.05,
        "state_space": 0.05,
        "noise_distractor": 0.05,
    }

    # 1. aligned_manual — manual router; mirrors the unit test that already
    #    proves the unbinding peaks rank correctly for this regime.
    receipts["aligned_manual"] = build_mahss(
        outputs, outputs["sparse_local"], config=cfg, router_weights=pinned_sparse
    )

    # 2. aligned_auto — same query, auto-router. Probe whether random
    #    hash-derived roles carry enough signal to pick the right mechanism.
    receipts["aligned_auto"] = build_mahss(outputs, outputs["sparse_local"], config=cfg)

    # 3. mixed_auto — query blends two mechanisms; auto-router.
    receipts["mixed_auto"] = build_mahss(outputs, _mixed_query(outputs), config=cfg)

    # 4. misaligned_manual — query at sparse, router pinned at dense.
    #    Probes whether ΔS strain rises under router/output disagreement.
    receipts["misaligned_manual"] = build_mahss(
        outputs, outputs["sparse_local"], config=cfg, router_weights=pinned_dense
    )

    # 5. aligned_via_outputs — content-aware auto-router. Projects the query
    #    through the actual attention outputs (not random role hashes) before
    #    scoring. This is the fix for the diagnostic gap surfaced by case 2.
    via_outputs_weights = intention_router_via_outputs(outputs["sparse_local"], outputs, config=cfg)
    receipts["aligned_via_outputs"] = build_mahss(
        outputs, outputs["sparse_local"], config=cfg, router_weights=via_outputs_weights
    )

    am = receipts["aligned_manual"]
    aa = receipts["aligned_auto"]
    mx = receipts["mixed_auto"]
    ms = receipts["misaligned_manual"]
    av = receipts["aligned_via_outputs"]
    mixed_top_two = {name for name, _ in sorted(mx.illumination.items(), key=lambda i: i[1], reverse=True)[:2]}

    summary = {
        "schema_version": "scbe_mahss_demo_v1",
        "dim": dim,
        "fold_strength": cfg.fold_strength,
        "cases": {
            label: {
                "selected_mechanism": r.selected_mechanism,
                "peak_margin": r.peak_margin,
                "cross_manifold_strain": r.cross_manifold_strain,
                "router_entropy": float(r.telemetry["router_entropy"]),
                "folded_norm": float(r.telemetry["folded_norm"]),
                "illumination": dict(r.illumination),
                "router_weights": dict(r.router_weights),
            }
            for label, r in receipts.items()
        },
        "claims": {
            # validated regime
            "manual_router_aligned_winner_is_sparse": am.selected_mechanism == "sparse_local",
            "manual_router_aligned_peak_margin_positive": am.peak_margin > 0.0,
            # diagnostic regime — these are the OPEN questions for the random-hash auto-router
            "auto_router_aligned_winner_is_sparse": aa.selected_mechanism == "sparse_local",
            "mixed_top_two_are_blend_pair": mixed_top_two == {"dense_global", "sparse_local"},
            "misaligned_strain_strictly_greater_than_aligned": (
                ms.cross_manifold_strain > am.cross_manifold_strain
            ),
            # query-projection fix
            "via_outputs_router_aligned_winner_is_sparse": av.selected_mechanism == "sparse_local",
            "via_outputs_router_peak_margin_positive": av.peak_margin > 0.0,
        },
        "findings": {
            "validated": [
                "manual-router regime: when router weights match query origin, "
                "unbinding peaks correctly rank the source mechanism on top.",
            ],
            "open_questions": [],
        },
    }

    if not summary["claims"]["auto_router_aligned_winner_is_sparse"]:
        summary["findings"]["open_questions"].append(
            "auto-router uses random hash-derived role vectors; query-to-role "
            "inner products do not encode mechanism affinity. The router needs "
            "either learned roles or a query-projection step that lifts the "
            "query into role-space before scoring."
        )
    if not summary["claims"]["mixed_top_two_are_blend_pair"]:
        summary["findings"]["open_questions"].append(
            "mixed-query unbinding does not isolate the blend pair from the "
            "noise distractor; suggests the role-hash basis is not orthogonal "
            "enough at this dim, or the fold contracts the wrong axes."
        )
    if not summary["claims"]["misaligned_strain_strictly_greater_than_aligned"]:
        summary["findings"]["open_questions"].append(
            "current cross_manifold_strain formula = "
            "abs(folded_norm - clipped_raw_projection) is a fold-contraction "
            "metric, not a router/output disagreement metric. To make ΔS catch "
            "router misalignment, add a term that compares the unbound peak "
            "winner against the top-weight router mechanism."
        )

    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON receipt instead of human summary")
    parser.add_argument("--dim", type=int, default=DIM, help="HRR dimension (default 32)")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    summary = run_demo(dim=args.dim)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    cfg = MAHSSConfig(dim=args.dim, fold_strength=summary["fold_strength"])
    outputs = _add_distractor(toy_attention_outputs(dim=args.dim), dim=args.dim)
    pinned_sparse = {
        "dense_global": 0.05,
        "sparse_local": 0.85,
        "state_space": 0.05,
        "noise_distractor": 0.05,
    }
    pinned_dense = {
        "dense_global": 0.85,
        "sparse_local": 0.05,
        "state_space": 0.05,
        "noise_distractor": 0.05,
    }
    aligned_manual = build_mahss(outputs, outputs["sparse_local"], config=cfg, router_weights=pinned_sparse)
    aligned_auto = build_mahss(outputs, outputs["sparse_local"], config=cfg)
    mixed_auto = build_mahss(outputs, _mixed_query(outputs), config=cfg)
    misaligned_manual = build_mahss(outputs, outputs["sparse_local"], config=cfg, router_weights=pinned_dense)
    via_outputs_weights = intention_router_via_outputs(outputs["sparse_local"], outputs, config=cfg)
    aligned_via_outputs = build_mahss(
        outputs, outputs["sparse_local"], config=cfg, router_weights=via_outputs_weights
    )

    print(_format_case("aligned_manual (router pinned at sparse, query at sparse)", aligned_manual))
    print()
    print(_format_case("aligned_auto (auto-router, query at sparse)", aligned_auto))
    print()
    print(_format_case("mixed_auto (auto-router, query = 0.5*dense + 0.5*sparse)", mixed_auto))
    print()
    print(_format_case("misaligned_manual (router at dense, query at sparse)", misaligned_manual))
    print()
    print(_format_case("aligned_via_outputs (content-aware router, query at sparse)", aligned_via_outputs))
    print()
    print("--- claims ---")
    for claim, value in summary["claims"].items():
        flag = "ok" if value else "FAIL"
        print(f"  [{flag}] {claim} = {value}")
    print()
    print("--- findings ---")
    print("validated:")
    for item in summary["findings"]["validated"]:
        print(f"  + {item}")
    if summary["findings"]["open_questions"]:
        print("open_questions:")
        for item in summary["findings"]["open_questions"]:
            print(f"  ? {item}")
    # Exit 0 if the validated-regime claims hold, even if open-question claims
    # do not. The diagnostic regime is expected to surface gaps.
    validated_keys = (
        "manual_router_aligned_winner_is_sparse",
        "manual_router_aligned_peak_margin_positive",
    )
    return 0 if all(summary["claims"][k] for k in validated_keys) else 1


if __name__ == "__main__":
    raise SystemExit(main())
