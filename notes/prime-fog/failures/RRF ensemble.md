---
tags: [prime-fog, failure, lesson]
updated_at: 2026-06-04
---

# RRF ensemble

Reciprocal Rank Fusion of top-k scoring methods.

## Result

Did not improve over frozen or simple centroid blend. Methods chosen for the ensemble were too correlated with each other — they all scored the same rows highly, so the fusion just reinforced existing picks without adding coverage.

## Lesson

Ensemble value comes from orthogonality. [[answer backprop distiller]] showed that [[frozen gate]], [[centroid_a]], and [[lambda shadow]] find *different* anchors. But RRF as implemented didn't exploit orthogonality — it just averaged rankings, which converged on the same overlap.

## What would help

An ensemble that maximizes set coverage (e.g. greedy coverage selection across ranked lists) rather than rank averaging. This is the quota selector problem.

## Related

- [[corr_frz_cen]] — the orthogonality that RRF failed to exploit
- [[answer backprop distiller]] — confirmed which lanes own which anchors
