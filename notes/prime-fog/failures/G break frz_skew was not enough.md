---
tags: [prime-fog, failure, cascade-break, lesson]
updated_at: 2026-06-04
---

# G break — frz_skew was not enough

[[cascade v2]] correctly identified G as "not dominant, not magnitude" via [[frz_skew]] > 0.4495 but prescribed [[frozen coherent]] weights that gave 4/214 (−6 vs frozen).

## The signal gap

frz_skew is a necessary but insufficient condition for frozen_coherent. Two ranges can have high frz_skew but very different frozen distributions:

| | [[frz_skew]] | [[frz_mean]] | [[frz_std]] | Best regime |
| --- | ---: | ---: | ---: | --- |
| F | 0.5135 | 0.0904 | 1.0002 | [[frozen coherent]] |
| G | 0.7379 | **0.2152** | **0.9241** | [[dominant]] |

G's frozen gate is in a compressed, shifted state. Cooperative blending amplifies that narrow state → diversity collapses → only 4 anchors.

## The lesson

A single-axis threshold on distribution shape is not enough. When the frozen distribution itself is in an anomalous state (not just skewed but *shifted and compressed*), cooperative blending fails. The regime needs to check *what kind* of high-skew it is.

## Proposed fix

[[cascade v3]]: add secondary frz_mean and frz_std conditions to split frozen_coherent from [[compressed frozen]].

## Related

- [[frz_mean]] — the missing axis
- [[frz_std]] — the missing axis
- [[cascade v3]] — proposed fix
- [[Ring H]] — validation board for the fix
