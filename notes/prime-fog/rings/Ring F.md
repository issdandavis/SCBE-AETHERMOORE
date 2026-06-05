---
tags: [ring, consumed, frozen-coherent]
---

# Ring F — 350M to 400M

**Hidden anchors:** 231
**Status:** consumed retrodiction board
**Cache:** `artifacts/prime_fog_row_cache/field_rows_l400000000_w36_h12_a4p0.json` (135.1s, 10,216 rows)

## Regime breakthrough

[[frz_skew]] = 0.5135 — first range above the 0.4495 threshold. The frozen gate has sharp right-tail discrimination here. This is the defining instance of the [[frozen coherent]] regime.

## Best known controller

[[frozen coherent]]: 16/231 (+5 vs frozen 11/231)
Blend: [[wf]]=+1.0, [[wa]]=0.0, [[wc]]=1.5

## Key features

- [[frz_skew]] = 0.5135 ← frozen_coherent trigger
- [[cen_std]] = 1.0247 (normal — not D-anomaly)
- [[frz_mean]] = 0.0904 (normal — not compressed_frozen)
- [[frz_std]] = 1.0002 (normal)
- [[corr_frz_cen]] = -0.1905 (anti-correlated — additive coverage confirmed)

## Critical finding: frozen ∩ centroid overlap = ZERO

The 20 anchors frozen finds on F and the 20 anchors centroid finds on F have **zero overlap**. They find completely different rows. This makes the cooperative blend genuinely additive, not redundant.

## v1 failure vs v2 success

- Classifier v1 predicted **dominant** on F → 5/231 (−6 vs frozen)
- Classifier v2 predicts **frozen_coherent** on F → 16/231 (+5 vs frozen)
- Delta: +11 anchors from fixing the regime prediction

## Regime

[[frozen coherent]]

## Related

- [[cascade v2]] — step 2 catches F via frz_skew
- [[Ring G]] — the next ring, which looks similar but breaks cooperative blending
