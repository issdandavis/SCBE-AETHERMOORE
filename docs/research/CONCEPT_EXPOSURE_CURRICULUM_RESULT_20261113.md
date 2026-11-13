# Concept-exposure curriculum result — 2026-11-13

Status: `COMPLETE_MECHANICS_NO_SELECTION`

Evidence class: `SYNTHETIC_SOURCE_DISJOINT_MECHANICS_ONLY`

No model promotion, partial unfreeze, or execution authority is authorized by
this experiment.

## Question

Does an exposure scheduler that replays under-seen samples and concept-aligned
elite gradients improve a frozen-feature action learner over ordinary uniform,
class-balanced, shuffled-ledger, and random-fixed sampling?

## Fixed protocol

- Three seeds: `11`, `29`, and `47`.
- Six 16x16 shape concepts.
- 740 imbalanced, thin, cardinal-offset training sheets.
- 600 balanced, thick, interstitial-offset holdout sheets from a disjoint
  renderer family.
- 3,000 Adam updates, batch size 64: 192,000 observed train samples per horse.
- One frozen 96-wide feature field and 582 trainable softmax parameters.
- Five matched arms and 15 completed horses.
- Selection required the exposure curriculum to beat every control on accuracy,
  macro-F1, and worst-concept accuracy by more than two pooled standard
  deviations.

## Market result

| Arm | Accuracy | Macro-F1 | Worst concept | Cross entropy |
| --- | ---: | ---: | ---: | ---: |
| uniform | 0.2828 +/- 0.0550 | 0.2259 +/- 0.0647 | 0.0000 +/- 0.0000 | 7.3249 |
| class-balanced | **0.3083 +/- 0.0769** | **0.2571 +/- 0.0874** | 0.0033 +/- 0.0058 | **6.3225** |
| exposure curriculum | 0.2917 +/- 0.0660 | 0.2354 +/- 0.0758 | 0.0033 +/- 0.0058 | 6.8878 |
| shuffled exposure | 0.2867 +/- 0.0593 | 0.2295 +/- 0.0678 | 0.0000 +/- 0.0000 | 7.2310 |
| random fixed | 0.2783 +/- 0.0586 | 0.2180 +/- 0.0695 | 0.0000 +/- 0.0000 | 7.2594 |

Verdict: `NO_SELECTION`.

## What the data says

The experiment did build the requested repeated concept gradients:

- every horse observed exactly 192,000 training samples;
- every sample and every declared variant was seen;
- every concept retained eight elite gradients;
- elite-gradient coherence was approximately `0.97` to `0.997`;
- all 582 trainable scalars changed while the feature field remained frozen.

Those gradients were not broad enough. All arms reached 100% training accuracy,
usually by the first 100-step checkpoint, while final holdout accuracy remained
between roughly 23% and 39%. In 14 of 15 horses, the best holdout-accuracy
checkpoint occurred before the final update; most peaked at step 100 and then
degraded. The learner memorized the thin cardinal renderer rather than folding
translation, thickness, occlusion, and noise into one concept region.

The failure is therefore not "too few repeats." It is repeated exposure to too
few independent views. High elite-gradient coherence here means the fixed views
agree strongly; it does not prove that the gradients span the concept's
transformation orbit.

## Next controlled hypothesis

Build a finite, hash-pinned orbit of transformed sheets for every concept and
replay cells in that orbit, while keeping a separate validation renderer for
checkpoint selection and a final renderer that is never sampled. Test two
claims separately:

1. transformed orbit replay beats matched static-image repetition;
2. the elite-gradient exposure scheduler beats class-balanced replay over the
   same orbit.

The next run must retain equal trainable parameter counts, seed-matched frozen
fields, exact exposure receipts, final source-disjoint evaluation, and the same
two-pooled-standard-deviation selection rule.

## Receipts

- Run: `C:\dev\clay-training-runs\concept-exposure-curriculum-20261113\full-v1`
- Result SHA-256: `2d5c0c65e27680b8e22ee576e3588c1ebaab7bf1db6777e7b7400fd84b67642d`
- Market report SHA-256: `1163dc021d2ba69dd1b27247920af5f9f606aa1bb2827465541a7b648411f92a`
- Dataset manifest SHA-256: `7d2b30f01e64475c2456b9ae2e54a301db1449ddcf415c67c51c843b56fffa9d`
- Campaign SHA-256: `4f15d57799cfbe51cb866997e7077969d277466efe20ded266481b0ad24e6cb0`

