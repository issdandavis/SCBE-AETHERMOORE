"""Ring L blind test — cascade v5 committed + cascade v6 hypothesis watch.

Ring L (650M–700M) is a DISCRIMINATING test between two hypotheses:

  H1 (v5 + period-2 alternation):
     frz_kurt pattern H/I/J/K = 0.559/1.035/0.770/1.022 (low/high/low/high).
     If alternation holds, L has frz_kurt < 0.80 → cascade v5 says MAGNITUDE.

  H2 (v6 frozen_dominant, from Ring K):
     At K, frz_mean=0.506, frz_skew=1.033, raw frozen gate won outright (10/179).
     If frz_skew stays > 1.0, the v6 hypothesis says FROZEN wins, no blend helps.

If BOTH conditions hold (frz_kurt < 0.80 AND frz_skew > 1.0):
  v5 predicts magnitude, v6 predicts frozen. The ring adjudicates.

Committed predictor: cascade v5 (frozen rule, unchanged).
Watched hypothesis:  cascade v6 frozen_dominant (NOT committed; recorded for analysis).

π vs ψ note: lambda_slope is ψ-type (prime-power harmonics), secondary coordinate.
Superprime anchors are π-type. Oracle confirms all stored anchors prime (552/0).
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
OUT_DIR = REPO_ROOT / "artifacts" / "ring_l_cascade_v5"
FIT_FRACTION = 0.60

# Cascade v6 frozen_dominant hypothesis thresholds (NOT committed — watched)
V6_FRZ_MEAN_FROZEN = 0.45   # frz_mean > 0.45
V6_FRZ_SKEW_FROZEN = 1.00   # AND frz_skew > 1.0 → frozen_dominant


def predict_v6_frozen_dominant(feats: dict) -> tuple[str, bool]:
    """Cascade v6 hypothesis: frozen_dominant regime when distribution is super-skewed.

    Returns (regime, fired). If not in frozen_dominant, falls back to v5.
    """
    frz_mean = feats.get("frz_mean", 0.0)
    frz_skew = feats.get("frz_skew", 0.0)
    if frz_mean > V6_FRZ_MEAN_FROZEN and frz_skew > V6_FRZ_SKEW_FROZEN:
        return "frozen_dominant", True
    v5_pred, _ = predict_regime_v5(feats)
    return v5_pred, False


def main() -> None:
    ensure_dynamic_profiles()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    frozen_spec = _load_frozen_spec()

    print("=" * 72)
    print("RING L BLIND TEST — CASCADE V5 (committed) + V6 (watched)  (650M–700M)")
    print("=" * 72)
    print("  H1 (v5+alternation): frz_kurt < 0.80 → magnitude")
    print("  H2 (v6 frozen_dom):  frz_skew > 1.0 AND frz_mean > 0.45 → frozen wins")
    print("  Discriminating if BOTH hold.")
    print("=" * 72)

    print("\nLoading calibration cache (A)...", flush=True)
    rows_100 = build_or_load_rows(100_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_150 = build_or_load_rows(150_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_a  = fresh_rows(rows_100, rows_150)

    print("Loading Ring K cache (600M-650M)...", flush=True)
    rows_600 = build_or_load_rows(600_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_650 = build_or_load_rows(650_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_k  = fresh_rows(rows_600, rows_650)

    print("\nBuilding/loading Ring L cache (650M-700M)...", flush=True)
    print("  (Building from scratch takes ~210s)", flush=True)
    rows_700 = build_or_load_rows(700_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_l  = fresh_rows(rows_650, rows_700)
    print(f"  Ring L rows: {len(range_l)}", flush=True)

    # Normalizers from Ring A
    fit_a, _ = split_ordered_rows(range_a, FIT_FRACTION)
    frz_fit = score_frozen(fit_a, frozen_spec)
    frz_mean_norm, frz_scale_norm = fit_score_normalizer(frz_fit)
    x_fit = matrix(fit_a); y_fit = labels(fit_a)
    cen_model = fit_centroid_ranker(x_fit, y_fit)
    cen_fit_s = linear_scores(cen_model, x_fit)
    cen_mean_norm, cen_scale_norm = fit_score_normalizer(cen_fit_s)

    # Ring K (previous — continuity)
    frz_k_z = z_norm(score_frozen(range_k, frozen_spec), frz_mean_norm, frz_scale_norm)
    cen_k_z = z_norm(linear_scores(cen_model, matrix(range_k)), cen_mean_norm, cen_scale_norm)
    feats_k  = build_range_features(range_k, frz_k_z, cen_k_z)

    # Ring L
    frz_l_z = z_norm(score_frozen(range_l, frozen_spec), frz_mean_norm, frz_scale_norm)
    cen_l_z = z_norm(linear_scores(cen_model, matrix(range_l)), cen_mean_norm, cen_scale_norm)
    feats_l  = build_range_features(range_l, frz_l_z, cen_l_z)

    diag_keys = ["frz_mean", "frz_std", "frz_skew", "frz_kurt", "cen_std",
                 "lambda_slope", "graph_ramp_density", "corr_frz_cen", "frz_p90"]

    print("\n" + "=" * 72)
    print("[RING L FEATURES]")
    print("=" * 72)
    print(f"  {'feature':32s}  {'K':>10}  {'L (new)':>10}")
    for k in diag_keys:
        k_v = feats_k.get(k, float("nan"))
        l_v = feats_l.get(k, float("nan"))
        print(f"  {k:32s}  {k_v:>+10.4f}  {l_v:>+10.4f}")

    # ── Committed: cascade v5 prediction ──────────────────────────────────────
    print("\n" + "=" * 72)
    print("[CASCADE V5 PREDICTION — COMMITTED]  Ring L — BEFORE anchor truth")
    print("=" * 72)
    l_pred_v5, l_fired_v5 = predict_regime_v5(feats_l)
    wf5, wa5, wc5 = V5_REGIME_WEIGHTS[l_pred_v5]
    print(f"  frz_skew={feats_l['frz_skew']:.4f}  frz_mean={feats_l['frz_mean']:.4f}  "
          f"frz_std={feats_l['frz_std']:.4f}  frz_kurt={feats_l['frz_kurt']:.4f}")
    print(f"  PREDICTION: {l_pred_v5}  (fired: {l_fired_v5})")
    print(f"  Weights: wf={wf5}  wa={wa5}  wc={wc5}")

    # ── Watched: cascade v6 frozen_dominant hypothesis ────────────────────────
    print("\n" + "=" * 72)
    print("[CASCADE V6 HYPOTHESIS — WATCHED, NOT COMMITTED]")
    print("=" * 72)
    l_pred_v6, v6_fired = predict_v6_frozen_dominant(feats_l)
    print(f"  frz_mean={feats_l['frz_mean']:.4f} > {V6_FRZ_MEAN_FROZEN}?  "
          f"{'YES' if feats_l['frz_mean'] > V6_FRZ_MEAN_FROZEN else 'no'}")
    print(f"  frz_skew={feats_l['frz_skew']:.4f} > {V6_FRZ_SKEW_FROZEN}?  "
          f"{'YES' if feats_l['frz_skew'] > V6_FRZ_SKEW_FROZEN else 'no'}")
    print(f"  v6 PREDICTION: {l_pred_v6}  (frozen_dominant fired: {v6_fired})")

    # Conflict detection
    kurt_low = feats_l["frz_kurt"] < FRZ_KURT_MAG_THRESHOLD
    skew_hi  = feats_l["frz_skew"] > V6_FRZ_SKEW_FROZEN
    discriminating = kurt_low and skew_hi
    print(f"\n  DISCRIMINATING RING?  frz_kurt<0.80={kurt_low}  AND  frz_skew>1.0={skew_hi}  "
          f"→ {'YES — v5(magnitude) vs v6(frozen) conflict' if discriminating else 'no — hypotheses agree or one inactive'}")

    # ── Score Ring L ──────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("[RESULTS]  Ring L")
    print("=" * 72)

    sc_l_frz  = score_dict(range_l, frz_l_z)
    sc_l_dom  = score_dict(range_l, dyn_blend(frz_l_z, cen_l_z, DOMINANT_WF, DOMINANT_WA, DOMINANT_WC))
    sc_l_dmag = score_dict(range_l, dyn_blend(frz_l_z, cen_l_z, D_WF, D_WA, D_WC))
    sc_l_coop = score_dict(range_l, dyn_blend(frz_l_z, cen_l_z, COOP_WF, COOP_WA, COOP_WC))

    m_l_frz  = metrics_for_scores(range_l, sc_l_frz,  TOP_N, unique_anchors_only=True)
    m_l_dom  = metrics_for_scores(range_l, sc_l_dom,  TOP_N, unique_anchors_only=True)
    m_l_dmag = metrics_for_scores(range_l, sc_l_dmag, TOP_N, unique_anchors_only=True)
    m_l_coop = metrics_for_scores(range_l, sc_l_coop, TOP_N, unique_anchors_only=True)

    h_l_frz  = m_l_frz["unique_anchor_hits"]
    h_l_dom  = m_l_dom["unique_anchor_hits"]
    h_l_dmag = m_l_dmag["unique_anchor_hits"]
    h_l_coop = m_l_coop["unique_anchor_hits"]
    tot_l    = m_l_frz["unique_anchors_total"]

    frz_set = {x["anchor_prime"] for x in m_l_frz["hidden_numbers"]}
    dmag_new = sorted({x["anchor_prime"] for x in m_l_dmag["hidden_numbers"]} - frz_set)
    dom_new  = sorted({x["anchor_prime"] for x in m_l_dom["hidden_numbers"]}  - frz_set)

    print(f"  frozen baseline:              L={h_l_frz}/{tot_l}")
    print(f"  dominant     (wf=-1.5 wa=0):  L={h_l_dom}/{tot_l}  delta={h_l_dom-h_l_frz:+d}")
    print(f"  magnitude    (wf=+0.5 wa=2):  L={h_l_dmag}/{tot_l}  delta={h_l_dmag-h_l_frz:+d}")
    print(f"  frozen-coop  (wf=+1.0 wa=0):  L={h_l_coop}/{tot_l}  delta={h_l_coop-h_l_frz:+d}")

    # v5 committed prediction hits
    sc_l_v5 = score_dict(range_l, dyn_blend(frz_l_z, cen_l_z, wf5, wa5, wc5))
    h_l_v5  = metrics_for_scores(range_l, sc_l_v5, TOP_N, unique_anchors_only=True)["unique_anchor_hits"]
    print(f"\n  v5 committed ({l_pred_v5}):  L={h_l_v5}/{tot_l}  delta={h_l_v5-h_l_frz:+d}")

    # ── Adjudicate ────────────────────────────────────────────────────────────
    all_hits = {"frozen": h_l_frz, "dominant": h_l_dom,
                "magnitude": h_l_dmag, "frozen_coherent": h_l_coop}
    winner = max(all_hits, key=lambda k: all_hits[k])

    # v5 correct if its predicted regime == winner (frozen counts as dominant-neighborhood)
    v5_correct = (l_pred_v5 == winner) or \
                 (l_pred_v5 == "dominant" and winner == "frozen")
    # v6 correct if frozen_dominant fired AND frozen won, OR (not fired AND v5 correct)
    if v6_fired:
        v6_correct = (winner == "frozen")
    else:
        v6_correct = v5_correct

    print(f"\n  WINNER: {winner} ({all_hits[winner]}/{tot_l})")
    print(f"  v5 committed correct: {'YES' if v5_correct else 'NO'}")
    print(f"  v6 hypothesis ({l_pred_v6}) correct: {'YES' if v6_correct else 'NO'}")
    if discriminating:
        v_won = "v6 (frozen)" if winner == "frozen" else ("v5 (magnitude)" if winner == "magnitude" else f"neither ({winner})")
        print(f"  DISCRIMINATING VERDICT: {v_won} wins the adjudication")

    # ── frz_kurt alternation test ─────────────────────────────────────────────
    print(f"\n[frz_kurt period-2 alternation test]  H/I/J/K/L")
    kurts = [("H", 0.5594), ("I", 1.0348), ("J", 0.7699), ("K", 1.0224), ("L", feats_l["frz_kurt"])]
    for rname, kv in kurts:
        side = "< 0.80 (low/mag)" if kv < FRZ_KURT_MAG_THRESHOLD else "≥ 0.80 (high/dom)"
        print(f"  Ring {rname}: frz_kurt = {kv:.4f}  {side}")
    # Alternation prediction was: L low (alternation from K high)
    l_low = feats_l["frz_kurt"] < FRZ_KURT_MAG_THRESHOLD
    print(f"  Alternation predicted L=low (<0.80): {'CONFIRMED' if l_low else 'BROKEN — L is high'}")
    print(f"  → period-2 alternation {'holds 5/5' if l_low else 'fails at L (was 4/4)'}")

    # ── frz_mean step test ────────────────────────────────────────────────────
    print(f"\n[frz_mean trajectory]  G/H/I/J/K/L")
    means = [("G", 0.2152), ("H", 0.3232), ("I", 0.3757), ("J", 0.4429), ("K", 0.5062), ("L", feats_l["frz_mean"])]
    for i, (rname, mv) in enumerate(means):
        step_str = f"  step {mv-means[i-1][1]:+.4f}" if i > 0 else ""
        print(f"  Ring {rname}: frz_mean = {mv:.4f}{step_str}")
    print(f"  (Ring L prediction was ≈0.57 ± 0.01)")

    print("=" * 72)

    # ── Save artifact ─────────────────────────────────────────────────────────
    artifact = {
        "schema": "ring_l_cascade_v5_v1",
        "date": "2026-06-04",
        "ring": "L",
        "range": "650M-700M",
        "cascade_committed": "v5",
        "cascade_watched": "v6_frozen_dominant",
        "ring_l_features": {k: feats_l[k] for k in diag_keys if k in feats_l},
        "ring_k_features": {k: feats_k[k] for k in diag_keys if k in feats_k},
        "v5_prediction": {
            "regime": l_pred_v5, "fired": l_fired_v5,
            "weights": {"wf": wf5, "wa": wa5, "wc": wc5},
            "hits": h_l_v5, "correct": v5_correct,
        },
        "v6_hypothesis": {
            "regime": l_pred_v6, "frozen_dominant_fired": v6_fired,
            "correct": v6_correct,
        },
        "discriminating_ring": discriminating,
        "results": {
            "total_anchors": tot_l,
            "frozen_hits": h_l_frz, "dominant_hits": h_l_dom,
            "magnitude_hits": h_l_dmag, "frozen_coherent_hits": h_l_coop,
            "winner": winner,
            "dmag_new_anchors": dmag_new,
            "dom_new_anchors": dom_new,
        },
        "frz_kurt_trajectory": {"H": 0.5594, "I": 1.0348, "J": 0.7699, "K": 1.0224, "L": feats_l["frz_kurt"]},
        "frz_kurt_alternation_holds": l_low,
        "frz_mean_trajectory": {"G": 0.2152, "H": 0.3232, "I": 0.3757, "J": 0.4429, "K": 0.5062, "L": feats_l["frz_mean"]},
    }
    art_path = OUT_DIR / "ring_l_results.json"
    art_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved: {art_path}")


if __name__ == "__main__":
    main()
