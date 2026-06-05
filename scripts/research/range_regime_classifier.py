"""Range-regime classifier v2 for P(P(n)) superprime prime gap field.

Three-regime cascade classifier. All inputs are pre-anchor (computed before
seeing any anchor labels).

Regime cascade (applied in order):
  1. cen_std < 0.98         ->  D-anomaly     (magnitude weights)
  2. frz_skew > 0.45        ->  frozen-coherent (cooperative weights)
  3. else                   ->  dominant      (adversarial weights)

Frozen-coherent axis (new in v2):
  frz_skew measures right-tail asymmetry of the frozen score distribution.
  High frz_skew means the frozen gate has sharp discrimination (a few rows
  score very high, most score near mean). When the frozen gate is sharp,
  cooperative blending (positive wf) preserves its strong picks while
  centroid adds from a different population.
  F=350M-400M is the first known frozen-coherent range (frz_skew=0.513).

Regime weights:
  dominant      ->  wf=-1.5, wa=0.0, wc=1.0   (C/E in-sample winner)
  D-anomaly     ->  wf=+0.5, wa=2.0, wc=2.0   (D in-sample winner)
  frozen-coherent -> wf=+1.0, wa=0.0, wc=1.5  (F in-sample winner)

Range-level features:
  - frozen_z score moments: mean/std/skew/kurt/p90/frac_extreme/mean_abs
  - centroid_z score moments: std/skew/kurt
  - corr(frz, cen)
  - Per raw-feature means across all rows in range (44 features)
  - Per raw-feature slope: delta between first/second half of range (trend)
  - Special physics aggregates:
      lambda_slope      = mean(lambda_gradient_channel)
      graph_ramp_dens   = mean(graph_monotone_ramp)
      cmpssz_density    = mean(cmpssz_log_zone_score)
      prime_ratio_slope = second_half_mean(prime_ratio_channel) - first_half_mean
      topo_saddle_mix   = mean(topo_asymmetry) * mean(topo_confidence)
      gap_acceleration  = mean(abs_scan_ratio) / (mean(scan_ratio) + 1e-9)

Outputs:
  artifacts/range_regime_classifier/RESULTS.md
  artifacts/range_regime_classifier/regime_classifier_v1.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

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
from scripts.research.run_field_branch_gate_search import (  # noqa: E402
    GateSpec,
    ensure_dynamic_profiles,
)

CACHE_DIR = DEFAULT_ROW_CACHE_DIR
OUT_DIR = REPO_ROOT / "artifacts" / "range_regime_classifier"

WINDOW = 36
HISTORY = 12
ANCHOR_THRESHOLD = 4.0
TOP_N = 20
FIT_FRACTION = 0.60

# Known optimal weights from dynamic blend + weight sweep sessions
DOMINANT_WF, DOMINANT_WA, DOMINANT_WC = -1.5, 0.0, 1.0   # C/E in-sample winner
D_WF, D_WA, D_WC = 0.5, 2.0, 2.0                         # D in-sample winner
COOP_WF, COOP_WA, COOP_WC = 1.0, 0.0, 1.5                # F in-sample winner (blend2 w=0.4 equivalent)

# Step-1 classifier: cen_std threshold for D-anomaly
CEN_STD_THRESHOLD = 0.97974    # midpoint D(0.959)/non-D(1.000)

# Step-2 classifier: frz_skew threshold for frozen-coherent
# F: frz_skew=0.5135 vs adversarial max=0.3855; midpoint=0.4495
FRZ_SKEW_THRESHOLD = 0.4495

# Step-2a G-split: compressed_frozen within high-frz_skew group
# G: frz_mean=0.2152, frz_std=0.9241 vs F: frz_mean=0.0904, frz_std=1.0002
# thresholds: midpoints between G and F values
FRZ_MEAN_THRESHOLD = 0.15     # midpoint G(0.2152)/F(0.0904) ≈ 0.1528
FRZ_STD_THRESHOLD  = 0.9621   # midpoint G(0.9241)/F(1.0002) ≈ 0.9621

REGIME_KNOWN = {
    "A": "dominant", "B": "dominant", "C": "dominant",
    "D": "magnitude", "E": "dominant", "F": "frozen_coherent",
    "G": "compressed_frozen",   # retrodictive — dominant weights win, v3 prescribes same
}


# ── helpers ────────────────────────────────────────────────────────────────────

def _load_frozen_spec() -> GateSpec:
    p = REPO_ROOT / "artifacts" / "prime_search_engine_bench" / "latest_report.json"
    data = json.loads(p.read_text())
    return GateSpec(**data["frozen_spec"])


def z_norm(scores: list[float], mean: float, scale: float) -> list[float]:
    return apply_score_normalizer(scores, mean, scale)


def score_dict(rows: list[dict], scores: list[float]) -> dict[int, float]:
    return {id(r): s for r, s in zip(rows, scores)}


def unique_hits(rows: list[dict], sc: dict[int, float]) -> int:
    return metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)["unique_anchor_hits"]


def anchor_set(rows: list[dict], sc: dict[int, float]) -> set:
    m = metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)
    return {h["anchor_prime"] for h in m["hidden_numbers"]}


def dyn_blend(frz_z: list[float], cen_z: list[float],
              wf: float, wa: float, wc: float) -> list[float]:
    return [wf * f + wa * abs(f) + wc * c for f, c in zip(frz_z, cen_z)]


# ── range-level feature extraction ────────────────────────────────────────────

def dist_moments(scores: list[float]) -> dict:
    n = len(scores)
    mu = sum(scores) / n
    var = sum((x - mu) ** 2 for x in scores) / n
    sd = var ** 0.5 if var > 0 else 1e-9
    skew = sum((x - mu) ** 3 for x in scores) / (n * sd ** 3)
    kurt = sum((x - mu) ** 4 for x in scores) / (n * sd ** 4) - 3.0
    sorted_s = sorted(scores)
    p10 = sorted_s[int(0.10 * n)]
    p25 = sorted_s[int(0.25 * n)]
    p75 = sorted_s[int(0.75 * n)]
    p90 = sorted_s[int(0.90 * n)]
    mean_abs = sum(abs(x) for x in scores) / n
    frac_extreme = sum(1 for x in scores if abs(x) > 1.5) / n
    return dict(mean=mu, std=sd, skew=skew, kurt=kurt,
                p10=p10, p25=p25, p75=p75, p90=p90,
                mean_abs=mean_abs, frac_extreme=frac_extreme)


def score_corr(a: list[float], b: list[float]) -> float:
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = (sum((x - ma) ** 2 for x in a)) ** 0.5
    db = (sum((y - mb) ** 2 for y in b)) ** 0.5
    return num / (da * db) if da * db > 0 else 0.0


def feat_idx(name: str) -> int:
    return list(FEATURE_NAMES).index(name)


def col_means(X: list[list[float]]) -> list[float]:
    n, w = len(X), len(X[0])
    return [sum(X[r][j] for r in range(n)) / n for j in range(w)]


def half_slope(X: list[list[float]], j: int) -> float:
    """Second-half mean minus first-half mean for feature j."""
    n = len(X)
    mid = n // 2
    first = sum(X[r][j] for r in range(mid)) / mid if mid else 0.0
    second = sum(X[r][j] for r in range(mid, n)) / (n - mid) if n - mid else 0.0
    return second - first


SENTINEL_CUTOFF = -100.0  # z-scores below this are NEG_INF sentinels


def build_range_features(
    rows: list[dict],
    frz_z: list[float],
    cen_z: list[float],
) -> dict:
    """Compute range-level feature vector (one per range)."""
    X = matrix(rows)

    # Separate sentinel rows from real frozen z-scores
    frz_real = [x for x in frz_z if x > SENTINEL_CUTOFF]
    frz_sentinel_frac = 1.0 - len(frz_real) / len(frz_z) if frz_z else 0.0

    # Score distribution moments (sentinels excluded from frz moments)
    fm = dist_moments(frz_real) if frz_real else dist_moments(frz_z)
    cm = dist_moments(cen_z)
    r = score_corr(frz_z, cen_z)

    # Per-feature means
    means = col_means(X)
    feat_mean = {FEATURE_NAMES[j]: means[j] for j in range(len(FEATURE_NAMES))}

    # Physics aggregates (requested by user)
    lam_idx = feat_idx("lambda_gradient_channel")
    ramp_idx = feat_idx("graph_monotone_ramp")
    cmpssz_idx = feat_idx("cmpssz_log_zone_score")
    prime_idx = feat_idx("prime_ratio_channel")
    topo_asym_idx = feat_idx("topo_asymmetry")
    topo_conf_idx = feat_idx("topo_confidence")
    scan_idx = feat_idx("scan_ratio")
    abs_scan_idx = feat_idx("abs_scan_ratio")
    graph_ev_idx = feat_idx("graph_edge_variance")
    graph_ret_idx = feat_idx("graph_return_rate")

    lambda_slope = means[lam_idx]
    graph_ramp_density = means[ramp_idx]
    cmpssz_density = means[cmpssz_idx]
    prime_ratio_slope = half_slope(X, prime_idx)
    topo_saddle_mix = means[topo_asym_idx] * means[topo_conf_idx]
    gap_acceleration = means[abs_scan_idx] / (abs(means[scan_idx]) + 1e-9)
    graph_edge_var = means[graph_ev_idx]
    graph_return = means[graph_ret_idx]

    # Per-feature slopes for key physics channels
    feat_slopes = {
        f"slope_{FEATURE_NAMES[j]}": half_slope(X, j)
        for j in [lam_idx, ramp_idx, cmpssz_idx, prime_idx,
                  topo_asym_idx, topo_conf_idx, abs_scan_idx, graph_ev_idx]
    }

    return {
        # score distribution (sentinel-filtered)
        "frz_sentinel_frac": round(frz_sentinel_frac, 5),
        "frz_mean": round(fm["mean"], 5),
        "frz_std": round(fm["std"], 5),
        "frz_skew": round(fm["skew"], 5),
        "frz_kurt": round(fm["kurt"], 5),
        "frz_p90": round(fm["p90"], 5),
        "frz_mean_abs": round(fm["mean_abs"], 5),
        "frz_frac_extreme": round(fm["frac_extreme"], 5),
        "cen_std": round(cm["std"], 5),
        "cen_skew": round(cm["skew"], 5),
        "cen_kurt": round(cm["kurt"], 5),
        "corr_frz_cen": round(r, 5),
        # physics aggregates
        "lambda_slope": round(lambda_slope, 6),
        "graph_ramp_density": round(graph_ramp_density, 6),
        "cmpssz_density": round(cmpssz_density, 6),
        "prime_ratio_slope": round(prime_ratio_slope, 6),
        "topo_saddle_mix": round(topo_saddle_mix, 6),
        "gap_acceleration": round(gap_acceleration, 6),
        "graph_edge_var": round(graph_edge_var, 6),
        "graph_return": round(graph_return, 6),
        # per-feature slopes
        **{k: round(v, 6) for k, v in feat_slopes.items()},
        # per-feature means (all 44)
        **{f"mean_{k}": round(v, 6) for k, v in feat_mean.items()},
    }


# ── threshold classifier ───────────────────────────────────────────────────────

def compute_separability(range_feats: dict[str, dict], d_label: str = "D") -> list[tuple]:
    """For each feature, compute D-separability: margin / non-D spread.

    Returns list of (score, feature, d_val, lo, hi, direction) sorted desc.
    """
    feat_keys = [k for k in next(iter(range_feats.values())) if isinstance(next(iter(range_feats.values()))[k], (int, float))]
    d_feats = range_feats[d_label]
    others = {k: v for k, v in range_feats.items() if k != d_label}

    results = []
    for fk in feat_keys:
        d_val = d_feats[fk]
        other_vals = [others[rng][fk] for rng in others]
        lo, hi = min(other_vals), max(other_vals)
        spread = hi - lo if hi > lo else 1e-9
        if d_val < lo:
            margin = lo - d_val
            direction = "LOW"
        elif d_val > hi:
            margin = d_val - hi
            direction = "HIGH"
        else:
            margin = 0.0
            direction = "inside"
        sep_score = margin / spread
        results.append((sep_score, fk, d_val, lo, hi, direction))

    results.sort(key=lambda x: -x[0])
    return results


def build_threshold_rule(sep_results: list[tuple], top_k: int = 3) -> list[dict]:
    """Build threshold rules from top-K most separating features.

    Threshold = midpoint between D value and nearest non-D boundary.
    """
    rules = []
    for sep_score, fk, d_val, lo, hi, direction in sep_results[:top_k]:
        if direction == "HIGH":
            threshold = (hi + d_val) / 2.0
            predicate = ">"
        elif direction == "LOW":
            threshold = (lo + d_val) / 2.0
            predicate = "<"
        else:
            continue
        rules.append({
            "feature": fk,
            "threshold": round(threshold, 6),
            "predicate": predicate,  # fire if feature {predicate} threshold
            "d_val": round(d_val, 6),
            "non_d_lo": round(lo, 6),
            "non_d_hi": round(hi, 6),
            "direction": direction,
            "sep_score": round(sep_score, 4),
        })
    return rules


# ── Cascade v5 constants ─────────────────────────────────────────────────────
# v5 adds frz_kurt split inside the compressed_frozen_late branch.
# Validated on rings H(0.559→mag), I(1.035→dom), J(0.770→mag) — 3/3 correct.
FRZ_MEAN_LATE_THRESHOLD = 0.27   # v4/v5 shared: frz_mean > 0.27 triggers late branch
FRZ_KURT_MAG_THRESHOLD  = 0.80   # v5: frz_kurt < 0.80 → magnitude; ≥ 0.80 → dominant

# v5 REGIME → WEIGHTS mapping  (resolve to same 3 weight sets as before)
V5_REGIME_WEIGHTS = {
    "magnitude":      (0.5,  2.0, 2.0),   # D-anomaly / compressed_frozen_late_mag
    "dominant":       (-1.5, 0.0, 1.0),   # default / compressed_frozen / late_dom
    "frozen_coherent": (1.0,  0.0, 1.5),  # high-skew, normal dist
}


def predict_regime_v5(feats: dict) -> tuple[str, list[str]]:
    """Cascade v5 — adds frz_kurt split inside compressed_frozen_late.

    Full cascade:
      1. cen_std < 0.97974                              → magnitude
      2. frz_skew > 0.4495
         AND frz_mean > 0.15 AND frz_std < 0.9621
         AND frz_mean > 0.27
         AND frz_kurt < 0.80                            → magnitude
         AND frz_kurt ≥ 0.80                            → dominant
      3. frz_skew > 0.4495
         (frz_mean ≤ 0.27 inside compressed_frozen)    → dominant
      4. frz_skew > 0.4495 (normal dist)               → frozen_coherent
      5. else                                           → dominant
    """
    if feats.get("cen_std", 1.0) < CEN_STD_THRESHOLD:
        return "magnitude", ["cen_std"]

    frz_skew = feats.get("frz_skew", 0.0)
    if frz_skew > FRZ_SKEW_THRESHOLD:
        frz_mean = feats.get("frz_mean", 0.0)
        frz_std  = feats.get("frz_std",  1.0)
        if frz_mean > FRZ_MEAN_THRESHOLD and frz_std < FRZ_STD_THRESHOLD:
            if frz_mean > FRZ_MEAN_LATE_THRESHOLD:
                frz_kurt = feats.get("frz_kurt", 0.0)
                if frz_kurt < FRZ_KURT_MAG_THRESHOLD:
                    return "magnitude", ["frz_skew", "frz_mean>0.27", "frz_kurt<0.80"]
                else:
                    return "dominant",  ["frz_skew", "frz_mean>0.27", "frz_kurt>=0.80"]
            return "dominant", ["frz_skew", "frz_mean", "frz_std"]  # compressed_frozen (early)
        return "frozen_coherent", ["frz_skew"]

    return "dominant", []


# ── Cascade v6 constants ─────────────────────────────────────────────────────
# v6 adds frozen_dominant as order-1 regime: when the frozen score distribution
# is concentrated and super-skewed (frz_mean > 0.45 AND frz_skew > 1.0), the raw
# frozen gate top-N is optimal and every blend term is noise.
# frozen_dominant weights (1,0,0) reduce dyn_blend to the raw frozen z-score.
# PRE-REGISTERED before Ring L (cascade_v6_spec.json). Validated: 4/4 retrodict
# (H/I/J/K) + blind L (frozen +8) = 5/5.
FROZEN_DOMINANT_FRZ_MEAN = 0.45   # frz_mean > 0.45
FROZEN_DOMINANT_FRZ_SKEW = 1.00   # AND frz_skew > 1.0

V6_REGIME_WEIGHTS = {
    "frozen_dominant":                 (1.0,  0.0, 0.0),   # raw frozen gate
    "magnitude":                       (0.5,  2.0, 2.0),   # D-anomaly
    "compressed_frozen_late_low_kurt": (0.5,  2.0, 2.0),   # magnitude weights
    "compressed_frozen_late_high_kurt": (-1.5, 0.0, 1.0),  # dominant weights
    "compressed_frozen_early":         (-1.5, 0.0, 1.0),   # dominant weights
    "frozen_coherent":                 (1.0,  0.0, 1.5),
    "dominant":                        (-1.5, 0.0, 1.0),
}


def predict_regime_v6(feats: dict) -> tuple[str, list[str]]:
    """Cascade v6 — canonical committed predictor (matches cascade_v6_spec.json).

    7-order cascade (first match wins):
      1. frz_mean > 0.45 AND frz_skew > 1.0       → frozen_dominant   (1, 0, 0)
      2. cen_std < 0.97974                         → magnitude         (0.5, 2, 2)
      3. frz_skew>0.4495 AND frz_mean>0.27
         AND frz_std<0.9621 AND frz_kurt < 0.80   → cf_late_low_kurt   (0.5, 2, 2)
      4. (same) AND frz_kurt >= 0.80               → cf_late_high_kurt  (-1.5, 0, 1)
      5. frz_skew>0.4495 AND frz_mean>0.15
         AND frz_std<0.9621                        → cf_early           (-1.5, 0, 1)
      6. frz_skew > 0.4495                         → frozen_coherent    (1, 0, 1.5)
      7. default                                   → dominant           (-1.5, 0, 1)

    Returns (regime_label, [fired_predicate_names]).
    """
    frz_mean = feats.get("frz_mean", 0.0)
    frz_skew = feats.get("frz_skew", 0.0)
    frz_std  = feats.get("frz_std",  1.0)
    frz_kurt = feats.get("frz_kurt", 0.0)
    cen_std  = feats.get("cen_std",  1.0)

    # Order 1: frozen_dominant (NEW in v6, takes precedence)
    if frz_mean > FROZEN_DOMINANT_FRZ_MEAN and frz_skew > FROZEN_DOMINANT_FRZ_SKEW:
        return "frozen_dominant", ["frz_mean>0.45", "frz_skew>1.0"]

    # Order 2: D-anomaly
    if cen_std < CEN_STD_THRESHOLD:
        return "magnitude", ["cen_std"]

    # Orders 3-6: high-skew family
    if frz_skew > FRZ_SKEW_THRESHOLD:
        if frz_mean > FRZ_MEAN_THRESHOLD and frz_std < FRZ_STD_THRESHOLD:
            if frz_mean > FRZ_MEAN_LATE_THRESHOLD:
                if frz_kurt < FRZ_KURT_MAG_THRESHOLD:
                    return "compressed_frozen_late_low_kurt", ["frz_skew", "frz_mean>0.27", "frz_kurt<0.80"]
                return "compressed_frozen_late_high_kurt", ["frz_skew", "frz_mean>0.27", "frz_kurt>=0.80"]
            return "compressed_frozen_early", ["frz_skew", "frz_mean>0.15", "frz_std<0.96"]
        return "frozen_coherent", ["frz_skew"]

    # Order 7: default
    return "dominant", []


def predict_regime(feats: dict, rules: list[dict], require_k: int = 1) -> tuple[str, list[str]]:
    """4-step cascade classifier (v3).

    Step 1: cen_std < 0.97974          → magnitude (D-anomaly)
    Step 2a: frz_skew > 0.4495
             AND frz_mean > 0.15
             AND frz_std  < 0.9621     → compressed_frozen (G-split; use dominant weights)
    Step 2b: frz_skew > 0.4495         → frozen_coherent
    Default:                           → dominant

    Returns (regime_label, [fired_feature_names]).
    """
    # Step 1: D-anomaly
    if feats.get("cen_std", 1.0) < CEN_STD_THRESHOLD:
        return "magnitude", ["cen_std"]

    frz_skew_val = feats.get("frz_skew", 0.0)
    if frz_skew_val > FRZ_SKEW_THRESHOLD:
        # Step 2a: G-split — compressed frozen distribution
        frz_mean_val = feats.get("frz_mean", 0.0)
        frz_std_val  = feats.get("frz_std",  1.0)
        if frz_mean_val > FRZ_MEAN_THRESHOLD and frz_std_val < FRZ_STD_THRESHOLD:
            return "compressed_frozen", ["frz_skew", "frz_mean", "frz_std"]
        # Step 2b: normal high-skew — cooperative
        return "frozen_coherent", ["frz_skew"]

    # Default
    return "dominant", []


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ensure_dynamic_profiles()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    frozen_spec = _load_frozen_spec()
    print(f"Frozen spec: {frozen_spec.spec_id}")
    print(f"Feature count: {len(FEATURE_NAMES)}")

    # Load row caches A-F
    print("\nLoading row caches A-F...", flush=True)
    rows_100 = build_or_load_rows(100_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_150 = build_or_load_rows(150_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_200 = build_or_load_rows(200_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_250 = build_or_load_rows(250_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_300 = build_or_load_rows(300_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_350 = build_or_load_rows(350_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_400 = build_or_load_rows(400_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_450 = build_or_load_rows(450_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_500 = build_or_load_rows(500_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)

    range_a = fresh_rows(rows_100, rows_150)
    range_b = fresh_rows(rows_150, rows_200)
    range_c = fresh_rows(rows_200, rows_250)
    range_d = fresh_rows(rows_250, rows_300)
    range_e = fresh_rows(rows_300, rows_350)
    range_f = fresh_rows(rows_350, rows_400)
    range_g = fresh_rows(rows_400, rows_450)
    range_h = fresh_rows(rows_450, rows_500)
    print(f"Sizes: A={len(range_a)} B={len(range_b)} C={len(range_c)} D={len(range_d)} "
          f"E={len(range_e)} F={len(range_f)} G={len(range_g)} H={len(range_h)}")

    # Frozen scores + z-norm (fit-set stats: frz on fit_a)
    fit_a, _ = split_ordered_rows(range_a, FIT_FRACTION)
    frz_fit = score_frozen(fit_a, frozen_spec)
    frz_mean, frz_scale = fit_score_normalizer(frz_fit)

    frz_a_z = z_norm(score_frozen(range_a, frozen_spec), frz_mean, frz_scale)
    frz_b_z = z_norm(score_frozen(range_b, frozen_spec), frz_mean, frz_scale)
    frz_c_z = z_norm(score_frozen(range_c, frozen_spec), frz_mean, frz_scale)
    frz_d_z = z_norm(score_frozen(range_d, frozen_spec), frz_mean, frz_scale)
    frz_e_z = z_norm(score_frozen(range_e, frozen_spec), frz_mean, frz_scale)
    frz_f_z = z_norm(score_frozen(range_f, frozen_spec), frz_mean, frz_scale)
    frz_g_z = z_norm(score_frozen(range_g, frozen_spec), frz_mean, frz_scale)
    frz_h_z = z_norm(score_frozen(range_h, frozen_spec), frz_mean, frz_scale)

    # Centroid scores + z-norm (trained on fit_a)
    x_fit = matrix(fit_a)
    y_fit = labels(fit_a)
    cen_model = fit_centroid_ranker(x_fit, y_fit)
    cen_fit_s = linear_scores(cen_model, x_fit)
    cen_mean, cen_scale = fit_score_normalizer(cen_fit_s)

    cen_a_z = z_norm(linear_scores(cen_model, matrix(range_a)), cen_mean, cen_scale)
    cen_b_z = z_norm(linear_scores(cen_model, matrix(range_b)), cen_mean, cen_scale)
    cen_c_z = z_norm(linear_scores(cen_model, matrix(range_c)), cen_mean, cen_scale)
    cen_d_z = z_norm(linear_scores(cen_model, matrix(range_d)), cen_mean, cen_scale)
    cen_e_z = z_norm(linear_scores(cen_model, matrix(range_e)), cen_mean, cen_scale)
    cen_f_z = z_norm(linear_scores(cen_model, matrix(range_f)), cen_mean, cen_scale)
    cen_g_z = z_norm(linear_scores(cen_model, matrix(range_g)), cen_mean, cen_scale)
    cen_h_z = z_norm(linear_scores(cen_model, matrix(range_h)), cen_mean, cen_scale)

    # Frozen baselines (for delta reporting)
    def frz_hits(rows, frz_z_list):
        sc = score_dict(rows, frz_z_list)
        m = metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)
        return m["unique_anchor_hits"], m["unique_anchors_total"]

    fb_a = frz_hits(range_a, frz_a_z)
    fb_b = frz_hits(range_b, frz_b_z)
    fb_c = frz_hits(range_c, frz_c_z)
    fb_d = frz_hits(range_d, frz_d_z)
    fb_e = frz_hits(range_e, frz_e_z)
    fb_f = frz_hits(range_f, frz_f_z)
    fb_g = frz_hits(range_g, frz_g_z)
    fb_h = frz_hits(range_h, frz_h_z)
    print(f"\nFrozen baseline: A={fb_a[0]}/{fb_a[1]} B={fb_b[0]}/{fb_b[1]} C={fb_c[0]}/{fb_c[1]} "
          f"D={fb_d[0]}/{fb_d[1]} E={fb_e[0]}/{fb_e[1]} F={fb_f[0]}/{fb_f[1]} "
          f"G={fb_g[0]}/{fb_g[1]} H={fb_h[0]}/{fb_h[1]}")

    # ── Build range-level features ──────────────────────────────────────────
    print("\n[Range features] Computing range-level summaries...", flush=True)
    range_feats = {}
    for label, rows, fz, cz in [
        ("A", range_a, frz_a_z, cen_a_z),
        ("B", range_b, frz_b_z, cen_b_z),
        ("C", range_c, frz_c_z, cen_c_z),
        ("D", range_d, frz_d_z, cen_d_z),
        ("E", range_e, frz_e_z, cen_e_z),
        ("F", range_f, frz_f_z, cen_f_z),
        ("G", range_g, frz_g_z, cen_g_z),
        ("H", range_h, frz_h_z, cen_h_z),
    ]:
        print(f"  Computing {label}...", flush=True)
        range_feats[label] = build_range_features(rows, fz, cz)
    print("  Done.")

    # ── Print top diagnostic features (score moments only) ──────────────────
    print("\n[Regime diagnostics] Score-moment comparison table:")
    diag_keys = ["frz_sentinel_frac", "frz_mean", "frz_std", "frz_skew", "frz_kurt",
                 "frz_p90", "frz_frac_extreme", "frz_mean_abs",
                 "cen_std", "cen_skew", "cen_kurt", "corr_frz_cen",
                 "lambda_slope", "graph_ramp_density", "cmpssz_density",
                 "prime_ratio_slope", "topo_saddle_mix", "gap_acceleration",
                 "graph_edge_var", "graph_return"]
    header = ["feature"] + ["A", "B", "C", "D", "E", "F", "G", "H"]
    print("  " + "  ".join(f"{h:>18}" for h in header))
    for k in diag_keys:
        vals = [k] + [f"{range_feats[r][k]:+.4f}" for r in ["A", "B", "C", "D", "E", "F", "G", "H"]]
        print("  " + "  ".join(f"{v:>18}" for v in vals))

    # ── Separability analysis (training = A/B/C/D/E; F held out) ───────────
    print("\n[Separability] Features where D is outside non-D range:")
    train_feats = {r: range_feats[r] for r in ["A", "B", "C", "D", "E"]}
    sep_results = compute_separability(train_feats, d_label="D")

    outliers_only = [(s, fk, dv, lo, hi, dir_) for s, fk, dv, lo, hi, dir_ in sep_results if dir_ != "inside"]
    print(f"  Total candidate features: {len(sep_results)}")
    print(f"  Features where D is outlier: {len(outliers_only)}")
    print()
    print("  Top 20 separating features (D outliers only):")
    print(f"  {'sep_score':>10}  {'feature':40}  {'D_val':>8}  {'non-D lo':>8}  {'non-D hi':>8}  {'dir':>5}")
    for sep_score, fk, dv, lo, hi, direction in outliers_only[:20]:
        print(f"  {sep_score:10.4f}  {fk:40s}  {dv:+8.4f}  {lo:+8.4f}  {hi:+8.4f}  {direction:>5}")

    # ── Build threshold rules ───────────────────────────────────────────────
    rules = build_threshold_rule(outliers_only, top_k=5)
    print(f"\n[Classifier] Top-5 threshold rules:")
    for rule in rules:
        print(f"  [{rule['sep_score']:5.3f}] {rule['feature']:40s} {rule['predicate']} {rule['threshold']:+.5f}  "
              f"(D={rule['d_val']:+.5f}, non-D=[{rule['non_d_lo']:+.5f},{rule['non_d_hi']:+.5f}])")

    # ── Retrodict all 6 known ranges with v2 cascade ───────────────────────
    print("\n[Validation v2] Retrodict A/B/C/D/E/F with 3-regime cascade:")
    print(f"  Rules:  cen_std < {CEN_STD_THRESHOLD:.5f} → magnitude")
    print(f"          frz_skew > {FRZ_SKEW_THRESHOLD:.4f} → frozen_coherent")
    print(f"          else → dominant")
    retrodiction = {}
    for label in ["A", "B", "C", "D", "E", "F", "G"]:
        pred, fired = predict_regime(range_feats[label], rules, require_k=1)
        truth = REGIME_KNOWN[label]
        correct = (pred == truth)
        retrodiction[label] = {"truth": truth, "pred": pred, "fired": fired, "correct": correct}
        ks = (f"cen_std={range_feats[label]['cen_std']:.4f}  "
              f"frz_skew={range_feats[label]['frz_skew']:.4f}  "
              f"frz_mean={range_feats[label]['frz_mean']:.4f}  "
              f"frz_std={range_feats[label]['frz_std']:.4f}")
        print(f"  {label}: truth={truth:18s}  pred={pred:18s}  {'OK' if correct else 'WRONG'}  ({ks})")

    retro_ok = sum(1 for v in retrodiction.values() if v["correct"])
    print(f"\n  Retrodiction: {retro_ok}/{len(retrodiction)} correct")

    # ── Score all regimes on F ─────────────────────────────────────────────
    print("\n[Range F scoring] All three regimes...")
    sc_f_dom  = score_dict(range_f, dyn_blend(frz_f_z, cen_f_z, DOMINANT_WF, DOMINANT_WA, DOMINANT_WC))
    sc_f_dmag = score_dict(range_f, dyn_blend(frz_f_z, cen_f_z, D_WF, D_WA, D_WC))
    sc_f_coop = score_dict(range_f, dyn_blend(frz_f_z, cen_f_z, COOP_WF, COOP_WA, COOP_WC))
    sc_f_frz  = score_dict(range_f, frz_f_z)

    m_f_dom  = metrics_for_scores(range_f, sc_f_dom,  TOP_N, unique_anchors_only=True)
    m_f_dmag = metrics_for_scores(range_f, sc_f_dmag, TOP_N, unique_anchors_only=True)
    m_f_coop = metrics_for_scores(range_f, sc_f_coop, TOP_N, unique_anchors_only=True)
    m_f_frz  = metrics_for_scores(range_f, sc_f_frz,  TOP_N, unique_anchors_only=True)

    frz_set_f = {h["anchor_prime"] for h in m_f_frz["hidden_numbers"]}
    dom_new  = sorted({h["anchor_prime"] for h in m_f_dom["hidden_numbers"]}  - frz_set_f)
    dmag_new = sorted({h["anchor_prime"] for h in m_f_dmag["hidden_numbers"]} - frz_set_f)
    coop_new = sorted({h["anchor_prime"] for h in m_f_coop["hidden_numbers"]} - frz_set_f)

    h_f_frz  = m_f_frz["unique_anchor_hits"]
    h_f_dom  = m_f_dom["unique_anchor_hits"]
    h_f_dmag = m_f_dmag["unique_anchor_hits"]
    h_f_coop = m_f_coop["unique_anchor_hits"]
    tot_f = m_f_frz["unique_anchors_total"]

    print(f"  frozen baseline:       F={h_f_frz}/{tot_f}")
    print(f"  dominant (wf=-1.5):    F={h_f_dom}/{tot_f}  delta={h_f_dom-h_f_frz:+d}  new={dom_new}")
    print(f"  D-anomaly (wf=+0.5):   F={h_f_dmag}/{tot_f}  delta={h_f_dmag-h_f_frz:+d}  new={dmag_new}")
    print(f"  frozen-coherent(+1.0): F={h_f_coop}/{tot_f}  delta={h_f_coop-h_f_frz:+d}  new={coop_new}")

    # v2 prediction for F
    f_pred_v2, f_fired_v2 = predict_regime(range_feats["F"], rules, require_k=1)
    pred_hits_map = {"dominant": h_f_dom, "magnitude": h_f_dmag, "frozen_coherent": h_f_coop}
    pred_new_map  = {"dominant": dom_new,  "magnitude": dmag_new,  "frozen_coherent": coop_new}
    pred_hits = pred_hits_map[f_pred_v2]
    pred_new  = pred_new_map[f_pred_v2]
    print(f"\n  v2 prediction for F: {f_pred_v2}  (fired: {f_fired_v2})")
    print(f"  Predicted-regime result: F={pred_hits}/{tot_f}  delta={pred_hits-h_f_frz:+d}  new={pred_new}")

    # v1 comparison (was wrongly predicted dominant)
    print(f"\n  v1 vs v2 on F:")
    print(f"    v1 predicted dominant → 5/{tot_f} (delta={5-h_f_frz:+d})")
    print(f"    v2 predicts {f_pred_v2} → {pred_hits}/{tot_f} (delta={pred_hits-h_f_frz:+d})")

    # ── Blind test: Range G (400M-450M) ───────────────────────────────────
    print("\n" + "=" * 70)
    print("[Blind test] Range G (400M-450M)")
    g_pred, g_fired = predict_regime(range_feats["G"], rules, require_k=1)
    g_ks = f"cen_std={range_feats['G']['cen_std']:.4f}  frz_skew={range_feats['G']['frz_skew']:.4f}"
    print(f"  Predicted regime: {g_pred}  (fired: {g_fired})  [{g_ks}]")

    # Score G with all three regimes
    sc_g_dom  = score_dict(range_g, dyn_blend(frz_g_z, cen_g_z, DOMINANT_WF, DOMINANT_WA, DOMINANT_WC))
    sc_g_dmag = score_dict(range_g, dyn_blend(frz_g_z, cen_g_z, D_WF, D_WA, D_WC))
    sc_g_coop = score_dict(range_g, dyn_blend(frz_g_z, cen_g_z, COOP_WF, COOP_WA, COOP_WC))
    sc_g_frz  = score_dict(range_g, frz_g_z)

    m_g_dom  = metrics_for_scores(range_g, sc_g_dom,  TOP_N, unique_anchors_only=True)
    m_g_dmag = metrics_for_scores(range_g, sc_g_dmag, TOP_N, unique_anchors_only=True)
    m_g_coop = metrics_for_scores(range_g, sc_g_coop, TOP_N, unique_anchors_only=True)
    m_g_frz  = metrics_for_scores(range_g, sc_g_frz,  TOP_N, unique_anchors_only=True)

    frz_set_g = {h["anchor_prime"] for h in m_g_frz["hidden_numbers"]}
    g_dom_new  = sorted({h["anchor_prime"] for h in m_g_dom["hidden_numbers"]}  - frz_set_g)
    g_dmag_new = sorted({h["anchor_prime"] for h in m_g_dmag["hidden_numbers"]} - frz_set_g)
    g_coop_new = sorted({h["anchor_prime"] for h in m_g_coop["hidden_numbers"]} - frz_set_g)

    h_g_frz  = m_g_frz["unique_anchor_hits"]
    h_g_dom  = m_g_dom["unique_anchor_hits"]
    h_g_dmag = m_g_dmag["unique_anchor_hits"]
    h_g_coop = m_g_coop["unique_anchor_hits"]
    tot_g = m_g_frz["unique_anchors_total"]

    print(f"  frozen baseline:       G={h_g_frz}/{tot_g}")
    print(f"  dominant (wf=-1.5):    G={h_g_dom}/{tot_g}  delta={h_g_dom-h_g_frz:+d}  new={g_dom_new}")
    print(f"  D-anomaly (wf=+0.5):   G={h_g_dmag}/{tot_g}  delta={h_g_dmag-h_g_frz:+d}  new={g_dmag_new}")
    print(f"  frozen-coherent(+1.0): G={h_g_coop}/{tot_g}  delta={h_g_coop-h_g_frz:+d}  new={g_coop_new}")

    g_pred_hits_map = {"dominant": h_g_dom, "magnitude": h_g_dmag,
                       "frozen_coherent": h_g_coop, "compressed_frozen": h_g_dom}
    g_pred_new_map  = {"dominant": g_dom_new, "magnitude": g_dmag_new,
                       "frozen_coherent": g_coop_new, "compressed_frozen": g_dom_new}
    g_pred_hits = g_pred_hits_map[g_pred]
    g_pred_new  = g_pred_new_map[g_pred]
    print(f"\n  Predicted ({g_pred}) → G={g_pred_hits}/{tot_g}  delta={g_pred_hits-h_g_frz:+d}")
    print(f"  New anchors: {g_pred_new}")
    print("=" * 70)

    # ── Blind test: Range H (450M-500M) ───────────────────────────────────
    print("\n" + "=" * 70)
    print("[Blind test] Range H (450M-500M) — CASCADE V3")
    h_ks = (f"cen_std={range_feats['H']['cen_std']:.4f}  "
            f"frz_skew={range_feats['H']['frz_skew']:.4f}  "
            f"frz_mean={range_feats['H']['frz_mean']:.4f}  "
            f"frz_std={range_feats['H']['frz_std']:.4f}")
    print(f"  Range features: {h_ks}")

    # Cascade v3 prediction — computed BEFORE seeing anchor truth
    h_pred, h_fired = predict_regime(range_feats["H"], rules, require_k=1)
    print(f"\n  v3 prediction: {h_pred}  (fired: {h_fired})")
    print(f"  Cascade path:")
    print(f"    cen_std={range_feats['H']['cen_std']:.4f} < {CEN_STD_THRESHOLD}? "
          f"{'YES → magnitude' if range_feats['H']['cen_std'] < CEN_STD_THRESHOLD else 'no'}")
    print(f"    frz_skew={range_feats['H']['frz_skew']:.4f} > {FRZ_SKEW_THRESHOLD}? "
          f"{'YES' if range_feats['H']['frz_skew'] > FRZ_SKEW_THRESHOLD else 'no → dominant'}")
    if range_feats['H']['frz_skew'] > FRZ_SKEW_THRESHOLD:
        print(f"    frz_mean={range_feats['H']['frz_mean']:.4f} > {FRZ_MEAN_THRESHOLD} "
              f"AND frz_std={range_feats['H']['frz_std']:.4f} < {FRZ_STD_THRESHOLD}? "
              f"{'YES → compressed_frozen' if h_pred == 'compressed_frozen' else 'no → frozen_coherent'}")

    # Score H with all four regimes
    sc_h_dom  = score_dict(range_h, dyn_blend(frz_h_z, cen_h_z, DOMINANT_WF, DOMINANT_WA, DOMINANT_WC))
    sc_h_dmag = score_dict(range_h, dyn_blend(frz_h_z, cen_h_z, D_WF, D_WA, D_WC))
    sc_h_coop = score_dict(range_h, dyn_blend(frz_h_z, cen_h_z, COOP_WF, COOP_WA, COOP_WC))
    sc_h_frz  = score_dict(range_h, frz_h_z)

    m_h_dom  = metrics_for_scores(range_h, sc_h_dom,  TOP_N, unique_anchors_only=True)
    m_h_dmag = metrics_for_scores(range_h, sc_h_dmag, TOP_N, unique_anchors_only=True)
    m_h_coop = metrics_for_scores(range_h, sc_h_coop, TOP_N, unique_anchors_only=True)
    m_h_frz  = metrics_for_scores(range_h, sc_h_frz,  TOP_N, unique_anchors_only=True)

    frz_set_h = {x["anchor_prime"] for x in m_h_frz["hidden_numbers"]}
    h_dom_new  = sorted({x["anchor_prime"] for x in m_h_dom["hidden_numbers"]}  - frz_set_h)
    h_dmag_new = sorted({x["anchor_prime"] for x in m_h_dmag["hidden_numbers"]} - frz_set_h)
    h_coop_new = sorted({x["anchor_prime"] for x in m_h_coop["hidden_numbers"]} - frz_set_h)

    h_h_frz  = m_h_frz["unique_anchor_hits"]
    h_h_dom  = m_h_dom["unique_anchor_hits"]
    h_h_dmag = m_h_dmag["unique_anchor_hits"]
    h_h_coop = m_h_coop["unique_anchor_hits"]
    tot_h = m_h_frz["unique_anchors_total"]

    print(f"\n  Results (all regimes):")
    print(f"  frozen baseline:       H={h_h_frz}/{tot_h}")
    print(f"  dominant (wf=-1.5):    H={h_h_dom}/{tot_h}  delta={h_h_dom-h_h_frz:+d}  new={h_dom_new}")
    print(f"  D-anomaly (wf=+0.5):   H={h_h_dmag}/{tot_h}  delta={h_h_dmag-h_h_frz:+d}  new={h_dmag_new}")
    print(f"  frozen-coherent(+1.0): H={h_h_coop}/{tot_h}  delta={h_h_coop-h_h_frz:+d}  new={h_coop_new}")

    # compressed_frozen uses dominant weights
    regime_weight_map = {
        "dominant":        (h_h_dom,  h_dom_new),
        "magnitude":       (h_h_dmag, h_dmag_new),
        "frozen_coherent": (h_h_coop, h_coop_new),
        "compressed_frozen": (h_h_dom, h_dom_new),  # same as dominant
    }
    h_pred_hits, h_pred_new = regime_weight_map[h_pred]
    print(f"\n  v3 prediction: {h_pred} → H={h_pred_hits}/{tot_h}  delta={h_pred_hits-h_h_frz:+d}")
    print(f"  New anchors under predicted regime: {h_pred_new}")

    beats_frozen = h_pred_hits >= h_h_frz
    print(f"\n  SUCCESS CRITERION (>= frozen baseline): {'PASS' if beats_frozen else 'FAIL'}")
    print("=" * 70)

    # ── Save artifacts ──────────────────────────────────────────────────────
    artifact = {
        "schema": "range_regime_classifier_v2",
        "feature_count": len(FEATURE_NAMES),
        "training_ranges": ["A", "B", "C", "D", "E"],
        "blind_range": "F",
        "regime_labels": REGIME_KNOWN,
        "cascade": {
            "step1": {"feature": "cen_std", "threshold": CEN_STD_THRESHOLD,
                      "predicate": "<", "regime": "magnitude"},
            "step2": {"feature": "frz_skew", "threshold": FRZ_SKEW_THRESHOLD,
                      "predicate": ">", "regime": "frozen_coherent"},
            "default": "dominant",
        },
        "dominant_weights":   {"w_f": DOMINANT_WF, "w_a": DOMINANT_WA, "w_c": DOMINANT_WC},
        "magnitude_weights":  {"w_f": D_WF,        "w_a": D_WA,        "w_c": D_WC},
        "coop_weights":       {"w_f": COOP_WF,     "w_a": COOP_WA,     "w_c": COOP_WC},
        "top_separating_features": [
            {"sep_score": s, "feature": fk, "d_val": round(dv, 6),
             "non_d_lo": round(lo, 6), "non_d_hi": round(hi, 6), "direction": dir_}
            for s, fk, dv, lo, hi, dir_ in outliers_only[:10]
        ],
        "threshold_rules": rules,
        "retrodiction": retrodiction,
        "f_prediction": {
            "v2_regime": f_pred_v2,
            "v2_fired": f_fired_v2,
        },
        "f_results": {
            "frozen":         {"hits": h_f_frz,  "total": tot_f},
            "dominant":       {"hits": h_f_dom,  "delta": h_f_dom  - h_f_frz, "new_anchors": dom_new},
            "magnitude":      {"hits": h_f_dmag, "delta": h_f_dmag - h_f_frz, "new_anchors": dmag_new},
            "frozen_coherent":{"hits": h_f_coop, "delta": h_f_coop - h_f_frz, "new_anchors": coop_new},
            "predicted_regime":     f_pred_v2,
            "predicted_hits":       pred_hits,
            "predicted_new_anchors": pred_new,
        },
        "g_results": {
            "frozen":         {"hits": h_g_frz,  "total": tot_g},
            "dominant":       {"hits": h_g_dom,  "delta": h_g_dom  - h_g_frz, "new_anchors": g_dom_new},
            "magnitude":      {"hits": h_g_dmag, "delta": h_g_dmag - h_g_frz, "new_anchors": g_dmag_new},
            "frozen_coherent":{"hits": h_g_coop, "delta": h_g_coop - h_g_frz, "new_anchors": g_coop_new},
            "predicted_regime":     g_pred,
            "predicted_hits":       g_pred_hits,
            "predicted_new_anchors": g_pred_new,
            "frz_skew": range_feats["G"]["frz_skew"],
            "cen_std":  range_feats["G"]["cen_std"],
        },
        "range_features": {r: {k: v for k, v in range_feats[r].items() if not k.startswith("mean_")}
                           for r in ["A", "B", "C", "D", "E", "F", "G"]},
    }

    art_path = OUT_DIR / "regime_classifier_v2.json"
    art_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved: {art_path}")

    # ── Markdown RESULTS.md ─────────────────────────────────────────────────
    md_lines = [
        "# Range-Regime Classifier Results (v2)",
        "",
        f"**Date:** 2026-06-04  ",
        f"**Training ranges:** A/B/C/D/E  **Blind test:** F=350M-400M  ",
        f"**Classifier:** 3-regime cascade (cen_std → frz_skew → dominant)  ",
        f"**Retrodiction accuracy:** {retro_ok}/{len(retrodiction)}",
        "",
        "## 3-Regime Cascade",
        "",
        "```",
        f"Step 1:  cen_std < {CEN_STD_THRESHOLD:.5f}  →  magnitude    (wf=+0.5, wa=2.0, wc=2.0)",
        f"Step 2:  frz_skew > {FRZ_SKEW_THRESHOLD:.4f}   →  frozen_coherent (wf=+1.0, wa=0.0, wc=1.5)",
        f"Default:                         →  dominant     (wf=-1.5, wa=0.0, wc=1.0)",
        "```",
        "",
        "## Regime Assignments",
        "",
        "| Range | Regime | wf | wa | wc |",
        "| --- | --- | ---: | ---: | ---: |",
        "| A 100-150M | dominant | -1.5 | 0.0 | 1.0 |",
        "| B 150-200M | dominant | -1.0 | 0.0 | 2.0 |",
        "| C 200-250M | dominant | -1.5 | 0.0 | 1.0 |",
        "| **D 250-300M** | **magnitude** | **+0.5** | **2.0** | **2.0** |",
        "| E 300-350M | dominant | -1.5 | 0.0 | 1.0 |",
        "| **F 350-400M** | **frozen_coherent** | **+1.0** | **0.0** | **1.5** |",
        "",
        "## Top Separating Features (D vs A/B/C/E)",
        "",
        "| sep_score | feature | D val | non-D lo | non-D hi | dir |",
        "| ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for sep_score, fk, dv, lo, hi, direction in outliers_only[:10]:
        md_lines.append(f"| {sep_score:.4f} | {fk} | {dv:+.4f} | {lo:+.4f} | {hi:+.4f} | {direction} |")

    md_lines += [
        "",
        "## Threshold Rules (D separability, top-5)",
        "",
        "| sep_score | rule | threshold |",
        "| ---: | --- | ---: |",
    ]
    for rule in rules:
        md_lines.append(f"| {rule['sep_score']:.3f} | `{rule['feature']} {rule['predicate']} {rule['threshold']}` | {rule['threshold']} |")

    md_lines += [
        "",
        "## Retrodiction (All 6 Ranges)",
        "",
        "| Range | Truth | Pred | Correct |",
        "| --- | --- | --- | --- |",
    ]
    for rng, rv in retrodiction.items():
        md_lines.append(f"| {rng} | {rv['truth']} | {rv['pred']} | {'✓' if rv['correct'] else '✗'} |")

    md_lines += [
        "",
        f"**Retrodiction accuracy:** {retro_ok}/{len(retrodiction)}",
        "",
        "## Blind Test: Range F (350M-400M)",
        "",
        f"**v2 prediction:** {f_pred_v2}  (fired: {f_fired_v2})",
        f"**frz_skew(F):** {range_feats['F']['frz_skew']:.4f}  (threshold={FRZ_SKEW_THRESHOLD})  "
        f"cen_std(F)={range_feats['F']['cen_std']:.4f}  (threshold={CEN_STD_THRESHOLD})",
        "",
        "| Method | F hits | Delta | New anchors |",
        "| --- | ---: | ---: | --- |",
        f"| frozen baseline | {h_f_frz}/{tot_f} | — | — |",
        f"| dominant (wf=-1.5 wa=0 wc=1) | {h_f_dom}/{tot_f} | {h_f_dom - h_f_frz:+d} | `{dom_new}` |",
        f"| magnitude (wf=+0.5 wa=2 wc=2) | {h_f_dmag}/{tot_f} | {h_f_dmag - h_f_frz:+d} | `{dmag_new}` |",
        f"| frozen_coherent (wf=+1.0 wc=1.5) | {h_f_coop}/{tot_f} | {h_f_coop - h_f_frz:+d} | `{coop_new}` |",
        f"| **v2 predicted ({f_pred_v2})** | **{pred_hits}/{tot_f}** | **{pred_hits - h_f_frz:+d}** | `{pred_new}` |",
        "",
        "**v1 vs v2 on F:**",
        f"- v1 predicted dominant → 5/{tot_f} (delta={5 - h_f_frz:+d})",
        f"- v2 predicts {f_pred_v2} → {pred_hits}/{tot_f} (delta={pred_hits - h_f_frz:+d})",
        "",
        "## Blind Test: Range G (400M-450M)",
        "",
        f"**v2 prediction:** {g_pred}  (fired: {g_fired})  "
        f"cen_std={range_feats['G']['cen_std']:.4f}  frz_skew={range_feats['G']['frz_skew']:.4f}",
        "",
        "| Method | G hits | Delta | New anchors |",
        "| --- | ---: | ---: | --- |",
        f"| frozen baseline | {h_g_frz}/{tot_g} | — | — |",
        f"| dominant (wf=-1.5 wa=0 wc=1) | {h_g_dom}/{tot_g} | {h_g_dom - h_g_frz:+d} | `{g_dom_new}` |",
        f"| magnitude (wf=+0.5 wa=2 wc=2) | {h_g_dmag}/{tot_g} | {h_g_dmag - h_g_frz:+d} | `{g_dmag_new}` |",
        f"| frozen_coherent (wf=+1.0 wc=1.5) | {h_g_coop}/{tot_g} | {h_g_coop - h_g_frz:+d} | `{g_coop_new}` |",
        f"| **v2 predicted ({g_pred})** | **{g_pred_hits}/{tot_g}** | **{g_pred_hits - h_g_frz:+d}** | `{g_pred_new}` |",
        "",
        "## Key Diagnostic Feature Values",
        "",
        "| feature | A | B | C | D | E | F | G |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for k in diag_keys:
        row = [k] + [f"{range_feats[r][k]:+.4f}" for r in ["A", "B", "C", "D", "E", "F", "G"]]
        md_lines.append("| " + " | ".join(row) + " |")

    md_lines += [
        "",
        "## Artifacts",
        "",
        "- `artifacts/range_regime_classifier/regime_classifier_v2.json`",
        "- `artifacts/fill_ranker/fill_ranker_dynamic.json`",
        "- `artifacts/fill_ranker/fill_ranker_regime_moments.json`",
    ]

    results_path = OUT_DIR / "RESULTS.md"
    results_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"Saved: {results_path}")


if __name__ == "__main__":
    main()
