---
tags: [prime-fog, alignment-ledger, axis-gate, falsification]
updated_at: 2026-06-05
---

# Geometric Alignment Axes

Status: diagnostic coordinates only. Not search-lane eligible.

Artifact:

`artifacts/prime_alignment_ledger_geometry/gate_demo.json`

Count-honest follow-up:

`artifacts/prime_alignment_ledger_gap_accel_count_honest/gap_acceleration_count_honest_probe.json`

Run:

```powershell
python scripts\research\prime_alignment_ledger.py --rings K,L,M,N --gate-demo --gate-seeds 120 --out-dir artifacts\prime_alignment_ledger_geometry
```

## Result

The alignment ledger gate tested five axes on K-N with the same frozen NMS count-proxy config:

| Axis | Verdict | Notes |
| --- | --- | --- |
| frozen | SEARCH-LANE ELIGIBLE | Clears precision>null_p95 and count honesty on every ring |
| rr_sqrt1 | REJECTED | Fails precision on 3/4 rings and fails count honesty on all rings |
| log_power_bridge | REJECTED | Below null and under-counts every ring; anti-aligned as a standalone lane |
| golden_spiral_phase | REJECTED | Below null and under-counts every ring; anti-aligned as a standalone lane |
| gap_acceleration | REJECTED | Clears precision>null on every ring, but sprays too many clusters and fails count honesty |

## Frontier Split

The rejection set is not uniform.

`log_power_bridge` and `golden_spiral_phase` are dead as standalone lanes. Their precision is only about 0.22-0.27 while the ring null floor is about 0.36-0.42. That is not merely "no signal"; high-scoring rows land on anchors less often than a random shuffle of the same scores. They remain harmless lookup-chart coordinates in the ledger, but should not be routed.

`gap_acceleration` is different. It clears precision-vs-null on every K-N ring:

| Ring | Precision | Null p95 | Count error |
| --- | ---: | ---: | ---: |
| K | 0.387 | 0.370 | +154 |
| L | 0.363 | 0.357 | +150 |
| M | 0.458 | 0.422 | +108 |
| N | 0.394 | 0.378 | +130 |

That is a weak but real matched-null identity signal. It fails only because it over-predicts roughly 290-330 clusters for roughly 180-202 anchors. Treat it as an activity coordinate: it can say "the field is disturbed here," but it cannot yet say "this is one anchor identity."

## Interpretation

The log3/log4 bridge and golden spiral phase are valid map coordinates, but not standalone controllers. They can be recorded in the relationship graph without being allowed to steer search.

Gap acceleration is more interesting than the dead coordinates: it has above-null precision on K-N, but it over-predicts by +108 to +154 clusters. That means it may be a "where the field is active" coordinate, not an identity coordinate. It is not eligible until a frozen companion gate can reduce count error without fitting per ring.

## Count-Honest Follow-Up

Run:

```powershell
python scripts\research\prime_alignment_ledger.py --rings K,L,M,N --count-honest-axis gap_acceleration --freeze-ring K --test-rings L,M,N --gate-seeds 120 --out-dir artifacts\prime_alignment_ledger_gap_accel_count_honest
```

Protocol:

1. Freeze one percentile on K using count closeness only.
2. Test the same percentile/radius on L, M, and N.
3. Compare precision against each ring's own random.shuffle null.

Fit on K:

| Percentile | Predicted | Actual | Count error | Precision |
| ---: | ---: | ---: | ---: | ---: |
| 0.950 | 176 | 179 | -3 | 0.415 |

Transfer:

| Ring | Precision | Null p95 | Predicted | Count error | Verdict |
| --- | ---: | ---: | ---: | ---: | --- |
| L | 0.433 | 0.451 | 164 | -14 | FAIL precision |
| M | 0.480 | 0.518 | 150 | -52 | FAIL precision |
| N | 0.469 | 0.467 | 162 | -18 | PASS |

Verdict: count-honest `gap_acceleration` is rejected. The weak precision edge from the scatter-heavy setting does not survive once the axis is forced to respect the anchor count. It remains a diagnostic/activity coordinate, not a search lane.

## Rule

Do not promote a geometric coordinate to a lane because it looks meaningful in the known map. Promotion requires:

1. one frozen score function,
2. precision_real > random.shuffle null_p95 on every gate ring,
3. abs(count_error) <= 30% * actual_anchors on every gate ring.
