---
tags: [prime-fog, cascade, validated, frozen]
updated_at: 2026-06-04
---

# cascade v5

Frozen rule after [[Ring J]].

```text
if cen_std < 0.97974:
    magnitude
elif frz_skew > 0.4495 and frz_mean > 0.27 and frz_std < 0.9621 and frz_kurt < 0.80:
    magnitude
elif frz_skew > 0.4495 and frz_mean > 0.27 and frz_std < 0.9621 and frz_kurt >= 0.80:
    dominant
elif frz_skew > 0.4495 and frz_mean > 0.15 and frz_std < 0.9621:
    dominant
elif frz_skew > 0.4495:
    frozen_coherent
else:
    dominant
```

Reason: [[Ring H]], [[Ring I]], and [[Ring J]] all crossed the late compressed-frozen threshold, but [[frz_kurt]] separated the winner.

## Validation

| Ring | frz_mean | frz_kurt | v5 says | Winner | Correct |
| --- | ---: | ---: | --- | --- | --- |
| H | 0.3232 | 0.5594 | magnitude | magnitude | yes |
| I | 0.3757 | 1.0348 | dominant | dominant | yes |
| J | 0.4429 | 0.7699 | magnitude | magnitude | yes |

Status: validated 3/3 on H/I/J and frozen for [[Ring K]] feature routing.

Boundary: do not tune with Ring K anchor truth. Compute Ring K features first, apply this cascade, then verify.

Artifact: `artifacts/range_regime_classifier/CASCADE_V5.md`

Related:
- [[cascade v4]]
- [[Ring I]]
- [[Ring J]]
- [[Ring K]]
- [[frz_kurt]]

