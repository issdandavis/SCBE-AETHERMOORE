---
tags: [ring, calibration]
---

# Ring A — 100M to 150M

**Hidden anchors:** 235
**Status:** calibration / fit source
**Cache:** `artifacts/prime_fog_row_cache/field_rows_l100000000_w36_h12_a4p0.json`

## Role

Training ground. [[centroid_a]] is fitted on 60% of this ring (fit_a = 7,567 rows). The holdout 40% is used for validation during training. All other rings are measured as generalization from this one.

## Best known controller

In-sample ceiling: 14/235 ([[dominant]] w=0.5 weight search on fit_a)

## Key features

- [[frz_skew]] = 0.3111 (normal)
- [[cen_std]] = 1.0004 (normal)
- [[corr_frz_cen]] = +0.0053 (near-zero — frozen and centroid are independent here)

The near-zero correlation on A is interesting: centroid was trained here, so they've already factored each other out.

## Regime

[[dominant]]

## Related

- [[centroid_a]] — fitted here
- [[cascade v2]] — uses A as part of the "dominant" training set
