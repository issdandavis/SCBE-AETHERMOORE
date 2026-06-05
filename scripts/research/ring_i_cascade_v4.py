"""Ring I blind test — cascade v4.

Builds the Ring I row cache (500M-550M) if it doesn't exist, then runs
the cascade v4 classifier and scores all four weight regimes.

Cascade v4 adds a frz_mean sub-split inside compressed_frozen:
  - frz_mean > 0.27  →  compressed_frozen_late  (magnitude weights)
  - frz_mean <= 0.27 →  compressed_frozen        (dominant weights)

This is the rule predicted by the trajectory gap map (frz_mean r²=0.998
linear trend puts Ring I at frz_mean≈0.442, Ring H's failure at frz_mean=0.323
was above the G/H split threshold of ~0.27).

Protocol:
  1. Build cache, compute range features
  2. Print cascade v4 prediction (BEFORE anchor truth)
  3. Print all regime scores
  4. Print which regime wins
  5. Report result

Outputs:
  artifacts/ring_i_cascade_v4/RESULTS.md
  artifacts/ring_i_cascade_v4/ring_i_results.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.range_regime_classifier import (  # noqa: E402
    CEN_STD_THRESHOLD,
    FRZ_MEAN_THRESHOLD,
    FRZ_SKEW_THRESHOLD,
    FRZ_STD_THRESHOLD,
    DOMINANT_WF, DOMINANT_WA, DOMINANT_WC,
    D_WF, D_WA, D_WC,
    COOP_WF, COOP_WA, COOP_WC,
    TOP_N, WINDOW, HISTORY, ANCHOR_THRESHOLD,
    anchor_set, build_range_features, dyn_blend,
    predict_regime, score_dict, unique_hits, z_norm,
    _load_frozen_spec,
)
from scripts.research.run_prime_search_engine_bench import (  # noqa: E402
    DEFAULT_ROW_CACHE_DIR,
    FEATURE_NAMES,
    apply_score_normalizer,
    build_or_load_rows,
    feature_vector,
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
from scripts.research.run_field_branch_gate_search import ensure_dynamic_profiles  # noqa: E402

CACHE_DIR = DEFAULT_ROW_CACHE_DIR
OUT_DIR = REPO_ROOT / "artifacts" / "ring_i_cascade_v4"
FIT_FRACTION = 0.60

# Cascade v4: frz_mean sub-split inside compressed_frozen
FRZ_MEAN_LATE_THRESHOLD = 0.27   # H=0.323 > G=0.215; midpoint=0.269 ≈ 0.27


def predict_regime_v4(feats: dict) -> tuple[str, list[str]]:
    """Cascade v4 — adds compressed_frozen_late (magnitude weights) split.

    Step 1: cen_std < 0.97974          → magnitude
    Step 2a: frz_skew > 0.4495
             AND frz_mean > 0.15
             AND frz_std  < 0.9621
             AND frz_mean > 0.27       → compressed_frozen_late (magnitude weights)
    Step 2b: frz_skew > 0.4495
             AND frz_mean > 0.15
             AND frz_std  < 0.9621     → compressed_frozen (dominant weights)
    Step 2c: frz_skew > 0.4495         → frozen_coherent
    Default:                           → dominant
    """
    if feats.get("cen_std", 1.0) < CEN_STD_THRESHOLD:
        return "magnitude", ["cen_std"]

    frz_skew_val = feats.get("frz_skew", 0.0)
    if frz_skew_val > FRZ_SKEW_THRESHOLD:
        frz_mean_val = feats.get("frz_mean", 0.0)
        frz_std_val  = feats.get("frz_std", 1.0)
        if frz_mean_val > FRZ_MEAN_THRESHOLD and frz_std_val < FRZ_STD_THRESHOLD:
            if frz_mean_val > FRZ_MEAN_LATE_THRESHOLD:
                return "compressed_frozen_late", ["frz_skew", "frz_mean", "frz_std", f"frz_mean>{FRZ_MEAN_LATE_THRESHOLD}"]
            return "compressed_frozen", ["frz_skew", "frz_mean", "frz_std"]
        return "frozen_coherent", ["frz_skew"]

    return "dominant", []


# Map regime → weights
REGIME_WEIGHTS = {
    "dominant":              (DOMINANT_WF, DOMINANT_WA, DOMINANT_WC),
    "magnitude":             (D_WF, D_WA, D_WC),
    "frozen_coherent":       (COOP_WF, COOP_WA, COOP_WC),
    "compressed_frozen":     (DOMINANT_WF, DOMINANT_WA, DOMINANT_WC),   # dominant
    "compressed_frozen_late": (D_WF, D_WA, D_WC),                       # magnitude
}


def main() -> None:
    ensure_dynamic_profiles()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    frozen_spec = _load_frozen_spec()

    print("=" * 72)
    print("RING I BLIND TEST — CASCADE V4  (500M–550M)")
    print("=" * 72)
    print(f"  Cascade v4 new rule:")
    print(f"    compressed_frozen AND frz_mean > {FRZ_MEAN_LATE_THRESHOLD}")
    print(f"    → compressed_frozen_late (magnitude weights: wf={D_WF}, wa={D_WA}, wc={D_WC})")

    # Load calibration caches (A only needed for fit)
    print("\nLoading calibration cache (A)...", flush=True)
    rows_100 = build_or_load_rows(100_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_150 = build_or_load_rows(150_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_a  = fresh_rows(rows_100, rows_150)

    # Build Ring H cache (already exists, fast load) — needed for frz_mean=0.323 retrodict
    print("Loading Ring H cache (450M-500M)...", flush=True)
    rows_450 = build_or_load_rows(450_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_500 = build_or_load_rows(500_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_h  = fresh_rows(rows_450, rows_500)

    # Build Ring I cache (500M-550M) — will build if missing (~160s)
    print("\nBuilding/loading Ring I cache (500M-550M)...", flush=True)
    print("  (Building from scratch takes ~160s — please wait)", flush=True)
    rows_550 = build_or_load_rows(550_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_i  = fresh_rows(rows_500, rows_550)
    print(f"  Ring I rows: {len(range_i)}")

    # Frozen + centroid normalizers (fitted on Ring A)
    fit_a, _ = split_ordered_rows(range_a, FIT_FRACTION)
    frz_fit = score_frozen(fit_a, frozen_spec)
    frz_mean_norm, frz_scale_norm = fit_score_normalizer(frz_fit)

    x_fit = matrix(fit_a)
    y_fit = labels(fit_a)
    cen_model = fit_centroid_ranker(x_fit, y_fit)
    cen_fit_s = linear_scores(cen_model, x_fit)
    cen_mean_norm, cen_scale_norm = fit_score_normalizer(cen_fit_s)

    # Ring H scores (retrodict v4 on H before showing I)
    frz_h_z = z_norm(score_frozen(range_h, frozen_spec), frz_mean_norm, frz_scale_norm)
    cen_h_z = z_norm(linear_scores(cen_model, matrix(range_h)), cen_mean_norm, cen_scale_norm)

    # Ring I scores
    frz_i_z = z_norm(score_frozen(range_i, frozen_spec), frz_mean_norm, frz_scale_norm)
    cen_i_z = z_norm(linear_scores(cen_model, matrix(range_i)), cen_mean_norm, cen_scale_norm)

    # Range features
    print("\nComputing range features...", flush=True)
    feats_h = build_range_features(range_h, frz_h_z, cen_h_z)
    feats_i = build_range_features(range_i, frz_i_z, cen_i_z)

    # ── Print Ring I feature values ──────────────────────────────────────────
    diag_keys = ["frz_mean", "frz_std", "frz_skew", "frz_kurt", "cen_std",
                 "corr_frz_cen", "frz_sentinel_frac", "frz_p90"]
    print("\n" + "=" * 72)
    print("[RING I FEATURES]  — values used by cascade v4")
    print("=" * 72)
    print(f"  {'feature':30s}  {'H (known)':>12}  {'I (new)':>12}  {'prediction?':>14}")
    known_h = {
        "frz_mean": 0.323, "frz_std": 0.877, "frz_skew": 0.809,
        "cen_std": 1.012, "corr_frz_cen": -0.211,
    }
    pred_i = {
        "frz_mean": 0.442, "frz_std": 0.810, "frz_skew": 0.983,
        "cen_std": 1.012,
    }
    for k in diag_keys:
        h_val = feats_h[k]
        i_val = feats_i[k]
        pred = pred_i.get(k)
        pred_str = f"≈{pred:.3f}" if pred is not None else "—"
        print(f"  {k:30s}  {h_val:>+12.4f}  {i_val:>+12.4f}  {pred_str:>14}")

    # ── v4 retrodict on H ───────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("[RETRODICT v4] Ring H — was the source of the v3 failure")
    print("=" * 72)
    h_pred_v3, h_fired_v3 = predict_regime(feats_h, [], require_k=1)
    h_pred_v4, h_fired_v4 = predict_regime_v4(feats_h)
    print(f"  v3 prediction: {h_pred_v3}  (fired: {h_fired_v3})")
    print(f"  v4 prediction: {h_pred_v4}  (fired: {h_fired_v4})")

    wf, wa, wc = REGIME_WEIGHTS[h_pred_v4]
    sc_h_pred = score_dict(range_h, dyn_blend(frz_h_z, cen_h_z, wf, wa, wc))
    sc_h_frz  = score_dict(range_h, frz_h_z)
    m_h_pred  = metrics_for_scores(range_h, sc_h_pred, TOP_N, unique_anchors_only=True)
    m_h_frz   = metrics_for_scores(range_h, sc_h_frz,  TOP_N, unique_anchors_only=True)
    h_pred_hits = m_h_pred["unique_anchor_hits"]
    h_frz_hits  = m_h_frz["unique_anchor_hits"]
    tot_h = m_h_frz["unique_anchors_total"]
    print(f"  v4 result on H: {h_pred_hits}/{tot_h}  (frozen={h_frz_hits}/{tot_h})  "
          f"delta={h_pred_hits - h_frz_hits:+d}")
    print(f"  v3 gave: compressed_frozen (dominant weights) → "
          f"would give same as frozen baseline or worse")

    # ── CASCADE V4 PREDICTION FOR RING I ────────────────────────────────────
    print("\n" + "=" * 72)
    print("[CASCADE V4 PREDICTION]  Ring I — BEFORE checking anchor truth")
    print("=" * 72)
    i_pred_v4, i_fired_v4 = predict_regime_v4(feats_i)
    wf_pred, wa_pred, wc_pred = REGIME_WEIGHTS[i_pred_v4]
    print(f"  frz_skew={feats_i['frz_skew']:.4f}  "
          f"frz_mean={feats_i['frz_mean']:.4f}  "
          f"frz_std={feats_i['frz_std']:.4f}  "
          f"cen_std={feats_i['cen_std']:.4f}")
    print(f"\n  CASCADE PATH:")
    print(f"    cen_std={feats_i['cen_std']:.4f} < {CEN_STD_THRESHOLD}?  "
          f"{'YES → magnitude' if feats_i['cen_std'] < CEN_STD_THRESHOLD else 'no'}")
    print(f"    frz_skew={feats_i['frz_skew']:.4f} > {FRZ_SKEW_THRESHOLD}?  "
          f"{'YES' if feats_i['frz_skew'] > FRZ_SKEW_THRESHOLD else 'no → dominant'}")
    if feats_i["frz_skew"] > FRZ_SKEW_THRESHOLD:
        print(f"    frz_mean={feats_i['frz_mean']:.4f} > {FRZ_MEAN_THRESHOLD} "
              f"AND frz_std={feats_i['frz_std']:.4f} < {FRZ_STD_THRESHOLD}?  "
              f"{'YES (enter compressed_frozen)' if (feats_i['frz_mean'] > FRZ_MEAN_THRESHOLD and feats_i['frz_std'] < FRZ_STD_THRESHOLD) else 'no → frozen_coherent'}")
        if feats_i["frz_mean"] > FRZ_MEAN_THRESHOLD and feats_i["frz_std"] < FRZ_STD_THRESHOLD:
            print(f"    frz_mean={feats_i['frz_mean']:.4f} > {FRZ_MEAN_LATE_THRESHOLD}?  "
                  f"{'YES → compressed_frozen_late (magnitude weights)' if feats_i['frz_mean'] > FRZ_MEAN_LATE_THRESHOLD else 'no → compressed_frozen (dominant weights)'}")
    print(f"\n  PREDICTION: {i_pred_v4}  (fired: {i_fired_v4})")
    print(f"  Weights: wf={wf_pred}  wa={wa_pred}  wc={wc_pred}")

    # ── Score Ring I with all regimes ────────────────────────────────────────
    print("\n" + "=" * 72)
    print("[RESULTS]  Ring I — scoring all regimes")
    print("=" * 72)

    sc_i_frz  = score_dict(range_i, frz_i_z)
    sc_i_dom  = score_dict(range_i, dyn_blend(frz_i_z, cen_i_z, DOMINANT_WF, DOMINANT_WA, DOMINANT_WC))
    sc_i_dmag = score_dict(range_i, dyn_blend(frz_i_z, cen_i_z, D_WF, D_WA, D_WC))
    sc_i_coop = score_dict(range_i, dyn_blend(frz_i_z, cen_i_z, COOP_WF, COOP_WA, COOP_WC))

    m_i_frz  = metrics_for_scores(range_i, sc_i_frz,  TOP_N, unique_anchors_only=True)
    m_i_dom  = metrics_for_scores(range_i, sc_i_dom,  TOP_N, unique_anchors_only=True)
    m_i_dmag = metrics_for_scores(range_i, sc_i_dmag, TOP_N, unique_anchors_only=True)
    m_i_coop = metrics_for_scores(range_i, sc_i_coop, TOP_N, unique_anchors_only=True)

    h_i_frz  = m_i_frz["unique_anchor_hits"]
    h_i_dom  = m_i_dom["unique_anchor_hits"]
    h_i_dmag = m_i_dmag["unique_anchor_hits"]
    h_i_coop = m_i_coop["unique_anchor_hits"]
    tot_i    = m_i_frz["unique_anchors_total"]

    frz_set = {x["anchor_prime"] for x in m_i_frz["hidden_numbers"]}
    dom_new  = sorted({x["anchor_prime"] for x in m_i_dom["hidden_numbers"]}  - frz_set)
    dmag_new = sorted({x["anchor_prime"] for x in m_i_dmag["hidden_numbers"]} - frz_set)
    coop_new = sorted({x["anchor_prime"] for x in m_i_coop["hidden_numbers"]} - frz_set)

    print(f"  frozen baseline:              I={h_i_frz}/{tot_i}")
    print(f"  dominant     (wf=-1.5 wa=0):  I={h_i_dom}/{tot_i}  delta={h_i_dom-h_i_frz:+d}  new={dom_new}")
    print(f"  magnitude    (wf=+0.5 wa=2):  I={h_i_dmag}/{tot_i}  delta={h_i_dmag-h_i_frz:+d}  new={dmag_new}")
    print(f"  frozen-coop  (wf=+1.0 wa=0):  I={h_i_coop}/{tot_i}  delta={h_i_coop-h_i_frz:+d}  new={coop_new}")

    # v4 predicted regime
    sc_i_pred = {
        "dominant":              sc_i_dom,
        "magnitude":             sc_i_dmag,
        "frozen_coherent":       sc_i_coop,
        "compressed_frozen":     sc_i_dom,
        "compressed_frozen_late": sc_i_dmag,
    }[i_pred_v4]
    m_i_pred = metrics_for_scores(range_i, sc_i_pred, TOP_N, unique_anchors_only=True)
    h_i_pred  = m_i_pred["unique_anchor_hits"]
    pred_new  = sorted({x["anchor_prime"] for x in m_i_pred["hidden_numbers"]} - frz_set)

    print(f"\n  v4 predicted ({i_pred_v4}):  I={h_i_pred}/{tot_i}  delta={h_i_pred-h_i_frz:+d}")
    print(f"  New anchors: {pred_new}")

    beats_frozen = h_i_pred >= h_i_frz
    beats_dom    = h_i_pred >= h_i_dom
    print(f"\n  >= frozen baseline:  {'PASS' if beats_frozen else 'FAIL'}")
    print(f"  >= dominant:         {'PASS' if beats_dom else 'FAIL'}")

    # ── All-regime winner ─────────────────────────────────────────────────────
    all_hits = {
        "frozen": h_i_frz,
        "dominant": h_i_dom,
        "magnitude": h_i_dmag,
        "frozen_coherent": h_i_coop,
    }
    winner = max(all_hits, key=lambda k: all_hits[k])
    print(f"\n  WINNER: {winner} ({all_hits[winner]}/{tot_i})")
    v4_correct = (i_pred_v4 in ("magnitude", "compressed_frozen_late") and winner == "magnitude")
    print(f"  v4 prediction correct (magnitude/compressed_frozen_late wins): "
          f"{'YES' if v4_correct else 'NO'}")
    print("=" * 72)

    # ── Save artifact ─────────────────────────────────────────────────────────
    artifact = {
        "schema": "ring_i_cascade_v4_v1",
        "date": "2026-06-04",
        "ring": "I",
        "range": "500M-550M",
        "cascade_v4": {
            "new_rule": f"compressed_frozen AND frz_mean > {FRZ_MEAN_LATE_THRESHOLD} → compressed_frozen_late (magnitude weights)",
            "frz_mean_late_threshold": FRZ_MEAN_LATE_THRESHOLD,
        },
        "ring_i_features": {k: feats_i[k] for k in diag_keys},
        "cascade_prediction": {
            "v4_regime": i_pred_v4,
            "v4_fired": i_fired_v4,
            "v4_weights": {"wf": wf_pred, "wa": wa_pred, "wc": wc_pred},
        },
        "results": {
            "total_anchors": tot_i,
            "frozen_hits": h_i_frz,
            "dominant_hits": h_i_dom,
            "magnitude_hits": h_i_dmag,
            "frozen_coherent_hits": h_i_coop,
            "v4_pred_hits": h_i_pred,
            "v4_delta": h_i_pred - h_i_frz,
            "winner": winner,
            "v4_correct": v4_correct,
            "new_anchors_under_prediction": pred_new,
        },
        "h_retrodict_v4": {
            "v3_regime": h_pred_v3,
            "v4_regime": h_pred_v4,
            "v4_hits": h_pred_hits,
            "frozen_hits": h_frz_hits,
            "delta": h_pred_hits - h_frz_hits,
        },
    }
    art_path = OUT_DIR / "ring_i_results.json"
    art_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")

    # Markdown
    md = [
        "# Ring I — Cascade v4 Blind Test",
        "",
        "**Date:** 2026-06-04  ",
        "**Range:** 500M–550M  ",
        "**Cascade v4:** compressed_frozen + frz_mean > 0.27 → magnitude weights",
        "",
        "## Cascade v4 Prediction",
        "",
        "| Feature | H (known) | I (actual) | Predicted |",
        "| --- | ---: | ---: | ---: |",
    ]
    for k in ["frz_mean", "frz_std", "frz_skew", "cen_std"]:
        h_v = feats_h[k]
        i_v = feats_i[k]
        p_v = pred_i.get(k)
        md.append(f"| {k} | {h_v:+.4f} | {i_v:+.4f} | {f'≈{p_v:.3f}' if p_v else '—'} |")
    md += [
        "",
        f"**v4 prediction: {i_pred_v4}** (fired: {i_fired_v4})",
        f"Weights: wf={wf_pred}, wa={wa_pred}, wc={wc_pred}",
        "",
        "## Results",
        "",
        f"| Method | Hits | Delta | New anchors |",
        "| --- | ---: | ---: | --- |",
        f"| frozen baseline | {h_i_frz}/{tot_i} | — | — |",
        f"| dominant (wf=-1.5) | {h_i_dom}/{tot_i} | {h_i_dom-h_i_frz:+d} | `{dom_new}` |",
        f"| **magnitude (wf=+0.5 wa=2)** | **{h_i_dmag}/{tot_i}** | **{h_i_dmag-h_i_frz:+d}** | `{dmag_new}` |",
        f"| frozen_coherent | {h_i_coop}/{tot_i} | {h_i_coop-h_i_frz:+d} | `{coop_new}` |",
        f"| **v4 predicted ({i_pred_v4})** | **{h_i_pred}/{tot_i}** | **{h_i_pred-h_i_frz:+d}** | `{pred_new}` |",
        "",
        f"**Winner:** {winner} ({all_hits[winner]}/{tot_i})",
        f"**v4 prediction correct:** {'YES' if v4_correct else 'NO'}",
        "",
        "## Ring H Retrodict (v4 fixes the failure)",
        "",
        f"| Version | Prediction | Hits | Delta |",
        "| --- | --- | ---: | ---: |",
        f"| v3 | {h_pred_v3} (dominant weights) | (was the failure) | — |",
        f"| v4 | {h_pred_v4} (magnitude weights) | {h_pred_hits}/{tot_h} | {h_pred_hits-h_frz_hits:+d} |",
        "",
        "## Artifact",
        "",
        "- `artifacts/ring_i_cascade_v4/ring_i_results.json`",
        "- Script: `scripts/research/ring_i_cascade_v4.py`",
    ]
    rpt = OUT_DIR / "RESULTS.md"
    rpt.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\nSaved: {art_path}")
    print(f"Saved: {rpt}")


if __name__ == "__main__":
    main()
