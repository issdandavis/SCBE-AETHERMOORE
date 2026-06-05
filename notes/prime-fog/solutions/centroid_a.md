---
tags: [prime-fog, solution, centroid, ranker]
updated_at: 2026-06-04
---

# centroid_a

Centroid ranker trained from A.

## Known Behavior

```text
B: 14/227
C: 12/256
D: 8/220
F pure centroid: 12/231
```

## Gravity

- Pulls toward [[dominant]].
- Helps when [[frozen_gate]] is weak or too narrow.
- Collides with training heterogeneity when retrained on ABC.

## Related Variables

- [[cen_std]]
- [[corr_frz_cen]]

