"""Ring J blind test — cascade v4 + frz_kurt watch.

Builds the Ring J row cache (550M-600M) if it doesn't exist, then runs
cascade v4. Primary question: does frz_kurt stay >= 0.80 (dominant wins)
or does it drop back (magnitude returns)?

Cascade v4:
  compressed_frozen AND frz_mean > 0.27 → magnitude weights
  (v5 hypothesis: AND frz_kurt < 0.80 → magnitude; frz_kurt >= 0.80 → dominant)

Saturation model predictions for J:
  frz_mean  ≈ 0.40–0.41  (Aitken asymptote L≈0.425)
  frz_skew  ≈ 0.97–0.99  (near ceiling)
  frz_std   ≈ 0.82–0.84  (continuing decline)
  frz_kurt  = ? (H=0.559, I=1.035; 2nd data point here)
"""
from __future__ import annotations
import json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.ring_i_cascade_v4 import (  # noqa: E402
    FRZ_MEAN_LATE_THRESHOLD, REGIME_WEIGHTS, predict_regime_v4,
)
from scripts.research.range_regime_classifier import (  # noqa: E402
    CEN_STD_THRESHOLD, FRZ_MEAN_THRESHOLD, FRZ_SKEW_THRESHOLD, FRZ_STD_THRESHOLD,
    DOMINANT_WF, DOMINANT_WA, DOMINANT_WC,
    D_WF, D_WA, D_WC,
    COOP_WF, COOP_WA, COOP_WC,
    TOP_N, WINDOW, HISTORY, ANCHOR_THRESHOLD,
    build_range_features, dyn_blend, score_dict, z_norm, _load_frozen_spec,
)
from scripts.research.run_prime_search_engine_bench import (  # noqa: E402
    DEFAULT_ROW_CACHE_DIR, build_or_load_rows, fit_centroid_ranker,
    fit_score_normalizer, fresh_rows, labels, linear_scores, matrix,
    metrics_for_scores, score_frozen, split_ordered_rows,
)
from scripts.research.run_field_branch_gate_search import ensure_dynamic_profiles  # noqa: E402

CACHE_DIR = DEFAULT_ROW_CACHE_DIR
OUT_DIR = REPO_ROOT / "artifacts" / "ring_j_cascade_v4"
FIT_FRACTION = 0.60


def main() -> None:
    ensure_dynamic_profiles()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    frozen_spec = _load_frozen_spec()

    print("=" * 72)
    print("RING J BLIND TEST — CASCADE V4  (550M–600M)")
    print(f"frz_kurt watch: H=0.559 → magnitude, I=1.035 → dominant")
    print(f"Saturation prediction: frz_mean ≈ 0.40–0.41, asymptote ≈ 0.425")
    print("=" * 72)

    print("\nLoading calibration cache (A)...", flush=True)
    rows_100 = build_or_load_rows(100_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_150 = build_or_load_rows(150_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_a  = fresh_rows(rows_100, rows_150)

    print("Loading Ring I cache (500M-550M)...", flush=True)
    rows_500 = build_or_load_rows(500_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_550 = build_or_load_rows(550_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_i  = fresh_rows(rows_500, rows_550)

    print("\nBuilding/loading Ring J cache (550M-600M)...", flush=True)
    print("  (Building from scratch takes ~180s — please wait)", flush=True)
    rows_600 = build_or_load_rows(600_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_j  = fresh_rows(rows_550, rows_600)
    print(f"  Ring J rows: {len(range_j)}", flush=True)

    # Normalizers from Ring A
    fit_a, _ = split_ordered_rows(range_a, FIT_FRACTION)
    frz_fit = score_frozen(fit_a, frozen_spec)
    frz_mean_norm, frz_scale_norm = fit_score_normalizer(frz_fit)
    x_fit = matrix(fit_a); y_fit = labels(fit_a)
    cen_model = fit_centroid_ranker(x_fit, y_fit)
    cen_fit_s = linear_scores(cen_model, x_fit)
    cen_mean_norm, cen_scale_norm = fit_score_normalizer(cen_fit_s)

    # Ring I scores (for context comparison)
    frz_i_z = z_norm(score_frozen(range_i, frozen_spec), frz_mean_norm, frz_scale_norm)
    cen_i_z = z_norm(linear_scores(cen_model, matrix(range_i)), cen_mean_norm, cen_scale_norm)

    # Ring J scores
    frz_j_z = z_norm(score_frozen(range_j, frozen_spec), frz_mean_norm, frz_scale_norm)
    cen_j_z = z_norm(linear_scores(cen_model, matrix(range_j)), cen_mean_norm, cen_scale_norm)

    print("\nComputing range features...", flush=True)
    feats_i = build_range_features(range_i, frz_i_z, cen_i_z)
    feats_j = build_range_features(range_j, frz_j_z, cen_j_z)

    # ── Feature table ─────────────────────────────────────────────────────────
    diag_keys = ["frz_mean", "frz_std", "frz_skew", "frz_kurt", "cen_std",
                 "corr_frz_cen", "frz_sentinel_frac", "frz_p90"]
    sat_pred = {"frz_mean": "0.40–0.41", "frz_skew": "0.97–0.99",
                "frz_std": "0.82–0.83", "frz_kurt": "?"}

    print("\n" + "=" * 72)
    print("[RING J FEATURES]  — cascade v4 + frz_kurt watch")
    print("=" * 72)
    print(f"  {'feature':30s}  {'H':>10}  {'I':>10}  {'J (new)':>10}  {'sat.pred':>10}")
    known_h = {"frz_mean": 0.3232, "frz_std": 0.8769, "frz_skew": 0.8094,
               "frz_kurt": 0.5594, "cen_std": 1.0118}
    for k in diag_keys:
        h_v = known_h.get(k, float("nan"))
        i_v = feats_i[k]
        j_v = feats_j[k]
        pred = sat_pred.get(k, "—")
        h_str = f"{h_v:+.4f}" if not (isinstance(h_v, float) and h_v != h_v) else "—"
        print(f"  {k:30s}  {h_str:>10}  {i_v:>+10.4f}  {j_v:>+10.4f}  {pred:>10}")

    # ── v4 prediction for J ───────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("[CASCADE V4 PREDICTION]  Ring J — BEFORE anchor truth")
    print("=" * 72)
    j_pred_v4, j_fired_v4 = predict_regime_v4(feats_j)
    wf_pred, wa_pred, wc_pred = REGIME_WEIGHTS[j_pred_v4]
    print(f"  frz_skew={feats_j['frz_skew']:.4f}  frz_mean={feats_j['frz_mean']:.4f}  "
          f"frz_std={feats_j['frz_std']:.4f}  frz_kurt={feats_j['frz_kurt']:.4f}")
    print(f"\n  CASCADE PATH:")
    print(f"    cen_std={feats_j['cen_std']:.4f} < {CEN_STD_THRESHOLD}?  "
          f"{'YES → magnitude' if feats_j['cen_std'] < CEN_STD_THRESHOLD else 'no'}")
    if feats_j["cen_std"] >= CEN_STD_THRESHOLD:
        print(f"    frz_skew={feats_j['frz_skew']:.4f} > {FRZ_SKEW_THRESHOLD}?  "
              f"{'YES' if feats_j['frz_skew'] > FRZ_SKEW_THRESHOLD else 'no → dominant'}")
        if feats_j["frz_skew"] > FRZ_SKEW_THRESHOLD:
            in_cf = (feats_j["frz_mean"] > FRZ_MEAN_THRESHOLD
                     and feats_j["frz_std"] < FRZ_STD_THRESHOLD)
            print(f"    frz_mean > {FRZ_MEAN_THRESHOLD} AND frz_std < {FRZ_STD_THRESHOLD}?  "
                  f"{'YES (compressed_frozen)' if in_cf else 'no → frozen_coherent'}")
            if in_cf:
                late = feats_j["frz_mean"] > FRZ_MEAN_LATE_THRESHOLD
                print(f"    frz_mean={feats_j['frz_mean']:.4f} > {FRZ_MEAN_LATE_THRESHOLD}?  "
                      f"{'YES → compressed_frozen_late (magnitude)' if late else 'no → compressed_frozen (dominant)'}")
    print(f"\n  PREDICTION: {j_pred_v4}  (fired: {j_fired_v4})")
    print(f"  Weights: wf={wf_pred}  wa={wa_pred}  wc={wc_pred}")

    # v5 hypothesis check
    kurt_j = feats_j["frz_kurt"]
    print(f"\n  [cascade v5 hypothesis]  frz_kurt={kurt_j:.4f}")
    if j_pred_v4 in ("compressed_frozen_late",):
        if kurt_j < 0.80:
            print(f"    frz_kurt < 0.80 → v5 would predict magnitude (SAME as v4)")
        else:
            print(f"    frz_kurt >= 0.80 → v5 would redirect to dominant")
            print(f"    v4 says magnitude, v5 hypothesis says dominant — watch the actual winner")

    # ── Score Ring J ──────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("[RESULTS]  Ring J")
    print("=" * 72)

    sc_j_frz  = score_dict(range_j, frz_j_z)
    sc_j_dom  = score_dict(range_j, dyn_blend(frz_j_z, cen_j_z, DOMINANT_WF, DOMINANT_WA, DOMINANT_WC))
    sc_j_dmag = score_dict(range_j, dyn_blend(frz_j_z, cen_j_z, D_WF, D_WA, D_WC))
    sc_j_coop = score_dict(range_j, dyn_blend(frz_j_z, cen_j_z, COOP_WF, COOP_WA, COOP_WC))

    m_j_frz  = metrics_for_scores(range_j, sc_j_frz,  TOP_N, unique_anchors_only=True)
    m_j_dom  = metrics_for_scores(range_j, sc_j_dom,  TOP_N, unique_anchors_only=True)
    m_j_dmag = metrics_for_scores(range_j, sc_j_dmag, TOP_N, unique_anchors_only=True)
    m_j_coop = metrics_for_scores(range_j, sc_j_coop, TOP_N, unique_anchors_only=True)

    h_j_frz  = m_j_frz["unique_anchor_hits"]
    h_j_dom  = m_j_dom["unique_anchor_hits"]
    h_j_dmag = m_j_dmag["unique_anchor_hits"]
    h_j_coop = m_j_coop["unique_anchor_hits"]
    tot_j    = m_j_frz["unique_anchors_total"]

    frz_set = {x["anchor_prime"] for x in m_j_frz["hidden_numbers"]}
    dom_new  = sorted({x["anchor_prime"] for x in m_j_dom["hidden_numbers"]}  - frz_set)
    dmag_new = sorted({x["anchor_prime"] for x in m_j_dmag["hidden_numbers"]} - frz_set)
    coop_new = sorted({x["anchor_prime"] for x in m_j_coop["hidden_numbers"]} - frz_set)

    print(f"  frozen baseline:              J={h_j_frz}/{tot_j}")
    print(f"  dominant     (wf=-1.5 wa=0):  J={h_j_dom}/{tot_j}  delta={h_j_dom-h_j_frz:+d}  new={dom_new}")
    print(f"  magnitude    (wf=+0.5 wa=2):  J={h_j_dmag}/{tot_j}  delta={h_j_dmag-h_j_frz:+d}  new={dmag_new}")
    print(f"  frozen-coop  (wf=+1.0 wa=0):  J={h_j_coop}/{tot_j}  delta={h_j_coop-h_j_frz:+d}  new={coop_new}")

    sc_j_pred = {
        "dominant":              sc_j_dom,
        "magnitude":             sc_j_dmag,
        "frozen_coherent":       sc_j_coop,
        "compressed_frozen":     sc_j_dom,
        "compressed_frozen_late": sc_j_dmag,
    }[j_pred_v4]
    m_j_pred = metrics_for_scores(range_j, sc_j_pred, TOP_N, unique_anchors_only=True)
    h_j_pred = m_j_pred["unique_anchor_hits"]
    pred_new = sorted({x["anchor_prime"] for x in m_j_pred["hidden_numbers"]} - frz_set)

    print(f"\n  v4 predicted ({j_pred_v4}):  J={h_j_pred}/{tot_j}  delta={h_j_pred-h_j_frz:+d}")
    print(f"  New anchors: {pred_new}")

    all_hits = {"frozen": h_j_frz, "dominant": h_j_dom,
                "magnitude": h_j_dmag, "frozen_coherent": h_j_coop}
    winner = max(all_hits, key=lambda k: all_hits[k])
    v4_correct = (j_pred_v4 in ("magnitude", "compressed_frozen_late") and winner == "magnitude") or \
                 (j_pred_v4 in ("dominant", "compressed_frozen") and winner == "dominant") or \
                 (j_pred_v4 == "frozen_coherent" and winner == "frozen_coherent")

    print(f"\n  WINNER: {winner} ({all_hits[winner]}/{tot_j})")
    print(f"  v4 correct: {'YES' if v4_correct else 'NO'}")

    # v5 verdict
    if j_pred_v4 in ("compressed_frozen_late",):
        v5_says = "dominant" if kurt_j >= 0.80 else "magnitude"
        v5_correct = (v5_says == winner)
        print(f"  v5 hypothesis ({v5_says}): {'CORRECT' if v5_correct else 'WRONG'}")
        print(f"  frz_kurt={kurt_j:.4f} ({'≥' if kurt_j >= 0.80 else '<'} 0.80 threshold)")

    print("=" * 72)

    # ── Frz_kurt trajectory update ────────────────────────────────────────────
    print("\n[frz_kurt trajectory]  (new axis — only H/I/J known)")
    kurts = [("H", 0.5594), ("I", 1.0348), ("J", feats_j["frz_kurt"])]
    for rname, kv in kurts:
        print(f"  Ring {rname}: frz_kurt = {kv:.4f}")
    if len(kurts) >= 2:
        step_HI = kurts[1][1] - kurts[0][1]
        step_IJ = kurts[2][1] - kurts[1][1]
        print(f"  Steps: H→I={step_HI:+.4f}  I→J={step_IJ:+.4f}")

    # ── Save artifact ─────────────────────────────────────────────────────────
    artifact = {
        "schema": "ring_j_cascade_v4_v1",
        "date": "2026-06-04",
        "ring": "J",
        "range": "550M-600M",
        "ring_j_features": {k: feats_j[k] for k in diag_keys},
        "ring_i_features": {k: feats_i[k] for k in diag_keys},
        "cascade_prediction": {
            "v4_regime": j_pred_v4,
            "v4_fired": j_fired_v4,
            "v4_weights": {"wf": wf_pred, "wa": wa_pred, "wc": wc_pred},
        },
        "results": {
            "total_anchors": tot_j,
            "frozen_hits": h_j_frz,
            "dominant_hits": h_j_dom,
            "magnitude_hits": h_j_dmag,
            "frozen_coherent_hits": h_j_coop,
            "v4_pred_hits": h_j_pred,
            "v4_delta": h_j_pred - h_j_frz,
            "winner": winner,
            "v4_correct": v4_correct,
            "new_anchors_under_prediction": pred_new,
        },
        "frz_kurt_trajectory": {
            "H": 0.5594, "I": feats_i["frz_kurt"], "J": feats_j["frz_kurt"],
        },
    }
    art_path = OUT_DIR / "ring_j_results.json"
    art_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved: {art_path}")


if __name__ == "__main__":
    main()
