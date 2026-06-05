---
tags: [prime-fog, ring, consumed, fail]
updated_at: 2026-06-04
---

# Ring H — 450M to 500M

**Status: CONSUMED — cascade v3 FAILED**

## Results

| Controller | Hits | Total | vs frozen |
| --- | ---: | ---: | --- |
| dominant (v3 prescription) | 8 | 221 | −2 |
| **D-anomaly / magnitude (winner)** | **11** | **221** | **+1** |
| frozen_coherent | 4 | 221 | −6 |

**Range features:**

| Feature | Value |
| --- | ---: |
| frz_skew | 0.8094 |
| frz_mean | 0.3232 |
| frz_std | 0.8769 |
| cen_std | 1.0118 |

## What cascade v3 predicted

`compressed_frozen` → dominant weights (wf=−1.5, wa=0, wc=1.0)

This was wrong. The frozen distribution had compressed far enough that the absolute magnitude signal (wa) needed to re-activate — same as [[magnitude]] (D), but arriving via a different feature path.

## Gap vector (off-course measure)

```
wf gap: +2.00   (needed +2.00 more than prescribed)
wa gap: +2.00   (needed +2.00 more — this was the critical miss)
wc gap: +1.00
|gap|:  3.000
```

The dominant error was in wa: cascade prescribed wa=0, actual winner needed wa=2.0.

## What the fitted solution line says

From [[trajectory gap map]] regression across all rings:

- frz_mean r²=0.998 (laser-straight trend)
- For H: fitted prediction wf=−0.13, wa=+1.76, wc=+1.76

The solution line was pointing toward magnitude territory. The cascade failed to follow it.

## Lesson

[[compressed frozen]] is not a single regime. It has two phases:

| Phase | frz_mean | Best weights |
| --- | ---: | --- |
| G (early compressed) | 0.22 | dominant (wa=0) |
| H (late compressed) | 0.32 | magnitude (wa=2) |

Split threshold: frz_mean ≈ 0.27 (midpoint G/H). When frz_mean crosses that line, wa must activate.

## Related

- [[cascade v3]] — controller being tested (failed)
- [[Ring G]] — the defining compressed_frozen instance (passed)
- [[trajectory gap map]] — the off-course tracking tool that explains the miss
- [[Ring I]] — next board; fitted line predicts wa≈2.5 will be needed
