# Clay multi-view data confirmation preregistration — 2026-11-13

## Question

Does independently sampling the same action task through all three legal
geometry views improve source-disjoint action classification, or did the first
campaign's 9/9 positive matched deltas arise from seed noise?

The first campaign selected no model. This confirmation is registered before
its new seeds, larger data banks, or larger evaluation banks are run.

## Fixed learner and data arms

Every horse uses the same ordinary 6,917-parameter MLP, optimizer, training-step
budget, and row count. Only the data exposure differs.

1. `static_unique`: 30,000 independent states from one canonical view.
2. `static_repeated`: 10,000 canonical states repeated three times each.
3. `curriculum_independent` (primary): 10,000 independent states from each of
   the three legal geometry views.

This separates raw row count, exact repetition, and cross-view concept support.
It does not force the three views of one latent state into the same gradient
batch because that treatment lost to independent mixing in the first campaign.

## Locked campaign

- Seeds: `71, 89, 107, 131, 149`
- Data seed offset: `1,000,000` (independent of the discovery campaign)
- Held sectors: `1, 4, 7`
- Rows per arm and fold: `30,000`
- Independent holdout and anchor rows per fold: `10,000` each
- Stable-class threshold: at least `32` natural holdout examples
- Steps per horse: `2,400`
- Batch size: `192`
- Learning rate: `0.001`; weight decay: `0.0001`
- Hidden width: `64`
- Horses: `3 arms x 5 seeds x 3 held sectors = 45`
- Expected row exposures: `2,400 x 192 / 30,000 = 15.36` per horse

No held-sector row enters training or checkpoint selection. The existing Clay
source tree remains read-only.

## Gate

The primary arm must beat both `static_unique` and `static_repeated` on held
accuracy and stable-class macro-F1 by more than two pooled standard deviations,
while retaining anchor accuracy within two percentage points of each control.
All-supported macro-F1, sparse classes, exact per-class support, and
worst-supported-class accuracy remain mandatory diagnostics so the threshold
cannot hide zeros or manufacture confidence from one-example classes.

A clearing result is evidence for multi-view data exposure, not automatic
promotion, execution authority, or partial unfreezing. A miss remains
`NO_SELECTION`; all initial, best, and final checkpoints are preserved.
