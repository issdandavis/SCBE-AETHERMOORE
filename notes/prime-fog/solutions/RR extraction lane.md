---
tags: [prime-fog, solution, residue, representation, controller]
updated_at: 2026-06-04
---

# RR extraction lane

Residue / Representation lane prototype.

Initial implementation targets modular `sqrt(1)` boundaries:

```text
n == +1 mod p
n == -1 mod p
n^2 == 1 mod product(p_i)
```

The lane is implemented in:

```text
scripts/research/audit_prime_anchor_count_proxy.py
```

Score families:

- `rr_sqrt1_exact` — weighted count of small-prime `±1` residue hits
- `rr_sqrt1_near` — multiscale closeness to CRT `sqrt(1)` shells
- `rr_sqrt1` — exact / near blend

## K-N Backtest

RR-only best per ring:

| Ring | Best RR config | Clusters | Actual | Error | Precision | Recall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| K | rr_sqrt1_p0p85_r36 | 180 | 179 | +1 | 51.7% | 52.0% |
| L | rr_sqrt1_exact_p0p8_r36 | 177 | 178 | -1 | 50.8% | 50.6% |
| M | rr_sqrt1_near_p0p9_r24 | 212 | 202 | +10 | 55.2% | 57.9% |
| N | rr_sqrt1_near_p0p8_r36 | 180 | 180 | 0 | 50.0% | 50.0% |

Ring M breaks the old ~52% precision/recall ceiling, but the count error rises
to +10. So RR improves location on M but does not preserve the count law by
itself.

## Disjoint Yield

Compared against the best density-family config per ring:

| Ring | Density hits | RR hits | RR new anchors | Density lost | Union hits |
| --- | ---: | ---: | ---: | ---: | ---: |
| K | 89 | 93 | 37 | 33 | 126 |
| L | 93 | 90 | 33 | 36 | 126 |
| M | 98 | 117 | 53 | 34 | 151 |
| N | 88 | 90 | 37 | 35 | 125 |

This confirms RR is a real orthogonal locator lane. It does not merely reproduce
the frozen/centroid clusters. It reaches deep into the missed bucket.

## Interpretation

The prior density lanes solved volume but not coordinates:

```text
count error near 0
precision / recall near 50%
```

RR partially breaks the substitution lock:

```text
new true anchors from missed bucket: 33-53 per ring
```

But RR also creates its own substitutions. The next problem is routing:

```text
keep density count stability
replace density ghosts with RR true anchors
```

Do not claim RR is a prime-counting method. Claim: RR is an orthogonal residue
locator that can supply replacement anchors for the density proxy.

## Next

Build a replacement audit:

```text
density clusters at fixed count
rank low-confidence density clusters for eviction
rank RR clusters for insertion
measure precision delta while holding cluster count near actual
```

Then test whether the combined lane breaks 60% precision without worsening
count error.

## Replacement Audit Result

See [[replacement router audit]].

Non-oracle replacement did not break 60%:

| Ring | Best non-oracle precision |
| --- | ---: |
| K | 52.5% |
| L | 53.4% |
| M | 56.7% |
| N | 50.6% |

Oracle swap capacity did break 60% on M and nearly did on N:

| Ring | Oracle precision |
| --- | ---: |
| M | 62.2% |
| N | 58.9% |

So RR candidate availability is sufficient in some rings. The missing piece is
replacement confidence: identifying density ghosts and RR true-new anchors
without looking at the verifier.

## Related

- [[anchor count proxy]]
- [[frozen coherent]]
- [[frozen_dominant overfit]]
- [[Ring M]]
- [[Ring N]]
