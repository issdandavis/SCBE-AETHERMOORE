---
tags: [prime-fog, methodology, null-floor, metric-audit, falsification]
updated_at: 2026-06-04
---

# Null-Floor Metric Audit — the top-20-unique metric is saturated

A proper random-selection null (real `random.shuffle`, 200–300 seeds) was run
against the two evaluation metrics used across the ring program. One metric is
invalid; the other survives. Two "orthogonal sensor" lanes are falsified.

## The density trap

Per ring, ~52–57% of ROWS are anchor-bearing, and each unique anchor spans
~18–21 rows (window + lead_steps structure):

| Ring | rows | anchor-bearing rows | unique anchors | rows/anchor |
| --- | ---: | ---: | ---: | ---: |
| K | 7056 | 3681 (52.2%) | 179 | 20.6 |
| M | 6246 | 3544 (56.7%) | 202 | 17.5 |

Consequence: a **random** pick of 20 rows catches ~10 *distinct* anchors. Any
lane that **scatters** its top-K picks looks like a genius; any lane that
**clusters** (correctly scoring an anchor's ~20-row neighborhood high) is
PENALIZED — its top-20 collapse onto 1–3 distinct anchors.

## Metric 1 — top-20-unique-anchor union: NULL-SATURATED, INVALID

Best controller vs random null (top-20 unique, 300 seeds):

| Ring | frozen | dominant | magnitude | coherent | null mean | null p95 | any > null95? |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| K | 9 | 9 | 5 | 6 | 9.9 | 14 | **NO** |
| L | 10 | 4 | 5 | 3 | 9.5 | 13 | **NO** |
| M | 4 | 7 | 6 | 5 | 11.1 | 15 | **NO** |
| N | 7 | 9 | 8 | 9 | 9.8 | 14 | **NO** |

**No controller beats the null on any ring.** This metric cannot establish a
winner. Everything measured on it is noise:

- **`inverse prime field` IP=9 / union 17 (Ring I): FALSIFIED.** Reproduced
  exactly (frozen 6, v4 8, ip 9, union 17), then IP lift +9 vs random-20 lift
  +9.6 = **0.9×**. The "ninth controller" was a density artifact.
- **`RR extraction lane` (rr_sqrt1): FALSIFIED.** Equal-budget top-20 lift =
  **1.0×** null across K/L/M/N, budgets 20–100. No signal.
- **The cascade winners (frozen wins K/L, coherent wins M/N): not established
  by this metric.** They may still hold under metric 2 — re-ground required.

## Metric 2 — NMS count-proxy precision: SURVIVES

The count-proxy de-duplicates by scan-gap radius (NMS), so it does NOT reward
scatter. Random scorer through the IDENTICAL machinery (p0.85, r12, 120 seeds):

| Ring | frozen | rr_sqrt1 | null mean | null p95 | frozen > null95? | rr > null95? |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| K | 44.0% | 36.4% | 35.6% | 37.3% | **YES** | no |
| L | 44.9% | 33.3% | 34.2% | 35.5% | **YES** | no |
| M | 47.2% | 42.4% | 40.2% | 42.0% | **YES** | tie |
| N | 48.1% | 33.6% | 35.7% | 37.5% | **YES** | no |

**Frozen beats null95 on all 4 rings** (~7–12 pts above). The controller
framework has real signal — under the RIGHT metric. **rr is at/below null on
3 of 4** (M only ties). RR is dead even here.

## Verdicts

1. Use the **NMS count-proxy**, never top-20-unique-anchor, to compare lanes
   or pick winners. The latter is anti-correlated with good localization.
2. **IP lane and RR lane are both falsified** as orthogonal locators. The
   "orthogonal sensor family" theory does not survive a null.
3. **Frozen (and the controller framework) is real** under the count-proxy.
   Re-ground the K–N ring winners on count-proxy precision, not top-20-unique.
4. **Every future "new lane catches anchors X misses" claim must clear a
   random-selection null first.** Two lanes and four controllers evaporated
   against it; the density floor is ~the whole apparent signal.

## Replacement classifier: NO-GO (random-re-ranker null, resolved 2026-06-04)

The joint density+rr router (`density_pct + α·rr_pct`, best-α per ring) was
null-tested by swapping rr for a RANDOM score through the identical pool +
α-sweep machinery (60 seeds):

| Ring | density-only | real rr joint | random-rr mean | random-rr p95 | real > rand p95? |
| --- | ---: | ---: | ---: | ---: | --- |
| K | 49.7% | 52.5% | 52.9% | 56.2% | **NO** |
| L | 56.0% | 55.4% | 56.0% | 58.3% | **NO** |
| M | 48.8% | 56.7% | 53.6% | 58.2% | **NO** |
| N | 48.9% | 50.6% | 52.5% | 56.1% | **NO** |

A random second pool reaches the SAME 52–58% as rr. The joint's lift over
density-alone is **pure in-sample α-tuning over a second candidate pool** — the
pool's content is irrelevant. M's 56.7% (which looked like "rr has info") is
BELOW random's p95 (58.2%). **Do not build the binary replacement classifier on
rr.** The oracle 62% capacity is truth-guided and unreachable blind because rr
≈ random. This is the third structure (after IP and the controllers on
top-20-unique) to evaporate against a proper null.

**Metric choice does not rescue a null axis.** L1/Manhattan/total-variation
routing over rr changes nothing — no distance recovers information that isn't
in the axis. The correct tool for "a blended score hides a weak axis" is the
per-axis null test above, not a fancier metric. (See the staircase-paradox
intuition: the blend is the diagonal shortcut; per-axis nulling is the fix.)

## Regime flip (frozen K/L → coherent M/N): DOES NOT SURVIVE (resolved 2026-06-05)

The entire v6 / frozen_dominant / manifold-navigator narrative rests on a
K/L-frozen → M/N-coherent regime flip — all of it measured on the dead
top-20-unique metric. Re-grounded on the count-proxy:

- **N: frozen robustly wins** all 8 configs (p0.70/0.80/0.85/0.90 × r12/r24).
- **M: frozen ≈ coherent.** At p0.85/r12 frozen edges it (47.2 vs 45.6); across
  configs coherent leads in 6/8, but the gap is ~1 pt mean and lives almost
  entirely on the radius axis (≈0 at r12, ≈+2 at r24).

The "M coherent lean" was then **null-tested directly**. coherent is just a
different blend `(wf=1, wa=0, wc=1.5)` over the SAME `frz_z`/`cen_z` as frozen
`(1,0,0)`. A random-reweighting null (400 draws, wf∈[0,1.5], wa∈[0,2],
wc∈[0,2]) on M p0.80/r24 — coherent's BIGGEST gap config:

| quantity | precision |
| --- | ---: |
| frozen (1,0,0) | 49.1% |
| coherent (1,0,1.5) | 52.7% |
| random-reweight p05 / median / p95 | 48.1% / 51.8% / 53.8% |
| fraction of random reweightings ≥ coherent | **31%** |

coherent's +3.6% is **inside the random-reweighting spread** — 31% of random
weight triples over the same two inputs match or beat it. It is blend-weight
wobble, not a regime. **There is no surviving regime flip.** Frozen's OWN M
precision swings ~40→53% across configs, so config variance (~12 pts) swamps
any inter-controller gap (~1 pt). "Winner-per-ring" is not a robust quantity
under the count-proxy; picking one config to crown a controller is the same
researcher-degree-of-freedom that bred the [[frozen_dominant overfit]].

**Only robust, null-clearing fact: frozen beats null95 on every ring K–N.**
That is the single mass-bearing coordinate. Ring O is therefore *confirmation,
not discrimination* — the flip was the only live prediction and it dissolved.
Do not spend the OOM-risk 850M build until a prediction O could actually FAIL
is stated; "frozen clears null95, precision ~44–50%" is near-foregone.

## Open frontier through the axis gate (2026-06-05)

Three never-tested transforms run through `prime_alignment_ledger.py`'s gate
(precision > null_p95 AND |count_err| ≤ 30%·actual on every ring, 60–120 seeds):

| axis | precision (K/L/M/N) | null p95 | count | verdict |
| --- | --- | ---: | --- | --- |
| log_power_bridge (log3/log4 chart) | .22/.24/.24/.23 | ~.37 | under | REJECTED — **below null** |
| golden_spiral_phase (φ-shell notches) | .24/.22/.27/.25 | ~.37 | under | REJECTED — **below null** |
| gap_acceleration (2nd diff of scan_ratio) | .39/.36/.46/.39 | ~.37 | +108..+154 over | REJECTED on COUNT only |
| ratio_graph_resonance (prime-pair log-ratio recurrence) | count-honest 9/14 vs value-shuffle | — | matched | REJECTED — 0/14 vs circular-shift (count-matched); see below |

- **log_power_bridge / golden_spiral_phase are anti-aligned** (below their own
  shuffle): no signal, falsified like IP and RR. Four dead transforms now.
- **gap_acceleration: edge is a count-inflation artifact — DEAD (resolved
  2026-06-05).** It cleared precision-vs-null on all 4 rings, but only while
  over-predicting (~330 clusters / 179 anchors). Hypothesis tested: is the
  over-prediction the "ultimate goal slope" (global ln-curvature)? **No** — on
  ring K the smooth trend (w51) holds 4.4% of variance, 96.2% is high-frequency
  residual; detrending makes the count WORSE (+154→+174). The over-prediction is
  scatter, not slope. Driving the count honest with the matched fix (low-pass
  smoothing) pincers it: w9 → 178 clusters (honest) but precision edge collapses
  to **+0.003 (null floor)**; the +0.03 edge at w5 comes WITH +55 over-predict.
  There is no operating point that is both count-honest AND above null. The edge
  IS the scatter. Same disease, subtler dress. Frozen remains the only axis.

## ratio_graph_resonance: count-matched null kills it (2026-06-05)

The prime-pair ratio graph (edge weight = log(p[j]/p[i]); each row scores by
recurrence of similar neighbouring log-ratios) was the strongest-looking
candidate of the open frontier. Under a per-ring count-honest percentile it beat
the value-shuffle null on **9/14** rings (p≪chance) — looked like the first new
lane since frozen.

It was the recall-inflation disease again, flipped onto precision. The score is
spatially autocorrelated (smooth → few NMS clusters, ~177–251); a `random.shuffle`
scatters it → ~270–380 clusters. So `precision_real` (÷177) beat `precision_shuffle`
(÷~300) by predicting **fewer** clusters on a dense field, not by localizing. The
value-shuffle null is **not count-matched** for an autocorrelated score.

The correct surrogate is a **circular-shift null** (roll the score in scan order;
preserves smoothness + cluster count, breaks only anchor alignment). Result:
**0/14 rings beat it** (p-values .25–.98; near-misses D/I/J/K ≈ .06–.07 = chance
fluke count). `ratio_graph_resonance` localizes no better than a random roll of
itself. **Six dead transforms now** (IP, RR, log3/log4, golden spiral,
gap_acceleration, ratio_graph_resonance). See [[prime ratio transition graph]].

**New reusable null rule:** for a spatially autocorrelated/smooth candidate score,
a value-shuffle null over-predicts cluster count and inflates the smoother axis.
Use a **circular/phase-shift surrogate** to keep the count matched and break only
the alignment.

## Legacy row-cache channels re-gated (2026-06-05)

The row cache carries ~30 pre-discipline transform channels (lambda, graph_map,
cassette/CMPSSZ, hyperbolic/topology, ratio-depth, thermal). Two families were
re-gated under the current discipline (count-honest per-ring percentile +
**circular-shift** null, both orientations, 14 rings):

| family | best channel | beats null | verdict |
| --- | --- | ---: | --- |
| hyperbolic/topology | topo_score/asymmetry/confidence | **0/14** each | stone dead (below chance: 2 beats / 112 cells) |
| | gravity_score_normalized | 1/14 | dead |
| CMPSSZ/cassette | cassette_adj_channel(+) | 5/14 @S60, **4/14 @S40 on different rings** | seed-UNSTABLE → noise |
| | cassette_channel / non_adj | 0/14 | dead |
| | cassette_triplet / cmpssz_* | ≤3/14 | dead |

Key tell: cassette_adj_channel's beat-set **moved** when only the null seed budget
changed (S60 lit H/I/J/M/N; S40 lit F/I/M/N). A real lane beats the SAME rings
regardless of seed count; a reshuffling beat-set is chance. No channel clears the
majority bar in either orientation.

**Leakage flag:** the cache also has `future_anchor*`, `top_future_*`,
`future_heat`, `future_*_counts`, `future_strength_channel` — all forward-looking.
Disqualified from gating regardless of score; an axis built on them reads the answer.

**lambda + graph_map + ratio-depth: CLOSED, all dead (2026-06-05).** Re-gated on 6
regime-spanning rings (C,D,F,K,M,N), circular-shift null, both orientations. Best
any channel reached was **2/6** (lambda_gradient(-), graph_attractor(+),
prime_ratio(+), resonant_soliton(+)) — at the ~0.3/6 chance floor across 26
channel-orientations. None clears majority. Scatter-family death as predicted. Only
thermal primitives remain un-regated and they're partly frozen's own ancestry
(standalone test near-tautological). **Every legacy row-cache family is now closed;
frozen is the sole null-clearing axis.** This is the null floor: no blind row-cache
axis localizes anchors better than its own autocorrelation.

## Method (reusable)

```text
proper null = mean over S≥120 seeds of metric(random scorer, same machinery)
report null mean AND null p95; a lane is real only if it clears p95 every ring
BUG TO AVOID: (i*M)%n is a permutation only if gcd(M,n)=1 — use random.shuffle
```

## Related

- [[anchor count proxy]] — the count-proxy tool (metric 2); now the canonical metric
- [[inverse prime field]] — IP=9 falsified here
- [[RR extraction lane]] — falsified here
- [[replacement router audit]] — needs the random-re-ranker null before classifier
- [[Ring O pre-registration]] — regime question is independent; still the real next test
- [[frozen_dominant overfit]] — same disease: committing on too few, unvalidated points
