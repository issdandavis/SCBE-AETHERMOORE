---
tags: [prime-fog, solution, counting, proxy]
updated_at: 2026-06-04
---

# anchor count proxy

Clustered score peaks can be used as a proxy count surface:

```text
A_hat(range) = number of clustered local score maxima
```

This is distinct from row-hit scoring. It asks whether the transformed field
can approximate the number of known hidden anchors in a ring.

## Audit

Artifact:

```text
artifacts/prime_anchor_count_proxy/RESULTS.md
artifacts/prime_anchor_count_proxy/latest_report.json
```

Runner:

```text
scripts/research/audit_prime_anchor_count_proxy.py
```

Focused tests:

```text
tests/benchmark/test_prime_anchor_count_proxy.py
```

## K-N Result

Best count-only config per ring can match the anchor total closely:

| Ring | Predicted clusters | Actual anchors | Count error |
| --- | ---: | ---: | ---: |
| K | 179 | 179 | 0 |
| L | 178 | 178 | 0 |
| M | 201 | 202 | -1 |
| N | 180 | 180 | 0 |

But the bijection is not solved:

| Ring | Precision | Recall | False | Missed | Duplicates |
| --- | ---: | ---: | ---: | ---: | ---: |
| K | 49.7% | 49.7% | 90 | 90 | 0 |
| L | 52.2% | 52.2% | 85 | 85 | 0 |
| M | 48.8% | 48.5% | 99 | 104 | 4 |
| N | 48.9% | 48.9% | 83 | 92 | 9 |

So count error can be near zero while the actual selected anchor identities are
only about half correct. That means this is a real count-like surface, not an
exact prime-counting function yet.

## Correct Formula

```text
pi(x) = A_hat(x) - false_clusters(x) + missed_anchors(x) - duplicate_clusters(x)
```

The proof target is:

```text
false_clusters = 0
missed_anchors = 0
duplicate_clusters = 0
```

Only then does:

```text
A_hat(x) = pi(x)
```

## Status

Promising as a geometric counting proxy. Not a certified prime-counting method.
The next hardening target is not lower count error; it is controlling the
bijection terms.

## Related

- [[prime truth oracle]]
- [[frozen gate]]
- [[frozen coherent]]
- [[Ring N]]
- [[frozen_dominant overfit]]
