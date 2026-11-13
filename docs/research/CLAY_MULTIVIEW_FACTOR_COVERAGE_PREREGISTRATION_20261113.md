# Clay multi-view factor-coverage preregistration — 2026-11-13

Status: frozen before implementation outcomes or optimizer results are read.

## Hypothesis

Independent legal views helped the action learner, but more exact repetition
did not make the controls catch up.  The next test asks whether selecting a
multi-view bank that covers declared interactions among phase, drive, target,
position, velocity, scope sign, memory, stagnation, and outburst improves
source-disjoint action learning over random multi-view data.

The primary claim is data-level: `multiview_factor` must beat all three declared
controls.  This is not a geometry-layer, scheduler, promotion, or unfreeze test.

## Locked protocol

- Arms: `static_unique`, `multiview_random`, `multiview_factor`, and
  `multiview_factor_shuffled`.
- Primary: `multiview_factor`.
- Seeds: `263`, `277`, `293`, `311`, and `331`.
- Held sectors: `1`, `4`, and `7`.
- Rows per arm/fold: `30,000`.
- Multi-view rows: exactly `10,000` per legal view.
- Candidate pool: `60,000` rows per legal view, training source only.
- Held and anchor rows: `10,000` each per fold.
- Learner: ordinary `Linear(37,64) -> GELU -> Linear(64,64) -> GELU ->
  Linear(64,5)` MLP.
- Steps: `4,800`; batch: `192`; AdamW learning rate `0.001`, decay `0.0001`.
- Stable held class support: at least `32` examples.
- Total: 60 horses.

The random arm establishes the exact `(view, action)` quota table.  Factor and
shuffled-factor arms must match it exactly and must be row-disjoint from each
other and the random arm.  The selector may inspect training inputs and training
labels for quota accounting only.  It may not inspect evaluation rows, rewards,
post-outcome fields, or model gradients.

Before any optimizer step, compute mean normalized entropy across every
observed `(view, action, factor-product)` cell table.  Abort the campaign if the
true factor bank does not exceed both the random and shuffled-factor banks on
this training-only coverage measure, or if any quota/overlap/manifest check
fails.  This prevents spending compute when the proposed data intervention did
not actually alter the declared factor support.

## Gate

Within each held sector and against each control, accuracy and stable macro-F1
must have positive mean deltas.  For both metrics, the delta must exceed the
larger of two pooled seed standard deviations and `2/sqrt(10000) = 0.02` in at
least two of three sectors.  Anchor accuracy must remain within two percentage
points in every sector.

All controls must pass for the mechanics verdict to clear.  Worst stable-class
accuracy, class support, cross entropy, matched wins/losses, gradient coherence,
weight drift, factor-cell coverage, exact exposure counts, and final trace
direction remain mandatory diagnostics.

A miss is `NO_SELECTION`.  A pass is
`PASS_FACTOR_DATA_MECHANICS_NO_PROMOTION`; it does not authorize checkpoint
promotion, execution authority, deployment, deletion, or partial unfreezing.

