# Clay multi-view exposure-depth result — 2026-11-13

Status: `COMPLETE_MECHANICS_NO_SELECTION`

No checkpoint is promoted, no layer is partially unfrozen, and no execution
authority is granted by this experiment.

## Outcome

Doubling the optimizer budget did not make exact repetition catch independent
multi-view data.  The independent three-view arm retained the best aggregate
held performance and beat the exact-repetition arm in all 15 matched
seed/fold comparisons on accuracy and stable macro-F1.

| Data arm | Held accuracy | Stable macro-F1 | Worst stable class | Anchor accuracy | Weight L2 drift |
| --- | ---: | ---: | ---: | ---: | ---: |
| `static_unique` | 0.8245 | 0.7027 | 0.3991 | 0.9800 | 14.7662 |
| `static_repeated` | 0.8073 | 0.6880 | 0.3605 | 0.9771 | 14.6085 |
| `curriculum_independent` | **0.8774** | **0.7463** | **0.4561** | 0.9791 | 14.5287 |

Against `static_unique`, the primary arm gained `+0.05286` accuracy and
`+0.04366` stable macro-F1, winning 14/15 matched pairs on both metrics.
Against `static_repeated`, it gained `+0.07012` and `+0.05829`, winning 15/15
matched pairs.  Every selected model changed all 6,917 trainable scalars.

The preregistered stratified verdict is still `NO_SELECTION`.  The candidate
had a positive mean accuracy and stable-F1 delta in every sector and retained
the anchor within two points everywhere, but it did not clear the noise floor
against `static_unique` in the required two of three sectors.

## Stratified gate

| Control | Held sector | Accuracy delta / required | Stable-F1 delta / required | Result |
| --- | ---: | ---: | ---: | --- |
| repeated | 1 | +0.08742 / 0.05734 | +0.06986 / 0.05074 | clears |
| repeated | 4 | +0.02402 / 0.02000 | +0.02645 / 0.02000 | clears |
| repeated | 7 | +0.09892 / 0.11386 | +0.07855 / 0.09238 | below noise floor |
| unique | 1 | +0.05640 / 0.07191 | +0.04449 / 0.05995 | below noise floor |
| unique | 4 | +0.02368 / 0.02000 | +0.02581 / 0.02000 | clears |
| unique | 7 | +0.07850 / 0.09182 | +0.06067 / 0.07353 | below noise floor |

The candidate passed the complete gate against exact repetition, but only
sector 4 cleared both metrics against the unique-row control.  This is a
variance-qualified data signal, not a promoted model result.

## What the model actually saw

Each horse received `4,800 x 192 = 921,600` optimizer observations.  Exact
schedule replay over all 45 horses found:

- every stored row was seen;
- 30,000-row arms received 11--58 visits per row, with median 31;
- the repeated arm's 10,000 underlying concepts received 55--140 visits, with
  median 92;
- no train row exactly matched the holdout or anchor;
- no selected training arm shared an exact row with another arm;
- no selected training row appeared in the preceding confirmation run.

The legal geometry views are action-equivariant.  The correct action changed
somewhere in the three-view orbit for 45.72%, 48.07%, and 44.75% of latent
states in held folds 1, 4, and 7.  The learner therefore had to see both the
state and the frame/action transformation; replaying one canonical vector did
not supply that relation.

The simple discrete-factor audit found near-complete marginal and pairwise
coverage in all 30,000-row banks.  The only holdout `action x phase` cell absent
from every held-7 training arm contained one evaluation record.  The remaining
gap is therefore not explained by an obvious large missing pairwise cell.  It
is consistent with continuous boundary difficulty, source shift, and
sector-dependent action support.

## Interpretation for data folding

Repeated exposure does build gradients, but it only densifies the support the
model has already seen.  The controlled image-like shape experiments in this
repository make the distinction explicit:

- static replay reached 100% training accuracy while source-disjoint accuracy
  remained near 30%;
- transformed-orbit replay raised accuracy to about 86%;
- covering the `x by y` transform product raised it to about 96% and improved
  the weak concept from about 60% to 86--88%;
- the adaptive elite-gradient scheduler did not beat its shuffled or ordinary
  orbit controls.

The supported rule is therefore **cover the concept's transformation lattice,
then replay it**.  A high exposure count, row count, or coherent gradient is not
enough when the data traces a thin correlated path through the concept region.

## Receipts

- Run: `C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-depth-confirm-v1`
- Campaign SHA-256: `eef66a7b0acc5fba659962b9a7cb1c87e2679470741f523c61b7727cf6ee2c3c`
- Producer result receipt: `d0d63af14275da8b69590ae13115d60464aeb01fe7607752a13e9b0d3c3141dd`
- Result file SHA-256: `693a0cc89680aefece71372838381cdfd8e671cd19fb98f97f2a16f51561c63a`
- Stratified gate SHA-256: `54c99b17f63fda0dcace998dce6b7b4529e52d80bf33e86074c043a2a380e379`
- Verified: 45 horse receipts, 135 checkpoint state hashes, 21 tensor-bank
  manifests, 15 matched initialization groups, and zero verification errors.

