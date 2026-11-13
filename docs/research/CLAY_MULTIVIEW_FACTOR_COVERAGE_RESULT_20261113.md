# Clay multi-view factor-coverage result — 2026-11-13

## Outcome

The preregistered semantic factor selector did not improve the ordinary Clay
action learner.  It increased measured conditional cell coverage and often
increased cross-view gradient cosine, but it lost to random multi-view data in
all three held sectors and reduced same-source anchor retention by more than
two percentage points.  The result is `NO_SELECTION`; no checkpoint is
promoted and no layer is partially unfrozen.

Run:
`C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-factor-coverage-v1`

Result receipt:
`b51cd41d2d441c95333e164d99301119d730ebba8927bd600c28502dc28113fc`

Stratified gate receipt:
`c57a0913f409fe353d1979010ad4546aeb3e6bc9945a38e2187fed5d9945c009`

## Global market

| Data arm | Held accuracy | Stable F1 | Worst stable | Anchor accuracy | Gradient cosine | Weight drift |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| static unique | 0.8400 | 0.7144 | 0.4284 | 0.9818 | 0.1898 | 13.4431 |
| random multi-view | 0.8901 | 0.7548 | 0.4783 | 0.9805 | 0.3709 | 14.3614 |
| semantic factor | 0.8560 | 0.7270 | 0.4522 | 0.9579 | 0.4656 | 9.6988 |
| shuffled-factor control | 0.9166 | 0.7763 | 0.5495 | 0.9816 | 0.2745 | 12.8326 |

Every arm used the same 6,917-parameter MLP, 30,000 training rows, 4,800
optimizer steps, five model seeds, three held sectors, and 10,000-row held and
anchor banks.  All 6,917 learned scalars changed in every horse.

## Sector evidence

| Held sector | Arm | Accuracy | Stable F1 | Anchor accuracy |
| ---: | --- | ---: | ---: | ---: |
| 1 | static unique | 0.7769 | 0.8243 | 0.9840 |
| 1 | random multi-view | 0.8284 | 0.8624 | 0.9821 |
| 1 | semantic factor | 0.7811 | 0.8263 | 0.9607 |
| 1 | shuffled-factor | 0.8729 | 0.8979 | 0.9819 |
| 4 | static unique | 0.9623 | 0.4989 | 0.9801 |
| 4 | random multi-view | 0.9900 | 0.5227 | 0.9786 |
| 4 | semantic factor | 0.9860 | 0.5113 | 0.9562 |
| 4 | shuffled-factor | 0.9902 | 0.5227 | 0.9813 |
| 7 | static unique | 0.7810 | 0.8200 | 0.9811 |
| 7 | random multi-view | 0.8520 | 0.8793 | 0.9808 |
| 7 | semantic factor | 0.8010 | 0.8433 | 0.9568 |
| 7 | shuffled-factor | 0.8868 | 0.9083 | 0.9816 |

Against random multi-view data, the proposed factor arm lost accuracy by
`-0.0473`, `-0.0040`, and `-0.0510` in sectors 1, 4, and 7.  Stable F1 deltas
were `-0.0361`, `-0.0113`, and `-0.0360`.  Anchor deltas were worse than the
registered two-point retention limit in every sector.

## What the data check changed

The intervention itself was real.  Before any optimizer step, the semantic
factor arm exceeded both controls on normalized conditional-cell entropy:

| Held sector | Semantic factor | Random | Shuffled binding |
| ---: | ---: | ---: | ---: |
| 1 | 0.93660 | 0.90990 | 0.89809 |
| 4 | 0.94176 | 0.91791 | 0.90777 |
| 7 | 0.93445 | 0.90769 | 0.89607 |

All view/action quotas matched, selected indices and exact feature rows were
disjoint, and neither holdout rows nor reward/post-outcome fields entered the
selector.  The failed result therefore does not mean that factor balancing was
absent.  It means that aggressively flattening these declared factor cells was
not aligned with the transfer objective.  Rare cells can be boundary, tie, or
otherwise low-margin examples; equalizing occupancy can amplify conflict
instead of building a useful concept gradient.

Gradient cosine is not a sufficient objective.  In sector 4, semantic factor
coverage raised selected cross-view cosine to `0.8770`, versus `0.7162` for
random multi-view data, while both transfer metrics and anchor retention got
worse.  Gradients can agree strongly while pointing toward a dominant class or
an unhelpful source-specific solution.

## Exploratory observation, not a selection

The shuffled-factor control was the strongest global arm.  Relative to static
unique data, it won all 15 matched accuracy pairs and all 15 stable-F1 pairs,
with mean deltas `+0.07659` and `+0.06189`.  Relative to random multi-view data,
it won 11/15 accuracy pairs and 10/15 stable-F1 pairs, with mean deltas
`+0.02651` and `+0.02150`; anchor accuracy was essentially unchanged.

This arm was registered as an ablation, not the primary hypothesis.  Its lead
cannot be promoted from this campaign.  A defensible interpretation is that
the shuffled signatures act as a deterministic spread/hash over the candidate
pool without over-weighting the named physical factors.  That explanation must
be tested against a fresh deterministic-hash sampler and new seeds rather than
accepted after seeing the result.

## Receipt audit

- Campaign receipt: `12e9bb5c4ba31ac729697b6a9c8ab40e08e36ab7078865d747f604959885d9db`.
- Result receipt: verified.
- Stratified gate receipt: verified.
- Horse receipts: `60/60`.
- Initial/best/final checkpoint hashes: `180/180`.
- Matched initialization groups: `15/15`.
- Tensor-bank manifests: `24/24`.
- Selection receipts: `3/3`.
- Independent exposure audit: `60/60` horse lineages and `15/15` deterministic
  schedules verified.  Every horse drew exactly 921,600 rows; every 30,000-row
  bank position was seen 10--60 times with median 31.  Audit receipt:
  `f791bb97c0b1a9e289b1cbeea0841fc66d3a9b5769b153ac749bd329363ab00f`;
  file SHA-256:
  `e57a4ac04d385d866b439652e0c91da1a126dbc2d182e7fd66195f454b999b7f`.
- Promotion authority: false.
- Partial-unfreeze authority: false.

## Next controlled data questions

1. Replicate the shuffled-selector lead as a primary arm against random
   multi-view, static unique, and a direct deterministic-hash sampler using new
   data and model seeds.
2. Separately record the action-credit margin for complete three-view concept
   orbits.  Test a clear-to-boundary curriculum that replays high-margin orbits
   first while retaining the correct per-view action transition.  Compare the
   same tensors and exposure budget with margin assignments shuffled.
3. Do not force transformed rows toward one invariant label.  Prior measured
   data show that only 54.88% of latent states retain one action across all
   three legal geometry views.

The durable rule is now narrower: expose the learner to valid transformed
support, but do not assume that maximum occupancy uniformity, same-label
grouping, or high gradient cosine is equivalent to useful concept learning.
