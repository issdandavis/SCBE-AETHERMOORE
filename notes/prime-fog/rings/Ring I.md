---
tags: [prime-fog, ring, consumed]
updated_at: 2026-06-04
---

# Ring I — 500M to 550M

**Status: CONSUMED — cascade v4 PARTIAL PASS**

## Actual features

| Feature | Predicted | Actual | Prediction accuracy |
| --- | ---: | ---: | --- |
| frz_skew | ≈0.983 | 0.9653 | close (+1.8%) |
| frz_mean | ≈0.442 | **0.3757** | overshot (−15%) |
| frz_std | ≈0.810 | 0.8458 | close (+4.4%) |
| frz_kurt | — | 1.0348 | not predicted |
| cen_std | ≈1.012 | 1.0253 | close (+1.3%) |

frz_skew, frz_std, cen_std were all accurate. frz_mean was right direction but overshot. The unseen variable: frz_kurt jumped from H=0.559 to I=1.035.

## Cascade v4 result

Prediction: `compressed_frozen_late` (magnitude weights: wf=0.5, wa=2.0, wc=2.0)  
Fired: frz_skew > 0.45, frz_mean=0.376 > 0.27

| Method | Hits | Delta |
| --- | ---: | ---: |
| frozen baseline | 6/204 | — |
| **dominant (wf=-1.5, wa=0)** | **11/204** | **+5** |
| magnitude (wf=+0.5, wa=2) | 8/204 | +2 |
| frozen_coherent | 9/204 | +3 |
| **v4 predicted (magnitude)** | **8/204** | **+2** |

**v4 beats frozen baseline: PASS (+2)**  
**v4 picks the best regime: FAIL (dominant wins at 11, not magnitude at 8)**

## Inverse-prime lane result

Protocol: score [[cascade v4]] first, then add [[inverse prime field]] as a ninth controller and compare only incremental anchors.

| Method | Unique anchors | New vs cascade v4 |
| --- | ---: | ---: |
| frozen baseline | 6/204 | 5 |
| cascade v4 | 8/204 | 0 |
| inverse-prime lane | 9/204 | 9 |
| cascade v4 OR inverse-prime | **17/204** | **9** |

IP top-20 found nine anchors cascade v4 missed:

`502890457, 504981319, 508554341, 517610881, 531287093, 531983927, 541747093, 547155109, 548532323`

This confirms the lane is not just retrodictive on A-G. On the first live test, IP is fully disjoint from cascade v4 at top-20 and doubles the verified coverage surface from 8 to 17 unique anchors.

Artifact: `artifacts/ring_i_cascade_v4_ip/RESULTS.md`

## The new discriminator: frz_kurt

H: frz_mean=0.323, frz_kurt=0.559 → magnitude wins  
I: frz_mean=0.376, frz_kurt=1.035 → dominant wins

Both passed frz_mean > 0.27 (v4's rule). But high frz_kurt (>0.8) in Ring I means heavier kurtosis — more central concentration in the frozen score distribution. When the frozen gate compresses into a high-kurtosis shape, the adversarial blend (wf=-1.5) is better at finding the tail, and dominant wins.

This is the cascade v5 hypothesis:
```
compressed_frozen AND frz_mean > 0.27 AND frz_kurt < 0.8 → magnitude
compressed_frozen AND frz_mean > 0.27 AND frz_kurt >= 0.8 → dominant (or new regime)
```

## Lessons

1. **Trajectory gap map**: frz_skew, frz_std, cen_std trend linearly (accurate). frz_mean trend r²=0.998 extrapolated too aggressively.
2. **Dominant is robust**: wins A, B, C, E, G, I — 6 of 9 rings.
3. **Magnitude is a specific anomaly**: only wins D and H. Not a simple frz_mean threshold.
4. **frz_kurt is a new axis**: H=0.559 (low) → magnitude; I=1.035 (high) → dominant. First sign this matters.
5. **Frozen baseline degrading**: only 6/204 in I vs 10/221 in H. The frozen gate is losing ground at higher frz_mean/kurt.

## Next

Build cascade v5: add frz_kurt < 0.80 as joint condition with frz_mean > 0.27 for the magnitude split.

## Related

- [[trajectory gap map]] — source of feature predictions
- [[cascade v4]] — correctly fired but chose wrong regime
- [[cascade v5]] — next: frz_kurt splits compressed_frozen_late further
- [[inverse prime field]] — ninth controller; adds 9 disjoint anchors on Ring I
- [[Ring H]] — frz_kurt=0.559 → magnitude (v4 retrodict correct)
- [[frz_mean]] — primary trend axis
- [[frz_kurt]] — newly identified discriminator
