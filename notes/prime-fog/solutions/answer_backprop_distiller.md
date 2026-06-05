---
tags: [prime-fog, solution, diagnostic, inverse-problem]
updated_at: 2026-06-04
---

# answer_backprop_distiller

Reverse known anchors into lane attribution.

This is the explicit inverse-problem tool:

```text
known anchor -> which visible lane explained it before verification?
```

## Fit Attribution

```text
frozen: 35
lambda: 47
graph: 18
cmpssz: 24
```

## Lesson

The lanes see real, separate rings. But proportional quotas lose too many [[frozen_gate]] hits. This is a diagnostic, not a net-positive controller yet.

## Related

- [[lambda_shadow_only]]
- [[graph_map_only]]
- [[CMPSSZ only]]
- [[frozen_gate]]

