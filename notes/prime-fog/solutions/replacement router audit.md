---
tags: [prime-fog, solution, router, replacement, audit]
updated_at: 2026-06-04
---

# replacement router audit

Tests whether [[RR extraction lane]] can replace low-confidence density clusters
while preserving the [[anchor count proxy]] volume budget.

Runner:

```text
scripts/research/audit_prime_anchor_replacement.py
```

Artifact:

```text
artifacts/prime_anchor_replacement/RESULTS.md
artifacts/prime_anchor_replacement/latest_report.json
```

## Protocol

1. Choose the best density-family cluster config for each ring.
2. Choose the best RR-family cluster config for each ring.
3. Preserve the density cluster count as the budget.
4. Try two non-oracle replacement policies:
   - fixed bottom-density / top-RR swap
   - joint score: `density_pct + alpha * rr_pct`
5. Also compute a truth-guided oracle swap capacity to separate candidate-pool
   sufficiency from routing-confidence failure.

## Non-Oracle Replacement

Best K-N non-oracle replacement:

| Ring | Strategy | Precision | Recall | Count error | Hits |
| --- | --- | ---: | ---: | ---: | ---: |
| K | joint alpha=2.0 | 52.5% | 52.5% | 0 | 94/179 |
| L | fixed swap=0.5 | 53.4% | 53.4% | 0 | 95/178 |
| M | joint alpha=3.0 | 56.7% | 56.4% | -1 | 114/202 |
| N | joint alpha=2.0 | 50.6% | 50.0% | -2 | 90/180 |

Verdict: does **not** break the 60% precision target. It improves M but leaves
K/L/N close to the old density ceiling.

## Oracle Swap Capacity

Truth-guided swap capacity:

| Ring | Precision | Recall | Count error | Hits | Inserted |
| --- | ---: | ---: | ---: | ---: | ---: |
| K | 50.8% | 50.8% | 0 | 91/179 | 2 |
| L | 55.6% | 55.6% | 0 | 99/178 | 6 |
| M | 62.2% | 61.9% | -1 | 125/202 | 27 |
| N | 58.9% | 58.9% | 0 | 106/180 | 18 |

Verdict: Ring M candidate pools are sufficient to break 60%, and Ring N is
close. The failure is not pure candidate availability. The failure is that the
current blind confidence rule cannot reliably identify which density clusters
are ghosts and which RR clusters are true replacements.

## Lesson

RR is the right third axis, but `rr_sqrt1` magnitude alone is not enough. The
next signal has to rank replacement confidence:

```text
P(density cluster is ghost)
P(RR cluster is true missed anchor)
```

The next useful model is not another count lane. It is a binary replacement
classifier trained on density false clusters vs RR true-new clusters, then
frozen before the next ring.

## Related

- [[RR extraction lane]]
- [[anchor count proxy]]
- [[Ring M]]
- [[Ring N]]
