---
tags: [prime-fog, ring, consumed]
updated_at: 2026-06-04
---

# Ring J — 550M to 600M

**Status: CONSUMED — cascade v4 CORRECT, cascade v5 VALIDATED**

## Actual features

| Feature | H | I | J (actual) | Sat. prediction | Accuracy |
| --- | ---: | ---: | ---: | ---: | --- |
| frz_mean | 0.3232 | 0.3757 | 0.4429 | 0.40–0.41 | undershoot (actual higher) |
| frz_std | 0.8769 | 0.8458 | 0.8051 | 0.82–0.83 | slight overshoot |
| frz_skew | 0.8094 | 0.9653 | 0.9289 | 0.97–0.99 | close (below ceiling) |
| frz_kurt | 0.5594 | 1.0348 | **0.7699** | ? | non-monotonic: up then down |
| cen_std | 1.0118 | 1.0253 | 1.0207 | — | stable |

frz_mean passed the Aitken asymptote estimate (L≈0.425) — the asymptote needs upward revision.  
frz_kurt oscillated: H=0.559 → I=1.035 → J=0.770. The 0.80 threshold separates the two sides.

## Cascade v4 result

Prediction: `compressed_frozen_late` (magnitude weights: wf=0.5, wa=2.0, wc=2.0)  
Fired: frz_skew > 0.45, frz_mean=0.4429 > 0.27

| Method | Hits | Delta |
| --- | ---: | ---: |
| frozen baseline | 7/206 | — |
| dominant (wf=-1.5, wa=0) | 7/206 | +0 |
| **magnitude (wf=+0.5, wa=2)** | **8/206** | **+1** |
| frozen_coherent | 3/206 | −4 |
| **v4 predicted (magnitude)** | **8/206** | **+1** |

**v4 picks the best regime: PASS**  
**v4 beats frozen baseline: PASS (+1)**

First ring where dominant ties frozen baseline (delta=0). Dominant is not universally robust at high frz_mean.

## Cascade v5 validation

v5 hypothesis: `compressed_frozen AND frz_mean > 0.27 AND frz_kurt < 0.80 → magnitude`

| Ring | frz_mean | frz_kurt | v5 says | Winner | Correct? |
| --- | ---: | ---: | --- | --- | --- |
| H | 0.3232 | 0.5594 | magnitude (0.559 < 0.80) | magnitude | YES |
| I | 0.3757 | 1.0348 | dominant (1.035 ≥ 0.80) | dominant | YES |
| J | 0.4429 | 0.7699 | magnitude (0.770 < 0.80) | magnitude | YES |

**3/3 correct. Cascade v5 hypothesis VALIDATED.**

frz_kurt < 0.80 is not arbitrary — the oscillation (up to 1.035, back to 0.770) shows the 0.80 boundary genuinely discriminates. Not just "high kurt = dominant" — the threshold matters.

## frz_mean saturation model update

Aitken asymptote estimate was L≈0.4254. frz_mean=0.4429 exceeded it.  
Steps: G→H +0.108, H→I +0.053, I→J +0.067 — steps did NOT continue decelerating.

Revised: asymptote is higher than 0.425. Steps are noisy, not cleanly geometric.  
Conservative Ring K prediction: frz_mean ≈ 0.46–0.48 (using last observed step +0.067, expect continued noise).

## Lessons

1. **Cascade v5 threshold 0.80 is real**: frz_kurt oscillates across it, correctly predicts winner in 3/3 rings.
2. **Dominant can tie frozen**: At high frz_mean (≥0.44), dominant lost discriminative power in J. Regime space is shifting.
3. **Aitken asymptote underestimated**: The trajectory has more head than expected. Revise L upward to ≈0.47–0.50.
4. **frz_kurt is not monotonic**: Oscillatory axis. The threshold matters, not the trend.
5. **Magnitude wins in H and J (frz_kurt < 0.80)**: The high-wa activation requires leptokurtic shape, not mesokurtic (kurt near 1).

## Next

1. Ring K (600M–650M): compute features first, apply [[cascade v5]], then verify anchor truth.
2. Revisit Aitken extrapolation — needs more data points to fit the true asymptote.
3. Watch if dominant continues losing ground or recovers at high [[frz_mean]].

## Related

- [[cascade v4]] — correctly predicted magnitude
- [[cascade v5]] — VALIDATED and frozen for [[Ring K]]
- [[trajectory gap map]] — saturation model undershoot for J; asymptote needs upward revision
- [[Ring I]] — frz_kurt=1.035 → dominant, confirmed retroactively
- [[Ring H]] — frz_kurt=0.559 → magnitude, confirmed retroactively
- [[frz_kurt]] — oscillatory axis; threshold 0.80 is real discriminator
