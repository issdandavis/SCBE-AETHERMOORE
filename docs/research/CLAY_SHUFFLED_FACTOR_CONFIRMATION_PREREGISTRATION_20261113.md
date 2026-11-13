# Clay shuffled-factor confirmation preregistration — 2026-11-13

Status: frozen before confirmation data or model outcomes are read.

## Hypothesis

The discovery run found that selection over shuffled factor signatures beat
static unique data in all 15 matched accuracy and stable-F1 comparisons and
led random multi-view data on average.  The proposed explanation is modest:
the shuffled signatures may provide a deterministic spread/hash over the
candidate pool without over-weighting the named physical factor cells.

The confirmation asks whether that lead replicates on fresh data and model
seeds.  It does not claim that shuffled signatures add information, discover
semantics, or authorize a learned geometry layer.

## Locked protocol

- Primary: `multiview_factor_shuffled`.
- Controls: `multiview_random`, `static_unique`, and `multiview_factor`.
- Model seeds: `347`, `359`, `373`, `389`, and `401`.
- Data seed offset: `5,000,000`.
- Held sectors: `1`, `4`, and `7`.
- Rows per arm/fold: `30,000`; exactly `10,000` per legal view for multi-view arms.
- Candidate rows: `60,000` per legal view, training source only.
- Held and anchor rows: `10,000` each per fold.
- Learner: ordinary `Linear(37,64) -> GELU -> Linear(64,64) -> GELU -> Linear(64,5)`.
- Budget: 4,800 AdamW steps, batch 192, learning rate 0.001, weight decay 0.0001.
- Stable class support floor: 32.
- Total: 60 horses.

All multi-view arms must have identical view/action quotas, no selected-index or
exact-feature overlap, finite tensors, valid receipts, and no train/evaluation
row collision.  Selection may use only training input factors and the action
label needed to hold quotas fixed.  Holdout rows, reward, post-outcome fields,
and model gradients are prohibited.

## Gate

Within each held sector and against every control:

1. mean accuracy and stable macro-F1 deltas must be positive;
2. each metric must exceed `max(2 x pooled seed SD, 0.02)` in at least two of
   three sectors; and
3. anchor accuracy must remain within two percentage points in every sector.

The report must also retain matched wins/losses, worst stable-class accuracy,
class support, cross entropy, gradient cosine, weight drift, best-step traces,
selection entropy, exact exposure receipts, and checkpoint hashes.

A miss is `NO_SELECTION`.  A pass is
`PASS_SHUFFLED_DATA_MECHANICS_NO_PROMOTION`.  Neither outcome authorizes
checkpoint promotion, deployment, execution authority, deletion, or partial
unfreezing.

## Separate future question

Action-credit margin and clear-to-boundary concept-orbit replay are not part of
this confirmation.  Mixing that new curriculum into this run would make it
impossible to tell whether the observed shuffled-selector lead replicated.
