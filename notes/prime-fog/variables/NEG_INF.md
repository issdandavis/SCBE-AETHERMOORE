---
tags: [prime-fog, variable, sentinel]
updated_at: 2026-06-04
---

# NEG_INF

Sentinel value used when a row should be excluded from scoring.

## Role

Distribution variables such as [[frz_skew]], [[frz_mean]], and [[frz_std]] must ignore sentinel rows. Otherwise the range-level moments become artifacts of exclusion rather than field shape.

