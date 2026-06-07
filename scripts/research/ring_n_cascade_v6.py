"""Ring N blind test — cascade v6 as-is disambiguator.

Ring M falsified the frozen_dominant conclusion while the v6 trigger still fired.
Ring N (750M-800M) is intentionally run with v6 unchanged:

  - if frozen wins again, M may have been a one-board reversal/noise point
  - if frozen_coherent or another blend wins again, M was a real turning point

Do not add the v7 corr_frz_cen exit here. This script tests the old rule.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.range_regime_classifier import (  # noqa: E402
    ANCHOR_THRESHOLD,
    COOP_WA,
    COOP_WC,
    COOP_WF,
    D_WA,
    D_WC,
    D_WF,
    DOMINANT_WA,
    DOMINANT_WC,
    DOMINANT_WF,
    FROZEN_DOMINANT_FRZ_MEAN,
    FROZEN_DOMINANT_FRZ_SKEW,
    HISTORY,
    TOP_N,
    V6_REGIME_WEIGHTS,
    WINDOW,
    _load_frozen_spec,
    build_range_features,
    dyn_blend,
    predict_regime_v6,
    score_dict,
    z_norm,
)
from scripts.research.run_field_branch_gate_search import (
    ensure_dynamic_profiles,
)  # noqa: E402
from scripts.research.run_prime_search_engine_bench import (  # noqa: E402
    DEFAULT_ROW_CACHE_DIR,
    build_or_load_rows,
    fit_centroid_ranker,
    fit_score_normalizer,
    fresh_rows,
    labels,
    linear_scores,
    matrix,
    metrics_for_scores,
    score_frozen,
    split_ordered_rows,
)

CACHE_DIR = DEFAULT_ROW_CACHE_DIR
OUT_DIR = REPO_ROOT / "artifacts" / "ring_n_cascade_v6"
FIT_FRACTION = 0.60

REGIME_TO_WINNER = {
    "frozen_dominant": "frozen",
    "compressed_frozen_late_low_kurt": "magnitude",
    "compressed_frozen_late_high_kurt": "dominant",
    "compressed_frozen_early": "dominant",
    "frozen_coherent": "frozen_coherent",
    "magnitude": "magnitude",
    "dominant": "dominant",
}


def _hits(rows: list[dict], scores: list[float]) -> dict:
    return metrics_for_scores(
        rows, score_dict(rows, scores), TOP_N, unique_anchors_only=True
    )


def main() -> None:
    ensure_dynamic_profiles()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frozen_spec = _load_frozen_spec()

    print("=" * 72)
    print("RING N BLIND TEST — CASCADE V6 AS-IS  (750M-800M)")
    print("=" * 72)
    print("No v7 exit is applied. This is the M-turning-point disambiguator.")

    print("\nLoading calibration cache (A: 100M-150M)...", flush=True)
    rows_100 = build_or_load_rows(
        100_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True
    )
    rows_150 = build_or_load_rows(
        150_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True
    )
    range_a = fresh_rows(rows_100, rows_150)

    print("Loading Ring M cache (700M-750M)...", flush=True)
    rows_700 = build_or_load_rows(
        700_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True
    )
    rows_750 = build_or_load_rows(
        750_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True
    )
    range_m = fresh_rows(rows_700, rows_750)

    print("\nBuilding/loading Ring N cache (750M-800M)...", flush=True)
    rows_800 = build_or_load_rows(
        800_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True
    )
    range_n = fresh_rows(rows_750, rows_800)
    print(f"  Ring N rows: {len(range_n)}", flush=True)

    fit_a, _ = split_ordered_rows(range_a, FIT_FRACTION)
    frz_fit = score_frozen(fit_a, frozen_spec)
    frz_mean_norm, frz_scale_norm = fit_score_normalizer(frz_fit)

    x_fit = matrix(fit_a)
    y_fit = labels(fit_a)
    cen_model = fit_centroid_ranker(x_fit, y_fit)
    cen_fit = linear_scores(cen_model, x_fit)
    cen_mean_norm, cen_scale_norm = fit_score_normalizer(cen_fit)

    frz_m_z = z_norm(score_frozen(range_m, frozen_spec), frz_mean_norm, frz_scale_norm)
    cen_m_z = z_norm(
        linear_scores(cen_model, matrix(range_m)), cen_mean_norm, cen_scale_norm
    )
    feats_m = build_range_features(range_m, frz_m_z, cen_m_z)

    frz_n_z = z_norm(score_frozen(range_n, frozen_spec), frz_mean_norm, frz_scale_norm)
    cen_n_z = z_norm(
        linear_scores(cen_model, matrix(range_n)), cen_mean_norm, cen_scale_norm
    )
    feats_n = build_range_features(range_n, frz_n_z, cen_n_z)

    diag_keys = [
        "frz_mean",
        "frz_std",
        "frz_skew",
        "frz_kurt",
        "cen_std",
        "lambda_slope",
        "graph_ramp_density",
        "corr_frz_cen",
        "frz_p90",
    ]

    print("\n[RING N FEATURES]")
    print(f"  {'feature':32s}  {'M':>10}  {'N (new)':>10}")
    for key in diag_keys:
        print(
            f"  {key:32s}  {feats_m.get(key, float('nan')):>+10.4f}  {feats_n.get(key, float('nan')):>+10.4f}"
        )

    regime, fired = predict_regime_v6(feats_n)
    wf, wa, wc = V6_REGIME_WEIGHTS[regime]
    expected_winner = REGIME_TO_WINNER.get(regime, regime)

    print("\n[CASCADE V6 PREDICTION — AS-IS]")
    print(
        f"  ORDER-1 frozen_dominant: "
        f"frz_mean>{FROZEN_DOMINANT_FRZ_MEAN}={feats_n['frz_mean'] > FROZEN_DOMINANT_FRZ_MEAN}  "
        f"AND frz_skew>{FROZEN_DOMINANT_FRZ_SKEW}={feats_n['frz_skew'] > FROZEN_DOMINANT_FRZ_SKEW}"
    )
    print(f"  prediction: {regime}  fired={fired}")
    print(f"  weights: wf={wf} wa={wa} wc={wc}")
    print(f"  expected winner: {expected_winner}")

    scores = {
        "frozen": frz_n_z,
        "dominant": dyn_blend(frz_n_z, cen_n_z, DOMINANT_WF, DOMINANT_WA, DOMINANT_WC),
        "magnitude": dyn_blend(frz_n_z, cen_n_z, D_WF, D_WA, D_WC),
        "frozen_coherent": dyn_blend(frz_n_z, cen_n_z, COOP_WF, COOP_WA, COOP_WC),
        "v6_committed": dyn_blend(frz_n_z, cen_n_z, wf, wa, wc),
    }
    metrics = {name: _hits(range_n, values) for name, values in scores.items()}
    hits = {name: item["unique_anchor_hits"] for name, item in metrics.items()}
    total = metrics["frozen"]["unique_anchors_total"]

    print("\n[RESULTS] Ring N")
    for name in ("frozen", "dominant", "magnitude", "frozen_coherent", "v6_committed"):
        delta = hits[name] - hits["frozen"]
        print(f"  {name:18s} N={hits[name]}/{total}  delta={delta:+d}")

    controller_hits = {
        key: hits[key] for key in ("frozen", "dominant", "magnitude", "frozen_coherent")
    }
    winner = max(controller_hits, key=controller_hits.get)
    v6_correct = expected_winner == winner

    print(f"\n  WINNER: {winner} ({controller_hits[winner]}/{total})")
    print(
        f"  v6 correct: {'YES' if v6_correct else 'NO'}  (predicted {expected_winner})"
    )
    print(
        f"  frozen margin: {hits['frozen'] - max(hits['dominant'], hits['magnitude'], hits['frozen_coherent']):+d}"
    )

    artifact = {
        "schema": "ring_n_cascade_v6_v1",
        "date": "2026-06-04",
        "ring": "N",
        "range": "750M-800M",
        "cascade_tested": "v6_as_is",
        "ring_m_features": {key: feats_m[key] for key in diag_keys if key in feats_m},
        "ring_n_features": {key: feats_n[key] for key in diag_keys if key in feats_n},
        "v6_prediction": {
            "regime": regime,
            "fired": fired,
            "weights": {"wf": wf, "wa": wa, "wc": wc},
            "expected_winner": expected_winner,
            "hits": hits["v6_committed"],
            "correct": v6_correct,
        },
        "results": {
            "total_anchors": total,
            "frozen_hits": hits["frozen"],
            "dominant_hits": hits["dominant"],
            "magnitude_hits": hits["magnitude"],
            "frozen_coherent_hits": hits["frozen_coherent"],
            "winner": winner,
            "frozen_margin": hits["frozen"]
            - max(hits["dominant"], hits["magnitude"], hits["frozen_coherent"]),
        },
    }
    out_path = OUT_DIR / "ring_n_results.json"
    out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
