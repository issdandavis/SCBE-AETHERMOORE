---
tags: [variable, frozen-distribution, regime-axis]
---

# frz_skew

**Type:** range-level feature (frozen score distribution)
**Formula:** skewness of frozen z-score distribution after removing [[NEG_INF]] sentinels
**Units:** dimensionless

## What it measures

Right-tail asymmetry of how the [[frozen_gate]] scores rows in a range. High frz_skew means a few rows score sharply above the mean — the gate has strong discrimination peaks. Low/normal skew means the gate scores more uniformly.

## Known values

| Range | frz_skew | Regime |
| --- | ---: | --- |
| A | 0.3111 | [[dominant]] |
| B | 0.3544 | [[dominant]] |
| C | 0.3855 | [[dominant]] |
| D | 0.3225 | [[magnitude]] |
| E | 0.3211 | [[dominant]] |
| **F** | **0.5135** | **[[frozen coherent]]** |
| **G** | **0.7379** | **[[compressed frozen]] (proposed)** |

## Role in cascade

**Step 2 of [[cascade v2]]:** `frz_skew > 0.4495` → frozen_coherent
- Threshold = midpoint between C max (0.3855) and F (0.5135) = 0.4495

**G break:** G fires step 2 but [[frozen coherent]] weights fail. G needs a secondary split using [[frz_mean]] and [[frz_std]].

## Linked solutions

- [[frozen coherent]] — primary trigger (frz_skew > 0.4495)
- [[compressed frozen]] — fires when frz_skew high AND [[frz_mean]] high AND [[frz_std]] compressed
- [[dominant]] — default when frz_skew is in normal range (< 0.4495)

## Source

`scripts/research/range_regime_classifier.py` → `build_range_features()` → `fm["skew"]`
