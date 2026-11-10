# Layer-14A predictive audio preregistration

## Question

Does the typed predictive dual-trit state provide source-disjoint information
about the next 0.5-second audio-energy direction beyond raw current/lag values,
adaptation and omission ablations, shuffled binding, random features, and no
input?

## Fixed boundary

- Sources: the three authority-hashed teacher WAV files in the existing private
  teacher-video corpus.
- Folds: hold out code, lists, and nested-loops audio in turn; the held source
  contributes no probe-training rows or normalization statistics.
- Window: 8,000 samples at 16 kHz (0.5 seconds), no overlap.
- Target: the sign of `score[t+1] - score[t]`; the dead-zone magnitude is the
  33rd percentile of absolute train-source deltas and is fitted separately in
  each fold without held-source access.
- Inputs: every feature row at t is computed from observations through t only.
- Arms: `predictive_trits`, `raw_lags`, `raw_current`, `no_adaptation`,
  `no_omission`, `shuffled_binding`, `random_features`, and `zero_features`.
- Probe: one `Linear(12, 3)` head, 39 parameters, weighted cross entropy, 400
  full-batch updates, and identical optimizer settings for every trained arm.
- Seeds: `202615011`, `202615047`, `202615079`, `202615113`, `202615149`.
- Matrix: 3 folds x 8 arms x 5 seeds = 120 horses.

## Gates

For every held source and every control, the candidate must:

1. have higher balanced accuracy in at least four of five paired seeds;
2. have a mean balanced-accuracy advantage greater than both two pooled seed
   standard deviations and a two-proportion finite-evaluation bound;
3. pass a paired exact prediction test at `p <= 0.05` in at least four seeds;
4. have lower mean cross entropy;
5. retain zero future-perturbation differences in all causal feature-prefix
   tests.

All horses must finish, the independent replay must have zero prediction/loss
mismatches, and every input/checkpoint/ledger hash must verify. Any failure is
`NO_PROMOTION_GATE_FAILED_OR_UNDERPOWERED`.

## Claim boundary

No existing Clay or SCBE weights are changed. The run cannot authorize model
promotion, prime-catalog scoring/training intake, Layer-13 integration, serving,
or partial unfreeze. Automatic transcripts are not used as labels.

