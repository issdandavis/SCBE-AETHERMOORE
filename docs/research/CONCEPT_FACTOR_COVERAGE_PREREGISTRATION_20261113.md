# Concept factor-coverage preregistration — 2026-11-13

Status: frozen before the full run.

Evidence class: `SYNTHETIC_SOURCE_DISJOINT_MECHANICS_ONLY`.

No promotion, unfreeze, tool dispatch, or execution authority can be granted by
this experiment.

## Triggering observation

The transformed-orbit campaign passed its data-diversity gate, but all orbit
arms remained at about 60% on `diag_up`. Saved-weight replay localized all 40
errors to the two same-sign corner translations `(-2,-2)` and `(2,2)`. The
training transform chose x and y offsets with two modular formulas. It covered
every marginal offset while tracing only a correlated subset of their Cartesian
product.

The missing test is whether explicit cross-factor coverage—not more steps,
parameters, or scheduler complexity—closes that hole.

## Intervention

Keep the original correlated orbit as the baseline. Build an equal-size factor
orbit with the same 740 labels, class counts, transform ranges, noise scale, and
optimizer budget. In the factor orbit, enumerate the 7x7 `dx x dy` product
before repetition and phase angle, scale, thickness, intensity, and occlusion
around that product.

The 80-record `diag_up` class therefore sees every offset pair at least once.
The 40-record box class remains capacity-limited to 40 of 49 pairs; this is
declared rather than hidden.

Both data banks share one calibration tensor, frozen feature field, initial
weights, validation family, and final holdout family within each seed.

## Arms

1. `correlated_uniform`
2. `correlated_class_balanced`
3. `factor_uniform`
4. `factor_class_balanced`
5. `factor_exposure`
6. `factor_shuffled_exposure`

The first claim compares `factor_class_balanced` with
`correlated_class_balanced`. The second, independent scheduler claim compares
`factor_exposure` with every other factor arm.

## Fixed protocol

- Seeds 11, 29, and 47.
- 1,500 Adam updates, batch size 64.
- Initial learning rate 0.003 with common cosine cooling to 10%.
- Validation-only checkpoint selection every 50 updates.
- Final holdout evaluated only after restoring the validation checkpoint.
- Six arms x three seeds = 18 horses and 96,000 train exposures per horse.

## Gates

Primary metrics are holdout accuracy, macro-F1, and worst-concept accuracy. A
claim passes only if all three improve by more than two pooled sample standard
deviations over every declared control. A single-seed win, a lower cross
entropy, or closing one concept hole does not independently pass.

