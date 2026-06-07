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
anchor. [[Ring L]] also passed strongly.

Falsification: [[Ring M]] and [[Ring N]] both satisfied the same trigger, but
[[frozen coherent]] won both. The original interpretation was too strong:
the frozen score distribution can become concentrated enough to fire the rule
while still needing centroid support to recover anchors.

Current status: not a stable controller rule. Treat as a local K/L behavior, not
a law.

Related:
- [[Ring K]]
- [[Ring L]]
- [[Ring M]]
- [[Ring N]]
- [[cascade v6]]
- [[frz_mean]]
- [[frz_skew]]
