---
tags: [prime-fog, variable, frozen-distribution, regime-axis]
updated_at: 2026-06-04
---

# frz_std

Standard deviation of the frozen score distribution after sentinels are removed.

## What It Measures

Whether frozen is broad enough to preserve diversity.

Compressed frozen can have a high tail but low spread. That makes cooperative blending brittle because too many rows collapse into the same narrow score pattern.

## Known Values

| Range | frz_std | Regime |
| --- | ---: | --- |
| A | 1.0065 | [[dominant]] |
| B | 1.0368 | [[dominant]] |
| C | 1.0051 | [[dominant]] |
| D | 1.0136 | [[magnitude]] |
| E | 1.0123 | [[dominant]] |
| F | 1.0002 | [[frozen coherent]] |
| G | 0.9241 | [[compressed frozen]] |

## Role

Proposed v3 split:

```text
frz_std < 0.95
```

This is the compression part of [[compressed frozen]].

