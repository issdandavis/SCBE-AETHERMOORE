# E92 exact-selection source-chain binding — 2026-11-10

## Bound scope and inventory

This amendment changes only the sealed E92 prospective runner, bundle writer,
independent bundle verifier, and their tests. It does not change catalog
construction, tokenization, retrieval scores, labels, model weights, serving,
training intake, partial unfreezing, or promotion.

- Cross-repository inventory receipt:
  `C:\dev\pc-health\runtime\prime-token-v7-eval-system-inventory-20261110T1954.json`
- Inventory SHA-256:
  `846e69ec1b9a41e6d8cb4c5c6ea9ab77396990a72c0a669362855ee7f8db03a9`
- SCBE base commit: `abd1ba5962ea488d208b7b1b36a37fd47cc2d62b`
- Loom audit producer commit: `5070cdabd0ab37ab6fbd7bb1ed5a545c42e4c6e9`
- Existing audit schema: `clay.prime-token-selection-audit.v1`

## Existing nodes and the missing edge

```text
closed source-disjoint scan
  -> REVIEW_QUEUE.json
  -> exact policy replay (Loom, hashes/counts only)
  -> QUEUE_SELECTION_AUDIT.json       [existing producer]

REVIEW_QUEUE + labels + preparation + source inventory + catalog integrity
  -> E92 benchmark/scorer/verifier    [existing consumer]
```

The audit producer is live and tested, but E92 does not currently require or
bundle its receipt. A queue could therefore reach scoring with valid downstream
labels and catalog evidence but without evidence that its candidate list exactly
replays the frozen selection policy.

## Concrete capability and reused components

- New capability: E92 fails closed unless the exact-selection receipt binds the
  same queue content hash, source-dataset hash, candidate count, and ordered
  candidate hashes, while retaining no-label/no-score/no-train/no-promote state.
- Reused producer: `audit_prime_queue_selection.py`; no second selector is added.
- Reused bundle mechanism: `SOURCE_CHAIN_BUNDLE_FILES` and exclusive pending
  directory publication.
- Reused verifier: `prime_token_prospective_verify.py`, extended with an
  independent receipt/binding check.

## Edge contract

Input is one JSON object with schema
`clay.prime-token-selection-audit.v1`. Required invariants are:

- status `PASS_EXACT_SELECTION_REPLAY_NO_SCORING`;
- canonical `audit_sha256` over the receipt excluding that field;
- dataset and queue hashes equal the frozen queue declarations;
- candidate count and ordered accepted-query hashes equal the queue;
- exact replay is true;
- private text emission and label opening are false; and
- scoring, training, and promotion authority are false.

The portable E92 bundle gains fixed role `selection_audit` at
`SOURCE_SELECTION_AUDIT.json`, with bundled-file and original-file hashes.

## Controls, capacity, rollback, and stop conditions

- Existing E92 controls remain: lexical/no-intervention/route-null baselines,
  three shuffled-binding seeds, three random-rank-fusion seeds, paired finite
  uncertainty, source diversity, and route-width matching.
- New adversarial tests mutate the audit authority and candidate bindings while
  recomputing outer hashes; both producer-side and independent verification must
  reject them.
- Capacity is one small JSON receipt per completed bundle; no checkpoint or
  catalog copy is added.
- Rollback is one isolated branch/commit. Existing v3 bundles remain immutable
  historical artifacts and intentionally do not satisfy the v4 contract.
- Stop before scoring on missing receipt, hash mismatch, schema/status drift,
  candidate mismatch, or any weakened authority field.

## Pre-build gate

- Existing component reused: yes.
- New tokenizer, selector, scorer, or dependency required: no.
- Inputs/outputs/schemas/invariants identified: yes.
- Controls and adversarial holdouts identified: yes.
- Compute/storage bounded: yes.
- Immutable save and rollback path identified: yes.
- Safe to implement in isolated worktree: yes.

## Post-build live handoff map

The v7 live chain had three independently running supervisors but no fourth
edge that consumed both completed artifacts and supplied the new E92 v4
argument. `scripts/tokenizer/watch_run_e92_prospective.py` closes that edge:

```text
collector READY + preparer PACKET_READY + selection audit VERIFIED
    -> wait for independently authored REVIEW_LABELS.json
    -> pinned run_e92_prospective.py --selection-audit ...
    -> pinned verify_e92_prospective.py
    -> E92_RESULT_INDEPENDENTLY_VERIFIED
    -> training/serving/merge/promotion remain NOT_AUTHORIZED
```

The watcher checks exact hashes for the queue from both upstream status files,
the preparation receipt, source inventory, selection audit, catalog database,
catalog-integrity audit, runner, and verifier. It does not resolve or read the
labels path until the first three authorities are ready. A pre-existing pending
result is preserved for audit rather than deleted or retried.
