# Prime-token frozen input-access handoff — 2026-11-11

## Claim boundary

The implementation mechanics are tested. Material training has **not** started.
The live headless processes are prospective-data, selection, E92, and
source-family watchers; they are not optimizer workers. No parent or descendant
weight changed, and no partial unfreeze, promotion, merge, serving, or tool
dispatch authority was granted.

## Exact source and evidence

- Functional source boundary: commit
  `0d4bf31ffc170f2769b3cc00d5de4b7e49d4e29f`.
- Runner receipt:
  `C:\dev\clay-training-runs\prime-token-catalog-20261106\successor-training-release-20261111\RUNNER_IMPLEMENTATION_TEST_RECEIPT_V4.json`
  (`69f3de7023acf14a966a6203c1c37af196a83290220175f2c31bf7091cadef7b`).
- Independent replay receipt:
  `C:\dev\clay-training-runs\prime-token-catalog-20261106\successor-training-release-20261111\INDEPENDENT_REPLAY_IMPLEMENTATION_TEST_RECEIPT_V4.json`
  (`fec908562c2331cb4107af138cc9c108d69e706ebc85873d29f77d3e0d029d54`).
- Evidence-aggregator receipt:
  `C:\dev\clay-training-runs\prime-token-catalog-20261106\successor-training-release-20261111\EVIDENCE_AGGREGATOR_IMPLEMENTATION_TEST_RECEIPT_V2.json`
  (`94ea2789c5acdf0535f785eef16af4e7b29cfe6e7fd5f2ddeb878e52efac79d9`).
- Material-runtime receipt:
  `C:\dev\clay-training-runs\prime-token-catalog-20261106\successor-training-release-20261111\MATERIAL_RUNTIME_IMPLEMENTATION_TEST_RECEIPT_V1.json`
  (`18de849adc4a0165762fc5a4da7385f6ef882a8d513ca2d5337a77c29672c75c`).
- Current release state:
  `C:\dev\clay-training-runs\prime-token-catalog-20261106\successor-training-release-20261111\CURRENT_RELEASE_STATE.json`.
- Current audit:
  `C:\dev\clay-training-runs\prime-token-catalog-20261106\successor-training-release-20261111\RELEASE_AUDIT.json`.

The old 26-, 29-, and 33-test receipts remain intact. The current receipts bind
37 passing tests to the recovered-parent material-runtime source boundary.

## Verified commands

The CI-compatible Black command (`--target-version py311 --line-length 120`),
Flake8, Ruff, both CLI help commands, and the following focused suite passed:

```text
python -m pytest tests/tokenizer/test_prime_token_input_access.py \
  tests/tokenizer/test_prime_token_training_release.py \
  tests/tokenizer/test_algebraic_radial_token_table.py -q
```

Result: `37 passed` on Python 3.12.10. The worktree was clean after the source
commit and before this documentation update.

The evidence aggregator now requires an exact 6-arm by 3-or-more-seed grid,
checks every bounded-output replay, uses seed-level pooled variance, runs a
paired finite-sample test on across-seed held-example means, and compares the
candidate with both no intervention and the strongest matched control. The
no-intervention arm replays without inventing an adapter checkpoint and now
provably omits prime-packet injection. Learned-arm replay requires packet use.
The concrete material runtime also binds the recovered parent and an exact
relationship/function evaluator receipt, while recording reader connection
strength, stable rank, per-view norms, output margin, and entropy.

## Live pipeline state

All five launcher/worker pairs were alive at the final poll. Their status files
were actively refreshing and reported:

- collector: `WAITING_FOR_SESSION_CLOSE`;
- preparer: `WAITING_FOR_PROSPECTIVE_QUEUE`, 0 candidates;
- selection audit: `WAITING_FOR_PROSPECTIVE_QUEUE`, 0 candidates;
- E92: `WAITING_FOR_PROSPECTIVE_QUEUE`, 0 candidates;
- source-family gate: `WAITING_FOR_PREPARATION_PACKET`, 0 candidates.

The regenerated release audit is
`WAITING_FOR_RELEASE_REQUIREMENTS` with 0 errors and 9 blockers. The blockers
are: 0/30 accepted final-test queries, 0/3 closed source sessions, missing E92
independent verification, E92 waiting, 0/3 fresh seeds, collector waiting,
selection audit waiting, source-disjoint assignment waiting, and source-family
gate waiting.

## Resume order

1. Poll the same status artifacts and confirm their files continue to refresh.
2. Do not restart healthy watchers merely because their state is unchanged.
3. When the prospective queue closes, independently verify the selection,
   source-disjoint, source-family, and E92 receipts before changing release
   state.
4. Re-run the release auditor after each independently verified evidence
   change.
5. Even if every machine gate passes, require a separate human authorization
   bound to that exact audit hash before importing material runtime data.
6. Run all declared arms and three fresh seeds; compare against both the
   no-intervention and strongest size-matched control using the sealed evidence
   aggregator.
7. Promotion and partial unfreeze remain separate decisions and default to
   `NOT_AUTHORIZED` / `NONE`.

Disk free space was approximately 25.45 GiB at the final poll. The storage
envelope gate remained `SPACE_ENVELOPE_OPEN`; no cleanup or deletion was
performed in this implementation turn.

## Continuation update — independent source replay and release binding

Independent replay now rebuilds held inputs and targets from pinned source
authorities rather than consuming producer cases. The implementation commit is
`5d4c8a0f04a5f8eb33166de1dec5c44a8154ced7`; release-status binding is commit
`9480ca1fe7600e8868a07959f08ca022a9c62b98`. The current state binds
`INDEPENDENT_SOURCE_REPLAY_IMPLEMENTATION_TEST_RECEIPT_V2.json`
(`269fea799989fdc06f4604f2b05b42a9a4dd1797a0283ca5ba0265b60f31b2a7`).

The release auditor now derives accepted immutable JSON statuses from the
hashed artifacts and rejects state/artifact disagreement. The contract also
requires material-runtime and evidence-aggregator receipts. The complete suite
passes `127/127`. The regenerated release audit remains fail-closed with 0
errors and 9 blockers; no optimizer, checkpoint, or model weights were opened.
