# Clay random multi-view confirmation preregistration — 2026-11-13

Status: frozen before candidate generation, selection receipts, or model
outcomes from this campaign.

## Hypothesis

Valid view diversity is more useful than repeated exposure to one canonical
sheet or deterministic balancing over declared/surrogate cells.  The primary
`multiview_random` arm should outperform `static_unique`, `multiview_factor`,
and `multiview_factor_shuffled` under the locked held-sector gate.

## Locked protocol

- Primary: `multiview_random`.
- Controls: `static_unique`, `multiview_factor`,
  `multiview_factor_shuffled`.
- Model seeds: `479`, `487`, `503`, `509`, `521`.
- Data seed offset: `7,000,000`.
- Held sectors: `1`, `4`, `7`.
- Rows per arm/fold: 30,000; 10,000 per legal view in multi-view arms.
- Candidate rows: 60,000 per legal view, training source only.
- Held and anchor banks: 10,000 rows each per fold.
- Learner: ordinary `Linear(37,64) -> GELU -> Linear(64,64) -> GELU -> Linear(64,5)`.
- Budget: 4,800 AdamW steps, batch 192, learning rate 0.001, weight decay 0.0001.
- Stable class support floor: 32.
- Total: 60 horses.

The selector must pass its existing preflight before any optimizer step: exact
shape and quota equality, no index or feature collisions, true-factor
intervention verification for the declared factor control, finite tensors, and
no training/evaluation overlap.  Selection may use training features, labels
only for fixed action quotas, locked seeds, and declared factors.  It may not
use holdout rows, rewards, gradients, losses, predictions, or post-outcome
fields.

## Frozen gate

Within each held sector and against every control:

1. mean accuracy and stable macro-F1 deltas must be positive;
2. each metric must exceed `max(2 x pooled seed SD, 0.02)` in at least two of
   the three sectors; and
3. anchor accuracy must remain within two percentage points in every sector.

Report matched wins/losses, class support, worst stable accuracy, cross entropy,
gradient cosine, per-layer weight movement, best-step traces, exact exposure,
all bank/checkpoint hashes, and an independent gate recomputation.

The existing generic evaluator emits
`PASS_FACTOR_DATA_MECHANICS_NO_PROMOTION` on a pass; in this campaign that label
means only that the configured random-primary comparison cleared the mechanics
gate.  A miss is `NO_SELECTION`.  Neither result authorizes model promotion,
deployment, execution authority, deletion, or partial unfreezing.  Seeds may
not be appended after outcomes are known.

