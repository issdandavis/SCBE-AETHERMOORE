# Clay frozen multiview adapter independent replication

Date: 2026-11-14

Status: `PREREGISTERED_NOT_STARTED`

Authority: measurement only; no execution, promotion, merge, serving, or partial unfreeze

## Prior result disclosure

The first fixed three-seed campaign (`20261131..20261133`) completed before this
document was written. Its multiview arm learned the source-disjoint action task
relative to the null and untouched controls, but did not beat the
parameter-matched static arm by the required two-pooled-standard-deviation
margin. Accuracy was `0.218000` versus `0.209333` (delta `+0.008667`, required
margin `0.019414`), and the paired exact two-sided p-value was approximately
`0.3141`. No promotion was authorized.

This run is therefore an independent replication, not an optional-stopping
extension of the first result. Its verdict must be reported separately before
any descriptive cross-run summary is made.

## Fixed question

Under the unchanged source-disjoint action dataset and frozen counting core,
does the legal three-view adapter beat both:

1. the equal-parameter static representation; and
2. the null/no-intervention controls?

The geometry-specific claim requires success against the static arm. Learning
relative to null alone is not sufficient.

## Fixed configuration

- Replication seeds: `20261134,20261135,20261136`.
- Dataset seed: `20261113`.
- Rows per training view: `1000`.
- Source-disjoint holdout rows: `1500`.
- Counting steps: `28000`.
- Adapter-growth steps: `18000`.
- Checkpoint interval: `500`.
- Batch size: `128`.
- Learning rate: `0.002`.
- CPU threads: `2`.
- Storage admission floor: `25.0 GiB`; it must not be lowered.
- Arms: untouched parent, equal-parameter static adapter, legal multiview
  adapter, and matched-schedule null adapter.

The launch manifest must hash-bind the runner, this preregistration, source
files, dataset manifest, vocabulary, and exact configuration. Existing parent
or child checkpoints are not inputs to the replication.

## Fixed evaluation and controls

Primary metrics are source-disjoint accuracy and macro F1. For each metric, the
multiview-minus-static mean must be positive and exceed `2 * pooled_sd` across
the three new seeds. The per-example paired exact sign test is reported as an
additional finite-sample check; it cannot rescue a failed pooled-SD gate.

The multiview arm must also beat the null and no-intervention controls under the
same margin. Counting retention must remain exact for every trained arm, and
all frozen-core hashes must remain bit-identical to their parents.

All three seeds and all four arms must finish. There is no metric-triggered
early stop, seed replacement, hyperparameter change, or selective rerun. A
crash may resume only from its own hash-bound checkpoint.

## Claim boundary

- A failed or underpowered replication is retained, not discarded.
- The original and replication campaigns are reported separately.
- No weights are promoted automatically, even if every gate passes.
- Prime-token prospective data remains outside this run; its independent
  30-query gate stays closed.
- Deterministic Clay labels remain the only action authority.
