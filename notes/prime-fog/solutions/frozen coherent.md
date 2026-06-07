---
tags: [prime-fog, solution, controller, cooperative]
updated_at: 2026-06-04
---

# frozen coherent

Cooperative frozen plus centroid.

Weights:

```text
wf=+1.0, wa=0.0, wc=1.5
```

## Trigger In v2

```text
frz_skew > 0.4495
```

## Gravity

- Works on [[Board F - 350M-400M]].
- F score: 16/231, +5 over [[frozen_gate]].
- Breaks on [[Board G - 400M-450M]] because high [[frz_skew]] alone was not enough.
- Returns at [[Ring M]] and [[Ring N]] after the frozen_dominant spike turns.
- M score: 9/202, +5 over raw frozen.
- N score: 13/180, +3 over raw frozen.

## Related Variables

- [[frz_skew]]
- [[frz_mean]]
- [[frz_std]]
