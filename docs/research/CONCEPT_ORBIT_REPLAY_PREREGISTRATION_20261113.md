# Concept-orbit replay preregistration — 2026-11-13

Status: frozen before the full run.

Evidence class: `SYNTHETIC_SOURCE_DISJOINT_MECHANICS_ONLY`.

This experiment cannot authorize model promotion, partial unfreeze, tool
dispatch, or execution authority.

## Motivation

The preceding concept-exposure run repeated each fixed training sheet hundreds
of times. It produced highly coherent elite gradients and 100% training
accuracy, but it did not generalize to a disjoint renderer. The data showed that
the learner had built exact-pixel gradients instead of a concept region spanning
translation, scale, small rotation, thickness, contrast, noise, and partial
occlusion.

## Hypotheses

1. At matched optimizer steps, parameters, class counts, and frozen fields,
   replaying a hash-pinned orbit of transformed concept sheets will outperform
   replaying fixed sheets.
2. On the transformed orbit, the elite-gradient exposure scheduler will
   outperform ordinary class-balanced sampling and a shuffled-ledger control.

The two claims are evaluated separately. A benefit from transformed data is not
evidence that the adaptive scheduler caused the benefit.

## Dataset and separation

- Six concepts: horizontal, vertical, both diagonals, plus, and box.
- Static and orbit training banks each contain the same 740 labels with the same
  imbalanced concept counts.
- Static training uses four fixed cardinal translations.
- Orbit training deterministically spans bounded translations, +/-7-degree
  rotations, five scales, one- and two-pixel strokes, four intensities, noise,
  and sparse occlusion.
- A balanced 480-sheet validation family chooses a checkpoint.
- A balanced 600-sheet obscured holdout family is evaluated once after the
  validation checkpoint is restored.
- All four source families, identities, and payload hashes are distinct.
- Validation records are declared `anchor`; validation and holdout records have
  zero sampler mass.

## Frozen field and trainable surface

Every arm in a seed receives the same frozen field and initial weights. The
field concatenates a 64-wide random pixel projection with fixed row, column,
diagonal, anti-diagonal, pooled-grid, and image-moment features. Only one linear
softmax stitch is trainable. This tests data exposure around a fixed sheet
geometry; it does not test full Clay or the governed action compiler.

## Arms

1. `static_uniform`: fixed sheets, empirical class frequency.
2. `static_class_balanced`: fixed sheets, ordinary inverse-frequency sampling.
3. `orbit_uniform`: transformed sheets, empirical class frequency.
4. `orbit_class_balanced`: transformed sheets, ordinary inverse-frequency sampling.
5. `orbit_exposure`: transformed sheets, exposure/loss/elite-gradient scheduler.
6. `orbit_shuffled_exposure`: transformed sheets with shuffled concepts only in
   the scheduler ledger; labels and optimizer targets remain correct.

## Fixed run

- Seeds: 11, 29, 47.
- 1,500 Adam updates per horse.
- Batch size: 64.
- Initial learning rate: 0.003.
- Shared cosine cooling to 10% of the initial rate.
- Validation every 50 updates and at update 1.
- Validation checkpoint ordering: macro-F1, then worst-concept accuracy, then
  lower cross entropy.
- Six arms x three seeds = 18 horses and 96,000 observed train records per horse.

## Gates

Primary metrics are holdout accuracy, macro-F1, and worst-concept accuracy.

- The orbit-data claim compares `orbit_class_balanced` against
  `static_class_balanced`.
- The scheduler claim compares `orbit_exposure` against every other arm.
- A claim passes only if every primary metric improves by more than two pooled
  sample standard deviations across the three seeds.
- Aggregate gains, single-seed wins, perfect training fit, or coherent gradients
  alone do not pass.

Regardless of result, this synthetic run writes weights and receipts only under
its run directory and does not replace or promote an existing Clay checkpoint.

