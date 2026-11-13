# Concept-orbit replay result — 2026-11-13

Status: `COMPLETE_SYNTHETIC_SIGNAL_NO_PROMOTION`

Evidence class: `SYNTHETIC_SOURCE_DISJOINT_MECHANICS_ONLY`.

No model promotion, partial unfreeze, or execution authority is authorized by
this result.

## Outcome first

Transformed data replay passed its preregistered control gate. The adaptive
elite-gradient scheduler did not.

| Arm | Accuracy | Macro-F1 | Worst concept | Cross entropy |
| --- | ---: | ---: | ---: | ---: |
| static uniform | 0.3111 +/- 0.0042 | 0.1567 +/- 0.0031 | 0.0000 +/- 0.0000 | 6.3115 |
| static class-balanced | 0.3150 +/- 0.0029 | 0.1594 +/- 0.0027 | 0.0000 +/- 0.0000 | 5.6735 |
| orbit uniform | 0.8594 +/- 0.0107 | 0.8586 +/- 0.0098 | 0.6000 +/- 0.0000 | 0.6961 |
| orbit class-balanced | 0.8494 +/- 0.0136 | 0.8494 +/- 0.0129 | 0.6033 +/- 0.0058 | 0.6621 |
| orbit exposure | **0.8650 +/- 0.0029** | **0.8639 +/- 0.0023** | 0.6000 +/- 0.0000 | **0.6497** |
| orbit shuffled exposure | 0.8639 +/- 0.0063 | 0.8627 +/- 0.0062 | 0.6000 +/- 0.0000 | 0.7488 |

All 18 horses completed, all exposure totals were exact, all trainable weights
changed, every feature field remained frozen, initialization and parameter
counts were matched within seed, and holdout metrics were absent from every
training trace.

## Passed claim: view diversity matters

Against the matched class-balanced static arm, the class-balanced transformed
orbit improved:

| Metric | Delta | Required delta (2 pooled SD) | Gate |
| --- | ---: | ---: | --- |
| Accuracy | +0.5344 | +0.0196 | PASS |
| Macro-F1 | +0.6900 | +0.0186 | PASS |
| Worst-concept accuracy | +0.6033 | +0.0082 | PASS |

This supports the narrow claim that repeatedly showing transformed views folds
more of a visual concept into the trainable stitch than repeatedly showing the
same fixed pixels. It does not establish a full-model, natural-image, action, or
language gain.

## Non-passed claim: adaptive scheduling

`orbit_exposure` did not beat the strong orbit controls by the preregistered
margin:

- versus orbit class balancing, accuracy improved `+0.0156`, below the required
  `+0.0196`;
- macro-F1 improved `+0.0144`, below the required `+0.0185`;
- worst-concept accuracy decreased `-0.0033`;
- it was statistically indistinguishable from the shuffled-ledger and uniform
  orbit arms.

The honest verdict is therefore `ORBIT_DATA_SIGNAL_ONLY`, not a scheduler win.

## Data-level diagnosis

The remaining floor was not random. Every orbit arm classified exactly about
60% of `diag_up`. Saved-weight replay showed that the failures were the 40
holdout records whose translation indices were `0` or `4` in the five-position
offset cycle: the `(-2,-2)` and `(2,2)` placements. The current training orbit
uses two modular offset formulas that trace only a correlated subset of the
`dx x dy` product. It covers the marginal x and y values but leaves pairwise
holes. The learner therefore saw many transformed images without seeing the
specific cross-axis placements needed by those holdout sheets.

This is an important qualification: a large transform count is not the same as
coverage of the transform lattice. The next data experiment should compare the
current correlated sequence with an equal-size factor-balanced or covering-array
sequence that explicitly covers each `dx x dy` pair before repetition. That
test should leave the optimizer, frozen field, evaluation families, and compute
budget unchanged.

## Receipts

- Run: `C:\dev\clay-training-runs\concept-orbit-replay-20261113\full-v1`
- Implementation commit: `4fbc0686fcc13467b060b3b1e70e55af3ca1c769`
- Result SHA-256: `00553fcf21da2936b1138d51d3882a44bc9afcb4b61c3f2fc5f3973ca6fb9671`
- Market report SHA-256: `fb0cd2f7883e3a44553fde35f44983a8a500e27cfc2788b285cb688658af08f3`
- Headless config SHA-256: `1803bcb00567fdb721fc0d298b9a4f46ba009c725cf57defe8b04d84489ee093`

