# Clay random multi-view confirmation result — 2026-11-13

## Outcome

The preregistered random-selector hypothesis did **not** pass its all-controls
gate.  Random multi-view data robustly beat one static canonical sheet, but it
was statistically indistinguishable from shuffled multi-view data and did not
clear the declared noise bound over semantic factor selection.  The producer
and independently rebuilt verdicts are both `NO_SELECTION`.  No checkpoint is
promoted, no layer is partially unfrozen, and no execution authority changes.

Run:
`C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-random-confirm-v1`

- Campaign: `7e7652ef3747248dc6032c3bc6370d4d362596328e8726d230cb93ac5a3694e4`.
- Result: `890213ea0d22920863c9d9f5e5b182eb71689a14f75568324ef5d10a96ad7fce`.
- Gate: `8280b478e07d3f39e5af999a3d0922d8bb4407cf6144325ca137d044a4527fdb`.
- Independent inference audit:
  `532b1628c8e7c3e2e6872ae05596c02f3147965448426f21059229f81c6942c0`.
- Exact exposure audit:
  `356f4bb23d220e4d4169a5f3a6fe6a77be21c7978dbdb5f7f5f6d57f200dbd73`.

## Global market

| Data arm | Held accuracy | Stable F1 | Worst stable | Cross entropy | Anchor accuracy | Gradient cosine | Weight drift |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| static unique | 0.8397 | 0.7154 | 0.4509 | 0.5353 | **0.9808** | -0.0815 | **14.4911** |
| random multi-view | **0.9147** | **0.7746** | 0.5133 | **0.2634** | 0.9796 | 0.0227 | 14.4546 |
| semantic factor | 0.8597 | 0.7297 | 0.4403 | 0.3499 | 0.9589 | **0.2811** | 11.2918 |
| shuffled factor | 0.9085 | 0.7740 | **0.5221** | 0.4331 | 0.9798 | -0.0396 | 12.7821 |

All arms used the same 6,917-parameter ordinary MLP, 30,000 unique training
rows per fold, 4,800 AdamW steps, five fresh model seeds, three held sectors,
and 10,000-row held and anchor banks.  Every horse changed all learned scalars.

## Sector evidence

| Held sector | Arm | Accuracy | Stable F1 | Worst stable | Anchor accuracy |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | static | 0.7764 | 0.8201 | 0.6681 | 0.9795 |
| 1 | random | **0.8823** | 0.9005 | 0.7670 | 0.9779 |
| 1 | factor | 0.7837 | 0.8257 | 0.6538 | 0.9583 |
| 1 | shuffled | 0.8788 | **0.9023** | **0.7987** | 0.9778 |
| 4 | static | 0.9632 | 0.5014 | 0.0000 | 0.9798 |
| 4 | random | 0.9869 | 0.5246 | 0.0036 | 0.9786 |
| 4 | factor | 0.9844 | 0.5169 | 0.0000 | 0.9577 |
| 4 | shuffled | **0.9872** | **0.5322** | **0.0071** | 0.9800 |
| 7 | static | 0.7797 | 0.8246 | 0.6846 | 0.9831 |
| 7 | random | **0.8750** | **0.8987** | **0.7694** | **0.9824** |
| 7 | factor | 0.8109 | 0.8464 | 0.6671 | 0.9606 |
| 7 | shuffled | 0.8596 | 0.8877 | 0.7605 | 0.9816 |

Sector 4 remains a warning against headline accuracy.  Random reached 0.9869
accuracy while its worst stable class remained at 0.0036.  The data recipe
improved broad transfer without solving that minority-action bottleneck.

## Registered comparisons

| Random minus control | Accuracy delta | 2x pooled SD | Stable-F1 delta | 2x pooled SD | Matched acc wins | Matched F1 wins |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| static unique | **+0.07497** | 0.15546 | **+0.05924** | 0.34267 | **15/15** | **15/15** |
| semantic factor | +0.05505 | 0.16119 | +0.04495 | 0.34332 | 14/15 | 13/15 |
| shuffled factor | +0.00617 | 0.12121 | +0.00056 | 0.36226 | 9/15 | 6/15 |

The global two-pooled-SD test is conservative because it mixes three sectors
with very different class geometry.  The preregistered stratified gate therefore
decides the result.  Random cleared both accuracy and stable-F1 gates in all
three sectors against static.  Against factor it cleared both metrics only in
sector 1.  Against shuffled it cleared no sector and had negative deltas in
sector 4.  Because every declared control had to pass, the correct campaign
verdict is `NO_SELECTION`.

## What changed in weights and outputs

Random's transfer gain over static did not come from simply moving farther:
mean best-checkpoint drift was 14.4546 for random and 14.4911 for static.
Likewise, semantic factor selection produced the highest gradient cosine
(0.2811) while learning worse outputs and losing about 2.1 anchor points.
Neither raw movement nor cross-view gradient agreement is a sufficient target.

The useful causal distinction is at the data boundary.  Static and random used
the same row count, update count, model, initialization groups, and exposure
schedules.  Random supplied 10,000 rows from each of three legal views; static
supplied 30,000 unique rows from one view.  Random won every matched transfer
comparison against static.  However, two other multi-view selectors performed
similarly, so this result supports **legal view diversity**, not random sampling
as a unique mechanism.

## Independent inference replay

The new verifier imports neither the campaign producer, its model class, its
metric helper, nor its gate.  It:

- hash-checked the four pinned Clay authority sources;
- regenerated all six 10,000-row held/anchor banks from the declared seeds;
- verified 24 saved bank manifests and three selection contracts;
- reopened 180 initial/best/final checkpoints read-only;
- evaluated all 60 best checkpoints through explicit matrix multiplies and the
  exact GELU equation;
- emitted 120 per-split prediction-ledger receipts;
- reproduced every confusion matrix and metric with maximum absolute float
  difference `1.1920928955078125e-07`; and
- independently reproduced the complete aggregate and stratified gate.

Prediction-ledger set:
`b4a41418f4db9419d8903c73ebd486a22681a209290c2b866fa0332b3352a66b`.

Independent audit file SHA-256:
`4aff23ce3173da7e7fba2d8b0378b67d3f190e38da99630391f6595da31ba3cb`.

## Exact exposure replay

The outcome-blind exposure auditor reconstructed 15 seed/fold schedules.  Each
horse drew exactly 921,600 positions from a 30,000-row bank, every row was seen,
and all four matched arms shared the same positional schedule for a given
seed/fold.  The selected support differed; training opportunity did not.

Exposure audit file SHA-256:
`38f7738573d607b733d1cded8579d9a94bc37a2df93df8397829eff702776735`.

## Consequence for the next run

Do not run another selector race.  The selector-specific hypotheses are now
closed at this budget.  The next legitimate bridge is a fresh, source-disjoint
frozen-input-adapter campaign that tests the confirmed **multi-view versus
static-view support** distinction while retaining the deterministic compiler
fallback and the existing equal-shape null/no-intervention controls.  It must
use new data and model seeds, independent inference replay, and fail closed.

