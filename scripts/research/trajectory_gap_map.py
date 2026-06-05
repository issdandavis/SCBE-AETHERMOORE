"""Trajectory gap map for P(P(n)) prime fog regime classifier.

For each ring A-H, we have:
  - feature vector (frz_skew, frz_mean, frz_std, cen_std, corr_frz_cen)
  - classifier-prescribed weight vector (wf, wa, wc)
  - actual best-known weight vector (wf, wa, wc)

The gap vector = actual - prescribed, in (wf, wa, wc) space.
The "line of solutions" is a linear fit from features to weights using all known rings.
The residual from that fit at each ring = off-course error.
Extrapolating feature trajectory to I predicts where we need to be.

Outputs:
  artifacts/trajectory_gap_map/gap_map.json
  artifacts/trajectory_gap_map/REPORT.md
"""
from __future__ import annotations
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "artifacts" / "trajectory_gap_map"

# ── Known ring data ────────────────────────────────────────────────────────────
# Features from range_regime_classifier runs (sentinel-filtered).
# Weights: best known from blind tests and in-sample sweeps.
# pred_w: what cascade v3 prescribes (dominant=-1.5/0/1, magnitude=+0.5/2/2,
#         frozen_coherent=+1/0/1.5, compressed_frozen→dominant=-1.5/0/1)
# actual_w: empirically best weight vector seen in blind test or sweep.
# hits / total: under actual_w.

RINGS = {
    "A": dict(
        range="100M-150M",
        frz_skew=0.3111, frz_mean=0.0380, frz_std=1.0065,
        cen_std=1.0004, corr=-0.0053,
        pred_regime="dominant",   pred_w=(-1.5, 0.0, 1.0),
        actual_regime="dominant", actual_w=(-1.5, 0.0, 1.5),
        hits=14, total=235,
    ),
    "B": dict(
        range="150M-200M",
        frz_skew=0.3544, frz_mean=0.0622, frz_std=1.0368,
        cen_std=1.0278, corr=-0.1880,
        pred_regime="dominant",   pred_w=(-1.5, 0.0, 1.0),
        actual_regime="dominant", actual_w=(-1.0, 0.0, 2.0),
        hits=14, total=227,
    ),
    "C": dict(
        range="200M-250M",
        frz_skew=0.3855, frz_mean=0.0599, frz_std=1.0051,
        cen_std=1.0122, corr=-0.2005,
        pred_regime="dominant",   pred_w=(-1.5, 0.0, 1.0),
        actual_regime="dominant", actual_w=(-1.5, 0.0, 1.0),
        hits=15, total=256,
    ),
    "D": dict(
        range="250M-300M",
        frz_skew=0.3225, frz_mean=0.0680, frz_std=1.0136,
        cen_std=0.9591, corr=-0.0037,
        pred_regime="magnitude",   pred_w=(0.5, 2.0, 2.0),
        actual_regime="magnitude", actual_w=(0.5, 2.0, 2.0),
        hits=14, total=220,
    ),
    "E": dict(
        range="300M-350M",
        frz_skew=0.3211, frz_mean=0.0754, frz_std=1.0123,
        cen_std=1.0108, corr=0.0042,
        pred_regime="dominant",   pred_w=(-1.5, 0.0, 1.0),
        actual_regime="dominant", actual_w=(-1.5, 0.0, 1.0),
        hits=13, total=224,
    ),
    "F": dict(
        range="350M-400M",
        frz_skew=0.5135, frz_mean=0.0904, frz_std=1.0002,
        cen_std=1.0247, corr=-0.1905,
        pred_regime="frozen_coherent",   pred_w=(1.0, 0.0, 1.5),
        actual_regime="frozen_coherent", actual_w=(1.0, 0.0, 1.5),
        hits=16, total=231,
    ),
    "G": dict(
        range="400M-450M",
        frz_skew=0.7379, frz_mean=0.2152, frz_std=0.9241,
        cen_std=1.0248, corr=-0.2029,
        pred_regime="compressed_frozen", pred_w=(-1.5, 0.0, 1.0),  # v3 → dominant
        actual_regime="dominant",        actual_w=(-1.5, 0.0, 1.0),
        hits=11, total=214,
    ),
    "H": dict(
        range="450M-500M",
        frz_skew=0.8094, frz_mean=0.3232, frz_std=0.8769,
        cen_std=1.0118, corr=-0.2105,
        pred_regime="compressed_frozen", pred_w=(-1.5, 0.0, 1.0),  # v3 → dominant
        actual_regime="magnitude",       actual_w=(0.5, 2.0, 2.0),
        hits=11, total=221,
    ),
}

WEIGHT_LABELS = ["wf", "wa", "wc"]
FEAT_KEYS = ["frz_skew", "frz_mean", "frz_std", "cen_std", "corr"]


# ── Pure-Python linear algebra helpers ────────────────────────────────────────

def dot(a, b):
    return sum(x * y for x, y in zip(a, b))

def mat_mul(A, B):
    rows, cols = len(A), len(B[0])
    inner = len(B)
    return [[dot(A[r], [B[k][c] for k in range(inner)]) for c in range(cols)]
            for r in range(rows)]

def transpose(M):
    return [[M[r][c] for r in range(len(M))] for c in range(len(M[0]))]

def mat_vec(M, v):
    return [dot(row, v) for row in M]

def solve_2x2(A, b):
    """Solve 2x2 linear system Ax = b."""
    a00, a01 = A[0]; a10, a11 = A[1]
    det = a00 * a11 - a01 * a10
    if abs(det) < 1e-12:
        return [0.0, 0.0]
    return [(b[0] * a11 - b[1] * a01) / det,
            (a00 * b[1] - a10 * b[0]) / det]

def least_squares_1d(X, y):
    """Ordinary least squares: fit w such that Xw ≈ y.
    X is n×p, y is length n. Returns w (length p) via normal equations X^T X w = X^T y.
    Uses Gaussian elimination for general p.
    """
    n, p = len(X), len(X[0])
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(p)] for a in range(p)]
    Xty = [sum(X[i][a] * y[i] for i in range(n)) for a in range(p)]
    # Gaussian elimination with partial pivoting
    A = [row[:] + [Xty[r]] for r, row in enumerate(XtX)]
    for col in range(p):
        # pivot
        max_row = max(range(col, p), key=lambda r: abs(A[r][col]))
        A[col], A[max_row] = A[max_row], A[col]
        if abs(A[col][col]) < 1e-12:
            continue
        for row in range(col + 1, p):
            f = A[row][col] / A[col][col]
            for j in range(col, p + 1):
                A[row][j] -= f * A[col][j]
    # back substitution
    w = [0.0] * p
    for i in range(p - 1, -1, -1):
        if abs(A[i][i]) < 1e-12:
            continue
        w[i] = (A[i][p] - sum(A[i][j] * w[j] for j in range(i + 1, p))) / A[i][i]
    return w

def vec_sub(a, b):
    return [x - y for x, y in zip(a, b)]

def vec_norm(v):
    return math.sqrt(sum(x * x for x in v))

def vec_add(a, b):
    return [x + y for x, y in zip(a, b)]


# ── Feature trajectory extrapolation ──────────────────────────────────────────

def fit_linear_trend(ring_seq, key):
    """Fit y = a*x + b where x is ring index. Returns (a, b, r2)."""
    xs = list(range(len(ring_seq)))
    ys = [RINGS[r][key] for r in ring_seq]
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-12:
        return 0.0, sy / n, 0.0
    a = (n * sxy - sx * sy) / denom
    b = (sy - a * sx) / n
    y_hat = [a * x + b for x in xs]
    ss_res = sum((y - yh) ** 2 for y, yh in zip(ys, y_hat))
    ss_tot = sum((y - sy / n) ** 2 for y in ys)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 1.0
    return a, b, r2


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ring_order = list(RINGS.keys())  # A-H

    # ── 1. Gap vectors ─────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("GAP VECTORS  (actual_w - pred_w, in wf/wa/wc space)")
    print("=" * 72)
    print(f"{'Ring':>5}  {'pred_regime':20}  {'actual_regime':20}  "
          f"{'gap_wf':>7}  {'gap_wa':>7}  {'gap_wc':>7}  {'|gap|':>7}  {'aligned':>8}")

    gap_data = {}
    for r in ring_order:
        d = RINGS[r]
        pw, aw = d["pred_w"], d["actual_w"]
        gap = vec_sub(aw, pw)
        norm = vec_norm(gap)
        aligned = norm < 0.05  # essentially zero gap
        gap_data[r] = {"gap": gap, "norm": norm, "aligned": aligned}
        print(f"  {r:>3}  {d['pred_regime']:20}  {d['actual_regime']:20}  "
              f"{gap[0]:+7.2f}  {gap[1]:+7.2f}  {gap[2]:+7.2f}  {norm:7.3f}  "
              f"{'YES' if aligned else 'NO':>8}")

    # ── 2. Feature trajectory (focus on the 3 trending axes: F→H) ─────────────
    print("\n" + "=" * 72)
    print("FEATURE TRAJECTORY  A→H  (with linear trend fit on F/G/H)")
    print("=" * 72)

    trending = ["frz_skew", "frz_mean", "frz_std"]
    trend_fits = {}
    fgh = ["F", "G", "H"]

    for key in trending:
        a, b, r2 = fit_linear_trend(fgh, key)
        trend_fits[key] = {"slope": a, "intercept": b, "r2": r2}
        vals = [f"{RINGS[r][key]:+.4f}" for r in ring_order]
        print(f"  {key:12s}  " + "  ".join(f"{v:>8}" for v in vals)
              + f"  slope={a:+.4f}  r²={r2:.3f}")

    # Extrapolate to I (index 3 in F/G/H sequence = next step)
    print("\n  Extrapolated features for I (500M-550M):")
    i_feats = {}
    for key in trending:
        tf = trend_fits[key]
        # F=0, G=1, H=2, I=3 in the local index
        predicted = tf["slope"] * 3 + tf["intercept"]
        i_feats[key] = predicted
        print(f"    {key:12s}  predicted={predicted:+.4f}  "
              f"(slope/step={tf['slope']:+.4f}, r²={tf['r2']:.3f})")
    # non-trending features: use H value as flat extrapolation
    for key in FEAT_KEYS:
        if key not in i_feats:
            i_feats[key] = RINGS["H"][key]
    print(f"    cen_std (flat): {i_feats['cen_std']:+.4f}")
    print(f"    corr    (flat): {i_feats['corr']:+.4f}")

    # ── 3. Linear regression: features → weights ──────────────────────────────
    print("\n" + "=" * 72)
    print("LINEAR FIT: features → weights  (trained on A-H)")
    print("=" * 72)

    # Build design matrix: [1, frz_skew, frz_mean, frz_std, cen_std]
    # (drop corr — low variance, avoid overfitting with 8 points and 5 predictors)
    feat_cols = ["frz_skew", "frz_mean", "frz_std", "cen_std"]
    X = [[1.0] + [RINGS[r][k] for k in feat_cols] for r in ring_order]
    regressors = {}
    fitted_w = {r: [] for r in ring_order}

    for wi, wlabel in enumerate(WEIGHT_LABELS):
        y = [RINGS[r]["actual_w"][wi] for r in ring_order]
        coef = least_squares_1d(X, y)
        regressors[wlabel] = coef
        resid = [y[i] - dot(X[i], coef) for i in range(len(ring_order))]
        rmse = math.sqrt(sum(e * e for e in resid) / len(resid))
        print(f"  {wlabel}: intercept={coef[0]:+.3f}  "
              + "  ".join(f"{feat_cols[j]}={coef[j+1]:+.3f}" for j in range(len(feat_cols)))
              + f"  RMSE={rmse:.3f}")
        for i, r in enumerate(ring_order):
            fitted_w[r].append(dot(X[i], coef))

    # ── 4. Fitted vs actual vs prescribed ─────────────────────────────────────
    print("\n" + "=" * 72)
    print("SOLUTION LINE: prescribed / fitted / actual per ring")
    print("=" * 72)
    print(f"{'Ring':>5}  "
          f"{'pred_wf':>8} {'pred_wa':>8} {'pred_wc':>8}  "
          f"{'fit_wf':>8} {'fit_wa':>8} {'fit_wc':>8}  "
          f"{'act_wf':>8} {'act_wa':>8} {'act_wc':>8}  "
          f"{'fit|gap|':>9}  {'pred|gap|':>9}")

    fit_gaps = {}
    for r in ring_order:
        d = RINGS[r]
        pw = list(d["pred_w"])
        aw = list(d["actual_w"])
        fw = fitted_w[r]
        pred_gap = vec_norm(vec_sub(aw, pw))
        fit_gap  = vec_norm(vec_sub(aw, fw))
        fit_gaps[r] = {"fit_w": fw, "fit_gap": fit_gap, "pred_gap": pred_gap}
        print(f"  {r:>3}  "
              f"{pw[0]:+8.2f} {pw[1]:+8.2f} {pw[2]:+8.2f}  "
              f"{fw[0]:+8.3f} {fw[1]:+8.3f} {fw[2]:+8.3f}  "
              f"{aw[0]:+8.2f} {aw[1]:+8.2f} {aw[2]:+8.2f}  "
              f"{fit_gap:9.3f}  {pred_gap:9.3f}")

    # ── 5. Predict ring I ──────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("PREDICTION: Ring I (500M-550M)")
    print("=" * 72)
    x_i = [1.0] + [i_feats[k] for k in feat_cols]
    pred_i_w = [dot(x_i, regressors[wl]) for wl in WEIGHT_LABELS]

    print(f"  Feature inputs:")
    for k in feat_cols:
        print(f"    {k:12s} = {i_feats[k]:+.4f}")

    print(f"\n  Fitted weight prediction for I:")
    for wl, wv in zip(WEIGHT_LABELS, pred_i_w):
        print(f"    {wl} = {wv:+.4f}")

    # Nearest known regime
    regime_templates = {
        "dominant":         (-1.5, 0.0, 1.0),
        "magnitude":        ( 0.5, 2.0, 2.0),
        "frozen_coherent":  ( 1.0, 0.0, 1.5),
        "compressed_frozen":(-1.5, 0.0, 1.0),  # same as dominant
    }
    nearest = min(regime_templates, key=lambda rk: vec_norm(
        vec_sub(list(regime_templates[rk]), pred_i_w)))
    nearest_gap = vec_norm(vec_sub(list(regime_templates[nearest]), pred_i_w))
    print(f"\n  Nearest discrete regime: {nearest}  (distance={nearest_gap:.3f})")
    print(f"  Recommended weights for I: wf={pred_i_w[0]:+.3f}, "
          f"wa={pred_i_w[1]:+.3f}, wc={pred_i_w[2]:+.3f}")

    # Cascade v3 prediction for I (from extrapolated features)
    from_cen_std = i_feats["cen_std"] < 0.97974
    from_skew    = i_feats["frz_skew"] > 0.4495
    from_mean    = i_feats["frz_mean"] > 0.15
    from_std     = i_feats["frz_std"]  < 0.9621
    if from_cen_std:
        v3_pred = "magnitude"
    elif from_skew and from_mean and from_std:
        v3_pred = "compressed_frozen"
    elif from_skew:
        v3_pred = "frozen_coherent"
    else:
        v3_pred = "dominant"
    v3_w = regime_templates[v3_pred]
    v3_gap = vec_norm(vec_sub(list(v3_w), pred_i_w))
    print(f"\n  Cascade v3 predicts: {v3_pred}  weights={v3_w}  "
          f"(gap from fitted line: {v3_gap:.3f})")

    gap_to_fill = vec_sub(pred_i_w, list(v3_w))
    print(f"  Gap vector (fitted_line - v3_prescription): "
          f"wf={gap_to_fill[0]:+.3f}  wa={gap_to_fill[1]:+.3f}  wc={gap_to_fill[2]:+.3f}")
    print(f"  |gap| = {vec_norm(gap_to_fill):.3f}  "
          f"(this is the error if we fly I with v3)")

    # ── 6. Gap trend: is the error growing? ───────────────────────────────────
    print("\n" + "=" * 72)
    print("GAP TREND: |pred_gap| per ring (is the classifier drifting off-course?)")
    print("=" * 72)
    for r in ring_order:
        bar_len = int(fit_gaps[r]["pred_gap"] * 10)
        bar = "█" * bar_len
        print(f"  {r}  pred|gap|={fit_gaps[r]['pred_gap']:.3f}  fit|gap|={fit_gaps[r]['fit_gap']:.3f}  {bar}")

    print(f"\n  Predicted I pred|gap| (v3 vs fitted line): {vec_norm(gap_to_fill):.3f}")

    # ── Save artifact ──────────────────────────────────────────────────────────
    artifact = {
        "rings": {r: {
            "features": {k: RINGS[r][k] for k in FEAT_KEYS},
            "pred_regime": RINGS[r]["pred_regime"],
            "pred_w": list(RINGS[r]["pred_w"]),
            "actual_regime": RINGS[r]["actual_regime"],
            "actual_w": list(RINGS[r]["actual_w"]),
            "gap_vector": gap_data[r]["gap"],
            "gap_norm": round(gap_data[r]["norm"], 4),
            "aligned": gap_data[r]["aligned"],
            "fitted_w": [round(x, 4) for x in fit_gaps[r]["fit_w"]],
            "fit_gap_norm": round(fit_gaps[r]["fit_gap"], 4),
            "hits": RINGS[r]["hits"],
            "total": RINGS[r]["total"],
        } for r in ring_order},
        "trend_fits": {k: {kk: round(v, 6) for kk, v in trend_fits[k].items()}
                       for k in trending},
        "regressors": {wl: [round(c, 6) for c in regressors[wl]]
                       for wl in WEIGHT_LABELS},
        "prediction_I": {
            "features": {k: round(i_feats[k], 4) for k in feat_cols},
            "fitted_w": {wl: round(wv, 4) for wl, wv in zip(WEIGHT_LABELS, pred_i_w)},
            "nearest_regime": nearest,
            "v3_regime": v3_pred,
            "v3_w": list(v3_w),
            "gap_to_fill": {wl: round(g, 4) for wl, g in zip(WEIGHT_LABELS, gap_to_fill)},
            "gap_norm": round(vec_norm(gap_to_fill), 4),
        },
    }
    art_path = OUT_DIR / "gap_map.json"
    art_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")

    # ── Markdown report ────────────────────────────────────────────────────────
    md = [
        "# Trajectory Gap Map",
        "",
        "**Date:** 2026-06-04  ",
        "**Rings:** A–H (known)  **Prediction target:** I = 500M–550M",
        "",
        "## Gap Vectors (actual_w − prescribed_w)",
        "",
        "| Ring | Range | Prescribed | Actual | gap_wf | gap_wa | gap_wc | \\|gap\\| | On-line |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for r in ring_order:
        d = RINGS[r]
        g = gap_data[r]
        pw = d["pred_w"]; aw = d["actual_w"]; gv = g["gap"]
        md.append(f"| {r} | {d['range']} | {d['pred_regime']} | {d['actual_regime']} "
                  f"| {gv[0]:+.2f} | {gv[1]:+.2f} | {gv[2]:+.2f} "
                  f"| {g['norm']:.3f} | {'✓' if g['aligned'] else '✗'} |")

    md += [
        "",
        "## Feature Trajectory (A→H, trend fit on F/G/H)",
        "",
        "| Feature | A | B | C | D | E | F | G | H | slope/step | r² |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key in trending:
        vals = " | ".join(f"{RINGS[r][key]:+.4f}" for r in ring_order)
        tf = trend_fits[key]
        md.append(f"| {key} | {vals} | {tf['slope']:+.4f} | {tf['r2']:.3f} |")

    md += [
        "",
        "## Solution Line: Prescribed / Fitted / Actual Weights",
        "",
        "| Ring | pred_wf | pred_wa | pred_wc | fit_wf | fit_wa | fit_wc | act_wf | act_wa | act_wc | fit\\|gap\\| | pred\\|gap\\| |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in ring_order:
        pw = RINGS[r]["pred_w"]; aw = RINGS[r]["actual_w"]; fw = fit_gaps[r]["fit_w"]
        md.append(f"| {r} | {pw[0]:+.2f} | {pw[1]:+.2f} | {pw[2]:+.2f} "
                  f"| {fw[0]:+.3f} | {fw[1]:+.3f} | {fw[2]:+.3f} "
                  f"| {aw[0]:+.2f} | {aw[1]:+.2f} | {aw[2]:+.2f} "
                  f"| {fit_gaps[r]['fit_gap']:.3f} | {fit_gaps[r]['pred_gap']:.3f} |")

    md += [
        "",
        "## Ring I Prediction (500M–550M)",
        "",
        "**Extrapolated features** (linear trend on F/G/H):",
        "",
        "| Feature | Extrapolated | Trend r² |",
        "| --- | ---: | ---: |",
    ]
    for key in feat_cols:
        if key in trend_fits:
            md.append(f"| {key} | {i_feats[key]:+.4f} | {trend_fits[key]['r2']:.3f} |")
        else:
            md.append(f"| {key} | {i_feats[key]:+.4f} | (flat) |")

    md += [
        "",
        f"**Fitted weight prediction:** wf={pred_i_w[0]:+.4f}, wa={pred_i_w[1]:+.4f}, wc={pred_i_w[2]:+.4f}",
        f"**Nearest discrete regime:** {nearest}",
        f"**Cascade v3 predicts:** {v3_pred}  weights={v3_w}",
        "",
        "**Gap vector (fitted_line − v3_prescription):**",
        "",
        f"```",
        f"wf gap: {gap_to_fill[0]:+.4f}",
        f"wa gap: {gap_to_fill[1]:+.4f}",
        f"wc gap: {gap_to_fill[2]:+.4f}",
        f"|gap|:  {vec_norm(gap_to_fill):.4f}",
        f"```",
        "",
        "This is the vector the cascade must close to stay on the solution line for I.",
        "",
        "## Gap Trend (is the classifier drifting off-course?)",
        "",
        "| Ring | pred\\|gap\\| | fit\\|gap\\| |",
        "| --- | ---: | ---: |",
    ]
    for r in ring_order:
        md.append(f"| {r} | {fit_gaps[r]['pred_gap']:.3f} | {fit_gaps[r]['fit_gap']:.3f} |")
    md.append(f"| I (predicted) | {vec_norm(gap_to_fill):.3f} | — |")

    md += [
        "",
        "## Artifacts",
        "",
        "- `artifacts/trajectory_gap_map/gap_map.json`",
    ]

    rpt_path = OUT_DIR / "REPORT.md"
    rpt_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\nSaved: {art_path}")
    print(f"Saved: {rpt_path}")


if __name__ == "__main__":
    main()
