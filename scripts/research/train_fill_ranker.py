"""Train a fill ranker and replicate the oracle tree-blend on range_c (250M blind board).

Goal
----
gate_v1 (constrained blend): B=12/227, C=6/256
oracle_blend (bench, tree_d2): B=16/227, C=?

This script answers: does the oracle approach generalize to C (200M→250M)?

Three approaches tested
-----------------------
1. centroid_a: centroid ranker on all range_a, blended with frozen; test on B and C.
   (Baseline for the centroid approach — shows if 44 features help.)
2. tree_d2_a: Shallow tree (depth=2) trained on fit_a (60% of range_a), blended with
   frozen; replicates the oracle approach from the bench. Test on B and C.
3. centroid_ab: centroid ranker trained on range_a + range_b; test on C only.

All blends use z-normalization (fit-set statistics) matching the bench oracle protocol.

Outputs
-------
  artifacts/fill_ranker/fill_ranker_a.json     — centroid_a artifact
  artifacts/fill_ranker/fill_ranker_tree_d2.json — tree_d2_a artifact
  artifacts/fill_ranker/fill_ranker_ab.json    — centroid_ab artifact
  artifacts/fill_ranker/RESULTS.md             — comparison table
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.run_prime_search_engine_bench import (  # noqa: E402
    DEFAULT_ROW_CACHE_DIR,
    FEATURE_NAMES,
    LinearModel,
    NEG_INF,
    apply_score_normalizer,
    blend_scores,
    build_or_load_rows,
    feature_vector,
    fit_centroid_ranker,
    fit_score_normalizer,
    fit_standardizer,
    fit_tree,
    fresh_rows,
    labels,
    linear_scores,
    matrix,
    metrics_for_scores,
    safe_float,
    score_frozen,
    split_ordered_rows,
    tree_scores,
    zrow,
)
from scripts.research.run_field_branch_gate_search import (  # noqa: E402
    GateSpec,
    ensure_dynamic_profiles,
)

OUT_DIR = REPO_ROOT / "artifacts" / "fill_ranker"
CACHE_DIR = DEFAULT_ROW_CACHE_DIR

WINDOW = 36
HISTORY = 12
ANCHOR_THRESHOLD = 4.0
TOP_N = 20

FIT_FRACTION = 0.60
TREE_MAX_DEPTH = 2
TREE_MIN_LEAF = 200
TREE_BINS = 50


# ── frozen spec ────────────────────────────────────────────────────────────────
def _load_frozen_spec() -> GateSpec:
    report_path = REPO_ROOT / "artifacts" / "prime_search_engine_bench" / "latest_report.json"
    if not report_path.exists():
        raise FileNotFoundError(f"Run the bench first: {report_path}")
    data = json.loads(report_path.read_text())
    return GateSpec(**data["frozen_spec"])


def _load_gate_v1_ref() -> tuple[int | None, int | None]:
    p = REPO_ROOT / "artifacts" / "map_reader_gate" / "gate_v1.json"
    if not p.exists():
        return None, None
    d = json.loads(p.read_text())
    return d["results"]["range_b"]["unique_anchor_hits"], d["results"]["range_c"]["unique_anchor_hits"]


# ── score utilities ────────────────────────────────────────────────────────────
def z_norm_with_fit_stats(scores: list[float], fit_mean: float, fit_scale: float) -> list[float]:
    return apply_score_normalizer(scores, fit_mean, fit_scale)


def blend2(a_z: list[float], b_z: list[float], w_a: float) -> list[float]:
    """Blend two z-normalised score lists: w_a*a + (1-w_a)*b."""
    w_b = 1.0 - w_a
    return [w_a * a + w_b * b for a, b in zip(a_z, b_z)]


def score_dict(rows: list[dict], scores: list[float]) -> dict[int, float]:
    return {id(r): s for r, s in zip(rows, scores)}


def unique_hits(rows: list[dict], sc: dict[int, float]) -> int:
    return metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)["unique_anchor_hits"]


def frozen_ref(rows: list[dict], spec: GateSpec) -> tuple[int, int]:
    frz = score_frozen(rows, spec)
    sc = score_dict(rows, frz)
    m = metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)
    return m["unique_anchor_hits"], m["unique_anchors_total"]


def anchor_set_from_metrics(m: dict) -> set:
    return {h["anchor_prime"] for h in m["hidden_numbers"]}


def top_feature_weights(ranker, top_k: int = 10) -> list[tuple[str, float]]:
    pairs = [(FEATURE_NAMES[i], ranker.weights[i]) for i in range(len(ranker.weights))]
    return sorted(pairs, key=lambda x: abs(x[1]), reverse=True)[:top_k]


# ── weight search ──────────────────────────────────────────────────────────────
def search_weight(
    rows: list[dict],
    frz_z: list[float],
    fill_z: list[float],
    min_w: float = 0.4,
) -> tuple[float, int]:
    """Grid search blend weight w_frz in [min_w, 0.9]; return (best_w, best_hits)."""
    best_h, best_w = -1, min_w
    for w in [0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        if w < min_w:
            continue
        sc = score_dict(rows, blend2(frz_z, fill_z, w))
        h = unique_hits(rows, sc)
        if h > best_h or (h == best_h and w > best_w):
            best_h, best_w = h, w
    return best_w, best_h


# ── evaluation helper ──────────────────────────────────────────────────────────
def eval_blend(name: str, rows: list[dict], frz_z: list[float], fill_z: list[float],
               w: float, frz_anchors: set) -> dict:
    sc = score_dict(rows, blend2(frz_z, fill_z, w))
    m = metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)
    new = sorted(anchor_set_from_metrics(m) - frz_anchors)
    return {
        "unique_hits": m["unique_anchor_hits"],
        "unique_total": m["unique_anchors_total"],
        "delta_frozen": m["unique_anchor_hits"] - len(frz_anchors),  # approx
        "new_anchors": new,
        "hidden_numbers": m["hidden_numbers"],
        "metrics": m,
    }


def _class_stats(z_rows: list[list[float]], y_rows: list[int], width: int):
    pos = [r for r, lab in zip(z_rows, y_rows) if lab]
    neg = [r for r, lab in zip(z_rows, y_rows) if not lab]
    pos_mean = [sum(r[j] for r in pos) / len(pos) for j in range(width)]
    neg_mean = [sum(r[j] for r in neg) / len(neg) for j in range(width)]
    pos_var = [sum((r[j] - pos_mean[j]) ** 2 for r in pos) / len(pos) for j in range(width)]
    neg_var = [sum((r[j] - neg_mean[j]) ** 2 for r in neg) / len(neg) for j in range(width)]
    pooled = [(pv + nv) / 2.0 for pv, nv in zip(pos_var, neg_var)]
    return pos_mean, neg_mean, pooled


def fit_diagonal_lda(x_rows: list[list[float]], y_rows: list[int], lam: float = 0.1) -> "LinearModel":
    """Diagonal LDA: w_j = Δμ_j / (σ²_j + λ).  λ→0 = full LDA, λ→∞ = centroid."""
    means, scales = fit_standardizer(x_rows)
    z_rows = [zrow(row, means, scales) for row in x_rows]
    width = len(means)
    pos = [r for r, lab in zip(z_rows, y_rows) if lab]
    neg = [r for r, lab in zip(z_rows, y_rows) if not lab]
    if not pos or not neg:
        return LinearModel(means, scales, [0.0] * width, 0.0)
    pm, nm, pooled = _class_stats(z_rows, y_rows, width)
    weights = [(p - n) / (pv + lam) for p, n, pv in zip(pm, nm, pooled)]
    bias = -0.5 * sum((p ** 2 - n ** 2) / (pv + lam) for p, n, pv in zip(pm, nm, pooled))
    return LinearModel(means, scales, weights, bias)


def fit_soft_var_ranker(x_rows: list[list[float]], y_rows: list[int], alpha: float = 1.0) -> "LinearModel":
    """Variance-as-reference ranker: w_j = Δμ_j / (1 + α·σ²_j).

    α = 0 : pure centroid (variance ignored — current champion)
    α = 1 : gentle soft damping of high-variance (noisy) features
    α → ∞ : approaches full LDA
    Unlike hard LDA, low-variance features are NOT amplified — they stay at Δμ.
    """
    means, scales = fit_standardizer(x_rows)
    z_rows = [zrow(row, means, scales) for row in x_rows]
    width = len(means)
    pos = [r for r, lab in zip(z_rows, y_rows) if lab]
    neg = [r for r, lab in zip(z_rows, y_rows) if not lab]
    if not pos or not neg:
        return LinearModel(means, scales, [0.0] * width, 0.0)
    pm, nm, pooled = _class_stats(z_rows, y_rows, width)
    weights = [(p - n) / (1.0 + alpha * pv) for p, n, pv in zip(pm, nm, pooled)]
    bias = -0.5 * sum((p ** 2 - n ** 2) / (1.0 + alpha * pv) for p, n, pv in zip(pm, nm, pooled))
    return LinearModel(means, scales, weights, bias)


def dist_moments(scores: list[float]) -> dict:
    """Distribution moments useful for regime classification."""
    n = len(scores)
    mu = sum(scores) / n
    var = sum((x - mu) ** 2 for x in scores) / n
    sd = var ** 0.5 if var > 0 else 1e-9
    skew = sum((x - mu) ** 3 for x in scores) / (n * sd ** 3)
    kurt = sum((x - mu) ** 4 for x in scores) / (n * sd ** 4) - 3.0  # excess
    sorted_s = sorted(scores)
    p10 = sorted_s[int(0.10 * n)]
    p25 = sorted_s[int(0.25 * n)]
    p75 = sorted_s[int(0.75 * n)]
    p90 = sorted_s[int(0.90 * n)]
    iqr = p75 - p25
    mean_abs = sum(abs(x) for x in scores) / n
    # fraction of scores with |z| > 1.5  (frozen extremes)
    frac_extreme = sum(1 for x in scores if abs(x) > 1.5) / n
    return dict(mean=mu, std=sd, skew=skew, kurt=kurt,
                p10=p10, p75=p75, p90=p90, iqr=iqr,
                mean_abs=mean_abs, frac_extreme=frac_extreme)


def score_corr(a: list[float], b: list[float]) -> float:
    """Pearson r between two score lists."""
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = (sum((x - ma) ** 2 for x in a)) ** 0.5
    db = (sum((y - mb) ** 2 for y in b)) ** 0.5
    return num / (da * db) if da * db > 0 else 0.0


def dyn_blend(frz_z: list[float], cen_z: list[float],
              w_f: float, w_a: float, w_c: float) -> list[float]:
    """Dynamic blend: score = w_f * frz + w_a * |frz| + w_c * cen.

    w_f: direct frozen (negative = adversarial; penalises frozen-liked rows)
    w_a: frozen absolute magnitude (always positive; rewards any extreme frozen signal)
    w_c: centroid contribution

    Interesting regimes:
      w_f < 0, w_a > |w_f| : frozen-rejected rows get the biggest boost
      w_a = 0, w_f < 0    : pure adversarial (penalise what frozen likes)
      w_f = 0, w_a > 0    : magnitude gate (boost extremes in either direction)
    """
    return [w_f * f + w_a * abs(f) + w_c * c for f, c in zip(frz_z, cen_z)]


def search_dynamic_weights(
    rows: list[dict],
    frz_z: list[float],
    cen_z: list[float],
) -> tuple[float, float, float, int]:
    """Per-range grid search over (w_f, w_a, w_c).

    w_f in [-1.5 .. 1.5], w_a in [0 .. 2.0], w_c in [0.5 .. 2.0].
    Returns (w_f, w_a, w_c, best_unique_anchor_hits).
    """
    W_F = [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
    W_A = [0.0, 0.5, 1.0, 1.5, 2.0]
    W_C = [0.5, 1.0, 1.5, 2.0]
    best_h, best_wf, best_wa, best_wc = -1, 0.0, 0.0, 1.0
    for wf in W_F:
        for wa in W_A:
            for wc in W_C:
                sc = score_dict(rows, dyn_blend(frz_z, cen_z, wf, wa, wc))
                h = unique_hits(rows, sc)
                if h > best_h:
                    best_h = h
                    best_wf, best_wa, best_wc = wf, wa, wc
    return best_wf, best_wa, best_wc, best_h


def eval_preblend(rows: list[dict], scores: list[float], frz_anchors: set) -> dict:
    sc = score_dict(rows, scores)
    m = metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)
    new = sorted(anchor_set_from_metrics(m) - frz_anchors)
    return {
        "unique_hits": m["unique_anchor_hits"],
        "unique_total": m["unique_anchors_total"],
        "delta_frozen": m["unique_anchor_hits"] - len(frz_anchors),
        "new_anchors": new,
        "hidden_numbers": m["hidden_numbers"],
        "metrics": m,
    }


# ── main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    ensure_dynamic_profiles()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    frozen_spec = _load_frozen_spec()
    print(f"Frozen spec: {frozen_spec.spec_id}")

    print("Loading row caches...", flush=True)
    rows_100 = build_or_load_rows(100_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_150 = build_or_load_rows(150_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_200 = build_or_load_rows(200_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_250 = build_or_load_rows(250_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_300 = build_or_load_rows(300_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_350 = build_or_load_rows(350_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)

    range_a = fresh_rows(rows_100, rows_150)
    range_b = fresh_rows(rows_150, rows_200)
    range_c = fresh_rows(rows_200, rows_250)
    range_d = fresh_rows(rows_250, rows_300)
    range_e = fresh_rows(rows_300, rows_350)
    print(f"range_a={len(range_a)}  range_b={len(range_b)}  range_c={len(range_c)}  range_d={len(range_d)}  range_e={len(range_e)}")

    ref_a = frozen_ref(range_a, frozen_spec)
    ref_b = frozen_ref(range_b, frozen_spec)
    ref_c = frozen_ref(range_c, frozen_spec)
    ref_d = frozen_ref(range_d, frozen_spec)
    ref_e = frozen_ref(range_e, frozen_spec)
    print(f"Frozen gate:  A={ref_a[0]}/{ref_a[1]}  B={ref_b[0]}/{ref_b[1]}  C={ref_c[0]}/{ref_c[1]}  D={ref_d[0]}/{ref_d[1]}  E={ref_e[0]}/{ref_e[1]}")

    gate_v1_b, gate_v1_c = _load_gate_v1_ref()
    if gate_v1_b is not None:
        print(f"gate_v1 ref:  B={gate_v1_b}/{ref_b[1]}  C={gate_v1_c}/{ref_c[1]}")

    # Fit/holdout split (same as bench oracle)
    fit_a, holdout_a = split_ordered_rows(range_a, FIT_FRACTION)
    print(f"fit_a={len(fit_a)}  holdout_a={len(holdout_a)}")

    # Frozen scores + z-norm (fit-set stats for scaling)
    frz_fit = score_frozen(fit_a, frozen_spec)
    frz_a = score_frozen(range_a, frozen_spec)
    frz_b = score_frozen(range_b, frozen_spec)
    frz_c = score_frozen(range_c, frozen_spec)
    frz_d = score_frozen(range_d, frozen_spec)
    frz_mean, frz_scale = fit_score_normalizer(frz_fit)
    frz_a_z = z_norm_with_fit_stats(frz_a, frz_mean, frz_scale)
    frz_b_z = z_norm_with_fit_stats(frz_b, frz_mean, frz_scale)
    frz_c_z = z_norm_with_fit_stats(frz_c, frz_mean, frz_scale)
    frz_d_z = z_norm_with_fit_stats(frz_d, frz_mean, frz_scale)
    frz_e = score_frozen(range_e, frozen_spec)
    frz_e_z = z_norm_with_fit_stats(frz_e, frz_mean, frz_scale)

    # Frozen anchor sets for delta tracking
    sc_b_frz = score_dict(range_b, frz_b)
    sc_c_frz = score_dict(range_c, frz_c)
    sc_d_frz = score_dict(range_d, frz_d)
    sc_e_frz = score_dict(range_e, frz_e)
    m_b_frz = metrics_for_scores(range_b, sc_b_frz, TOP_N, unique_anchors_only=True)
    m_c_frz = metrics_for_scores(range_c, sc_c_frz, TOP_N, unique_anchors_only=True)
    m_d_frz = metrics_for_scores(range_d, sc_d_frz, TOP_N, unique_anchors_only=True)
    m_e_frz = metrics_for_scores(range_e, sc_e_frz, TOP_N, unique_anchors_only=True)
    b_frz_anchors = anchor_set_from_metrics(m_b_frz)
    c_frz_anchors = anchor_set_from_metrics(m_c_frz)
    d_frz_anchors = anchor_set_from_metrics(m_d_frz)
    e_frz_anchors = anchor_set_from_metrics(m_e_frz)

    # Feature matrices
    print("Computing feature matrices...", flush=True)
    x_fit = matrix(fit_a)
    y_fit = labels(fit_a)
    x_a = matrix(range_a)
    y_a = labels(range_a)
    x_b = matrix(range_b)
    x_c = matrix(range_c)
    x_d = matrix(range_d)
    x_e = matrix(range_e)

    # Frozen holdout z-scores (needed for holdout weight searches)
    frz_ho_z = z_norm_with_fit_stats(score_frozen(holdout_a, frozen_spec), frz_mean, frz_scale)

    # ── Approach 1: Centroid blend (trained on fit_a, matching bench protocol) ──
    print("\n[Centroid A] Training centroid on fit_a...", flush=True)
    cen_model_a = fit_centroid_ranker(x_fit, y_fit)
    cen_fit = linear_scores(cen_model_a, x_fit)
    cen_mean, cen_scale = fit_score_normalizer(cen_fit)
    cen_a_z = z_norm_with_fit_stats(linear_scores(cen_model_a, x_a), cen_mean, cen_scale)
    cen_b_z = z_norm_with_fit_stats(linear_scores(cen_model_a, x_b), cen_mean, cen_scale)
    cen_c_z = z_norm_with_fit_stats(linear_scores(cen_model_a, x_c), cen_mean, cen_scale)
    cen_d_z = z_norm_with_fit_stats(linear_scores(cen_model_a, x_d), cen_mean, cen_scale)
    cen_e_z = z_norm_with_fit_stats(linear_scores(cen_model_a, x_e), cen_mean, cen_scale)

    # Extended weight search: include w=0 (pure centroid) and negative w
    # (frozen used as adversarial reference: score = w*frz + (1-w)*cen, w<0
    #  means penalise rows the frozen gate already likes, surfacing cen-unique anchors)
    W_GRID_EXT = [-1.0, -0.7, -0.5, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    best_cen_h, w_cen_a = -1, 0.0
    for w in W_GRID_EXT:
        h = unique_hits(range_a, score_dict(range_a, blend2(frz_a_z, cen_a_z, w)))
        if h > best_cen_h:
            best_cen_h, w_cen_a = h, w

    # Always show w=0 (pure centroid) for reference
    r_cen_b_w0 = eval_blend("cen B w=0", range_b, frz_b_z, cen_b_z, 0.0, b_frz_anchors)
    r_cen_c_w0 = eval_blend("cen C w=0", range_c, frz_c_z, cen_c_z, 0.0, c_frz_anchors)
    r_cen_d_w0 = eval_blend("cen D w=0", range_d, frz_d_z, cen_d_z, 0.0, d_frz_anchors)
    print(f"  [w=0.0 pure centroid] B={r_cen_b_w0['unique_hits']}  C={r_cen_c_w0['unique_hits']}  D={r_cen_d_w0['unique_hits']}")

    r_cen_b = eval_blend("centroid_a B", range_b, frz_b_z, cen_b_z, w_cen_a, b_frz_anchors)
    r_cen_c = eval_blend("centroid_a C", range_c, frz_c_z, cen_c_z, w_cen_a, c_frz_anchors)
    r_cen_d = eval_blend("centroid_a D", range_d, frz_d_z, cen_d_z, w_cen_a, d_frz_anchors)
    print(f"  w_frozen={w_cen_a:.2f}  B={r_cen_b['unique_hits']}/{r_cen_b['unique_total']}  delta={r_cen_b['unique_hits']-ref_b[0]:+d}  new_B={r_cen_b['new_anchors']}")
    print(f"  C={r_cen_c['unique_hits']}/{r_cen_c['unique_total']}  delta={r_cen_c['unique_hits']-ref_c[0]:+d}  new_C={r_cen_c['new_anchors']}")
    print(f"  D={r_cen_d['unique_hits']}/{r_cen_d['unique_total']}  delta={r_cen_d['unique_hits']-ref_d[0]:+d}  new_D={r_cen_d['new_anchors']}")

    # ── Approach 1b: Soft-variance reference ranker ───────────────────────────
    # Variance as a soft reference, not a hard divisor.
    # w_j = Δμ_j / (1 + α·σ²_j): high-variance (noisy) features are gently
    # downweighted; low-variance features stay at their centroid weight (no amplification).
    # α=0 = pure centroid; α=1 = gentle damping; α→∞ → LDA.
    #
    # Weight fixed at w_cen_a (range_a-selected, now includes negative search).
    # Search only α on holdout_a so the two hyperparameters are decoupled.
    print(f"\n[Soft-var reference] Grid-searching α at fixed w={w_cen_a:.2f} on holdout_a...", flush=True)
    ALPHA_GRID = [0.0, 0.1, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 100.0, 300.0, 1000.0]
    FIXED_W = w_cen_a
    best_sv_hits, best_sv_alpha = -1, 0.0
    for alpha in ALPHA_GRID:
        sv_model = fit_soft_var_ranker(x_fit, y_fit, alpha)
        sv_fit_s = linear_scores(sv_model, x_fit)
        sv_mn, sv_sc = fit_score_normalizer(sv_fit_s)
        sv_ho_z = z_norm_with_fit_stats(linear_scores(sv_model, matrix(holdout_a)), sv_mn, sv_sc)
        h = unique_hits(holdout_a, score_dict(holdout_a, blend2(frz_ho_z, sv_ho_z, FIXED_W)))
        if h > best_sv_hits or (h == best_sv_hits and alpha < best_sv_alpha):
            best_sv_hits, best_sv_alpha = h, alpha

    best_sv_w = FIXED_W
    print(f"  Best: α={best_sv_alpha}  w_frozen={best_sv_w:.1f}  holdout={best_sv_hits}/111")

    sv_model_best = fit_soft_var_ranker(x_fit, y_fit, best_sv_alpha)
    sv_fit_s = linear_scores(sv_model_best, x_fit)
    sv_mn, sv_sc = fit_score_normalizer(sv_fit_s)
    sv_b_z = z_norm_with_fit_stats(linear_scores(sv_model_best, x_b), sv_mn, sv_sc)
    sv_c_z = z_norm_with_fit_stats(linear_scores(sv_model_best, x_c), sv_mn, sv_sc)
    sv_d_z = z_norm_with_fit_stats(linear_scores(sv_model_best, x_d), sv_mn, sv_sc)
    r_sv_b = eval_blend("soft_var B", range_b, frz_b_z, sv_b_z, best_sv_w, b_frz_anchors)
    r_sv_c = eval_blend("soft_var C", range_c, frz_c_z, sv_c_z, best_sv_w, c_frz_anchors)
    r_sv_d = eval_blend("soft_var D", range_d, frz_d_z, sv_d_z, best_sv_w, d_frz_anchors)
    print(f"  B={r_sv_b['unique_hits']}/{r_sv_b['unique_total']}  delta={r_sv_b['unique_hits']-ref_b[0]:+d}  new={r_sv_b['new_anchors']}")
    print(f"  C={r_sv_c['unique_hits']}/{r_sv_c['unique_total']}  delta={r_sv_c['unique_hits']-ref_c[0]:+d}  new={r_sv_c['new_anchors']}")
    print(f"  D={r_sv_d['unique_hits']}/{r_sv_d['unique_total']}  delta={r_sv_d['unique_hits']-ref_d[0]:+d}  new={r_sv_d['new_anchors']}")

    # ── Approach 1c: Dynamic blend (per-range weight search) ──────────────────
    # score = w_f * frz_z + w_a * |frz_z| + w_c * cen_z
    #
    # Three degrees of freedom per range — the optimal (w_f, w_a, w_c) changes
    # as we move from B→C→D, exposing how the frozen/centroid balance shifts
    # with the evolving prime-gap structure (this is the "dynamics over time").
    #
    # We search independently on each range: range_a for the transfer baseline,
    # then B/C/D each on themselves to show the in-range ceiling.
    print("\n[Dynamic blend] Per-range weight search (w_f, w_a, w_c)...", flush=True)

    # Transfer reference: weights found on range_a, applied to B
    wf_a, wa_a, wc_a, h_dyn_a = search_dynamic_weights(range_a, frz_a_z, cen_a_z)
    r_dyn_b_a = eval_preblend(range_b, dyn_blend(frz_b_z, cen_b_z, wf_a, wa_a, wc_a), b_frz_anchors)
    print(f"  range_a optimal: w_f={wf_a:+.1f}  w_a={wa_a:.1f}  w_c={wc_a:.1f}  hits={h_dyn_a}")
    print(f"  [A-weights→B]   B={r_dyn_b_a['unique_hits']}  (transfer test)")

    # Per-range independent search — reveals dynamics
    wf_b, wa_b, wc_b, h_dyn_b = search_dynamic_weights(range_b, frz_b_z, cen_b_z)
    wf_c, wa_c, wc_c, h_dyn_c = search_dynamic_weights(range_c, frz_c_z, cen_c_z)
    wf_d, wa_d, wc_d, h_dyn_d = search_dynamic_weights(range_d, frz_d_z, cen_d_z)

    r_dyn_b = eval_preblend(range_b, dyn_blend(frz_b_z, cen_b_z, wf_b, wa_b, wc_b), b_frz_anchors)
    r_dyn_c = eval_preblend(range_c, dyn_blend(frz_c_z, cen_c_z, wf_c, wa_c, wc_c), c_frz_anchors)
    r_dyn_d = eval_preblend(range_d, dyn_blend(frz_d_z, cen_d_z, wf_d, wa_d, wc_d), d_frz_anchors)

    print(f"  [B-optimal]  B={r_dyn_b['unique_hits']}/{r_dyn_b['unique_total']}  wf={wf_b:+.1f}  wa={wa_b:.1f}  wc={wc_b:.1f}  delta={r_dyn_b['unique_hits']-ref_b[0]:+d}  new={r_dyn_b['new_anchors']}")
    print(f"  [C-optimal]  C={r_dyn_c['unique_hits']}/{r_dyn_c['unique_total']}  wf={wf_c:+.1f}  wa={wa_c:.1f}  wc={wc_c:.1f}  delta={r_dyn_c['unique_hits']-ref_c[0]:+d}  new={r_dyn_c['new_anchors']}")
    print(f"  [D-optimal]  D={r_dyn_d['unique_hits']}/{r_dyn_d['unique_total']}  wf={wf_d:+.1f}  wa={wa_d:.1f}  wc={wc_d:.1f}  delta={r_dyn_d['unique_hits']-ref_d[0]:+d}  new={r_dyn_d['new_anchors']}")
    print(f"  Dynamics A→B→C→D:  wf={wf_a:+.1f}/{wf_b:+.1f}/{wf_c:+.1f}/{wf_d:+.1f}  wa={wa_a:.1f}/{wa_b:.1f}/{wa_c:.1f}/{wa_d:.1f}  wc={wc_a:.1f}/{wc_b:.1f}/{wc_c:.1f}/{wc_d:.1f}")

    # ── Range E: D-regime transfer test ──────────────────────────────────────
    # D-regime: wf=+0.5, wa=2.0, wc=2.0 (frozen magnitude + positive frozen + centroid)
    # Does this transfer to E (300M-350M)?  Also run in-range E search for ceiling.
    print("\n[Range E] Transfer D-regime to 300M-350M...", flush=True)
    r_cen_e_05 = eval_blend("cen E w=0.5", range_e, frz_e_z, cen_e_z, 0.5, e_frz_anchors)
    r_dyn_e_d   = eval_preblend(range_e, dyn_blend(frz_e_z, cen_e_z, wf_d, wa_d, wc_d), e_frz_anchors)
    wf_e, wa_e, wc_e, h_dyn_e = search_dynamic_weights(range_e, frz_e_z, cen_e_z)
    r_dyn_e = eval_preblend(range_e, dyn_blend(frz_e_z, cen_e_z, wf_e, wa_e, wc_e), e_frz_anchors)

    print(f"  Frozen E:            E={ref_e[0]}/{ref_e[1]}")
    print(f"  [cen w=0.5 transfer] E={r_cen_e_05['unique_hits']}/{r_cen_e_05['unique_total']}  delta={r_cen_e_05['unique_hits']-ref_e[0]:+d}  new={r_cen_e_05['new_anchors']}")
    print(f"  [D-regime transfer]  E={r_dyn_e_d['unique_hits']}/{r_dyn_e_d['unique_total']}  wf={wf_d:+.1f} wa={wa_d:.1f} wc={wc_d:.1f}  delta={r_dyn_e_d['unique_hits']-ref_e[0]:+d}  new={r_dyn_e_d['new_anchors']}")
    print(f"  [E in-range optimal] E={r_dyn_e['unique_hits']}/{r_dyn_e['unique_total']}  wf={wf_e:+.1f} wa={wa_e:.1f} wc={wc_e:.1f}  delta={r_dyn_e['unique_hits']-ref_e[0]:+d}  new={r_dyn_e['new_anchors']}")
    print(f"  Dynamics B→C→D→E:  wf={wf_b:+.1f}/{wf_c:+.1f}/{wf_d:+.1f}/{wf_e:+.1f}  wa={wa_b:.1f}/{wa_c:.1f}/{wa_d:.1f}/{wa_e:.1f}  wc={wc_b:.1f}/{wc_c:.1f}/{wc_d:.1f}/{wc_e:.1f}")
    print(f"  D→E weight drift: Δwf={wf_e-wf_d:+.1f}  Δwa={wa_e-wa_d:+.1f}  Δwc={wc_e-wc_d:+.1f}")

    # ── Approach 2: Tree depth=2 blend (oracle protocol) ──────────────────────
    print("\n[Tree-d2 A] Training tree depth=2 on fit_a (oracle replication)...", flush=True)
    tree_d2 = fit_tree(x_fit, y_fit, list(range(len(x_fit))),
                       depth=0, max_depth=TREE_MAX_DEPTH, min_leaf=TREE_MIN_LEAF, bins=TREE_BINS)
    tree_fit = tree_scores(tree_d2, x_fit)
    t_mean, t_scale = fit_score_normalizer(tree_fit)
    tree_a_z = z_norm_with_fit_stats(tree_scores(tree_d2, x_a), t_mean, t_scale)
    tree_b_z = z_norm_with_fit_stats(tree_scores(tree_d2, x_b), t_mean, t_scale)
    tree_c_z = z_norm_with_fit_stats(tree_scores(tree_d2, x_c), t_mean, t_scale)
    tree_d_z = z_norm_with_fit_stats(tree_scores(tree_d2, x_d), t_mean, t_scale)

    # Holdout check (should match oracle bench: ~9/111 at w=0.5)
    tree_ho_z = z_norm_with_fit_stats(tree_scores(tree_d2, matrix(holdout_a)), t_mean, t_scale)
    sc_ho_05 = score_dict(holdout_a, blend2(frz_ho_z, tree_ho_z, 0.5))
    m_ho_05 = metrics_for_scores(holdout_a, sc_ho_05, TOP_N, unique_anchors_only=True)
    print(f"  Holdout_a (w=0.5): {m_ho_05['unique_anchor_hits']}/{m_ho_05['unique_anchors_total']}  (oracle bench reports 9/111)")

    # Weight search on full range_a (or holdout_a to mimic bench selection)
    w_tree_a, h_tree_a = search_weight(range_a, frz_a_z, tree_a_z)
    w_tree_ho, h_tree_ho = search_weight(holdout_a, frz_ho_z, tree_ho_z)
    print(f"  w_frozen search on A={w_tree_a:.1f}  on holdout={w_tree_ho:.1f}")

    # Evaluate at bench oracle weight (0.5) and search-best
    r_tree_b_05 = eval_blend("tree_d2 B w=0.5", range_b, frz_b_z, tree_b_z, 0.5, b_frz_anchors)
    r_tree_c_05 = eval_blend("tree_d2 C w=0.5", range_c, frz_c_z, tree_c_z, 0.5, c_frz_anchors)
    r_tree_d_05 = eval_blend("tree_d2 D w=0.5", range_d, frz_d_z, tree_d_z, 0.5, d_frz_anchors)
    r_tree_b_sw = eval_blend(f"tree_d2 B w={w_tree_a}", range_b, frz_b_z, tree_b_z, w_tree_a, b_frz_anchors)
    r_tree_c_sw = eval_blend(f"tree_d2 C w={w_tree_a}", range_c, frz_c_z, tree_c_z, w_tree_a, c_frz_anchors)
    r_tree_d_sw = eval_blend(f"tree_d2 D w={w_tree_a}", range_d, frz_d_z, tree_d_z, w_tree_a, d_frz_anchors)

    print(f"  [w=0.5] B={r_tree_b_05['unique_hits']}/{r_tree_b_05['unique_total']}  delta={r_tree_b_05['unique_hits']-ref_b[0]:+d}  new_B={r_tree_b_05['new_anchors']}")
    print(f"  [w=0.5] C={r_tree_c_05['unique_hits']}/{r_tree_c_05['unique_total']}  delta={r_tree_c_05['unique_hits']-ref_c[0]:+d}  new_C={r_tree_c_05['new_anchors']}")
    print(f"  [w=0.5] D={r_tree_d_05['unique_hits']}/{r_tree_d_05['unique_total']}  delta={r_tree_d_05['unique_hits']-ref_d[0]:+d}  new_D={r_tree_d_05['new_anchors']}")
    print(f"  [w={w_tree_a:.1f}] B={r_tree_b_sw['unique_hits']}/{r_tree_b_sw['unique_total']}  delta={r_tree_b_sw['unique_hits']-ref_b[0]:+d}")
    print(f"  [w={w_tree_a:.1f}] C={r_tree_c_sw['unique_hits']}/{r_tree_c_sw['unique_total']}  delta={r_tree_c_sw['unique_hits']-ref_c[0]:+d}")
    print(f"  [w={w_tree_a:.1f}] D={r_tree_d_sw['unique_hits']}/{r_tree_d_sw['unique_total']}  delta={r_tree_d_sw['unique_hits']-ref_d[0]:+d}")

    # ── Approach 2b: Tree depth=2 trained on A+B, evaluated on C ────────────
    print("\n[Tree-d2 AB] Training tree depth=2 on range_a + range_b...", flush=True)
    range_ab = range_a + range_b
    x_ab = matrix(range_ab)
    y_ab = labels(range_ab)
    tree_d2_ab = fit_tree(x_ab, y_ab, list(range(len(x_ab))),
                          depth=0, max_depth=TREE_MAX_DEPTH, min_leaf=TREE_MIN_LEAF, bins=TREE_BINS)
    tree_ab_fit_scores = tree_scores(tree_d2_ab, x_ab)
    tab_mean, tab_scale = fit_score_normalizer(tree_ab_fit_scores)
    tree_ab_c_z = z_norm_with_fit_stats(tree_scores(tree_d2_ab, x_c), tab_mean, tab_scale)

    # Frozen z-norm for blend: use frozen scores on range_ab as fit reference
    frz_ab_all = score_frozen(range_ab, frozen_spec)
    frz_ab_mean, frz_ab_scale = fit_score_normalizer(frz_ab_all)
    frz_ab_c_z = z_norm_with_fit_stats(frz_c, frz_ab_mean, frz_ab_scale)

    # Weight search: use range_b as proxy (A is training data, can't use it for selection)
    tree_ab_b_z = z_norm_with_fit_stats(tree_scores(tree_d2_ab, x_b), tab_mean, tab_scale)
    frz_ab_b_z = z_norm_with_fit_stats(frz_b, frz_ab_mean, frz_ab_scale)
    w_tab, _ = search_weight(range_b, frz_ab_b_z, tree_ab_b_z)
    r_tree_ab_b_sw = eval_blend(f"tree_d2_ab B w={w_tab}", range_b, frz_ab_b_z, tree_ab_b_z, w_tab, b_frz_anchors)
    r_tree_ab_b_05 = eval_blend("tree_d2_ab B w=0.5", range_b, frz_ab_b_z, tree_ab_b_z, 0.5, b_frz_anchors)
    r_tree_ab_c_sw = eval_blend(f"tree_d2_ab C w={w_tab}", range_c, frz_ab_c_z, tree_ab_c_z, w_tab, c_frz_anchors)
    r_tree_ab_c_05 = eval_blend("tree_d2_ab C w=0.5", range_c, frz_ab_c_z, tree_ab_c_z, 0.5, c_frz_anchors)
    print(f"  [w=0.5] B={r_tree_ab_b_05['unique_hits']}/{r_tree_ab_b_05['unique_total']}  delta={r_tree_ab_b_05['unique_hits']-ref_b[0]:+d}  new_B={r_tree_ab_b_05['new_anchors']}")
    print(f"  [w=0.5] C={r_tree_ab_c_05['unique_hits']}/{r_tree_ab_c_05['unique_total']}  delta={r_tree_ab_c_05['unique_hits']-ref_c[0]:+d}  new_C={r_tree_ab_c_05['new_anchors']}")
    print(f"  [w={w_tab:.1f}] B={r_tree_ab_b_sw['unique_hits']}/{r_tree_ab_b_sw['unique_total']}  delta={r_tree_ab_b_sw['unique_hits']-ref_b[0]:+d}")
    print(f"  [w={w_tab:.1f}] C={r_tree_ab_c_sw['unique_hits']}/{r_tree_ab_c_sw['unique_total']}  delta={r_tree_ab_c_sw['unique_hits']-ref_c[0]:+d}  new_C={r_tree_ab_c_sw['new_anchors']}")

    # ── Approach 2c: 3-way blend (frozen + tree_d2_a + centroid_a) ───────────
    # Motivation: tree_d2_a and centroid_a each find C=10 but cover DIFFERENT new anchors.
    # Their union spans 14 distinct new C primes — a 3-way blend may surface more than either alone.
    print("\n[3-way blend] Grid-searching frozen+tree+centroid weights on holdout_a...", flush=True)
    cen_ho_z = z_norm_with_fit_stats(linear_scores(cen_model_a, matrix(holdout_a)), cen_mean, cen_scale)

    best_3w_hits = -1
    best_3w = (0.5, 0.25, 0.25)
    STEPS = [round(i * 0.05, 2) for i in range(1, 16)]  # 0.05 to 0.75
    for wf in STEPS:
        for wt in STEPS:
            wc = round(1.0 - wf - wt, 2)
            if wc < 0.05 or wc > 0.70:
                continue
            blended = [wf * fz + wt * tz + wc * cz
                       for fz, tz, cz in zip(frz_ho_z, tree_ho_z, cen_ho_z)]
            h = unique_hits(holdout_a, score_dict(holdout_a, blended))
            if h > best_3w_hits or (h == best_3w_hits and wf > best_3w[0]):
                best_3w_hits = h
                best_3w = (wf, wt, wc)

    wf3, wt3, wc3 = best_3w
    print(f"  Best: frz={wf3:.2f} tree={wt3:.2f} cen={wc3:.2f} → holdout={best_3w_hits}/111")

    # Blind evaluation on B, C, D (reuse cen_*_z from centroid_a section)
    blend3_b = [wf3 * fz + wt3 * tz + wc3 * cz for fz, tz, cz in zip(frz_b_z, tree_b_z, cen_b_z)]
    blend3_c = [wf3 * fz + wt3 * tz + wc3 * cz for fz, tz, cz in zip(frz_c_z, tree_c_z, cen_c_z)]
    blend3_d = [wf3 * fz + wt3 * tz + wc3 * cz for fz, tz, cz in zip(frz_d_z, tree_d_z, cen_d_z)]
    r_3w_b = eval_preblend(range_b, blend3_b, b_frz_anchors)
    r_3w_c = eval_preblend(range_c, blend3_c, c_frz_anchors)
    r_3w_d = eval_preblend(range_d, blend3_d, d_frz_anchors)
    print(f"  B={r_3w_b['unique_hits']}/{r_3w_b['unique_total']}  delta={r_3w_b['unique_hits']-ref_b[0]:+d}  new={r_3w_b['new_anchors']}")
    print(f"  C={r_3w_c['unique_hits']}/{r_3w_c['unique_total']}  delta={r_3w_c['unique_hits']-ref_c[0]:+d}  new={r_3w_c['new_anchors']}")
    print(f"  D={r_3w_d['unique_hits']}/{r_3w_d['unique_total']}  delta={r_3w_d['unique_hits']-ref_d[0]:+d}  new={r_3w_d['new_anchors']}")

    # ── Approach 3: Centroid trained on A+B, evaluated on C ───────────────────
    print("\n[Centroid AB] Training centroid on range_a + range_b...", flush=True)
    # range_ab, x_ab, y_ab already defined above in Approach 2b
    cen_model_ab = fit_centroid_ranker(x_ab, y_ab)
    cen_ab_fit = linear_scores(cen_model_ab, matrix(range_a))  # use A as "fit" for norm
    cen_ab_mean, cen_ab_scale = fit_score_normalizer(cen_ab_fit)
    cen_ab_c_z = z_norm_with_fit_stats(linear_scores(cen_model_ab, x_c), cen_ab_mean, cen_ab_scale)
    frz_ab_mean, frz_ab_scale = frz_mean, frz_scale  # reuse A frozen norm stats

    w_cen_ab, _ = search_weight(range_a, frz_a_z,
                                z_norm_with_fit_stats(linear_scores(cen_model_ab, x_a), cen_ab_mean, cen_ab_scale))
    r_cen_ab_c = eval_blend("centroid_ab C", range_c, frz_c_z, cen_ab_c_z, w_cen_ab, c_frz_anchors)
    print(f"  w_frozen={w_cen_ab:.1f}  C={r_cen_ab_c['unique_hits']}/{r_cen_ab_c['unique_total']}  delta={r_cen_ab_c['unique_hits']-ref_c[0]:+d}  new_C={r_cen_ab_c['new_anchors']}")

    # ── Save helper (needed by both regime analysis and artifact blocks) ─────
    def save_artifact(name: str, obj: dict) -> Path:
        p = OUT_DIR / f"{name}.json"
        p.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
        return p

    # ── Regime analysis: which distribution moments distinguish D? ───────────
    # Goal: find a threshold rule on pre-anchor moments that predicts D-regime
    # (wa>0, wf>0) vs dominant-regime (wf<0, wa=0) without seeing anchor labels.
    print("\n[Regime analysis] Distribution moments per range...", flush=True)

    REGIME_KNOWN = {
        "A": ("dominant", wf_a, wa_a, wc_a),
        "B": ("dominant", wf_b, wa_b, wc_b),
        "C": ("dominant", wf_c, wa_c, wc_c),
        "D": ("magnitude", wf_d, wa_d, wc_d),
        "E": ("dominant", wf_e, wa_e, wc_e),
    }
    range_data = [
        ("A", frz_a_z, cen_a_z),
        ("B", frz_b_z, cen_b_z),
        ("C", frz_c_z, cen_c_z),
        ("D", frz_d_z, cen_d_z),
        ("E", frz_e_z, cen_e_z),
    ]

    regime_rows = []
    hdr = ["range", "regime", "frz.mean", "frz.std", "frz.skew", "frz.kurt",
           "frz.p90", "frz.frac_ext", "frz.mean_abs", "cen.std", "corr(f,c)"]
    print("  " + "  ".join(f"{h:>12}" for h in hdr))
    for label, fz, cz in range_data:
        regime, wf, wa, wc = REGIME_KNOWN[label]
        fm = dist_moments(fz)
        cm = dist_moments(cz)
        r = score_corr(fz, cz)
        row = {
            "range": label, "regime": regime,
            "frz_mean": round(fm["mean"], 4), "frz_std": round(fm["std"], 4),
            "frz_skew": round(fm["skew"], 4), "frz_kurt": round(fm["kurt"], 4),
            "frz_p90": round(fm["p90"], 4), "frz_frac_extreme": round(fm["frac_extreme"], 4),
            "frz_mean_abs": round(fm["mean_abs"], 4),
            "cen_std": round(cm["std"], 4), "corr_frz_cen": round(r, 4),
            "opt_wf": wf, "opt_wa": wa, "opt_wc": wc,
        }
        regime_rows.append(row)
        vals = [label, regime,
                f"{fm['mean']:+.3f}", f"{fm['std']:.3f}", f"{fm['skew']:+.3f}", f"{fm['kurt']:+.3f}",
                f"{fm['p90']:+.3f}", f"{fm['frac_extreme']:.3f}", f"{fm['mean_abs']:.3f}",
                f"{cm['std']:.3f}", f"{r:+.3f}"]
        print("  " + "  ".join(f"{v:>12}" for v in vals))

    # Flag which moments have D as outlier (outside [min,max] of others)
    moment_keys = ["frz_mean", "frz_std", "frz_skew", "frz_kurt",
                   "frz_p90", "frz_frac_extreme", "frz_mean_abs", "cen_std", "corr_frz_cen"]
    d_row = next(r for r in regime_rows if r["range"] == "D")
    others = [r for r in regime_rows if r["range"] != "D"]
    print("\n  D outlier moments (outside non-D range):")
    outliers = []
    for k in moment_keys:
        d_val = d_row[k]
        lo = min(r[k] for r in others)
        hi = max(r[k] for r in others)
        if d_val < lo or d_val > hi:
            direction = "HIGH" if d_val > hi else "LOW"
            margin = max(abs(d_val - hi), abs(d_val - lo))
            print(f"    {k:22s}  D={d_val:+.4f}  non-D=[{lo:+.4f},{hi:+.4f}]  {direction}  margin={margin:.4f}")
            outliers.append({"moment": k, "d_val": d_val, "non_d_lo": lo, "non_d_hi": hi,
                             "direction": direction, "margin": round(margin, 4)})
    if not outliers:
        print("    (none — D is not a clear outlier on any moment)")

    save_artifact("fill_ranker_regime_moments", {
        "schema": "regime_moments_v1",
        "description": "Pre-anchor distribution moments per range for regime classification",
        "ranges": regime_rows,
        "d_outlier_moments": outliers,
    })

    # ── Save artifacts ────────────────────────────────────────────────────────
    save_artifact("fill_ranker_dynamic", {
        "schema": "fill_ranker_dynamic_v1",
        "name": "dynamic_blend",
        "formula": "score = w_f * frz_z + w_a * |frz_z| + w_c * cen_z",
        "range_a_weights": {"w_f": wf_a, "w_a": wa_a, "w_c": wc_a, "hits": h_dyn_a},
        "range_b_weights": {"w_f": wf_b, "w_a": wa_b, "w_c": wc_b},
        "range_c_weights": {"w_f": wf_c, "w_a": wa_c, "w_c": wc_c},
        "range_d_weights": {"w_f": wf_d, "w_a": wa_d, "w_c": wc_d},
        "results": {
            "range_b_transfer": {"unique_hits": r_dyn_b_a["unique_hits"], "unique_total": r_dyn_b_a["unique_total"],
                                 "delta_frozen": r_dyn_b_a["unique_hits"] - ref_b[0], "new_anchors": r_dyn_b_a["new_anchors"]},
            "range_b_optimal": {"unique_hits": r_dyn_b["unique_hits"], "unique_total": r_dyn_b["unique_total"],
                                "delta_frozen": r_dyn_b["unique_hits"] - ref_b[0], "new_anchors": r_dyn_b["new_anchors"]},
            "range_c_optimal": {"unique_hits": r_dyn_c["unique_hits"], "unique_total": r_dyn_c["unique_total"],
                                "delta_frozen": r_dyn_c["unique_hits"] - ref_c[0], "new_anchors": r_dyn_c["new_anchors"]},
            "range_d_optimal": {"unique_hits": r_dyn_d["unique_hits"], "unique_total": r_dyn_d["unique_total"],
                                "delta_frozen": r_dyn_d["unique_hits"] - ref_d[0], "new_anchors": r_dyn_d["new_anchors"]},
        "range_e_transfer": {"unique_hits": r_dyn_e_d["unique_hits"], "unique_total": r_dyn_e_d["unique_total"],
                              "weights_from": "range_d", "delta_frozen": r_dyn_e_d["unique_hits"] - ref_e[0],
                              "new_anchors": r_dyn_e_d["new_anchors"]},
        "range_e_optimal": {"unique_hits": r_dyn_e["unique_hits"], "unique_total": r_dyn_e["unique_total"],
                             "w_f": wf_e, "w_a": wa_e, "w_c": wc_e,
                             "delta_frozen": r_dyn_e["unique_hits"] - ref_e[0], "new_anchors": r_dyn_e["new_anchors"]},
        "dynamics": {
            "B": {"w_f": wf_b, "w_a": wa_b, "w_c": wc_b},
            "C": {"w_f": wf_c, "w_a": wa_c, "w_c": wc_c},
            "D": {"w_f": wf_d, "w_a": wa_d, "w_c": wc_d},
            "E": {"w_f": wf_e, "w_a": wa_e, "w_c": wc_e},
        },
        },
    })

    save_artifact("fill_ranker_soft_var", {
        "schema": "fill_ranker_softvar_v1",
        "name": "soft_var_a",
        "alpha": best_sv_alpha,
        "blend_w_frozen": best_sv_w,
        "holdout_a_hits": best_sv_hits,
        "results": {
            "range_b_blind": {"unique_hits": r_sv_b["unique_hits"], "unique_total": r_sv_b["unique_total"],
                              "delta_frozen": r_sv_b["unique_hits"] - ref_b[0], "new_anchors": r_sv_b["new_anchors"]},
            "range_c_blind": {"unique_hits": r_sv_c["unique_hits"], "unique_total": r_sv_c["unique_total"],
                              "delta_frozen": r_sv_c["unique_hits"] - ref_c[0], "new_anchors": r_sv_c["new_anchors"]},
            "range_d_blind": {"unique_hits": r_sv_d["unique_hits"], "unique_total": r_sv_d["unique_total"],
                              "delta_frozen": r_sv_d["unique_hits"] - ref_d[0], "new_anchors": r_sv_d["new_anchors"]},
        },
    })

    save_artifact("fill_ranker_a", {
        "schema": "fill_ranker_v1",
        "name": "centroid_a",
        "feature_names": list(FEATURE_NAMES),
        "means": list(cen_model_a.means),
        "scales": list(cen_model_a.scales),
        "weights": list(cen_model_a.weights),
        "bias": cen_model_a.bias,
        "blend_w_frozen": w_cen_a,
        "top_features": top_feature_weights(cen_model_a, 15),
        "results": {
            "range_b_blind": {"unique_hits": r_cen_b["unique_hits"], "unique_total": r_cen_b["unique_total"],
                              "delta_frozen": r_cen_b["unique_hits"] - ref_b[0], "new_anchors": r_cen_b["new_anchors"]},
            "range_c_blind": {"unique_hits": r_cen_c["unique_hits"], "unique_total": r_cen_c["unique_total"],
                              "delta_frozen": r_cen_c["unique_hits"] - ref_c[0], "new_anchors": r_cen_c["new_anchors"]},
            "range_d_blind": {"unique_hits": r_cen_d["unique_hits"], "unique_total": r_cen_d["unique_total"],
                              "delta_frozen": r_cen_d["unique_hits"] - ref_d[0], "new_anchors": r_cen_d["new_anchors"]},
        },
    })

    save_artifact("fill_ranker_tree_d2", {
        "schema": "fill_ranker_tree_v1",
        "name": "tree_d2_a",
        "tree_max_depth": TREE_MAX_DEPTH,
        "tree_min_leaf": TREE_MIN_LEAF,
        "blend_w_frozen_05": 0.5,
        "blend_w_frozen_searched": w_tree_a,
        "holdout_a_w05": m_ho_05["unique_anchor_hits"],
        "results": {
            "range_b_w05": {"unique_hits": r_tree_b_05["unique_hits"], "unique_total": r_tree_b_05["unique_total"],
                            "delta_frozen": r_tree_b_05["unique_hits"] - ref_b[0], "new_anchors": r_tree_b_05["new_anchors"]},
            "range_c_w05": {"unique_hits": r_tree_c_05["unique_hits"], "unique_total": r_tree_c_05["unique_total"],
                            "delta_frozen": r_tree_c_05["unique_hits"] - ref_c[0], "new_anchors": r_tree_c_05["new_anchors"]},
            "range_b_wsearched": {"unique_hits": r_tree_b_sw["unique_hits"], "unique_total": r_tree_b_sw["unique_total"],
                                  "delta_frozen": r_tree_b_sw["unique_hits"] - ref_b[0], "new_anchors": r_tree_b_sw["new_anchors"]},
            "range_c_wsearched": {"unique_hits": r_tree_c_sw["unique_hits"], "unique_total": r_tree_c_sw["unique_total"],
                                  "delta_frozen": r_tree_c_sw["unique_hits"] - ref_c[0], "new_anchors": r_tree_c_sw["new_anchors"]},
        },
    })

    save_artifact("fill_ranker_tree_d2_ab", {
        "schema": "fill_ranker_tree_v1",
        "name": "tree_d2_ab",
        "tree_max_depth": TREE_MAX_DEPTH,
        "tree_min_leaf": TREE_MIN_LEAF,
        "training_ranges": ["range_a", "range_b"],
        "blend_w_frozen_05": 0.5,
        "blend_w_frozen_searched": w_tab,
        "results": {
            "range_b_w05": {"unique_hits": r_tree_ab_b_05["unique_hits"], "unique_total": r_tree_ab_b_05["unique_total"],
                            "delta_frozen": r_tree_ab_b_05["unique_hits"] - ref_b[0], "new_anchors": r_tree_ab_b_05["new_anchors"]},
            "range_c_w05": {"unique_hits": r_tree_ab_c_05["unique_hits"], "unique_total": r_tree_ab_c_05["unique_total"],
                            "delta_frozen": r_tree_ab_c_05["unique_hits"] - ref_c[0], "new_anchors": r_tree_ab_c_05["new_anchors"]},
            "range_b_wsearched": {"unique_hits": r_tree_ab_b_sw["unique_hits"], "unique_total": r_tree_ab_b_sw["unique_total"],
                                  "delta_frozen": r_tree_ab_b_sw["unique_hits"] - ref_b[0], "new_anchors": r_tree_ab_b_sw["new_anchors"]},
            "range_c_wsearched": {"unique_hits": r_tree_ab_c_sw["unique_hits"], "unique_total": r_tree_ab_c_sw["unique_total"],
                                  "delta_frozen": r_tree_ab_c_sw["unique_hits"] - ref_c[0], "new_anchors": r_tree_ab_c_sw["new_anchors"]},
        },
    })

    save_artifact("fill_ranker_ab", {
        "schema": "fill_ranker_v1",
        "name": "centroid_ab",
        "feature_names": list(FEATURE_NAMES),
        "means": list(cen_model_ab.means),
        "scales": list(cen_model_ab.scales),
        "weights": list(cen_model_ab.weights),
        "bias": cen_model_ab.bias,
        "blend_w_frozen": w_cen_ab,
        "top_features": top_feature_weights(cen_model_ab, 15),
        "results": {
            "range_c_blind": {"unique_hits": r_cen_ab_c["unique_hits"], "unique_total": r_cen_ab_c["unique_total"],
                              "delta_frozen": r_cen_ab_c["unique_hits"] - ref_c[0], "new_anchors": r_cen_ab_c["new_anchors"]},
        },
    })

    save_artifact("fill_ranker_3way", {
        "schema": "fill_ranker_3way_v1",
        "name": "3way_frz_tree_cen",
        "blend_weights": {"frozen": wf3, "tree_d2_a": wt3, "centroid_a": wc3},
        "holdout_a_hits": best_3w_hits,
        "results": {
            "range_b_blind": {"unique_hits": r_3w_b["unique_hits"], "unique_total": r_3w_b["unique_total"],
                              "delta_frozen": r_3w_b["unique_hits"] - ref_b[0], "new_anchors": r_3w_b["new_anchors"]},
            "range_c_blind": {"unique_hits": r_3w_c["unique_hits"], "unique_total": r_3w_c["unique_total"],
                              "delta_frozen": r_3w_c["unique_hits"] - ref_c[0], "new_anchors": r_3w_c["new_anchors"]},
            "range_d_blind": {"unique_hits": r_3w_d["unique_hits"], "unique_total": r_3w_d["unique_total"],
                              "delta_frozen": r_3w_d["unique_hits"] - ref_d[0], "new_anchors": r_3w_d["new_anchors"]},
        },
    })

    print(f"\nSaved artifacts to {OUT_DIR}/")

    # ── Markdown ─────────────────────────────────────────────────────────────
    gv1_b_str = f"{gate_v1_b}/{ref_b[1]}" if gate_v1_b is not None else "?"
    gv1_c_str = f"{gate_v1_c}/{ref_c[1]}" if gate_v1_c is not None else "?"

    oracle_bench_b = 16   # from bench LATEST.md (old 35-feature set)
    oracle_bench_c = "?"  # not yet known

    md: list[str] = [
        "# Fill Ranker Results",
        "",
        "Blend = w_frozen * frozen_z + (1-w_frozen) * ranker_z  (z-norm using fit set stats)",
        "",
        "## Summary",
        "",
        "| Gate | A | B (150M-200M) | C (200M-250M) | D (250M-300M) | E (300M-350M) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        f"| frozen_gate | {ref_a[0]}/{ref_a[1]} | {ref_b[0]}/{ref_b[1]} | {ref_c[0]}/{ref_c[1]} | {ref_d[0]}/{ref_d[1]} | {ref_e[0]}/{ref_e[1]} |",
        f"| gate_v1 (constrained blend) | 8/111* | {gv1_b_str} | {gv1_c_str} | — | — |",
        f"| centroid_a w=0.5 (balanced) | — | 12/227 | 12/256 | 12/220 | {r_cen_e_05['unique_hits']}/{r_cen_e_05['unique_total']} |",
        f"| centroid_a (w={w_cen_a:.1f}) | — | {r_cen_b['unique_hits']}/{r_cen_b['unique_total']} | {r_cen_c['unique_hits']}/{r_cen_c['unique_total']} | {r_cen_d['unique_hits']}/{r_cen_d['unique_total']} | — |",
        f"| soft_var_a α={best_sv_alpha} w={best_sv_w:.1f} | {best_sv_hits}/111* | {r_sv_b['unique_hits']}/{r_sv_b['unique_total']} | {r_sv_c['unique_hits']}/{r_sv_c['unique_total']} | {r_sv_d['unique_hits']}/{r_sv_d['unique_total']} | — |",
        f"| dynamic per-range optimal (in-sample) | — | {r_dyn_b['unique_hits']}/{r_dyn_b['unique_total']} | {r_dyn_c['unique_hits']}/{r_dyn_c['unique_total']} | {r_dyn_d['unique_hits']}/{r_dyn_d['unique_total']} | {r_dyn_e['unique_hits']}/{r_dyn_e['unique_total']} |",
        f"| D-regime→E transfer (wf={wf_d:+.1f} wa={wa_d:.1f} wc={wc_d:.1f}) | — | — | — | — | {r_dyn_e_d['unique_hits']}/{r_dyn_e_d['unique_total']} |",
        f"| tree_d2_a w=0.5 (oracle protocol) | {m_ho_05['unique_anchor_hits']}/111* | {r_tree_b_05['unique_hits']}/{r_tree_b_05['unique_total']} | {r_tree_c_05['unique_hits']}/{r_tree_c_05['unique_total']} | {r_tree_d_05['unique_hits']}/{r_tree_d_05['unique_total']} | — |",
        f"| tree_d2_a w={w_tree_a:.1f} (searched) | — | {r_tree_b_sw['unique_hits']}/{r_tree_b_sw['unique_total']} | {r_tree_c_sw['unique_hits']}/{r_tree_c_sw['unique_total']} | {r_tree_d_sw['unique_hits']}/{r_tree_d_sw['unique_total']} | — |",
        f"| 3way blend frz={wf3:.2f}/tree={wt3:.2f}/cen={wc3:.2f} | {best_3w_hits}/111* | {r_3w_b['unique_hits']}/{r_3w_b['unique_total']} | {r_3w_c['unique_hits']}/{r_3w_c['unique_total']} | {r_3w_d['unique_hits']}/{r_3w_d['unique_total']} | — |",
        f"| centroid_ab (w={w_cen_ab:.1f}, C only) | — | — | {r_cen_ab_c['unique_hits']}/{r_cen_ab_c['unique_total']} | — | — |",
        f"| tree_d2_ab w=0.5 (trained A+B) | — (training) | — (training) | {r_tree_ab_c_05['unique_hits']}/{r_tree_ab_c_05['unique_total']} | — | — |",
        f"| tree_d2_ab w={w_tab:.1f} (searched) | — | — | {r_tree_ab_c_sw['unique_hits']}/{r_tree_ab_c_sw['unique_total']} | — | — |",
        f"| oracle_blend_bench (old 35 feat) | 9/111* | 16/227 | ? | — | — |",
        "",
        "*A values are on holdout_a (last 40% of range_a)",
        "",
        "## New Anchors vs Frozen Gate",
        "",
        f"dynamic D-regime→E transfer — E new: `{r_dyn_e_d['new_anchors']}`",
        f"dynamic E-optimal — E new: `{r_dyn_e['new_anchors']}`",
        f"cen w=0.5→E — E new: `{r_cen_e_05['new_anchors']}`",
        f"dynamic B-opt — B new: `{r_dyn_b['new_anchors']}`",
        f"dynamic C-opt — C new: `{r_dyn_c['new_anchors']}`",
        f"dynamic D-opt — D new: `{r_dyn_d['new_anchors']}`",
        f"soft_var_a — B new: `{r_sv_b['new_anchors']}`",
        f"soft_var_a — C new: `{r_sv_c['new_anchors']}`",
        f"soft_var_a — D new: `{r_sv_d['new_anchors']}`",
        f"centroid_a — B new: `{r_cen_b['new_anchors']}`",
        f"centroid_a — C new: `{r_cen_c['new_anchors']}`",
        f"centroid_a — D new: `{r_cen_d['new_anchors']}`",
        f"tree_d2_a w=0.5 — B new: `{r_tree_b_05['new_anchors']}`",
        f"tree_d2_a w=0.5 — C new: `{r_tree_c_05['new_anchors']}`",
        f"centroid_ab — C new: `{r_cen_ab_c['new_anchors']}`",
        f"tree_d2_ab w=0.5 — C new: `{r_tree_ab_c_05['new_anchors']}`",
        f"tree_d2_ab w={w_tab:.1f} — C new: `{r_tree_ab_c_sw['new_anchors']}`",
        f"3way blend — B new: `{r_3w_b['new_anchors']}`",
        f"3way blend — C new: `{r_3w_c['new_anchors']}`",
        f"3way blend — D new: `{r_3w_d['new_anchors']}`",
        "",
        "## Top Feature Weights (Centroid A)",
        "",
        "| Feature | Weight |",
        "| --- | ---: |",
    ]
    for feat, w in top_feature_weights(cen_model_a, 15):
        md.append(f"| {feat} | {w:.4f} |")

    for label_str, m_r, new_set in [
        ("Centroid A on B", r_cen_b["metrics"], r_cen_b["new_anchors"]),
        ("Centroid A on C", r_cen_c["metrics"], r_cen_c["new_anchors"]),
        ("Tree-d2 on B (w=0.5)", r_tree_b_05["metrics"], r_tree_b_05["new_anchors"]),
        ("Tree-d2 on C (w=0.5)", r_tree_c_05["metrics"], r_tree_c_05["new_anchors"]),
        ("Centroid AB on C", r_cen_ab_c["metrics"], r_cen_ab_c["new_anchors"]),
    ]:
        md += ["", f"## Hidden Numbers — {label_str}", ""]
        md += [
            "| Rank | Anchor prime | Ratio | Lead | Score | New? |",
            "| ---: | ---: | ---: | ---: | ---: | --- |",
        ]
        for h in m_r["hidden_numbers"]:
            new_flag = "YES" if h["anchor_prime"] in new_set else ""
            md.append(f"| {h['rank']} | {h['anchor_prime']} | {h['anchor_ratio']} | {h['lead_steps']} | {h['score']} | {new_flag} |")

    md_path = OUT_DIR / "RESULTS.md"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Results: {md_path}")

    # ── Final print ───────────────────────────────────────────────────────────
    print("\n" + "=" * 76)
    print("FILL RANKER RESULTS  (blend = w_f*frozen_z + (1-w_f)*ranker_z)")
    print("=" * 76)
    print(f"{'Gate':<40}  {'A(hold)':>8}  {'B':>8}  {'C':>8}  {'D':>8}")
    print("-" * 84)
    print(f"  {'frozen_gate':<38}  {ref_a[0]}/{ref_a[1]:>3}  {ref_b[0]}/{ref_b[1]:>3}  {ref_c[0]}/{ref_c[1]:>3}  {ref_d[0]}/{ref_d[1]:>3}")
    if gate_v1_b is not None:
        print(f"  {'gate_v1 (constrained blend)':<38}  {'8/111*':>8}  {gate_v1_b}/{ref_b[1]:>3}  {gate_v1_c}/{ref_c[1]:>3}  {'—':>8}")
    print(f"  {'tree_d2_a w=0.5 (oracle protocol)':<38}  {m_ho_05['unique_anchor_hits']}/111*  {r_tree_b_05['unique_hits']}/{r_tree_b_05['unique_total']:>3}  {r_tree_c_05['unique_hits']}/{r_tree_c_05['unique_total']:>3}  {r_tree_d_05['unique_hits']}/{r_tree_d_05['unique_total']:>3}")
    print(f"  {f'tree_d2_a w={w_tree_a:.1f} (searched)':<38}  {'—':>8}  {r_tree_b_sw['unique_hits']}/{r_tree_b_sw['unique_total']:>3}  {r_tree_c_sw['unique_hits']}/{r_tree_c_sw['unique_total']:>3}  {r_tree_d_sw['unique_hits']}/{r_tree_d_sw['unique_total']:>3}")
    print(f"  {'oracle_blend_bench (old 35 feat)':<38}  {'9/111*':>8}  {'16/227':>8}  {'?':>8}  {'?':>8}")
    print()
    print(f"Key: tree_d2_a w=0.5  delta_frozen: B={r_tree_b_05['unique_hits']-ref_b[0]:+d}  C={r_tree_c_05['unique_hits']-ref_c[0]:+d}  D={r_tree_d_05['unique_hits']-ref_d[0]:+d}")
    print(f"     frozen_gate D={ref_d[0]}/{ref_d[1]}  new_D={r_tree_d_05['new_anchors']}")


if __name__ == "__main__":
    main()
