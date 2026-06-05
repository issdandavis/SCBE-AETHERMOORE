---
tags: [prime-fog, cascade, retrodiction]
updated_at: 2026-06-04
---

# cascade v2

The v2 controller cascade retrodicted A-F, then failed on G.

```text
if cen_std < 0.97974:
    magnitude
elif frz_skew > 0.4495:
    frozen coherent
else:
    dominant
```

## Pulls

- [[cen_std]] -> [[magnitude]] -> [[Board D - 250M-300M]]
- [[frz_skew]] -> [[frozen coherent]] -> [[Board F - 350M-400M]]
- default -> [[dominant]]

## Result

- A-F retrodiction: 6/6.
- F: [[frozen coherent]] reached 16/231, +5 over [[frozen_gate]].
- G: predicted [[frozen coherent]], but scored 4/214 against frozen 10/214 and [[dominant]] 11/214.

## Break

See [[G break - frz_skew was not enough]].

