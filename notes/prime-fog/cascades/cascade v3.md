---
tags: [prime-fog, cascade, proposed, unvalidated]
updated_at: 2026-06-04
---

# cascade v3 — 4-regime, proposed

> ⚠️ Retrodictively defined from G. Not validated until [[Ring H]] is run blind.

## Rules

```python
if cen_std < 0.97974:
    regime = "magnitude"         # wf=+0.5, wa=2.0, wc=2.0
elif frz_skew > 0.4495 and frz_mean > 0.15 and frz_std < 0.95:
    regime = "compressed_frozen" # use dominant weights: wf=-1.5, wa=0.0, wc=1.0
elif frz_skew > 0.4495:
    regime = "frozen_coherent"   # wf=+1.0, wa=0.0, wc=1.5
else:
    regime = "dominant"          # wf=-1.5, wa=0.0, wc=1.0
```

## New branch

[[compressed frozen]] fires when all three conditions hold:
- [[frz_skew]] > 0.4495 — high discrimination peaks exist
- [[frz_mean]] > 0.15 — frozen distribution shifted high (G: 0.2152, others < 0.10)
- [[frz_std]] < 0.95 — frozen distribution compressed (G: 0.9241, others > 1.00)

Thresholds:
- frz_mean > 0.15 — midpoint G (0.2152) / F (0.0904) = 0.1528 ≈ 0.15
- frz_std < 0.95 — midpoint G (0.9241) / F (1.0002) = 0.9621 ≈ 0.95

## Retrodiction on A-G

| Ring | cen_std | frz_skew | frz_mean | frz_std | v3 pred | truth |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| A | 1.000 | 0.311 | 0.038 | 1.007 | dominant | dominant |
| B | 1.028 | 0.354 | 0.062 | 1.037 | dominant | dominant |
| C | 1.012 | 0.386 | 0.060 | 1.005 | dominant | dominant |
| D | 0.959 | — | — | — | magnitude | magnitude |
| E | 1.011 | 0.321 | 0.075 | 1.012 | dominant | dominant |
| F | 1.025 | 0.514 | 0.090 | 1.000 | frozen_coherent | frozen_coherent |
| G | 1.025 | 0.738 | 0.215 | 0.924 | compressed_frozen | TBD |

7/7 retrodiction if compressed_frozen is correct for G.

## Validation target

[[Ring H]]. If H features hit the compressed_frozen branch and dominant weights win → confirmed.

## Variables

- [[cen_std]] — step 1
- [[frz_skew]] — step 2 gate
- [[frz_mean]] — step 2 sub-split
- [[frz_std]] — step 2 sub-split
