---
tags: [prime-fog, solution, manifold, navigator]
updated_at: 2026-06-04
---

# manifold navigator

Feature-only trajectory reader for the ring sequence. It does not score rows and
does not open the next ring's anchor truth.

Artifact:

```text
artifacts/prime_fog_manifold_navigator/latest_report.json
artifacts/prime_fog_manifold_navigator/RESULTS.md
```

## A-L embedding

Common dimensions:

```text
frz_mean
frz_std
frz_skew
frz_kurt
cen_std
```

PC1 explains 84.0% of the A-L variance:

| Feature | Loading |
| --- | ---: |
| frz_mean | +0.480 |
| frz_std | -0.474 |
| frz_skew | +0.481 |
| frz_kurt | +0.451 |
| cen_std | +0.331 |

Interpretation: PC1 is the frozen concentration axis. Moving forward on PC1
means frozen mean/skew/kurt rise while frozen standard deviation falls.

## Ring M readout

Projected [[Ring M]] features:

| Feature | Projection |
| --- | ---: |
| frz_mean | 0.5420 |
| frz_std | 0.7782 |
| frz_skew | 1.3073 |
| frz_kurt | 1.9563 |
| cen_std | 1.0367 |

Projected regime: [[frozen_dominant]].

Threshold margins:

| Threshold | Margin |
| --- | ---: |
| frz_mean - 0.45 | +0.0920 |
| frz_skew - 1.0 | +0.3073 |
| cen_std - 0.97974 | +0.0569 |

Readout: [[Ring M]] remains on the frozen-concentration path. The expected
controller is [[cascade v6]] order 1, which is raw [[frozen gate]].

## Cross-validation — two independent navigators agree

A second navigator (`scripts/research/manifold_navigator.py`,
`artifacts/manifold_navigator/navigator.json`) projects Ring M by **finite-difference
extrapolation** on J/K/L (linear 2L−K, quad 3L−3K+J, Aitken) instead of PCA. It
converges on the same regime:

| feature | PCA navigator | FD navigator (blended) | agree? |
| --- | ---: | ---: | --- |
| frz_mean | 0.542 | 0.546 | yes (~0.54) |
| frz_skew | 1.307 | 1.341 | yes (>1.0) |
| frz_kurt | 1.956 | 2.171 | loose (irrelevant to decision) |
| frz_std | 0.778 | 0.805 | close |
| regime | frozen_dominant | frozen_dominant | **YES** |

Two different projection geometries (PCA PC1 vs local finite-difference) landing on
the same regime with near-identical decision coordinates is a genuine robustness
signal — not one method's artifact.

**Robust vs not (both navigators):** frozen_dominant depends only on
`frz_mean > 0.45 AND frz_skew > 1.0`. Both are projected with comfortable margin.
frz_kurt is NOT reliably forecastable (FD methods scatter 0.57–2.49) but is irrelevant
to the order-1 decision, so the regime call survives.

## Dynamics — the trajectory is ACCELERATING, not settling

5D step speed |ring_n − ring_{n-1}|:

| step | speed |
| --- | ---: |
| A→B … D→E | 0.09–0.12 (calm) |
| E→F→G | 0.20, 0.27 (phase onset) |
| H→I | 0.504 |
| J→K | 0.283 |
| **K→L** | **0.596 (max of A–L)** |

K→L is the largest jump anywhere. The concentration phase is **speeding up**.
Decomposed: frz_mean saturates (steps +0.063, +0.024) while frz_skew/frz_kurt
accelerate. The distribution **keeps its center but grows an ever-sharper spike**.

Implications:
- One-step projection (M) is safe for the regime. **Two+ steps (M+1, M+2) are not** —
  the manifold is still curving hard.
- A runaway spike predicts a **near-future breakdown**: once the frozen distribution
  is sharp enough, the top-20 may degenerate (too few rows above the spike, or anchors
  hiding just under it). **Watch for the frozen margin to peak then fall.**

## VERIFIED — Ring M built, projection PARTIALLY falsified

Disk was freed (cache moved to F: via junction). Ring M built; actuals vs projection:

| feature | projected (PCA / FD) | actual M | verdict |
| --- | ---: | ---: | --- |
| frz_mean | 0.542 / 0.546 | **0.606** | WRONG — did not saturate, still climbing |
| frz_skew | 1.307 / 1.341 | 1.167 | right sign (>1.0), overshot |
| frz_kurt | 1.956 / 2.171 | 1.615 | WRONG — flattened, no runaway |
| regime | frozen_dominant | **frozen_coherent** | **WRONG — regime flipped** |

**Scorecard:**
- **Dynamics warning: CORRECT.** "Watch for the frozen margin to peak then fall" / "near-future
  breakdown" — margin went K +1 → L +8 → **M −5**. The navigator called the breakdown.
- **Regime + coordinate projection: WRONG.** Both navigators extrapolated the accelerating
  trajectory forward into continued frozen_dominant. The system was actually at a **turning point**:
  L→M speed collapsed to ~0.085 (from K→L's 0.596), frz_skew turned over, the cooperative regime
  returned. Extrapolating acceleration assumes no turning point — there was one.

**Operating lesson:** trust the navigator's qualitative dynamics flags (speed, "breakdown coming"),
NOT its quantitative one-step coordinates. A trajectory at maximum speed is often a trajectory about
to turn, not one about to continue. See [[Ring M]] for the full falsification.

Related:
- [[Ring L]]
- [[Ring M]]
- [[cascade v6]]
- [[frozen_dominant]]
- [[trajectory gap map]]
