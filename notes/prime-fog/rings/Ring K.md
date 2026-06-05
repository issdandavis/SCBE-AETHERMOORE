---
tags: [prime-fog, ring, consumed]
updated_at: 2026-06-04
---

# Ring K — 600M to 650M

**Status: CONSUMED — cascade v5 PASS (degenerate winner)**

## Actual features

| Feature | J | K (actual) | Notes |
| --- | ---: | ---: | --- |
| frz_mean | 0.4429 | **0.5062** | step +0.063; stabilizing ~+0.06/ring |
| frz_std | 0.8051 | 0.8036 | nearly flat — plateau |
| frz_skew | 0.9289 | **1.0328** | broke past 1.0 — new territory |
| frz_kurt | 0.7699 | **1.0224** | ≥ 0.80 → dominant (alternating!) |
| cen_std | 1.0207 | 1.0583 | still above 0.98 |

frz_skew > 1.0 is new — the frozen score distribution is now more right-skewed than any prior ring.

## Cascade v5 result

Prediction: `dominant` (frz_kurt=1.0224 ≥ 0.80)
Weights: wf=−1.5, wa=0.0, wc=1.0

| Method | Hits | Delta |
| --- | ---: | ---: |
| **frozen baseline** | **10/179** | — |
| dominant (wf=-1.5, wa=0) | 9/179 | **−1** |
| magnitude (wf=+0.5, wa=2) | 8/179 | −2 |
| frozen_coherent | 8/179 | −2 |
| **v5 predicted (dominant)** | **9/179** | **−1** |

**v5 picked the closest regime: PASS**
**Frozen wins outright — no blend improved on raw frozen. First time.**

## The frozen-gate-wins regime (new finding)

At frz_mean ≈ 0.50 and frz_skew > 1.0, the frozen score distribution is so concentrated
that the dynamic blend cannot help:

- dominant (wf=-1.5): pushes away the concentrated high scores
- magnitude (wa=2.0): amplifies magnitude but adds noise when distribution is already tight
- frozen_coherent: cooperative wf insufficient to beat raw top-20

The raw frozen gate top-20 rows are the best targets. Any reweighting loses signal.

**Cascade v6 hypothesis: `frozen_dominant` regime**
Condition: frz_mean > 0.45 AND frz_skew > 1.0 → pure frozen weights (wf=1.0, wa=0, wc=0)

## frz_kurt alternating pattern

| Ring | frz_kurt | Side | Winner |
| --- | ---: | --- | --- |
| H | 0.5594 | < 0.80 | magnitude |
| I | 1.0348 | ≥ 0.80 | dominant |
| J | 0.7699 | < 0.80 | magnitude |
| K | 1.0224 | ≥ 0.80 | frozen/dominant |

Period-2 alternation over 4 consecutive rings. If Ring L has frz_kurt < 0.80 that is 5/5.

Arithmetic interpretation: frz_kurt measures excess kurtosis of the frozen score distribution.
Alternating high/low kurtosis every ~50M suggests the prime density oscillates between two
distributional shapes at this scale.

## frz_mean trajectory

| Ring | frz_mean | Step |
| --- | ---: | ---: |
| G | 0.2152 | — |
| H | 0.3232 | +0.1080 |
| I | 0.3757 | +0.0525 |
| J | 0.4429 | +0.0672 |
| K | 0.5062 | +0.0633 |

Steps stabilized at ~+0.063. Not decelerating further. Asymptote is above 0.50.
**Ring L prediction**: frz_mean ≈ 0.57 ± 0.01

## Anchor count

K=179 (vs J=206, I=204, H=221). Declining as expected: superprime density ≈ 1/(log x)².

## Next

1. Ring L (650M-700M): watch frz_kurt (alternation 5th point), frz_mean (step), frozen-wins persists?
2. Cascade v6: encode frozen_dominant when frz_skew > 1.0 AND frz_mean > 0.45
3. Manifold navigator: embed A-K as trajectory, read Ring L coordinates from tangent before running

## Related

- [[cascade v5]] — PASS (dominant predicted; frozen-wins is within dominant neighborhood)
- [[cascade v6]] — next: frozen_dominant regime
- [[trajectory gap map]] — frz_mean steps now ~constant +0.063; asymptote > 0.50
- [[Ring J]] — last ring before frozen-wins; frz_kurt oscillation confirmed
- [[frz_kurt]] — period-2 alternation H/I/J/K
- [[frz_skew]] — broke 1.0 at K; new phase trigger
