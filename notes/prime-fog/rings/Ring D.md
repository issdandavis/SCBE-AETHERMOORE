---
tags: [ring, anomaly]
---

# Ring D — 250M to 300M

**Hidden anchors:** 220
**Status:** anomaly board — consumed
**Cache:** `artifacts/prime_fog_row_cache/field_rows_l250000000_w36_h12_a4p0.json`

## Anomaly signature

[[cen_std]] = 0.9591 — the only range below 0.97974. The centroid ranker's score distribution compresses: many rows score similarly. This is not noise; it's the strongest D-separator out of 74 range features (separability = 1.509).

## Best known controller

[[magnitude]] in-sample: 14/220 (+7 vs frozen 7/220)
Blend: [[wf]]=+0.5, [[wa]]=2.0, [[wc]]=2.0

## Key features

- [[cen_std]] = 0.9591 ← primary anomaly signal
- [[frz_skew]] = 0.3225 (normal)
- [[corr_frz_cen]] = -0.0037 (near-zero — frozen and centroid barely interact)
- [[wa]] = 2.0 is uniquely needed here: frozen's absolute magnitude is the signal

## Regime

[[magnitude]] — triggered by [[cen_std]] < 0.97974

## What D taught

The range around 250M-300M has a structural change: the centroid ranker loses discriminative spread. Whether this is a prime gap distribution shift, a feature distribution change, or something deeper in the 14-layer geometry is unknown. The [[wa]] insight is: when centroid can't discriminate well, use how *certain* the frozen gate is (even in the wrong direction) as a proxy.

## Related

- [[magnitude]] — the regime it defines
- [[cascade v2]] — step 1 catches D via cen_std
