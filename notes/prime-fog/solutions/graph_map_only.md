---
tags: [prime-fog, solution, scout-lane, graph-map]
updated_at: 2026-06-04
---

# graph_map_only

Graph landmark / road-sign lane.

It treats local field events as a map of transitions and relationships instead of one scalar score.

## Known Behavior

```text
B: 7/227
```

This lane has low overlap with [[frozen_gate]] and [[lambda_shadow_only]], so it is useful for coverage even when routing is brittle.

## Related Variables

- [[graph_ramp_density]]

