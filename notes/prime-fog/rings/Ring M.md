---
tags: [prime-fog, ring, next, unseen, projected]
updated_at: 2026-06-04
---

# Ring M - 700M to 750M

**Status: UNSEEN - feature projection only**

Do not check anchors before feature-first routing.

## Manifold navigator projection

Source: [[manifold navigator]]

| Feature | Projection |
| --- | ---: |
| frz_mean | 0.5420 |
| frz_std | 0.7782 |
| frz_skew | 1.3073 |
| frz_kurt | 1.9563 |
| cen_std | 1.0367 |

Projected [[cascade v6]] regime:

```text
frozen_dominant
```

Reason:

```text
frz_mean > 0.45
frz_skew > 1.0
```

Expected controller: raw [[frozen gate]].

## Watch variables

- [[frz_skew]] - must stay above 1.0 for [[frozen_dominant]].
- [[frz_mean]] - projected near 0.542, close to the J/K/L Aitken limit.
- [[frz_std]] - projected lower, meaning concentration deepens.
- [[frz_kurt]] - projected high; do not revive the period-2 oscillation claim.
- raw frozen margin - the real benchmark question is whether the +8 L margin
  holds, grows, or starts to collapse.

## Cross-check + dynamics

A second navigator (finite-difference on J/K/L) independently projects
frz_mean≈0.546, frz_skew≈1.341 → **frozen_dominant**, agreeing with the PCA
projection above. Two different geometries, same regime → robust call.

But the trajectory is **accelerating**: K→L 5D speed = 0.596, the largest jump in
A–L. frz_mean saturates while frz_skew/frz_kurt run away. This is a **one-step**
projection only — M+1, M+2 would be unreliable. And watch for a near-future
breakdown: a runaway spike can eventually degenerate the frozen top-20.

## BLOCKED — empirical verification pending disk

The 700M–750M sieve is **OS-killed by the disk wall** (C: at 2 GB free / 100% used).
No traceback = out-of-memory/paging kill, not a code error. Ring M stays a projection
until disk headroom is freed. The committed prediction (frozen_dominant, frz_skew>1.0,
raw frozen wins) is recorded and falsifiable — verify when the build can run.

## Protocol

1. Free disk headroom (build wall) — then build/load the 750M row cache.
2. Compute features before reading anchor truth.
3. Apply frozen [[cascade v6]].
4. Verify anchors afterward using [[prime truth oracle]].

Related:
- [[Ring L]]
- [[cascade v6]]
- [[frozen_dominant]]
- [[manifold navigator]]
