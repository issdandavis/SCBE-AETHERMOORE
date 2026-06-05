"""Manifold navigator — embed rings A–L in feature space, project the next ring.

Motivation (Issac's framing): solutions are stars on a manifold. Each ring is a
point; the trajectory across rings is a path. Read the local tangent + curvature
to project where the next ring lands, then route the projected coordinates through
the committed cascade (v6) to predict its controller BEFORE building the cache.

This is the disk-cheap path: it uses only the already-built A–L row caches
(no 750M+ sieve), so it works when the build wall (disk pressure) blocks new rings.

A projection is NOT a blind anchor test — it predicts feature coordinates and the
v6 regime. The empirical anchor verification waits until the cache can be built.

Feature embedding (5D): frz_mean, frz_skew, frz_kurt, frz_std, cen_std.

Projection methods per feature:
  linear   : M = 2·L − K              (constant-velocity tangent)
  quad     : M = 3·L − 3·K + J        (constant-curvature, parabolic)
  saturate : Aitken Δ² fixed point on J/K/L (for features approaching asymptote)

Trajectory speed |L−K| gauges whether we are approaching a fixed point (speed→0,
phase settled) or still moving (regime still evolving).
"""
from __future__ import annotations
import json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.range_regime_classifier import (  # noqa: E402
    FROZEN_DOMINANT_FRZ_MEAN, FROZEN_DOMINANT_FRZ_SKEW,
    V6_REGIME_WEIGHTS,
    TOP_N, WINDOW, HISTORY, ANCHOR_THRESHOLD,
    build_range_features, z_norm, _load_frozen_spec, predict_regime_v6,
)
from scripts.research.run_prime_search_engine_bench import (  # noqa: E402
    DEFAULT_ROW_CACHE_DIR, build_or_load_rows, fit_centroid_ranker,
    fit_score_normalizer, fresh_rows, labels, linear_scores, matrix,
    score_frozen, split_ordered_rows,
)
from scripts.research.run_field_branch_gate_search import ensure_dynamic_profiles  # noqa: E402

CACHE_DIR = DEFAULT_ROW_CACHE_DIR
OUT_DIR = REPO_ROOT / "artifacts" / "manifold_navigator"
FIT_FRACTION = 0.60

EMBED_KEYS = ["frz_mean", "frz_skew", "frz_kurt", "frz_std", "cen_std"]

# Ring upper bounds (M): A=100-150 ... L=650-700. Project M=700-750.
RING_BOUNDS = [
    ("A", 100_000_000, 150_000_000), ("B", 150_000_000, 200_000_000),
    ("C", 200_000_000, 250_000_000), ("D", 250_000_000, 300_000_000),
    ("E", 300_000_000, 350_000_000), ("F", 350_000_000, 400_000_000),
    ("G", 400_000_000, 450_000_000), ("H", 450_000_000, 500_000_000),
    ("I", 500_000_000, 550_000_000), ("J", 550_000_000, 600_000_000),
    ("K", 600_000_000, 650_000_000), ("L", 650_000_000, 700_000_000),
]


def aitken(x0: float, x1: float, x2: float) -> float | None:
    """Aitken Δ² fixed-point estimate from three successive terms."""
    denom = (x2 - x1) - (x1 - x0)
    if abs(denom) < 1e-12:
        return None
    return x0 - (x1 - x0) ** 2 / denom


def main() -> None:
    ensure_dynamic_profiles()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frozen_spec = _load_frozen_spec()

    print("=" * 72)
    print("MANIFOLD NAVIGATOR — embed A–L, project Ring M (700M–750M)")
    print("=" * 72)

    # Load all caches once
    print("\nLoading 13 ring caches (A–L)...", flush=True)
    caches = {}
    for _, lo, hi in RING_BOUNDS:
        for b in (lo, hi):
            if b not in caches:
                caches[b] = build_or_load_rows(b, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)

    # A-fitted normalizers + centroid model (same protocol as ring scripts)
    range_a = fresh_rows(caches[100_000_000], caches[150_000_000])
    fit_a, _ = split_ordered_rows(range_a, FIT_FRACTION)
    frz_fit = score_frozen(fit_a, frozen_spec)
    frz_mn, frz_sc = fit_score_normalizer(frz_fit)
    x_fit = matrix(fit_a); y_fit = labels(fit_a)
    cen_model = fit_centroid_ranker(x_fit, y_fit)
    cen_fit_s = linear_scores(cen_model, x_fit)
    cen_mn, cen_sc = fit_score_normalizer(cen_fit_s)

    # Compute features for every ring A–L
    print("Computing features for rings A–L...", flush=True)
    ring_feats = {}
    for name, lo, hi in RING_BOUNDS:
        rng = fresh_rows(caches[lo], caches[hi])
        frz_z = z_norm(score_frozen(rng, frozen_spec), frz_mn, frz_sc)
        cen_z = z_norm(linear_scores(cen_model, matrix(rng)), cen_mn, cen_sc)
        ring_feats[name] = build_range_features(rng, frz_z, cen_z)

    # ── Embedding table ───────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("[FEATURE EMBEDDING]  rings A–L in 5D")
    print("=" * 72)
    hdr = "  " + "ring".ljust(5) + "".join(k.rjust(11) for k in EMBED_KEYS)
    print(hdr)
    for name, _, _ in RING_BOUNDS:
        f = ring_feats[name]
        print("  " + name.ljust(5) + "".join(f"{f[k]:>+11.4f}" for k in EMBED_KEYS))

    # ── Trajectory speed (concentration phase) ────────────────────────────────
    print("\n" + "=" * 72)
    print("[TRAJECTORY SPEED]  |ring_n − ring_{n-1}| in 5D (concentration phase)")
    print("=" * 72)
    names = [n for n, _, _ in RING_BOUNDS]
    for i in range(1, len(names)):
        a, b = ring_feats[names[i - 1]], ring_feats[names[i]]
        speed = sum((b[k] - a[k]) ** 2 for k in EMBED_KEYS) ** 0.5
        print(f"  {names[i-1]}→{names[i]}: speed={speed:.4f}")

    # ── Project Ring M ────────────────────────────────────────────────────────
    J, K, L = ring_feats["J"], ring_feats["K"], ring_feats["L"]
    print("\n" + "=" * 72)
    print("[PROJECTION]  Ring M coordinates from J/K/L")
    print("=" * 72)
    print(f"  {'feature':10s}  {'J':>9}  {'K':>9}  {'L':>9}  {'linear':>9}  {'quad':>9}  {'aitken':>9}")
    proj_linear, proj_quad, proj_blend = {}, {}, {}
    for k in EMBED_KEYS:
        j, kk, ll = J[k], K[k], L[k]
        lin = 2 * ll - kk
        quad = 3 * ll - 3 * kk + j
        ait = aitken(j, kk, ll)
        proj_linear[k] = lin
        proj_quad[k] = quad
        # Blended projection: if a clean Aitken fixed point exists between L and lin,
        # the feature is saturating → use Aitken; else use linear tangent.
        if ait is not None and min(ll, lin) - 0.05 <= ait <= max(ll, lin) + 0.05:
            proj_blend[k] = ait
        else:
            proj_blend[k] = lin
        ait_s = f"{ait:>9.4f}" if ait is not None else "     —   "
        print(f"  {k:10s}  {j:>9.4f}  {kk:>9.4f}  {ll:>9.4f}  {lin:>9.4f}  {quad:>9.4f}  {ait_s}")

    print(f"\n  Blended projection (saturate where Aitken fixed-point is local, else linear tangent):")
    for k in EMBED_KEYS:
        print(f"    {k:10s} = {proj_blend[k]:+.4f}")

    # ── Route projections through v6 ──────────────────────────────────────────
    print("\n" + "=" * 72)
    print("[V6 ROUTING OF PROJECTED M]")
    print("=" * 72)
    for label, proj in [("linear", proj_linear), ("quad", proj_quad), ("blended", proj_blend)]:
        regime, fired = predict_regime_v6(proj)
        wf, wa, wc = V6_REGIME_WEIGHTS[regime]
        fd = (proj["frz_mean"] > FROZEN_DOMINANT_FRZ_MEAN and proj["frz_skew"] > FROZEN_DOMINANT_FRZ_SKEW)
        print(f"  {label:8s}: frz_mean={proj['frz_mean']:.3f} frz_skew={proj['frz_skew']:.3f} "
              f"frz_kurt={proj['frz_kurt']:.3f} → {regime}  (frozen_dominant={fd})  w=({wf},{wa},{wc})")

    # Consensus
    regimes = {label: predict_regime_v6(proj)[0]
               for label, proj in [("linear", proj_linear), ("quad", proj_quad), ("blended", proj_blend)]}
    consensus = len(set(regimes.values())) == 1
    print(f"\n  Projection consensus: {'YES — all agree on ' + list(regimes.values())[0] if consensus else 'NO — ' + str(regimes)}")

    # ── Verdict ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("[NAVIGATOR VERDICT — Ring M prediction, to verify when disk frees]")
    print("=" * 72)
    blend_regime = regimes["blended"]
    print(f"  Projected regime (blended): {blend_regime}")
    print(f"  Projected frz_mean ≈ {proj_blend['frz_mean']:.3f}  "
          f"(saturation asymptote J/K/L Aitken; expect ~0.54–0.58)")
    print(f"  Projected frz_skew ≈ {proj_blend['frz_skew']:.3f}  (>1.0 ⟹ frozen_dominant active)")
    last_speed = sum((L[k] - K[k]) ** 2 for k in EMBED_KEYS) ** 0.5
    print(f"  Last trajectory speed (K→L): {last_speed:.4f}  "
          f"({'still moving — regime evolving' if last_speed > 0.1 else 'slowing — phase settling'})")
    if blend_regime == "frozen_dominant":
        print(f"  ⟹ Ring M should be frozen-dominant: raw frozen gate wins, blends lose.")
        print(f"    Falsifier: if frz_skew comes in < 1.0, the concentration phase has broken.")

    # ── Save ──────────────────────────────────────────────────────────────────
    artifact = {
        "schema": "manifold_navigator_v1",
        "date": "2026-06-04",
        "embed_keys": EMBED_KEYS,
        "ring_features": {n: {k: ring_feats[n][k] for k in EMBED_KEYS} for n, _, _ in RING_BOUNDS},
        "projection_M": {
            "linear": proj_linear, "quad": proj_quad, "blended": proj_blend,
            "regimes": regimes, "consensus": consensus,
            "blended_regime": blend_regime,
        },
        "last_speed_KL": last_speed,
        "note": "Projection only — no Ring M cache built (disk wall at 2GB free). "
                "Verify empirically when disk frees and 750M sieve can run.",
    }
    (OUT_DIR / "navigator.json").write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved: {OUT_DIR / 'navigator.json'}")


if __name__ == "__main__":
    main()
