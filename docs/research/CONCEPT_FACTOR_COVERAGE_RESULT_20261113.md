# Concept factor-coverage result — 2026-11-13

Status: `COMPLETE_SYNTHETIC_SIGNAL_NO_PROMOTION`

Evidence class: `SYNTHETIC_SOURCE_DISJOINT_MECHANICS_ONLY`.

No promotion, partial unfreeze, tool dispatch, or execution authority is
authorized.

## Outcome

Explicit cross-factor coverage passed. Adaptive scheduling did not.

| Arm | Accuracy | Macro-F1 | Worst concept | Cross entropy |
| --- | ---: | ---: | ---: | ---: |
| correlated uniform | 0.8639 +/- 0.0095 | 0.8628 +/- 0.0087 | 0.6000 +/- 0.0000 | 0.7047 |
| correlated class-balanced | 0.8522 +/- 0.0146 | 0.8521 +/- 0.0139 | 0.6033 +/- 0.0058 | 0.6613 |
| factor uniform | 0.9622 +/- 0.0107 | 0.9625 +/- 0.0103 | 0.8767 +/- 0.0058 | 0.1188 |
| factor class-balanced | 0.9533 +/- 0.0148 | 0.9540 +/- 0.0138 | 0.8633 +/- 0.0115 | 0.1594 |
| factor exposure | 0.9572 +/- 0.0178 | 0.9578 +/- 0.0168 | 0.8733 +/- 0.0153 | 0.1279 |
| factor shuffled exposure | **0.9644 +/- 0.0082** | **0.9647 +/- 0.0079** | **0.8833 +/- 0.0058** | **0.1140** |

All 18 horses completed with exact exposure totals. Every trainable weight
changed, all fields remained frozen, initial weights and parameter counts were
matched within seed, and holdout metrics never entered training traces.

## Passed claim: factor coverage

`factor_class_balanced` versus `correlated_class_balanced`:

| Metric | Delta | Required delta (2 pooled SD) | Gate |
| --- | ---: | ---: | --- |
| Accuracy | +0.1011 | +0.0294 | PASS |
| Macro-F1 | +0.1019 | +0.0277 | PASS |
| Worst-concept accuracy | +0.2600 | +0.0183 | PASS |

The weak `diag_up` concept rose from a mean `0.6033` to `0.8633` under the
matched class-balanced comparison. Factor arms reached approximately 95--96%
overall accuracy and 86--88% worst-concept accuracy across three seeds.

This supports a precise version of the user's data-folding claim: repeated views
only build a useful concept region when the data schedule covers interactions
between transform axes. Marginal coverage of x and y separately did not replace
coverage of the `x by y` product.

## Non-passed claim: elite-gradient scheduling

`factor_exposure` failed every preregistered scheduler comparison. Relative to
factor class balancing its deltas were only `+0.0039` accuracy, `+0.0038`
macro-F1, and `+0.0100` worst-concept accuracy, all below two pooled standard
deviations. It also trailed factor uniform and the shuffled-ledger arm.

The best current training rule is therefore not the adaptive scheduler. The
useful intervention is the data lattice itself. Until a scheduler beats the
shuffled control, its elite-gradient scores remain diagnostic metadata rather
than a promoted training policy.

## Implication for larger Clay data

Before increasing epochs or model width, data builders should emit a coverage
receipt over the factors that are expected to define a concept: source family,
token/byte view, grammar role, case, sector, transform, and any paired axes. A
large row count can still trace a thin correlated path. Repetition should be
allocated after pairwise or declared higher-order cells are covered, then use
held-out source families to test whether the region transfers.

This run does not prove the same effect on natural images, action traces, or
language tokens. It provides a tested data-control mechanism to apply there.

## Receipts

- Run: `C:\dev\clay-training-runs\concept-factor-coverage-20261113\full-v1`
- Implementation commit: `0d3a05cb8e6e749e8288d73ad9d2454a13f55d4b`
- Result SHA-256: `2259d8087ab80e942f8ebddaee3c84f3ab36945494bd099636731d844fcb110f`
- Market report SHA-256: `928c3f50ffface2023bf300b0e091720a567e141d9dba85a5e2c4ca3ecf9b151`
- Headless config SHA-256: `b8057a36bd56158ca7f22944941228e555feb51861426c00e06a800b09f768a5`

