---
tags: [prime-fog, solution, compressed-frozen, late-phase]
updated_at: 2026-06-04
---

# compressed_frozen_late

Late compressed-frozen branch introduced by [[cascade v4]].

Rule:

```text
frz_skew > 0.4495
frz_mean > 0.27
frz_std < 0.9621
```

Initial [[cascade v4]] prescription: [[magnitude]] weights.

Ring I showed this branch is incomplete: [[cascade v4]] beat the [[frozen gate]] baseline but missed the actual dominant winner.

[[cascade v5]] splits it with [[frz_kurt]]:

```text
frz_kurt < 0.80  -> magnitude
frz_kurt >= 0.80 -> dominant
```

Validated on H/I/J and frozen for [[Ring K]].

Related:
- [[Ring I]]
- [[Ring J]]
- [[Ring K]]
- [[cascade v5]]
- [[compressed frozen]]
