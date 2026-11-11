# Prime-token frozen input-access implementation — 2026-11-11

Status: `MECHANICS_TESTED_MATERIAL_TRAINING_NOT_RELEASED`

This implementation closes the code-mechanics prerequisites in the frozen
prime-token input-access preregistration. It does not close any data, source,
E92, seed, or human-release gate.

## Implemented boundary

- `python/scbe/prime_token_input_access.py` builds sealed, processor-owned
  packets for the canonical six-view candidate and four equal-width controls.
  The views remain correlated descriptions of one occurrence. The wrapper
  replaces owned hidden positions before block 0 and zeros the owned raw and
  route lanes so placeholder bytes cannot leak through another path. The
  shuffled arm requires an explicit dataset-wide occurrence pool, constructs a
  true vector derangement, and seals both the pool and permutation receipts;
  duplicate canonical vectors cannot silently become fixed points.
- `python/scbe/prime_token_training.py` trains only the low-rank reader. It
  checks the parent hash after every step and persists adapter, optimizer,
  sampler, Python, NumPy, CPU RNG, and CUDA RNG state in alternating atomic
  checkpoint slots. Training rows must be in the `train` split and supervise
  only declared causal positions in one bounded route/function-token vocabulary
  tied to an exact evaluator receipt.
- `scripts/tokenizer/run_prime_token_input_access.py` requires both a completely
  passing release audit and a separate, audit-hash-bound human authorization
  before importing a material runtime factory. Each `(arm, seed)` receives a
  dedicated lineage. Tool dispatch, promotion, and partial unfreezing remain
  disabled. Its evaluator owns held examples separately, must use the pinned
  receipt, and fails if record IDs or source families overlap training.
- `python/scbe/prime_token_independent_replay.py` reconstructs packet features
  without calling the producer builder, verifies the checkpoint pointer and
  parent lineage, ignores producer metric aggregates, and recomputes
  only the declared held route/function outputs rather than scoring unrelated
  sequence positions.
- `scripts/tokenizer/replay_prime_token_input_access.py` exposes that path for a
  separately supplied held-out runtime and fails when a producer ledger differs
  from replay.

## Tested invariants

The focused implementation suite proves:

1. deterministic packet seals and mutation detection;
2. equal feature width and reader parameter count across learned arms;
3. lexical-only auxiliary zeroing and a dataset-wide, receipt-bound shuffled
   vector derangement that rejects singleton and duplicate-vector pools;
4. independent reconstruction equality for all five learned packet modes;
5. bit-identical delegation when no packet is present;
6. owned placeholder insensitivity and unowned-token sensitivity;
7. no influence from a future owned record on earlier logits in the compatible
   causal test core;
8. reader update with a bit-identical frozen parent;
9. split save/load/next-step equality with uninterrupted training;
10. bounded causal supervision, train/held source-family separation, and exact
    evaluator-receipt matching;
11. fail-closed material admission and checkpoint/ledger tamper detection.

Command:

```text
python -m pytest tests/tokenizer/test_prime_token_input_access.py \
  tests/tokenizer/test_prime_token_training_release.py \
  tests/tokenizer/test_algebraic_radial_token_table.py -q
```

Result: `29 passed` on Python 3.12.10 after Black and Ruff. This is mechanics
evidence only. No catalog row was labelled, no source session was opened, no
parent or descendant weight was modified, and no material trainer was started.

The verified source boundary is commit
`17d312148e76140c85d9aca8ba6b4e6b8cbc42a5`. Immutable V2 receipts are stored
outside the worktree in the release directory as
`RUNNER_IMPLEMENTATION_TEST_RECEIPT_V2.json` and
`INDEPENDENT_REPLAY_IMPLEMENTATION_TEST_RECEIPT_V2.json`. Their SHA-256 values
are respectively
`3549ecbb465ccedc6237714beee1c4494bbdc296ebea891401465ef7d4462453` and
`b2f071be5e87e8acdf4eb19d5bc1c31e9b32d953e49cf6ed13debb2f52269eb2`.
The earlier 26-test receipts remain preserved as historical evidence rather
than being overwritten.

The later multi-seed evidence implementation is bound to commit
`e2de35c06d0533137739843d38c2bb3d67aff0ad`. The focused suite now passes
`33/33`. New immutable receipts preserve the earlier versions:

- `RUNNER_IMPLEMENTATION_TEST_RECEIPT_V3.json`
  (`815992ec3edc80d0e16b8caaa8101b5580349ea0a384ef678af7ea6c06b4212d`);
- `INDEPENDENT_REPLAY_IMPLEMENTATION_TEST_RECEIPT_V3.json`
  (`d1640e3239a84d07b8275f654b3dabe4b64015204dd9510f83fbc19b6842180e`);
- `EVIDENCE_AGGREGATOR_IMPLEMENTATION_TEST_RECEIPT_V1.json`
  (`08fec8bb1f7d34e79f3aba4b11c4afcb92208ddb17c564e05ae186591cf4497b`).

The aggregator and checkpoint-free baseline replay are described in
`docs/research/PRIME_TOKEN_INPUT_ACCESS_EVIDENCE_AGGREGATION_20261111.md`.

The concrete recovered-parent runtime, multi-coordinate evaluator, reader
connectivity diagnostics, and corrected packet-free no-intervention baseline
are described in
`docs/research/PRIME_TOKEN_MATERIAL_RUNTIME_20261111.md`. Its expanded focused
suite passes `37/37`. Material data and weights were still not loaded during
that implementation check.

That boundary is commit
`0d4bf31ffc170f2769b3cc00d5de4b7e49d4e29f`. Its immutable receipts are:

- `RUNNER_IMPLEMENTATION_TEST_RECEIPT_V4.json`
  (`69f3de7023acf14a966a6203c1c37af196a83290220175f2c31bf7091cadef7b`);
- `INDEPENDENT_REPLAY_IMPLEMENTATION_TEST_RECEIPT_V4.json`
  (`fec908562c2331cb4107af138cc9c108d69e706ebc85873d29f77d3e0d029d54`);
- `EVIDENCE_AGGREGATOR_IMPLEMENTATION_TEST_RECEIPT_V2.json`
  (`94ea2789c5acdf0535f785eef16af4e7b29cfe6e7fd5f2ddeb878e52efac79d9`);
- `MATERIAL_RUNTIME_IMPLEMENTATION_TEST_RECEIPT_V1.json`
  (`18de849adc4a0165762fc5a4da7385f6ef882a8d513ca2d5337a77c29672c75c`).

The target-invariant material producer, closed-session snapshot binding,
dual-source connected-component split, exact manifest cross-binding, and
runtime family/function target check are described in
`docs/research/PRIME_TOKEN_MATERIAL_CASES_20261111.md`. Its focused suite passes
`16/16`; the complete prime-token/release suite passes `120/120`. No material
data or optimizer was opened by that implementation check.

That boundary is commit
`dfc0de2239050fff5c39ab11888a39dc49d4255c`. Its immutable receipt is
`MATERIAL_CASE_BUILDER_IMPLEMENTATION_TEST_RECEIPT_V1.json`
(`338bd1561b2a29c90837e919800d21fe5360f9427a8a02455ce58533ef485dcf`).
Independent replay still consumes runtime-produced target arrays; rebuilding
targets directly from pinned source authority remains a separate obligation
before any evidentiary promotion claim.

## Remaining release blockers

The current release remains `WAITING_FOR_RELEASE_REQUIREMENTS`. In particular,
it still needs the prospective query minimum and closed source sessions, the
source-disjoint assignment and source-family gate, completed E92 plus independent
verification, three declared fresh seeds, and explicit human material release.
Passing those gates would authorize only a reviewed training launch, never
promotion, serving, tool dispatch, or partial unfreezing.
