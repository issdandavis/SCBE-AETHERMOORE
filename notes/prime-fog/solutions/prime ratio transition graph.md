---
tags: [prime-fog, ratio-graph, alignment-ledger, axis-gate]
updated_at: 2026-06-05
---

# Prime Ratio Transition Graph

Status: **FALSIFIED** under the circular-shift null (2026-06-05). Diagnostic
transition-space coordinate only; carries no anchor-localization signal beyond
its own autocorrelation. Not search-lane eligible.

This tests the idea:

```text
prime pair edge weight = log(p[j] / p[i])
ratio curvature        = log(p[i+1] / p[i]) - log(p[i] / p[i-1])
transition resonance   = repeated/similar edge weights in ratio space
```

The "laser" moves through transition space, not through raw prime values.

## Implemented Axes

In `scripts/research/prime_alignment_ledger.py`:

- `ratio_curvature`: absolute ratio-of-ratios bend.
- `ratio_graph_resonance`: recurrence of similar neighboring prime-pair log-ratios.

Artifacts:

- `artifacts/prime_alignment_ledger_ratio_graph/gate_demo.json`
- `artifacts/prime_alignment_ledger_ratio_graph_count_honest/ratio_graph_resonance_count_honest_probe.json`

## Gate Result

Run:

```powershell
python scripts\research\prime_alignment_ledger.py --rings K,L,M,N --gate-demo --gate-seeds 120 --axes frozen,rr_sqrt1,log_power_bridge,golden_spiral_phase,gap_acceleration,ratio_curvature,ratio_graph_resonance --out-dir artifacts\prime_alignment_ledger_ratio_graph
```

| Axis | K | L | M | N | Verdict |
| --- | ---: | ---: | ---: | ---: | --- |
| ratio_curvature precision | 0.360 | 0.366 | 0.404 | 0.368 | fails precision on 3/4 and count on all |
| ratio_curvature null p95 | 0.371 | 0.356 | 0.419 | 0.376 | rejected |
| ratio_graph_resonance precision | 0.412 | 0.381 | 0.432 | 0.385 | clears precision on 4/4 |
| ratio_graph_resonance null p95 | 0.373 | 0.359 | 0.421 | 0.378 | fails count on all |

`ratio_curvature` is not useful as a lane in this form.

`ratio_graph_resonance` has a weak real identity signal at the scatter-heavy setting, similar to gap acceleration. It over-predicts by +103 to +151 clusters, so it is count-dishonest and cannot be promoted.

## Count-Honest Follow-Up

Run:

```powershell
python scripts\research\prime_alignment_ledger.py --rings K,L,M,N --count-honest-axis ratio_graph_resonance --freeze-ring K --test-rings L,M,N --gate-seeds 120 --out-dir artifacts\prime_alignment_ledger_ratio_graph_count_honest
```

Fit on K:

| Percentile | Predicted | Actual | Count error | Precision |
| ---: | ---: | ---: | ---: | ---: |
| 0.940 | 177 | 179 | -2 | 0.486 |

Transfer:

| Ring | Precision | Null p95 | Predicted | Count error | Verdict |
| --- | ---: | ---: | ---: | ---: | --- |
| L | 0.446 | 0.425 | 157 | -21 | PASS |
| M | 0.490 | 0.500 | 157 | -45 | FAIL precision |
| N | 0.435 | 0.447 | 147 | -33 | FAIL precision |

Verdict: rejected. The count-honest cutoff transfers to L, but fails M and N. This is not a new lane.

## Per-ring count-honest re-test, then the circular-shift kill (2026-06-05)

The 4-ring fixed-K transfer above forced K's percentile onto every ring, which
under-predicted badly on M/N (157 vs 202) and unfairly depressed precision there.
The fairer test sets a **per-ring count-honest percentile** (tune the cutoff to
hit the *known count*, then measure precision-vs-null at that point — the count
is known truth, not a free precision sweep). Under that, 14 rings posted 9/14
"beats value-shuffle null at count-honest" (p≪chance). That looked like the first
real lane since frozen.

**It was an artifact. The value-shuffle null is not count-matched.** Real
`ratio_graph_resonance` is spatially autocorrelated (consecutive primes → correlated
log-ratios → smooth score → few local maxima → ~177–251 NMS clusters). A
`random.shuffle` of the same values scatters them → nearly every point is a local
peak → it predicts ~270–380 clusters. So `precision_real = hits/177` was being
compared against `precision_shuffle = hits/~300`: real "won" largely by predicting
**fewer, less-duplicated clusters on a 52%-dense field** — the exact recall-inflation
disease from [[null floor metric audit]], flipped onto precision.

The discriminating test is a **circular-shift null**: roll the score sequence (in
scan order) by a random offset. This preserves the score's *exact* spatial structure
— smoothness, NMS cluster count (~177, auto count-matched), duplicate behaviour —
and breaks **only** the alignment to anchor positions.

| | value-shuffle null (confounded) | circular-shift null (correct) |
| --- | --- | --- |
| real vs null predicted count | 177–251 vs **270–380** (mismatched) | both ~177–251 (matched) |
| rings beating null (p<.05) | 9/14 | **0/14** |

Per-ring circular-shift p-values: A .80, B .78, C .98, D .058, E .88, F .25,
G .53, H .73, I .067, J .075, K .067, L .40, M .53, N .40. Zero clear p<.05; the
four near-misses (D/I/J/K ≈ .06–.07) are exactly the fluke count 14 trials yield.

Artifact: `artifacts/prime_alignment_ledger_ratio_graph_count_honest/` (run logged
inline in session blrf9fm44).

## Interpretation

`ratio_graph_resonance` localizes anchors **no better than a random roll of its own
autocorrelated self**. The graph construction is mathematically clean and stays as a
map coordinate, but it is a dead lane — same disease as `gap_acceleration` (the edge
IS the scatter), now caught one level deeper because the null had to be made
count-matched to expose it. Six dead transforms now (IP, RR, log3/log4, golden
spiral, gap_acceleration, ratio_graph_resonance). Frozen remains the only
null-clearing axis.

Methodology lesson (reusable): **for a spatially autocorrelated score, a value-shuffle
null is NOT count-matched** — it scatters, over-predicts cluster count, and inflates
the smoother axis's precision. Use a **circular/phase-shift surrogate** (preserves
autocorrelation, breaks only alignment) whenever the candidate score is smooth. The
user's standing rule "do not sweep ratio thresholds per ring" is the same guard from
the other side: the per-ring percentile is the freedom the circular-shift null
neutralizes.
