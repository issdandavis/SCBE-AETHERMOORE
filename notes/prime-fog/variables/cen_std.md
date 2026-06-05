---
tags: [variable, centroid-distribution, regime-axis]
---

# cen_std

**Type:** range-level feature (centroid score distribution)
**Formula:** standard deviation of centroid ranker z-scores across all rows in range
**Units:** dimensionless (z-score scale)

## What it measures

How spread out the centroid ranker's scores are across the rows. When cen_std is low, the centroid scores compress — many rows look similar to the centroid, meaning the centroid signal has reduced discriminative range. This is the D-anomaly signature.

## Known values

| Range | cen_std | Regime |
| --- | ---: | --- |
| A | 1.0004 | [[dominant]] |
| B | 1.0278 | [[dominant]] |
| C | 1.0122 | [[dominant]] |
| **D** | **0.9591** | **[[magnitude]]** |
| E | 1.0108 | [[dominant]] |
| F | 1.0247 | [[frozen coherent]] |
| G | 1.0248 | [[compressed frozen]] |

## Role in cascade

**Step 1 of [[cascade v2]]:** `cen_std < 0.97974` → magnitude
- Threshold = midpoint between D (0.9591) and non-D floor (1.0004) = 0.97974
- Separability score: 1.509 (strongest D separator of all 74 range features)

## Linked solutions

- [[magnitude]] — primary trigger (cen_std < 0.97974)
- [[dominant]] — normal cen_std range (1.00–1.03)

## Source

`scripts/research/range_regime_classifier.py` → `build_range_features()` → `cm["std"]`
