---
tags: [prime-fog, solution, frozen-dominant]
updated_at: 2026-06-04
---

# frozen_dominant

Regime introduced after [[Ring K]] and frozen into [[cascade v6]].

Condition from the Ring K note:

```text
frz_mean > 0.45
frz_skew > 1.0
```

Controller:

```text
pure frozen gate
wf=1.0, wa=0.0, wc=0.0
```

Validation: [[Ring K]] had `frz_mean=0.5062` and `frz_skew=1.0328`; raw
[[frozen gate]] won outright at 10/179 while every blend lost at least one
anchor.

Interpretation: the frozen score distribution becomes concentrated enough that
blending loses signal. The raw [[frozen gate]] top-20 is the best route.

Related:
- [[Ring K]]
- [[cascade v6]]
- [[frz_mean]]
- [[frz_skew]]
