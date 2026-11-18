# Clay Prime-Scissor Input Trial — System Map

Date: 2026-11-18
Authority: measurement only; no launch, upload, promotion, or partial unfreeze

## Source roots

- Experiment worktree: `C:\dev\_wt_clay_prime_scissor_input_20261118`
  at SCBE base `12dde4d50fcbc700bc88bc6706c7473476104691`.
- Reused exact math component: `C:\dev\_wt_clay_debruijn_shell_20261118`
  at `0a5a06bed57e922f7e9ca04229664266aa8d215c`.
- Reused baseline parents and evaluator surfaces:
  `C:\dev\clay-training-runs\frozen-multiview-adapter-replication-20261114-v1`.
- Runtime Clay data source is supplied by `--source-dir` and accepted only when
  its four hashes match the baseline manifest. The baseline's Windows path is
  never cloud execution authority.

## Causal path

`canonical byte ID`
→ exact `next-cyclic` and `previous-cyclic` prime-slot/scissor receipts
→ dual 912-column integer table
→ exact 205-column affine pivot selection over `F_1000003`
→ constant rail + 205 normalized variables
→ fixed 206-dimensional row
→ learned bias-free `206 → 64` projection
→ addition at the explicitly owned 148 payload positions
→ frozen GRU
→ existing action adapter/head.

The caller supplies a boolean owner mask. Wrappers, targets, padding, and all
autoregressive continuation tokens are false even when a token ID happens to
fall in the private byte-token range. Counting always follows the original
parent embedding.

## Five matched arms

1. dual-policy prime-scissor table;
2. canonical Hadamard table with the candidate's uniform-token spectrum/Gram;
3. candidate table with independent train/held occurrence bindings broken;
4. seeded random directions with each token's candidate row norm;
5. zero table with identical trainable topology.

All arms share parents, samples, deterministic batches, 18,000 steps, optimizer,
projection/adapter/head topology, and trainable scalar count. Conditioning
classes are deliberately reported separately; no blanket equal-conditioning
claim is made.

## Durable surfaces

- Construction/model: `python/scbe/clay_prime_scissor_input.py`
- Resume-safe staged runner: `python/scbe/clay_prime_scissor_input_campaign.py`
- Core tests: `tests/test_clay_prime_scissor_input.py`
- Campaign tests: `tests/test_clay_prime_scissor_input_campaign.py`
- Preregistration:
  `docs/research/CLAY_PRIME_SCISSOR_INPUT_PREREGISTRATION_20261118.md`
- Preflight receipt:
  `docs/research/CLAY_PRIME_SCISSOR_INPUT_PREFLIGHT_20261118.json`

## Cloud execution boundary

The first Kaggle invocation must be `--calibration-only`. It times the slower
shuffled-binding arm for 500 representative batch-128 updates plus held
generation, projects all 15 horses with 20% margin, and refuses a projection
above 24 hours. `--preflight-receipt` is mandatory, and all regenerated tensors,
pivots, conditioning, and split-local bindings must match it bit-for-bit before
calibration. The private calibration packet additionally supplies a deterministic,
hash-pinned frozen-artifact pack so Kaggle loads the exact local float32 tables
and uint8 split bindings instead of rerunning platform-sensitive NumPy SVD or
derangement construction. Sample IDs, tensor hashes, seals, conditioning, and
the preflight authority are rechecked on load. A later invocation may select
explicit `--seed`/`--arm` pairs or
`--max-horses`. The aggregator accepts exactly 15 unique, config-identical horse
receipts and rejects missing, duplicate, revision-mismatched, or model-hash-
mismatched artifacts.

No Kaggle process or material training run was started during this build.
