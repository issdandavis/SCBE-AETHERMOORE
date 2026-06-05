---
tags: [prime-fog, variable, correlation, regime-axis]
updated_at: 2026-06-04
---

# corr_frz_cen

Correlation between [[frozen_gate]] scores and [[centroid_a]] scores at range level.

## What It Measures

Whether frozen and centroid are looking at the same rows or different rows.

Negative correlation can mean useful orthogonality, but it is not enough by itself. B, C, F, and G all have negative values, yet they do not want the same controller.

## Known Values

| Range | corr_frz_cen |
| --- | ---: |
| A | 0.0053 |
| B | -0.1880 |
| C | -0.2005 |
| D | -0.0037 |
| E | 0.0042 |
| F | -0.1905 |
| G | -0.2029 |

## Role

This variable helps identify lane separation, but must be combined with [[frz_mean]], [[frz_std]], and [[frz_skew]].

