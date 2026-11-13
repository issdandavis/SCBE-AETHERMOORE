# Clay hash-spread specificity preregistration — 2026-11-13

Status: frozen before implementation output, selected data, or model outcomes
are read.

## Hypothesis

Selection over shuffled factor signatures has led the global market in two
independent campaigns.  This run tests whether that advantage is specific to
the shuffled factor-table structure or is captured by a factor-free
deterministic hash spread.

Primary hypothesis: `multiview_factor_shuffled` will outperform
`multiview_hash_spread`, `multiview_random`, and `static_unique` under the same
sector-stratified gate.  A tie with hash spread supports generic dispersion,
not factor-specific structure.

## Locked protocol

- Primary: `multiview_factor_shuffled`.
- Controls: `multiview_hash_spread`, `multiview_random`, `static_unique`.
- Model seeds: `419`, `431`, `443`, `457`, `461`.
- Data seed offset: `6,000,000`.
- Held sectors: `1`, `4`, `7`.
- Rows per arm/fold: 30,000; exactly 10,000 per legal view for multi-view arms.
- Candidate rows: 60,000 per legal view, training source only.
- Held and anchor rows: 10,000 each per fold.
- Learner: ordinary `Linear(37,64) -> GELU -> Linear(64,64) -> GELU -> Linear(64,5)`.
- Budget: 4,800 AdamW steps, batch 192, learning rate 0.001, weight decay 0.0001.
- Stable class support floor: 32.
- Total: 60 horses.

Hash signatures must be derived only from the exact training feature-row digest,
the locked data seed, and the signature-column address.  Column cardinalities
must match the factor-signature columns.  No label may enter the hash except as
the already-required view/action quota partition.  Holdout rows, anchor rows,
reward, post-outcome fields, model losses, and gradients are prohibited.

All multi-view arms must have identical view/action quotas, zero selected-index
and exact-feature overlap, finite tensors, and valid receipts.  The hash arm
must improve normalized hash-cell entropy over both other multi-view arms before
the first optimizer step.  Failure is a zero-compute abort, not a relaxed gate.

## Frozen gate

Within each held sector and against every control:

1. mean accuracy and stable macro-F1 deltas must be positive;
2. each metric must exceed `max(2 x pooled seed SD, 0.02)` in at least two of
   three sectors; and
3. anchor accuracy must remain within two percentage points in every sector.

Report matched wins/losses, worst stable-class accuracy, class support, cross
entropy, gradient cosine, weight drift, best-step traces, true-factor and
hash-space coverage, exact exposure vectors, all bank/checkpoint hashes, and an
independent gate recomputation.

A miss is `NO_SELECTION`.  A pass is
`PASS_SHUFFLED_OVER_HASH_MECHANICS_NO_PROMOTION`.  Neither outcome authorizes
checkpoint promotion, deployment, execution authority, deletion, or partial
unfreezing.  Seeds may not be appended to this run after outcomes are known.
