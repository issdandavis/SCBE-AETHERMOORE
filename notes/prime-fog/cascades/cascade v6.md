---
tags: [prime-fog, cascade, frozen]
updated_at: 2026-06-04
---

# cascade v6

Frozen controller spec after [[Ring K]]. This rule uses Ring K as the postmortem
that introduced [[frozen_dominant]]; [[Ring L]] is the first unseen validation.

Adds [[frozen_dominant]]:

```text
if frz_mean > 0.45 and frz_skew > 1.0:
    frozen_dominant -> pure frozen gate
else:
    cascade v5
```

Status: **FROZEN BEFORE RING L**.

Retrodiction:

| Ring | Predicted regime | Winner | Result |
| --- | --- | --- | --- |
| [[Ring H]] | compressed_frozen_late_low_kurt | magnitude | pass |
| [[Ring I]] | compressed_frozen_late_high_kurt | dominant | pass |
| [[Ring J]] | compressed_frozen_late_low_kurt | magnitude | pass |
| [[Ring K]] | frozen_dominant | frozen | pass |

Artifact: `artifacts/range_regime_classifier/cascade_v6_spec.json`

Related:
- [[cascade v5]]
- [[Ring K]]
- [[Ring L]]
- [[frozen_dominant]]
