# Clay paired concept-orbit data preregistration — 2026-11-13

## Prior evidence

The fundamentals portfolio campaign drew 614,400 samples per horse from a
fixed 8,000-row bank. Every sampler exhausted that bank and replayed each row a
median 77 times, but no online transformation expanded support. The shifted
diagonal holdout was farther from training than a same-source anchor in all
three held-sector folds.

An earlier 100,000-step on-policy curriculum already cycled cardinal and
plus/minus 22.5-degree worlds. Reinforced held reward (6.3468) did not beat
frozen (7.0387), random-fixed (6.5253), or shuffled-reward (6.4435). This test
therefore does not ask whether merely cycling worlds helps.

## Hypothesis

The missing intervention is a complete local concept orbit: the same canonical
state rendered through each of the three legal training geometries inside one
gradient unit. If this creates useful cross-view gradients, paired grouping
should beat both static replay and the exact same paired rows trained with
their grouping removed.

## Fixed learner and data arms

Every arm uses an ordinary `Linear(37,64) -> GELU -> Linear(64,64) -> GELU ->
Linear(64,5)` MLP, AdamW, identical initialization per seed, and the same row,
step, and batch budget.

1. `static_unique`: equal-count unique cardinal states; standard control.
2. `static_repeated`: one cardinal state repeated three times per latent group.
3. `curriculum_independent`: equal numbers from cardinal, +22.5, and -22.5
   worlds, but independently sampled latent states.
4. `paired_orbit_shuffled`: exact paired-orbit tensors with ordinary row
   sampling.
5. `paired_orbit_grouped`: same tensors, but every sampled latent state brings
   all three views into the batch.

The paired arms are byte-identical data. Only batching/group identity differs.
All banks exclude the held angular sector. The 45-degree shifted-physics source
appears only in final evaluation. A separate cardinal anchor selects
checkpoints and measures retention.

## Measurements

- held accuracy, macro-F1, worst-class accuracy, and cross-entropy;
- cardinal-anchor retention;
- cosine similarity among the three per-view gradient vectors;
- exact initial/best/final weight hashes, changed scalars, and L2 drift;
- per-arm dataset and source-code hashes;
- three seeds and held sectors 1, 4, and 7.

## Gate

The paired-grouped arm must beat every control on held accuracy and macro-F1 by
more than twice pooled standard deviation and remain within two anchor-accuracy
points. Otherwise report `NO_SELECTION`; do not call an underpowered difference
a refutation. No result authorizes model promotion, deployment, or partial
unfreeze.
