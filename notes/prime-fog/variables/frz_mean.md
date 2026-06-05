---
tags: [prime-fog, variable, frozen-distribution, regime-axis]
updated_at: 2026-06-04
---

# frz_mean

Mean of the frozen score distribution after sentinels are removed.

## What It Measures

Whether the whole frozen field is shifted upward or downward.

High [[frz_skew]] means the right tail is sharp. High frz_mean means the whole frozen distribution has moved, which can make cooperative blending dangerous.

## Known Values

| Range | frz_mean | Regime |
| --- | ---: | --- |
| A | 0.0380 | [[dominant]] |
| B | 0.0622 | [[dominant]] |
| C | 0.0599 | [[dominant]] |
| D | 0.0680 | [[magnitude]] |
| E | 0.0754 | [[dominant]] |
| F | 0.0904 | [[frozen coherent]] |
| G | 0.2152 | [[compressed frozen]] |

## Role

Proposed v3 split:

```text
frz_mean > 0.15
```

This separates [[Board G - 400M-450M]] from [[Board F - 350M-400M]].

