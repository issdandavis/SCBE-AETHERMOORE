"""Ring M blind test — cascade v6 (committed predictor).

v6 is now the canonical committed cascade (predict_regime_v6, matches
cascade_v6_spec.json). It passed pre-registered blind on Ring L (frozen +8).

Ring M (700M–750M) questions:
  1. Does frozen_dominant fire again? (frz_skew likely still > 1.0)
  2. Does the frozen-wins margin hold/grow/break? (K: +1, L: +8)
  3. Is the concentration phase transition still monotonic?
     (mean↑ skew↑ kurt↑ std↓ — does it persist or start to reverse?)
  4. frz_mean near asymptote? (J/K/L Aitken ≈ 0.546; M prediction ≈ 0.55 ± 0.01)

If frozen_dominant fires AND frozen wins → v6 is 6/6.
If the distribution de-concentrates (frz_skew drops < 1.0) → new phase, watch
which controller resurfaces.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.range_regime_classifier import (  # noqa: E402
    FROZEN_DOMINANT_FRZ_MEAN, FROZEN_DOMINANT_FRZ_SKEW,
    V6_REGIME_WEIGHTS,
    DOMINANT_WF, DOMINANT_WA, DOMINANT_WC,
    D_WF, D_WA, D_WC,
    COOP_WF, COOP_WA, COOP_WC,
    TOP_N, WINDOW, HISTORY, ANCHOR_THRESHOLD,
    build_range_features, dyn_blend, score_dict, z_norm,
    _load_frozen_spec, predict_regime_v6,
)
from scripts.research.run_prime_search_engine_bench import (  # noqa: E402
    DEFAULT_ROW_CACHE_DIR, build_or_load_rows, fit_centroid_ranker,
    fit_score_normalizer, fresh_rows, labels, linear_scores, matrix,
    metrics_for_scores, score_frozen, split_ordered_rows,
)
from scripts.research.run_field_branch_gate_search import ensure_dynamic_profiles  # noqa: E402

CACHE_DIR = DEFAULT_ROW_CACHE_DIR
OUT_DIR = REPO_ROOT / "artifacts" / "ring_m_cascade_v6"
FIT_FRACTION = 0.60

# Known ring features for v6 retrodict (H-L confirmed)
RETRODICT = [
    ("H", {"frz_mean": 0.3232, "frz_std": 0.8769, "frz_skew": 0.8094, "frz_kurt": 0.5594, "cen_std": 1.0118}, "magnitude"),
    ("I", {"frz_mean": 0.37575, "frz_std": 0.84584, "frz_skew": 0.96529, "frz_kurt": 1.03477, "cen_std": 1.02533}, "dominant"),
    ("J", {"frz_mean": 0.44285, "frz_std": 0.80508, "frz_skew": 0.92893, "frz_kurt": 0.76986, "cen_std": 1.02066}, "magnitude"),
    ("K", {"frz_mean": 0.50621, "frz_std": 0.80357, "frz_skew": 1.0328, "frz_kurt": 1.02235, "cen_std": 1.05832}, "frozen"),
    ("L", {"frz_mean": 0.5306, "frz_std": 0.7853, "frz_skew": 1.1867, "frz_kurt": 1.5965, "cen_std": 1.0310}, "frozen"),
]

# Which v6 regimes correspond to which empirical winner label
REGIME_TO_WINNER = {
    "frozen_dominant": "frozen",
    "compressed_frozen_late_low_kurt": "magnitude",
    "compressed_frozen_late_high_kurt": "dominant",
    "compressed_frozen_early": "dominant",
    "frozen_coherent": "frozen_coherent",
    "magnitude": "magnitude",
    "dominant": "dominant",
}


def retrodict_v6() -> None:
    print("\n[CASCADE V6 RETRODICT — H through L]")
    print(f"  {'Ring':4}  {'frz_mean':>9}  {'frz_skew':>9}  {'frz_kurt':>9}  "
          f"{'v6_regime':>34}  {'→winner':>12}  {'known':>12}  {'ok':>3}")
    correct = 0
    for rname, feats, known in RETRODICT:
        regime, _ = predict_regime_v6(feats)
        winner_pred = REGIME_TO_WINNER.get(regime, regime)
        ok = winner_pred == known
        correct += ok
        print(f"  {rname:4}  {feats['frz_mean']:>9.3f}  {feats['frz_skew']:>9.3f}  "
              f"{feats['frz_kurt']:>9.3f}  {regime:>34}  {winner_pred:>12}  {known:>12}  "
              f"{'✓' if ok else '✗':>3}")
    print(f"\n  Retrodict: {correct}/{len(RETRODICT)} = {correct/len(RETRODICT):.0%}")


def main() -> None:
    ensure_dynamic_profiles()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    frozen_spec = _load_frozen_spec()

    print("=" * 72)
    print("RING M BLIND TEST — CASCADE V6 (committed)  (700M–750M)")
    print("=" * 72)

    retrodict_v6()

    print("\nLoading calibration cache (A)...", flush=True)
    rows_100 = build_or_load_rows(100_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_150 = build_or_load_rows(150_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_a  = fresh_rows(rows_100, rows_150)

    print("Loading Ring L cache (650M-700M)...", flush=True)
    rows_650 = build_or_load_rows(650_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_700 = build_or_load_rows(700_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_l  = fresh_rows(rows_650, rows_700)

    print("\nBuilding/loading Ring M cache (700M-750M)...", flush=True)
    print("  (Building from scratch takes ~220s)", flush=True)
    rows_750 = build_or_load_rows(750_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_m  = fresh_rows(rows_700, rows_750)
    print(f"  Ring M rows: {len(range_m)}", flush=True)

    # Normalizers from Ring A
    fit_a, _ = split_ordered_rows(range_a, FIT_FRACTION)
    frz_fit = score_frozen(fit_a, frozen_spec)
    frz_mean_norm, frz_scale_norm = fit_score_normalizer(frz_fit)
    x_fit = matrix(fit_a); y_fit = labels(fit_a)
    cen_model = fit_centroid_ranker(x_fit, y_fit)
    cen_fit_s = linear_scores(cen_model, x_fit)
    cen_mean_norm, cen_scale_norm = fit_score_normalizer(cen_fit_s)

    # Ring L (previous — continuity)
    frz_l_z = z_norm(score_frozen(range_l, frozen_spec), frz_mean_norm, frz_scale_norm)
    cen_l_z = z_norm(linear_scores(cen_model, matrix(range_l)), cen_mean_norm, cen_scale_norm)
    feats_l  = build_range_features(range_l, frz_l_z, cen_l_z)

    # Ring M
    frz_m_z = z_norm(score_frozen(range_m, frozen_spec), frz_mean_norm, frz_scale_norm)
    cen_m_z = z_norm(linear_scores(cen_model, matrix(range_m)), cen_mean_norm, cen_scale_norm)
    feats_m  = build_range_features(range_m, frz_m_z, cen_m_z)

    diag_keys = ["frz_mean", "frz_std", "frz_skew", "frz_kurt", "cen_std",
                 "lambda_slope", "graph_ramp_density", "corr_frz_cen", "frz_p90"]

    print("\n" + "=" * 72)
    print("[RING M FEATURES]")
    print("=" * 72)
    print(f"  {'feature':32s}  {'L':>10}  {'M (new)':>10}")
    for k in diag_keys:
        l_v = feats_l.get(k, float("nan"))
        m_v = feats_m.get(k, float("nan"))
        print(f"  {k:32s}  {l_v:>+10.4f}  {m_v:>+10.4f}")

    # ── v6 committed prediction ───────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("[CASCADE V6 PREDICTION — COMMITTED]  Ring M — BEFORE anchor truth")
    print("=" * 72)
    m_regime, m_fired = predict_regime_v6(feats_m)
    wf, wa, wc = V6_REGIME_WEIGHTS[m_regime]
    print(f"  frz_mean={feats_m['frz_mean']:.4f}  frz_skew={feats_m['frz_skew']:.4f}  "
          f"frz_std={feats_m['frz_std']:.4f}  frz_kurt={feats_m['frz_kurt']:.4f}  "
          f"cen_std={feats_m['cen_std']:.4f}")
    print(f"\n  ORDER-1 frozen_dominant: frz_mean>{FROZEN_DOMINANT_FRZ_MEAN}={feats_m['frz_mean']>FROZEN_DOMINANT_FRZ_MEAN}  "
          f"AND frz_skew>{FROZEN_DOMINANT_FRZ_SKEW}={feats_m['frz_skew']>FROZEN_DOMINANT_FRZ_SKEW}")
    print(f"\n  PREDICTION: {m_regime}  (fired: {m_fired})")
    print(f"  Weights: wf={wf}  wa={wa}  wc={wc}")
    pred_winner = REGIME_TO_WINNER.get(m_regime, m_regime)
    print(f"  Expected winner: {pred_winner}")

    # ── Score Ring M ──────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("[RESULTS]  Ring M")
    print("=" * 72)

    sc_m_frz  = score_dict(range_m, frz_m_z)
    sc_m_dom  = score_dict(range_m, dyn_blend(frz_m_z, cen_m_z, DOMINANT_WF, DOMINANT_WA, DOMINANT_WC))
    sc_m_dmag = score_dict(range_m, dyn_blend(frz_m_z, cen_m_z, D_WF, D_WA, D_WC))
    sc_m_coop = score_dict(range_m, dyn_blend(frz_m_z, cen_m_z, COOP_WF, COOP_WA, COOP_WC))

    m_m_frz  = metrics_for_scores(range_m, sc_m_frz,  TOP_N, unique_anchors_only=True)
    m_m_dom  = metrics_for_scores(range_m, sc_m_dom,  TOP_N, unique_anchors_only=True)
    m_m_dmag = metrics_for_scores(range_m, sc_m_dmag, TOP_N, unique_anchors_only=True)
    m_m_coop = metrics_for_scores(range_m, sc_m_coop, TOP_N, unique_anchors_only=True)

    h_frz  = m_m_frz["unique_anchor_hits"]
    h_dom  = m_m_dom["unique_anchor_hits"]
    h_dmag = m_m_dmag["unique_anchor_hits"]
    h_coop = m_m_coop["unique_anchor_hits"]
    tot    = m_m_frz["unique_anchors_total"]

    print(f"  frozen baseline:              M={h_frz}/{tot}")
    print(f"  dominant     (wf=-1.5 wa=0):  M={h_dom}/{tot}  delta={h_dom-h_frz:+d}")
    print(f"  magnitude    (wf=+0.5 wa=2):  M={h_dmag}/{tot}  delta={h_dmag-h_frz:+d}")
    print(f"  frozen-coop  (wf=+1.0 wa=0):  M={h_coop}/{tot}  delta={h_coop-h_frz:+d}")

    # v6 committed hits (apply predicted weights)
    sc_m_v6 = score_dict(range_m, dyn_blend(frz_m_z, cen_m_z, wf, wa, wc))
    h_v6 = metrics_for_scores(range_m, sc_m_v6, TOP_N, unique_anchors_only=True)["unique_anchor_hits"]
    print(f"\n  v6 committed ({m_regime}):  M={h_v6}/{tot}  delta={h_v6-h_frz:+d}")

    all_hits = {"frozen": h_frz, "dominant": h_dom, "magnitude": h_dmag, "frozen_coherent": h_coop}
    winner = max(all_hits, key=lambda k: all_hits[k])
    v6_correct = (pred_winner == winner)
    print(f"\n  WINNER: {winner} ({all_hits[winner]}/{tot})")
    print(f"  v6 correct: {'YES' if v6_correct else 'NO'}  (predicted {pred_winner})")

    # ── Trajectory updates ────────────────────────────────────────────────────
    print(f"\n[frozen-wins margin]  K/L/M")
    margins = [("K", 10, 9), ("L", 13, 5), ("M", h_frz, max(h_dom, h_dmag, h_coop))]
    for rname, fr, best_blend in margins:
        print(f"  Ring {rname}: frozen={fr}  best_blend={best_blend}  margin={fr-best_blend:+d}")

    print(f"\n[concentration trajectory]  L → M")
    for k in ["frz_mean", "frz_skew", "frz_kurt", "frz_std"]:
        delta = feats_m[k] - feats_l[k]
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "=")
        print(f"  {k:10s}: {feats_l[k]:+.4f} → {feats_m[k]:+.4f}  ({delta:+.4f} {arrow})")

    print(f"\n[frz_mean trajectory]  J/K/L/M")
    means = [("J", 0.4429), ("K", 0.5062), ("L", 0.5306), ("M", feats_m["frz_mean"])]
    for i, (rname, mv) in enumerate(means):
        step = f"  step {mv-means[i-1][1]:+.4f}" if i > 0 else ""
        print(f"  Ring {rname}: frz_mean = {mv:.4f}{step}")
    print(f"  (J/K/L Aitken asymptote ≈ 0.546; M prediction was ≈0.55 ± 0.01)")

    print("=" * 72)

    # ── Save artifact ─────────────────────────────────────────────────────────
    artifact = {
        "schema": "ring_m_cascade_v6_v1",
        "date": "2026-06-04",
        "ring": "M",
        "range": "700M-750M",
        "cascade_committed": "v6",
        "ring_m_features": {k: feats_m[k] for k in diag_keys if k in feats_m},
        "ring_l_features": {k: feats_l[k] for k in diag_keys if k in feats_l},
        "v6_prediction": {
            "regime": m_regime, "fired": m_fired,
            "weights": {"wf": wf, "wa": wa, "wc": wc},
            "expected_winner": pred_winner,
            "hits": h_v6, "correct": v6_correct,
        },
        "results": {
            "total_anchors": tot,
            "frozen_hits": h_frz, "dominant_hits": h_dom,
            "magnitude_hits": h_dmag, "frozen_coherent_hits": h_coop,
            "winner": winner,
            "frozen_margin": h_frz - max(h_dom, h_dmag, h_coop),
        },
        "frz_mean_trajectory": {"J": 0.4429, "K": 0.5062, "L": 0.5306, "M": feats_m["frz_mean"]},
        "frz_skew_trajectory": {"K": 1.0328, "L": 1.1867, "M": feats_m["frz_skew"]},
        "frz_kurt_trajectory": {"K": 1.0224, "L": 1.5965, "M": feats_m["frz_kurt"]},
    }
    art_path = OUT_DIR / "ring_m_results.json"
    art_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved: {art_path}")


if __name__ == "__main__":
    main()
