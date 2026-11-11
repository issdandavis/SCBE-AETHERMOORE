# Prime-token frozen input-access handoff — 2026-11-11

## Claim boundary

The implementation mechanics are tested. Material training has **not** started.
The live headless processes are prospective-data, selection, E92, and
source-family watchers; they are not optimizer workers. No parent or descendant
weight changed, and no partial unfreeze, promotion, merge, serving, or tool
dispatch authority was granted.

## Exact source and evidence

- Functional source boundary: commit
  `e2de35c06d0533137739843d38c2bb3d67aff0ad`.
- Documentation boundary at handoff creation: commit
  `559d40fd3efb306dd34eb11962f1f542cb6efcaf`.
- Runner receipt:
  `C:\dev\clay-training-runs\prime-token-catalog-20261106\successor-training-release-20261111\RUNNER_IMPLEMENTATION_TEST_RECEIPT_V3.json`
  (`815992ec3edc80d0e16b8caaa8101b5580349ea0a384ef678af7ea6c06b4212d`).
- Independent replay receipt:
  `C:\dev\clay-training-runs\prime-token-catalog-20261106\successor-training-release-20261111\INDEPENDENT_REPLAY_IMPLEMENTATION_TEST_RECEIPT_V3.json`
  (`d1640e3239a84d07b8275f654b3dabe4b64015204dd9510f83fbc19b6842180e`).
- Evidence-aggregator receipt:
  `C:\dev\clay-training-runs\prime-token-catalog-20261106\successor-training-release-20261111\EVIDENCE_AGGREGATOR_IMPLEMENTATION_TEST_RECEIPT_V1.json`
  (`08fec8bb1f7d34e79f3aba4b11c4afcb92208ddb17c564e05ae186591cf4497b`).
- Current release state:
  `C:\dev\clay-training-runs\prime-token-catalog-20261106\successor-training-release-20261111\CURRENT_RELEASE_STATE.json`.
- Current audit:
  `C:\dev\clay-training-runs\prime-token-catalog-20261106\successor-training-release-20261111\RELEASE_AUDIT.json`.

The old 26-test and V2 29-test receipts remain intact. The current receipts bind
33 passing tests to the multi-seed evidence source boundary.

## Verified commands

The CI-compatible Black command (`--target-version py311 --line-length 120`),
Flake8, Ruff, both CLI help commands, and the following focused suite passed:

```text
python -m pytest tests/tokenizer/test_prime_token_input_access.py \
  tests/tokenizer/test_prime_token_training_release.py \
  tests/tokenizer/test_algebraic_radial_token_table.py -q
```

Result: `33 passed` on Python 3.12.10. The worktree was clean after the checks.

The evidence aggregator now requires an exact 6-arm by 3-or-more-seed grid,
checks every bounded-output replay, uses seed-level pooled variance, runs a
paired finite-sample test on across-seed held-example means, and compares the
candidate with both no intervention and the strongest matched control. The
no-intervention arm replays without inventing an adapter checkpoint.

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

Disk free space was approximately 25.5 GiB at the final poll. The storage
envelope gate remained `SPACE_ENVELOPE_OPEN`; no cleanup or deletion was
performed in this implementation turn.
