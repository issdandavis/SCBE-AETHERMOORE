# Clay fundamentals data-coverage result — 2026-11-13

## Result

The completed fundamentals portfolio campaign exhausted a static row bank; it
did not grow the support of the concept manifold while training.

Receipt: `63905f743b60ef2a79f9acba9fea19544e2cabeafaa5f5286e8269c87ea2f2eb`

| Held sector | Stored train rows | Draws per horse | Median replays per row | Holdout nearest RMS-z | Same-source anchor RMS-z |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8,000 | 614,400 | 77 | 0.5676 | 0.4787 |
| 4 | 8,000 | 614,400 | 77 | 0.5422 | 0.4774 |
| 7 | 8,000 | 614,400 | 77 | 0.5645 | 0.4765 |

Every reconstructed sampler saw every stored training row. Across seeds, the
least-used row was still drawn 41--45 times and the most-used row 111--115
times. There was no online transform, augmentation, new source family, or new
factor cell after row saturation.

The independent sampled factors were not simply missing. The full
`phase x drive x target` product was present in all three folds, as was
`phase x target x sector`. Some outcome products were sparse, but those include
deterministic policy constraints and cannot be called reachable holes from
occupancy alone.

Exact train/holdout row overlap was zero. The shifted-physics holdout was also
farther from training than the same-source anchor in every fold. The transfer
challenge is therefore real; repeating the same bank cannot densify it.

## Existing control that must not be repeated

The prior `on-policy-geometry-curriculum-20261112-v2` campaign already cycled
cardinal, +22.5 degree, and -22.5 degree worlds for 100,000 environment steps.
It did not produce a successor: mean held reward was 6.3468 for reinforced,
versus 7.0387 frozen, 6.5253 random-fixed, and 6.4435 shuffled-reward. Merely
cycling worlds is therefore not the next hypothesis.

## Next controlled hypothesis

Test paired concept orbits. Present the *same canonical state* through each
training geometry in one gradient unit, compare it with:

1. equal-count unique cardinal rows;
2. repeated cardinal rows;
3. equal-count independently sampled curriculum rows; and
4. the exact paired-orbit rows with their grouping shuffled.

This separates more rows, more views, shared latent identity, and batching
effects. The standard learner, parameter count, optimization budget, held
diagonal source, and same-source anchor must remain fixed. Report gradient
cosine across views, weight drift, accuracy, macro-F1, worst class, and anchor
retention over at least three seeds.

No architecture promotion or partial unfreeze follows from this audit.
