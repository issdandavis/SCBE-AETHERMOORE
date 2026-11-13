# Clay multi-view data confirmation result — 2026-11-13

## Outcome

The corrected confirmation completed all `45/45` optimizer horses and exited
zero.  The ordinary 6,917-parameter MLP learned better source-disjoint action
behavior from independent samples across three legal geometry views than from
either 30,000 unique canonical-view rows or 10,000 canonical rows copied three
times.

The registered verdict remains `NO_SELECTION`.  No checkpoint is promoted and
no layer is partially unfrozen.  The primary arm won every matched seed/fold
comparison, but the preregistered global two-pooled-SD gate pooled three held
sectors with very different task difficulty and did not clear.

## Controlled market

| Arm | Held accuracy | Stable macro-F1 | Worst stable class | Anchor accuracy | Weight L2 drift |
| --- | ---: | ---: | ---: | ---: | ---: |
| `static_unique` | 0.8251 | 0.7024 | 0.4057 | 0.9789 | 11.0188 |
| `static_repeated` | 0.8311 | 0.7076 | 0.4209 | 0.9767 | 10.6721 |
| `curriculum_independent` | **0.8923** | **0.7542** | **0.5055** | 0.9770 | 10.8001 |

Against `static_unique`, independent views gained `+0.06723` accuracy and
`+0.05184` stable macro-F1.  Against `static_repeated`, they gained `+0.06118`
and `+0.04665`.  Accuracy and stable macro-F1 were positive in `15/15` matched
seed/fold pairs against each control.  This sign consistency is a diagnostic,
not a replacement for the registered gate.

Anchor retention passed against both controls.  All 6,917 scalars changed in
every selected model, so the result is a weight effect rather than a static
feature-reporting artifact.

## Why the global gate did not clear

The three held sectors have different class support and difficulty.  Raw held
accuracy varied enough across sectors that the global two-pooled-SD thresholds
were `0.18263` versus `static_unique` and `0.16965` versus
`static_repeated`, larger than the gains.  Stable-F1 thresholds were `0.33627`
and `0.33832`.

Viewed only as a post-run diagnostic, ten of the twelve per-sector
metric/control checks cleared their own two-pooled-SD threshold.  The two misses
were held sector 1 versus `static_unique`.  This does not retroactively change
the preregistered result; it motivates stratifying any future gate before the
next run.

## What the model actually saw

Each horse took `2,400 x 192 = 460,800` training draws.  The 30,000-row unique
and independent banks therefore received 15.36 expected visits per row.  Exact
simulation of all 15 schedules per arm found no unseen rows: row exposure ranged
from 2 to 36, with median 15.  The repeated control exposed each of its 10,000
underlying concepts 19 to 77 times, mean 46.08.

This separates repetition depth from support width:

- `static_repeated`: 10,000 exact feature vectors, each copied three times.
- `static_unique`: 30,000 different canonical-view feature vectors.
- `curriculum_independent`: 10,000 independent vectors from each of three legal
  views.

Across the three folds, training-label total variation between the primary arm
and `static_unique` was only 0.0052 to 0.0090.  There were zero exact feature-row
collisions between any selected training arm and its holdout or anchor bank,
and zero exact cross-arm collisions.

The geometry views are action-equivariant rather than ordinary same-label
augmentation.  The correct action changed somewhere in a three-view latent
orbit for 45.12%, 48.42%, and 44.93% of groups in held folds 1, 4, and 7.
Training uses each transformed row's correct transformed label.

## Learning dynamics

The primary arm's selected steps ranged from 1,400 to 2,400; only 2/15 selected
the final step.  Nevertheless, its last logged interval still reduced mean
training loss by 0.0253 and improved anchor macro-F1 in 10/15 horses.  This is
enough to test a deeper equal-budget exposure schedule, but not to overwrite
the preserved best checkpoints.

## Receipts

- Run: `C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-confirm-v2`
- Campaign SHA-256: `00f5e4015c48319a16874cc2cf5dc378c82ba91d4b9edf9d004f969c8090289d`
- Result receipt: `454a82debf0bf8a8219066ac26fa8a758b89381f268adf0ac8657c08a9d52bbb`
- Result file SHA-256: `b5eadd0cdf7b32f0b13f5401dbc6b67700b5176ef05247eab407de5f55666bf6`
- Verified: 45 horse receipts, 135 checkpoint files, 21 tensor banks, matched
  initial hashes for every seed, and zero verification errors.

