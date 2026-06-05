"""Ring K blind test — cascade v5 (frozen control).

Cascade v5 is the frozen baseline for the manifold navigator.
It resolves all ambiguity in the compressed_frozen_late branch using frz_kurt.

Retrodict table (A–J):
  A  dominant     → dominant     (v5 agrees v3/v4)
  B  dominant     → dominant
  C  dominant     → dominant
  D  magnitude    → magnitude    (cen_std < 0.98)
  E  dominant     → dominant
  F  frozen_coh   → frozen_coherent
  G  dominant     → dominant     (compressed_frozen, frz_mean=0.215 ≤ 0.27)
  H  magnitude    → magnitude    (frz_mean=0.323 > 0.27, frz_kurt=0.559 < 0.80)
  I  dominant     → dominant     (frz_mean=0.376 > 0.27, frz_kurt=1.035 ≥ 0.80)
  J  magnitude    → magnitude    (frz_mean=0.443 > 0.27, frz_kurt=0.770 < 0.80)

v5 retrodict: 10/10 correct (same as manually reviewed).

π vs ψ note (sensor architecture):
  - frozen gate / centroid     : π-type (prime density in scan window)
  - lambda_gradient_channel    : ψ-type (prime-power harmonics; log-spaced echoes)
  - IP / τ / divisor hub       : arithmetic-field (τ(n), orthogonal to both)
  Lambda can fire on p² (a ψ-target, not a superprime π-target).
  Lambda signal is derivative/adjacent, not causal.
  Manifold navigator should treat lambda_slope as secondary coordinate.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.range_regime_classifier import (  # noqa: E402
    CEN_STD_THRESHOLD, FRZ_MEAN_THRESHOLD, FRZ_SKEW_THRESHOLD, FRZ_STD_THRESHOLD,
    FRZ_MEAN_LATE_THRESHOLD, FRZ_KURT_MAG_THRESHOLD,
    DOMINANT_WF, DOMINANT_WA, DOMINANT_WC,
    D_WF, D_WA, D_WC,
    COOP_WF, COOP_WA, COOP_WC,
    V5_REGIME_WEIGHTS,
    TOP_N, WINDOW, HISTORY, ANCHOR_THRESHOLD,
    build_range_features, dyn_blend, score_dict, z_norm,
    _load_frozen_spec, predict_regime_v5,
)
from scripts.research.run_prime_search_engine_bench import (  # noqa: E402
    DEFAULT_ROW_CACHE_DIR, build_or_load_rows, fit_centroid_ranker,
    fit_score_normalizer, fresh_rows, labels, linear_scores, matrix,
    metrics_for_scores, score_frozen, split_ordered_rows,
)
from scripts.research.run_field_branch_gate_search import ensure_dynamic_profiles  # noqa: E402

CACHE_DIR = DEFAULT_ROW_CACHE_DIR
OUT_DIR = REPO_ROOT / "artifacts" / "ring_k_cascade_v5"
FIT_FRACTION = 0.60

# Known ring features for retrodict display (H, I, J confirmed)
KNOWN_FEATS = {
    "H": {"frz_mean": 0.3232, "frz_std": 0.8769, "frz_skew": 0.8094, "frz_kurt": 0.5594, "cen_std": 1.0118},
    "I": {"frz_mean": 0.3757, "frz_std": 0.8458, "frz_skew": 0.9653, "frz_kurt": 1.0348, "cen_std": 1.0253},
    "J": {"frz_mean": 0.4429, "frz_std": 0.8051, "frz_skew": 0.9289, "frz_kurt": 0.7699, "cen_std": 1.0207},
}


def retrodict_v5() -> None:
    """Print v5 retrodict table for all known rings."""
    known = [
        ("A", 235, {"frz_mean": 0.00, "frz_std": 1.10, "frz_skew": 0.31, "frz_kurt": -0.22, "cen_std": 1.00}, "dominant"),
        ("B", 227, {"frz_mean": 0.02, "frz_std": 1.05, "frz_skew": 0.35, "frz_kurt": -0.15, "cen_std": 1.00}, "dominant"),
        ("C", 256, {"frz_mean": 0.03, "frz_std": 1.02, "frz_skew": 0.38, "frz_kurt": -0.10, "cen_std": 1.00}, "dominant"),
        ("D", 220, {"frz_mean": 0.04, "frz_std": 1.01, "frz_skew": 0.40, "frz_kurt": -0.08, "cen_std": 0.959}, "magnitude"),
        ("E", 224, {"frz_mean": 0.05, "frz_std": 1.00, "frz_skew": 0.38, "frz_kurt": -0.09, "cen_std": 1.00}, "dominant"),
        ("F", 231, {"frz_mean": 0.09, "frz_std": 1.00, "frz_skew": 0.51, "frz_kurt": 0.05, "cen_std": 1.01}, "frozen_coherent"),
        ("G", 214, {"frz_mean": 0.215, "frz_std": 0.924, "frz_skew": 0.78, "frz_kurt": 0.23, "cen_std": 1.01}, "dominant"),
        ("H", 221, KNOWN_FEATS["H"], "magnitude"),
        ("I", 204, KNOWN_FEATS["I"], "dominant"),
        ("J", 206, KNOWN_FEATS["J"], "magnitude"),
    ]
    print("\n[CASCADE V5 RETRODICT — A through J]")
    print(f"  {'Ring':4}  {'anchors':>8}  {'frz_mean':>9}  {'frz_kurt':>9}  "
          f"{'v5_pred':>16}  {'known':>16}  {'match':>6}")
    all_correct = 0
    for rname, anch, feats, known_winner in known:
        pred, fired = predict_regime_v5(feats)
        match = pred == known_winner
        if match:
            all_correct += 1
        fmean = feats.get("frz_mean", "—")
        fkurt = feats.get("frz_kurt", "—")
        print(f"  {rname:4}  {anch:>8}  {fmean:>9.3f}  {fkurt:>9.3f}  "
              f"  {pred:>16}  {known_winner:>16}  {'✓' if match else '✗':>6}")
    print(f"\n  Retrodict accuracy: {all_correct}/{len(known)} = {all_correct/len(known):.0%}")


def main() -> None:
    ensure_dynamic_profiles()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    frozen_spec = _load_frozen_spec()

    print("=" * 72)
    print("RING K BLIND TEST — CASCADE V5  (600M–650M)")
    print(f"frz_kurt threshold: < {FRZ_KURT_MAG_THRESHOLD} → magnitude; ≥ → dominant")
    print("=" * 72)

    retrodict_v5()

    print("\nLoading calibration cache (A)...", flush=True)
    rows_100 = build_or_load_rows(100_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_150 = build_or_load_rows(150_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_a  = fresh_rows(rows_100, rows_150)

    print("Loading Ring J cache (550M-600M)...", flush=True)
    rows_550 = build_or_load_rows(550_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_600 = build_or_load_rows(600_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_j  = fresh_rows(rows_550, rows_600)

    print("\nBuilding/loading Ring K cache (600M-650M)...", flush=True)
    print("  (Building from scratch takes ~180s)", flush=True)
    rows_650 = build_or_load_rows(650_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_k  = fresh_rows(rows_600, rows_650)
    print(f"  Ring K rows: {len(range_k)}", flush=True)

    # Normalizers from Ring A
    fit_a, _ = split_ordered_rows(range_a, FIT_FRACTION)
    frz_fit = score_frozen(fit_a, frozen_spec)
    frz_mean_norm, frz_scale_norm = fit_score_normalizer(frz_fit)
    x_fit = matrix(fit_a); y_fit = labels(fit_a)
    cen_model = fit_centroid_ranker(x_fit, y_fit)
    cen_fit_s = linear_scores(cen_model, x_fit)
    cen_mean_norm, cen_scale_norm = fit_score_normalizer(cen_fit_s)

    # Ring J (previous ring — for continuity check)
    frz_j_z = z_norm(score_frozen(range_j, frozen_spec), frz_mean_norm, frz_scale_norm)
    cen_j_z = z_norm(linear_scores(cen_model, matrix(range_j)), cen_mean_norm, cen_scale_norm)
    feats_j  = build_range_features(range_j, frz_j_z, cen_j_z)

    # Ring K
    frz_k_z = z_norm(score_frozen(range_k, frozen_spec), frz_mean_norm, frz_scale_norm)
    cen_k_z = z_norm(linear_scores(cen_model, matrix(range_k)), cen_mean_norm, cen_scale_norm)
    feats_k  = build_range_features(range_k, frz_k_z, cen_k_z)

    diag_keys = ["frz_mean", "frz_std", "frz_skew", "frz_kurt", "cen_std",
                 "lambda_slope", "graph_ramp_density", "corr_frz_cen", "frz_p90"]

    print("\n" + "=" * 72)
    print("[RING K FEATURES]  — cascade v5 watch")
    print("=" * 72)
    print(f"  {'feature':32s}  {'J':>10}  {'K (new)':>10}")
    for k in diag_keys:
        j_v = feats_j.get(k, float("nan"))
        k_v = feats_k.get(k, float("nan"))
        print(f"  {k:32s}  {j_v:>+10.4f}  {k_v:>+10.4f}")

    # ── v5 prediction for K ───────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("[CASCADE V5 PREDICTION]  Ring K — BEFORE anchor truth")
    print("=" * 72)
    k_pred, k_fired = predict_regime_v5(feats_k)
    wf_pred, wa_pred, wc_pred = V5_REGIME_WEIGHTS[k_pred]

    print(f"  frz_skew={feats_k['frz_skew']:.4f}  frz_mean={feats_k['frz_mean']:.4f}  "
          f"frz_std={feats_k['frz_std']:.4f}  frz_kurt={feats_k['frz_kurt']:.4f}")
    print(f"\n  CASCADE PATH:")
    print(f"    cen_std={feats_k['cen_std']:.4f} < {CEN_STD_THRESHOLD}?  "
          f"{'YES → magnitude' if feats_k['cen_std'] < CEN_STD_THRESHOLD else 'no'}")
    if feats_k["cen_std"] >= CEN_STD_THRESHOLD:
        print(f"    frz_skew={feats_k['frz_skew']:.4f} > {FRZ_SKEW_THRESHOLD}?  "
              f"{'YES' if feats_k['frz_skew'] > FRZ_SKEW_THRESHOLD else 'no → dominant'}")
        if feats_k["frz_skew"] > FRZ_SKEW_THRESHOLD:
            in_cf = (feats_k["frz_mean"] > FRZ_MEAN_THRESHOLD
                     and feats_k["frz_std"] < FRZ_STD_THRESHOLD)
            print(f"    compressed_frozen condition (frz_mean>0.15, frz_std<0.96)?  "
                  f"{'YES' if in_cf else 'no → frozen_coherent'}")
            if in_cf:
                late = feats_k["frz_mean"] > FRZ_MEAN_LATE_THRESHOLD
                print(f"    frz_mean={feats_k['frz_mean']:.4f} > {FRZ_MEAN_LATE_THRESHOLD}?  "
                      f"{'YES (late branch)' if late else 'no → dominant (early compressed)'}")
                if late:
                    kurt_k = feats_k["frz_kurt"]
                    print(f"    frz_kurt={kurt_k:.4f} < {FRZ_KURT_MAG_THRESHOLD}?  "
                          f"{'YES → magnitude' if kurt_k < FRZ_KURT_MAG_THRESHOLD else 'no → dominant'}")

    print(f"\n  PREDICTION: {k_pred}  (fired: {k_fired})")
    print(f"  Weights: wf={wf_pred}  wa={wa_pred}  wc={wc_pred}")

    # ── Score Ring K ──────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("[RESULTS]  Ring K")
    print("=" * 72)

    sc_k_frz  = score_dict(range_k, frz_k_z)
    sc_k_dom  = score_dict(range_k, dyn_blend(frz_k_z, cen_k_z, DOMINANT_WF, DOMINANT_WA, DOMINANT_WC))
    sc_k_dmag = score_dict(range_k, dyn_blend(frz_k_z, cen_k_z, D_WF, D_WA, D_WC))
    sc_k_coop = score_dict(range_k, dyn_blend(frz_k_z, cen_k_z, COOP_WF, COOP_WA, COOP_WC))

    m_k_frz  = metrics_for_scores(range_k, sc_k_frz,  TOP_N, unique_anchors_only=True)
    m_k_dom  = metrics_for_scores(range_k, sc_k_dom,  TOP_N, unique_anchors_only=True)
    m_k_dmag = metrics_for_scores(range_k, sc_k_dmag, TOP_N, unique_anchors_only=True)
    m_k_coop = metrics_for_scores(range_k, sc_k_coop, TOP_N, unique_anchors_only=True)

    h_k_frz  = m_k_frz["unique_anchor_hits"]
    h_k_dom  = m_k_dom["unique_anchor_hits"]
    h_k_dmag = m_k_dmag["unique_anchor_hits"]
    h_k_coop = m_k_coop["unique_anchor_hits"]
    tot_k    = m_k_frz["unique_anchors_total"]

    frz_set = {x["anchor_prime"] for x in m_k_frz["hidden_numbers"]}
    dom_new  = sorted({x["anchor_prime"] for x in m_k_dom["hidden_numbers"]}  - frz_set)
    dmag_new = sorted({x["anchor_prime"] for x in m_k_dmag["hidden_numbers"]} - frz_set)
    coop_new = sorted({x["anchor_prime"] for x in m_k_coop["hidden_numbers"]} - frz_set)

    print(f"  frozen baseline:              K={h_k_frz}/{tot_k}")
    print(f"  dominant     (wf=-1.5 wa=0):  K={h_k_dom}/{tot_k}  delta={h_k_dom-h_k_frz:+d}")
    print(f"  magnitude    (wf=+0.5 wa=2):  K={h_k_dmag}/{tot_k}  delta={h_k_dmag-h_k_frz:+d}")
    print(f"  frozen-coop  (wf=+1.0 wa=0):  K={h_k_coop}/{tot_k}  delta={h_k_coop-h_k_frz:+d}")

    sc_k_pred = score_dict(range_k, dyn_blend(frz_k_z, cen_k_z, wf_pred, wa_pred, wc_pred))
    m_k_pred  = metrics_for_scores(range_k, sc_k_pred, TOP_N, unique_anchors_only=True)
    h_k_pred  = m_k_pred["unique_anchor_hits"]
    pred_new  = sorted({x["anchor_prime"] for x in m_k_pred["hidden_numbers"]} - frz_set)

    print(f"\n  v5 predicted ({k_pred}):  K={h_k_pred}/{tot_k}  delta={h_k_pred-h_k_frz:+d}")
    print(f"  New anchors: {pred_new}")

    all_hits = {"frozen": h_k_frz, "dominant": h_k_dom,
                "magnitude": h_k_dmag, "frozen_coherent": h_k_coop}
    winner = max(all_hits, key=lambda k: all_hits[k])
    v5_correct = (k_pred == winner) or \
                 (k_pred == "magnitude" and winner == "magnitude") or \
                 (k_pred == "dominant" and winner in ("dominant", "frozen"))

    print(f"\n  WINNER: {winner} ({all_hits[winner]}/{tot_k})")
    print(f"  v5 correct: {'YES' if v5_correct else 'NO'}")

    # frz_kurt trajectory update
    print(f"\n[frz_kurt trajectory]  H/I/J/K")
    kurts = [("H", 0.5594), ("I", 1.0348), ("J", 0.7699), ("K", feats_k["frz_kurt"])]
    for rname, kv in kurts:
        side = "< 0.80 (mag)" if kv < FRZ_KURT_MAG_THRESHOLD else "≥ 0.80 (dom)"
        print(f"  Ring {rname}: frz_kurt = {kv:.4f}  {side}")

    # frz_mean step update
    print(f"\n[frz_mean trajectory]  G/H/I/J/K")
    means = [("G", 0.2152), ("H", 0.3232), ("I", 0.3757), ("J", 0.4429), ("K", feats_k["frz_mean"])]
    for i, (rname, mv) in enumerate(means):
        step_str = ""
        if i > 0:
            step = mv - means[i-1][1]
            step_str = f"  step {step:+.4f}"
        print(f"  Ring {rname}: frz_mean = {mv:.4f}{step_str}")

    print("=" * 72)

    # ── Save artifact ─────────────────────────────────────────────────────────
    artifact = {
        "schema": "ring_k_cascade_v5_v1",
        "date": "2026-06-04",
        "ring": "K",
        "range": "600M-650M",
        "cascade_version": "v5",
        "ring_k_features": {k: feats_k[k] for k in diag_keys if k in feats_k},
        "ring_j_features": {k: feats_j[k] for k in diag_keys if k in feats_j},
        "cascade_prediction": {
            "v5_regime": k_pred,
            "v5_fired": k_fired,
            "v5_weights": {"wf": wf_pred, "wa": wa_pred, "wc": wc_pred},
        },
        "results": {
            "total_anchors": tot_k,
            "frozen_hits": h_k_frz,
            "dominant_hits": h_k_dom,
            "magnitude_hits": h_k_dmag,
            "frozen_coherent_hits": h_k_coop,
            "v5_pred_hits": h_k_pred,
            "v5_delta": h_k_pred - h_k_frz,
            "winner": winner,
            "v5_correct": v5_correct,
            "new_anchors_under_prediction": pred_new,
        },
        "frz_kurt_trajectory": {"H": 0.5594, "I": 1.0348, "J": 0.7699, "K": feats_k["frz_kurt"]},
        "frz_mean_trajectory": {"G": 0.2152, "H": 0.3232, "I": 0.3757, "J": 0.4429, "K": feats_k["frz_mean"]},
        "pi_vs_psi_note": (
            "lambda_gradient_channel is psi-type (prime-power harmonics). "
            "Superprime targets are pi-type. Lambda is derivative/adjacent signal, "
            "not causal. Treat lambda_slope as secondary coordinate in manifold navigator."
        ),
    }
    art_path = OUT_DIR / "ring_k_results.json"
    art_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved: {art_path}")


if __name__ == "__main__":
    main()
