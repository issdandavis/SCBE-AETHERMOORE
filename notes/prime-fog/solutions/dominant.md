---
tags: [prime-fog, solution, controller]
updated_at: 2026-06-04
---

# dominant

Controller family that suppresses frozen and lets centroid steer.

Canonical v2 default:

```text
wf=-1.5, wa=0.0, wc=1.0
```

## Gravity

- Default branch of [[cascade v2]].
- Works on [[Board G - 400M-450M]] where [[frozen coherent]] collapses.
- Pulls toward [[centroid_a]] and away from pure [[frozen_gate]] preservation.

## Known Scores

```text
G: 11/214, +1 vs frozen_gate
F: 5/231, -6 vs frozen_gate
```

