---
tags: [prime-fog, index, solution-gravity-map]
source: docs/research/prime_fog_known_solution_rings_2026-06-04.md
updated_at: 2026-06-04
---

# Prime Fog Solution Gravity Map

This is the Obsidian map for treating the benchmark like a flight path through known rings.

The verifier rings are known anchors. The rocket path is the rule that lines up with those rings before the verifier is allowed to reveal them.

## Core Idea

```text
known anchors -> visible pre-anchor variables -> controller trajectory -> next unseen board
```

Calibration is allowed to use known rings. Flight is not. The rule becomes real only after it is frozen and tested on the next unseen board.

## Ring Boards

- [[Board A - 100M-150M]]
- [[Board B - 150M-200M]]
- [[Board C - 200M-250M]]
- [[Board D - 250M-300M]]
- [[Board E - 300M-350M]]
- [[Board F - 350M-400M]]
- [[Board G - 400M-450M]]
- [[Board H - 450M-500M]]

## Trajectory Controllers

- [[frozen_gate]]
- [[dominant]]
- [[magnitude]]
- [[frozen coherent]]
- [[compressed frozen]]
- [[centroid_a]]
- [[lambda_shadow_only]]
- [[graph_map_only]]
- [[CMPSSZ only]]
- [[answer_backprop_distiller]]

## Variable Isolations

- [[cen_std]]
- [[frz_skew]]
- [[frz_mean]]
- [[frz_std]]
- [[corr_frz_cen]]
- [[frz_frac_extreme]]
- [[lambda_slope]]
- [[graph_ramp_density]]
- [[cmpssz_density]]
- [[NEG_INF]]

## Cascades

- [[cascade v2]]
- [[cascade v3 hypothesis]]
- [[G break - frz_skew was not enough]]
- [[target lock map]]

## Current Read

The map now says:

- [[cen_std]] pulls toward [[magnitude]] and [[Board D - 250M-300M]].
- [[frz_skew]] pulls toward [[frozen coherent]], but only until [[Board G - 400M-450M]] proves it needs more context.
- [[frz_mean]] and [[frz_std]] explain why G is not F.
- [[compressed frozen]] is a proposed fourth controller class, not validated yet.
- [[target lock map]] shows the current projections already see 36-45 exact anchors per board in top-20 union space.
- [[Board H - 450M-500M]] is the next real test.

## Source Docs

- [Known solution rings](../../docs/research/prime_fog_known_solution_rings_2026-06-04.md)
- [Range-regime artifact](../../artifacts/range_regime_classifier/RESULTS.md)
