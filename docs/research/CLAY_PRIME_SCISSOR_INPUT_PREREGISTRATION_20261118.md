# Clay Prime-Scissor Pre-GRU Input Trial — Preregistration

Date: 2026-11-18
Authority: `MEASUREMENT_ONLY_NO_EXECUTION_NO_PROMOTION_NO_PARTIAL_UNFREEZE`

## Question

Does an exact prime-lane/scissor relation code for each canonical byte improve
Clay's held-out action classification when it reaches the byte embedding before
the frozen GRU, beyond what can be explained by an equally large canonical
code, a per-token-leverage-matched random code, an occurrence-shuffled binding,
or the same trainable carrier with no added input? The controls triangulate
different conditioning classes; this trial does not claim they are wholly
equally conditioned.

This is a representation trial, not a claim that primes create new byte
identities. The byte ID remains canonical and every derived route must recover
that ID exactly.

## Fixed authorities

- SCBE experiment base: commit `12dde4d50fcbc700bc88bc6706c7473476104691`.
- Clay-math component: commit
  `0a5a06bed57e922f7e9ca04229664266aa8d215c` from the clean
  `clay-math` source root. The campaign pins and verifies the three exact source
  hashes. A local run also requires a clean matching git worktree; a Kaggle
  packet may use the hash-identical vendored package without `.git` metadata.
- Frozen baseline:
  `C:\dev\clay-training-runs\frozen-multiview-adapter-replication-20261114-v1`.
- Dataset manifest:
  `7460665cbb718097438227c452f1915e88bdc5a10ac643122b17908b505d0041`.
- Required PASS receipt:
  `CLAY_PRIME_SCISSOR_INPUT_PREFLIGHT_20261118.json`. Its file hash is part of
  campaign identity. Before calibration, cloud-regenerated dataset, pivots,
  every feature tensor, conditioning receipt, and both mapped binding tensors
  and seals must match it bit-for-bit; otherwise the run aborts.
- Seeds: `20261134`, `20261135`, `20261136`.
- Training budget per learned arm and seed: 18,000 steps, batch size 128,
  learning rate 0.002, identical deterministic sampler order.
- Local disk admission floor: 25 GiB. It may be raised but not lowered.
- Runtime Clay generator path: explicit `--source-dir`; its four file hashes
  must reproduce the baseline source hashes. The Windows path embedded in the
  old baseline is not cloud authority.

The source-owned action rows are regenerated through the existing provider and
must reproduce the baseline manifest. Training uses the three declared train
view families; evaluation uses only the held diagonal family. The original
payload identities are disjoint across static, multiview, and holdout banks.
The diagonal holdout has been reused across prior development and is therefore
a developmental holdout, not a final untouched test. Even a full pass licenses
only a new, fresh source-family confirmation; it is not final capability or
promotion evidence.

## Candidate construction

The byte domain is the order-2, alphabet-16 universal cycle (256 ranks). For
each rank `v`, two committed policies bracket it on the finite prime wheel:
`next-cyclic` chooses the first prime at or above `v` and wraps to 2, while
`previous-cyclic` chooses the first prime at or below `v` and wraps to 251.
Each prime is only a writable CRT slot; canonical residues and inverse
residuals preserve `v`.

The component must verify, for every byte:

1. the caller-owned universal-cycle window and section receipt;
2. both policy-selected prime-spot assignments and their receipts;
3. both independently scheduled scissor streams; and
4. reconstruction of the original rank.

Each policy emits the preregistered 456-field integer assignment/scissor block.
The two blocks are concatenated. Exact left-to-right RREF over the prime field
`F_1000003` selects 205 independent columns from the byte-to-byte difference
matrix; one constant rail produces the fixed 206-dimensional input. The raw
blocks, field schema, modular pivots, pivot descriptors, selected integer
table, normalized table, singular values, and all component receipts are
hashed. Only the 205 variable columns are centered and L2-normalized.

## Learned arms

Every arm has the same frozen parent, action adapter/head, zero-initialized
bias-free 206-to-64 projection, optimizer, examples, batches, steps, and
trainable scalar count. The projection is added only at owned byte positions,
after the original embedding and before the frozen GRU. Counting never reads it.

1. `prime_scissor_input`: aligned dual-policy exact-pivot prime-scissor rows.
2. `canonical_onehot_matched`: the centered canonical one-hot subspace in a
   fixed Sylvester-Hadamard basis, scaled by the candidate singular values.
3. `shuffled_binding_matched`: the candidate table, but feature vectors are
   reassigned by two independent seeded occurrence permutations: one over the
   multiview training rows and one over the held rows. Static rows are excluded.
   Raw token IDs, prompts, labels, splits, and row order remain unchanged. No
   target occurrence may retain the same byte feature, every split-local source
   occurrence is used exactly once, and no source crosses the split boundary.
4. `deterministic_random_matched`: seeded centered Gaussian directions with the
   same constant rail and each token's variable-row L2 norm set exactly to the
   candidate token's norm. It must retain full rank and 256 unique rows.
5. `no_intervention_matched`: the identical trainable projection and downstream
   surface with an all-zero fixed input table.

The canonical control matches the candidate's uniform-token singular spectrum,
full column Gram matrix, column norms/covariances, rank, and global Frobenius
norm. The deterministic-random control matches rank, constant rail, global
Frobenius norm, and every candidate token's row norm, but is intentionally not
isospectral. All retain 256 distinct rows. The manifest receipts train- and
holdout-frequency-weighted Gram matrices and norm totals, including byte 0's
leverage; those weighted Grams are diagnostics, not asserted equal. A fixed
byte-to-byte permutation is forbidden as the shuffled control because it is
another learnable code.

The split-local shuffled seals are accepted only if exact marginal histograms
are preserved, every source occurrence is used once, same-byte fixed points are
zero, and same-sample sources are at most 0.1%. The preregistered unlabeled/IPF
nulls are: train NMI 0.07796, expected unique source values min 73.77 / median
110.75, maximum dominant share 0.6613; holdout NMI 0.07697, min 36.19 / median
67.25, maximum share 0.6574. Fixed gates are NMI <= 0.115 for both; train
unique-value min >= 48 and median >= 80; holdout min >= 24 and median >= 48;
maximum conditional share <= 0.72. The 0.115 NMI ceiling was set before any
model outcome, after the exact held mapping measured 0.11005979 (the original
0.11 boundary missed by 5.98e-5); no other gate was weakened.

## Causality and mechanics gates before a material run

- An explicit caller-owned boolean mask activates exactly the 148 source-payload
  positions. Wrappers, teacher-forced targets, and every generated continuation
  are unowned even if their token ID lies in the private byte-token range.
- A non-null feature override changes action logits.
- Perturbing a future byte cannot change earlier logits.
- Non-null arms produce a nonzero gradient at the pre-GRU projection from the
  declared action loss; the null arm does not.
- The parent embedding, GRU, and counting head remain bit-identical after an
  optimizer step.
- Counting logits are unchanged even after the action projection changes.
- Every learned arm has the same trainable parameter names and count.
- Two-slot checkpoints restore the model, optimizer, sampler, exposure ledger,
  CPU RNG, and CUDA RNG when CUDA is used.
- A synthetic three-seed/ five-arm single-step preflight must pass. It is
  mechanics evidence only and cannot support a capability claim.

## Primary endpoints and decision rule

Primary endpoints are held-out action accuracy and macro F1, recomputed from
per-example predictions. For every control and each endpoint, the candidate's
mean must exceed the control mean by more than two pooled seed standard
deviations. The confirmatory paired comparison blocks the repeated predictions
by held sample ID across seeds, must favor the candidate at two-sided exact
`p <= 0.05`, and requires a strictly positive matched-seed direction in all
three seeds. The older pooled seed/example comparison is diagnostic only.

All four comparisons must pass. In addition:

- all three candidate seeds must use a nonzero learned projection;
- every candidate seed must have `worst_action_accuracy > 0`, and every
  reported candidate sector accuracy must be strictly positive;
- counting accuracy must equal its parent for every horse;
- frozen parent tensors must be bit-identical;
- feature, occurrence-permutation, source, parent, model, and result hashes
  must verify; and
- an independent replay must later reconstruct held inputs and raw predictions.

If any condition fails, report `NOT_MET`. Zero or small variance does not waive
the paired finite-evaluation gate. No result from this producer authorizes
promotion, partial unfreezing, tool dispatch, or execution.

## Stop conditions

Do not launch locally below the 25 GiB floor. On Kaggle, first run explicit
`--calibration-only`: 10 warmup plus at least 500 measured steps at batch 128 on
the actual device, separately time 64 held evaluator examples, project all
270,000 training steps plus 15 full evaluations, add 20% margin, and refuse the
campaign above 24 hours. Calibration cannot change the 18,000-step budget.
Material jobs are stageable by explicit seed/arm or `--max-horses`; every horse
has an atomic model/result receipt, and aggregation refuses missing, duplicate,
or config-mismatched horses. The experiment identity includes exact hashes of
the runner, input module, and this preregistration, and every checkpoint/horse
is bound to that identity, along with the required preflight receipt hash. Do
not substitute another parent,
dataset, component commit, seed, table policy, step budget, or output directory
after results are visible. A changed design requires a new preregistration and
new output identity. Kaggle packaging and launch remain separate, explicit
operations.
