---
tags: [prime-fog, ring, consumed]
updated_at: 2026-06-04
---

# Ring N — 750M to 800M

**Status: CONSUMED — v6 as-is failed again. M was not a one-board noise point.**

Ring N was run as the disambiguator after [[Ring M]]. No v7 exit was applied.
The test intentionally kept [[cascade v6]] unchanged.

## Result

v6 order-1 fired again:

```text
frz_mean = 0.62379 > 0.45
frz_skew = 1.07750 > 1.0
```

So v6 predicted [[frozen_dominant]] / raw [[frozen gate]].

Actual winner: [[frozen coherent]].

| Method | Hits |
| --- | ---: |
| frozen baseline / v6 committed | 10/180 |
| dominant | 9/180 |
| magnitude | 10/180 |
| **frozen_coherent** | **13/180** |

Frozen margin: **-3**.

## What This Resolves

M was not just noise. The post-L sequence is now:

| Ring | v6 trigger | Frozen | Frozen coherent | Winner |
| --- | --- | ---: | ---: | --- |
| K | fired | 10 | 9 | frozen |
| L | fired | 13 | 5 | frozen |
| M | fired | 4 | 9 | frozen_coherent |
| N | fired | 10 | 13 | frozen_coherent |

The v6 trigger remains true, but the controller conclusion is false after L.
The high-skew concentration phase appears to have turned into a cooperative
phase where adding centroid back recovers anchors.

## Feature Movement

| Feature | M | N |
| --- | ---: | ---: |
| frz_mean | 0.6060 | 0.6238 |
| frz_std | 0.7701 | 0.7283 |
| frz_skew | 1.1673 | 1.0775 |
| frz_kurt | 1.6152 | 1.2753 |
| cen_std | 1.0564 | 1.0688 |
| corr_frz_cen | -0.1590 | -0.2022 |
| frz_p90 | 1.6976 | 1.6262 |

Important correction: the first [[Ring M]] v7 hypothesis based on
`corr_frz_cen > -0.19` does **not** generalize to N. N moved back to `-0.2022`
and frozen_coherent still won.

The stronger candidate exit variable is now:

```text
frz_mean > ~0.57
```

or a turn signal:

```text
frz_skew falling while frz_mean remains high
frz_p90 falling while frz_mean remains high
```

This is still only two confirming rings (M/N). Do not commit v7 yet.

## Artifact

```text
artifacts/ring_n_cascade_v6/ring_n_results.json
```

## Related

- [[Ring M]]
- [[cascade v6]]
- [[cascade v7]]
- [[frozen_dominant overfit]]
- [[frozen coherent]]
- [[frz_mean]]
- [[frz_skew]]
