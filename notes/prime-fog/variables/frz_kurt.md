---
tags: [prime-fog, variable, distribution-shape]
updated_at: 2026-06-04
---

# frz_kurt

Kurtosis of the sentinel-filtered frozen-gate z-score distribution.

Use:

```text
high frz_kurt = heavier concentration/tails in the frozen score distribution
```

Ring I made this variable relevant:

```text
H: frz_mean=0.323, frz_kurt=0.559 -> magnitude wins
I: frz_mean=0.376, frz_kurt=1.035 -> dominant wins
J: frz_mean=0.443, frz_kurt=0.770 -> magnitude wins
```

Interpretation: [[frz_mean]] alone is not enough for late compressed-frozen routing. [[frz_kurt]] separates magnitude-style compression from dominant-style heavy-tail concentration.

Threshold:

```text
frz_kurt < 0.80  -> magnitude
frz_kurt >= 0.80 -> dominant
```

Validated in [[cascade v5]] on H/I/J.

Related:
- [[Ring I]]
- [[Ring J]]
- [[cascade v5]]
- [[compressed_frozen_late]]
