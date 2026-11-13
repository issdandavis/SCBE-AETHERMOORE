# Clay paired-orbit data result — 2026-11-13

## Outcome

Looking at the actual data changed the diagnosis. The long-horizon action run
did not lack repeated exposure: each 8,000-row bank received 614,400 sampled
draws per horse, with a median row exposure of about 77. Every sampler reached
every stored row. More steps over that fixed bank could reinforce existing
samples, but could not expand the learned concept support.

Cross-view data did show a repeatable exploratory benefit. Independent samples
from the three legal geometry views beat the single-view static control in all
9 matched seed/fold comparisons. However, neither the original 1,000-row
evaluation nor the independent 10,000-row diagnostic cleared the registered
two-standard-deviation gate. No checkpoint is selected, promoted, or partially
unfrozen.

## Data audit

Source run:
`C:\dev\clay-training-runs\fundamentals-portfolio-longhorizon-20261111-v2`

Audit receipt:
`63905f743b60ef2a79f9acba9fea19544e2cabeafaa5f5286e8269c87ea2f2eb`

- All stored rows were sampled.
- Minimum row exposure was 41--45; maximum was 111--115; median was 77.
- Exact train/holdout row overlap was zero.
- Each held fold was farther from training than a same-source anchor in RMS-z
  feature distance, confirming a real source-disjoint shift.
- The saved bank was static; there was no online augmentation or new-state
  generation during the 2,400 optimizer steps.

## Controlled campaign

Run:
`C:\dev\clay-training-runs\paired-orbit-data-20261113\full-v2`

Result receipt:
`b72bef1c6284c02766978a6d6b049269b6ff37b3f1c8ef5df3879b04a7ea0702`

The campaign trained 45 ordinary 6,917-parameter MLPs: five equal-row data
arms, three seeds, and three held sectors. Every final model changed all 6,917
trainable parameters. Initial, best, and final weights were retained.

| Data arm | Held accuracy | Macro-F1 | Worst supported | Anchor accuracy |
| --- | ---: | ---: | ---: | ---: |
| static unique | 0.8277 | 0.7041 | 0.4028 | 0.9769 |
| static repeated | 0.8442 | 0.7163 | 0.4258 | 0.9703 |
| curriculum independent | 0.8823 | 0.7430 | 0.5075 | 0.9742 |
| paired orbit shuffled | 0.8788 | 0.7394 | 0.4747 | 0.9703 |
| paired orbit grouped | 0.8746 | 0.7369 | 0.4846 | 0.9737 |

The preregistered grouped treatment did not win. It trailed independent mixing
by 0.78 accuracy points and 0.61 macro-F1 points, and trailed shuffled paired
orbits by 0.42 and 0.25 points. The useful part was view diversity, not forcing
three views of one latent state into one gradient unit.

An initial `full-v1` launch was stopped before any horse trained because data
inspection exposed an evaluator defect: absent action classes were being scored
as failures. The corrected evaluator scores only true-supported classes and
reports absent classes separately.

## Independent 10,000-row diagnostic

Diagnostic:
`C:\dev\clay-training-runs\paired-orbit-data-20261113\full-v2\large-holdout-diagnostic`

Diagnostic receipt:
`a011681a0cf908078316cccb9163d7ecf058068505b3335536dcc2bea38be43b`

The diagnostic generated 10,000 new held rows and 10,000 new anchor rows per
fold, then evaluated the same immutable 45 best checkpoints. A stable class
requires at least 32 natural examples; sparse and absent classes remain visible
but cannot manufacture a macro score from one observation.

| Data arm | Accuracy | All-supported F1 | Stable F1 | Worst stable | Anchor accuracy |
| --- | ---: | ---: | ---: | ---: | ---: |
| static unique | 0.8244 | 0.6446 | 0.7059 | 0.4118 | 0.9734 |
| static repeated | 0.8419 | 0.6524 | 0.7168 | 0.4341 | 0.9670 |
| curriculum independent | 0.8777 | 0.6894 | 0.7451 | 0.5128 | 0.9691 |
| paired orbit shuffled | 0.8768 | 0.6943 | 0.7441 | 0.4829 | 0.9679 |
| paired orbit grouped | 0.8735 | 0.6888 | 0.7420 | 0.4931 | 0.9698 |

Independent multi-view exposure beat static unique in all 9 matched cases:

- Accuracy mean delta `+0.05333`; two-SD threshold `0.06615`.
- Stable macro-F1 mean delta `+0.03921`; two-SD threshold `0.05304`.

Both are consistent exploratory gains and both fail the strict noise gate.
Exact repetition was positive in only 5 of 9 accuracy and macro-F1 pairs, so
replaying identical rows is not an adequate substitute for concept views.

Natural action support is highly sector-dependent. The three held-fold counts
were `[1567,3514,1,4918,0]`, `[1584,0,8326,40,50]`, and
`[1583,4893,0,0,3524]`. That is why aggregate accuracy alone is unsafe and why
the confirmation gate includes stable-class F1 plus exact support receipts.

## Next registered run

The fresh confirmation is defined in
`CLAY_MULTIVIEW_DATA_CONFIRMATION_PREREGISTRATION_20261113.md` and runs at:

`C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-confirm-v1`

It uses new data seeds, 30,000 rows per arm, 10,000-row held and anchor banks,
five unseen model seeds, 2,400 steps, and the two controls needed to distinguish
cross-view support from raw row count and exact repetition.

Status remains `NO_SELECTION`. Existing weights are preserved.
