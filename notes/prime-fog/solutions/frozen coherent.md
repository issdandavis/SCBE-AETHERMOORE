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

## Related Variables

- [[frz_skew]]
- [[frz_mean]]
- [[frz_std]]

