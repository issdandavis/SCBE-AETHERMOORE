---
tags: [prime-fog, target-lock, calibration, known-solutions]
updated_at: 2026-06-04
source: artifacts/prime_target_lock/RESULTS.md
---

# target lock map

Anchor-level diagnostic for hitting the exact known hidden numbers.

This is calibration only:

```text
known anchor -> best controller rank -> hit / near-lock / miss
```

It tells us whether the current projection lanes can already see the target numbers and which controller gets closest to each one.

## Summary

| Range | Known anchors | Union top20 | Union top50 | Union top100 |
| --- | ---: | ---: | ---: | ---: |
| A | 235 | 36 | 74 | 118 |
| B | 227 | 45 | 77 | 114 |
| C | 256 | 45 | 91 | 140 |
| D | 220 | 37 | 70 | 115 |
| E | 224 | 39 | 83 | 114 |
| F | 231 | 43 | 82 | 126 |
| G | 214 | 43 | 77 | 128 |

## Meaning

The projections can already hit many more exact anchors than any single controller. The missing piece is the flight selector:

```text
choose the right controller per local geometry
without using the anchor answer during flight
```

Top-100 near-lock means the target is visible but the launch angle is still wrong.

## Source

- [Prime target lock results](../../artifacts/prime_target_lock/RESULTS.md)
- [Target lock JSON](../../artifacts/prime_target_lock/target_lock_latest.json)
- [Target lock CSV](../../artifacts/prime_target_lock/target_lock_latest.csv)

## Related

- [[Prime Fog Solution Gravity Map]]
- [[cascade v3 hypothesis]]
- [[frozen_gate]]
- [[dominant]]
- [[magnitude]]
- [[frozen coherent]]
- [[compressed frozen]]
- [[lambda_shadow_only]]
- [[graph_map_only]]
- [[CMPSSZ only]]

