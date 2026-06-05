---
tags: [prime-fog, failure, regime-break, g-board]
updated_at: 2026-06-04
---

# G break - frz_skew was not enough

[[Board G - 400M-450M]] broke [[cascade v2]].

## Facts

```text
frz_skew=0.7379
frz_mean=0.2152
frz_std=0.9241
```

Scores:

```text
frozen_gate:      10/214
dominant:         11/214
magnitude:         4/214
frozen coherent:   4/214
```

## Interpretation

G looked frozen-coherent by [[frz_skew]], but the distribution was already too shifted and compressed. Cooperative blending amplified the wrong part of frozen and killed diversity.

The winning controller on G was [[dominant]], because adversarial frozen suppressed the over-compressed frozen lane enough for [[centroid_a]] to add a different anchor.

## New Isolation

G creates the proposed [[compressed frozen]] class:

```text
frz_skew high
frz_mean high
frz_std compressed
```

