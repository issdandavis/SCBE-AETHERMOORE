# Concept-exposure curriculum around a frozen feature field

Status: **preregistered; no result at the time of this record**

Date: 2026-11-13

## Five-W definition

- **Who:** a small supervised action/image probe with a frozen random feature
  field and one trainable softmax stitch. It is not the full Clay model.
- **What:** test whether repeated views become more useful when sampling is
  driven by a payload-free concept ledger that measures exposure, transform
  coverage, loss, and aligned improving gradients.
- **When:** after the frozen-component stitch mechanics passed and after the
  prior 8,000-record action campaign showed roughly 76.8 average record
  exposures but did not account for concept-level exposure or saturation.
- **Where:** a source-disjoint synthetic 16x16 shape task. Training and holdout
  renderers use distinct offset/thickness/noise families.
- **Why:** more optimizer steps do not prove that a model saw a concept from
  enough useful directions. The proposed ledger distinguishes blind repetition
  from repeated, transformed evidence that points weights toward a shared
  decision basin.

## Fixed hypothesis

At equal trainable parameter count, optimizer, data, batch size, and update
count, `exposure_curriculum` will improve all three source-disjoint metrics:

1. holdout accuracy;
2. holdout macro-F1; and
3. worst-concept holdout accuracy.

It must beat both ordinary controls (`uniform`, `class_balanced`) and both
structure controls (`shuffled_exposure`, `random_fixed`) by more than two pooled
standard deviations across seeds 11, 29, and 47. Otherwise the verdict is
`NO_SELECTION`; a positive mean alone is not promotion evidence.

## Arms

| Arm | Sampling rule | Purpose |
| --- | --- | --- |
| `uniform` | equal mass per stored training record | Standard empirical-risk baseline; common concepts receive more total views because they own more records. |
| `class_balanced` | equal total mass per concept | Strong ordinary control for the simplest explanation. |
| `exposure_curriculum` | bounded concept, variant, sample, loss, and elite-gradient factors with a 10% uniform exploration floor | Proposed intervention. |
| `shuffled_exposure` | identical adaptive rule over a fixed permutation of concept identities | Tests whether any dynamic reweighting is enough. |
| `random_fixed` | one bounded fixed random distribution with the same exploration floor | Capacity-free routing control. |

All arms share the exact frozen feature projection and initial trainable weights
within a seed. No arm receives more parameters or optimizer steps.

The sealed run uses seeds `11, 29, 47`, 3,000 Adam updates per horse, batch 64,
learning rate 0.003, and a 96-wide frozen random projection. There are 15 horses
(`5 arms x 3 seeds`) and 192,000 record exposures per horse. Logging occurs every
100 updates. These values are fixed before the result run.

## Data and leakage boundary

The task has six geometric concepts rendered into 16x16 float32 sheets. The
training split is deliberately imbalanced and contains repeated noise instances
of declared transform variants. The holdout split is concept-balanced and uses
offsets, thickness, and noise/occlusion rules absent from training.

Training stores 740 sheets with concept counts `240/200/120/80/60/40`; holdout
stores 100 sheets for each concept (600 total). Repetition comes only from the
sampler, so every exposure can be charged back to an exact stored sheet and
declared transform variant.

Every record carries a payload SHA-256, concept, variant, source family, and
split. The ledger indexes only `train` records. It fails closed if a source
family appears in both training and evaluation, and it rejects any attempt to
observe or sample a holdout/anchor ID. Holdout features are used only by the
evaluator.

## Weight and gradient receipts

Each horse records:

- initial/final weight SHA-256;
- L2/L-infinity weight delta and number of changed scalars;
- per-concept exposure count, samples/variants seen, effective exposure count,
  loss EMA, improvement EMA, elite-gradient count/coherence, and saturation;
- training and holdout cross-entropy, accuracy, macro-F1, worst-concept
  accuracy, and calibration error;
- exact dataset, ledger, configuration, and implementation hashes.

An elite gradient is only a bounded sketch from an exposure whose loss improved
relative to that sample's prior EMA. It is routing evidence, not a second label
or a claim of biological learning.

## Authority boundary

This experiment may update only its newly initialized softmax stitch weights.
The frozen projection cannot change. It cannot dispatch tools, enter the action
compiler, promote a checkpoint, unfreeze inherited weights, or admit private
data. A successful result would justify a separately reviewed integration test,
not automatic use in Clay.
