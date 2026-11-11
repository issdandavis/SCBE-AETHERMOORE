# E92 prospective bundle source-chain map — 2026-11-08

## Scope and inventory

This map covers the source-disjoint E92 evaluation boundary only. It does not
change catalog construction, retrieval scoring, model weights, adapters,
serving, package defaults, or promotion policy.

- bounded read-only inventory:
  `prospective_bundle_system_inventory_20261108.json`
- inventory SHA-256:
  `409cc4481131da25dc5310e4eb05d763195070453c3e06e5918ff77a444ab8df`
- inventory size: `47,687` bytes
- mapped roots: the SCBE repository and the local prime-token run root
- repository enumeration was capped at 5,000 files and is explicitly marked
  truncated; the four implementation/test nodes below were inspected directly

## Existing nodes and responsibility

| Node | Responsibility before this change | Source-chain gap |
| --- | --- | --- |
| `prime_token_prospective.py` | Validates queue, labels, preparation receipt, source inventory, then builds benchmark/result/receipt | Returned only derived benchmark/result/receipt |
| `run_e92_prospective.py` | Atomically writes a pending bundle and renames it complete | Wrote only three derived files |
| `prime_token_prospective_verify.py` | Independently recomputes result aggregates, controls, gates, and provenance bindings | Could not reopen raw review evidence from a moved/offline bundle |
| `test_prime_token_prospective.py` | Exercises strict runner and adversarial result/receipt mutations | Did not test portable raw source-chain reconstruction |

## Data and trust edges

```text
post-freeze queue -----------+
independent review labels ---+--> strict E92 builder --> BENCHMARK.json --> RESULT.json
preparation receipt ---------+              |                    |              |
catalog source inventory ----+              +--> RUN_RECEIPT.json+--------------+
catalog.sqlite3 -------------+                       |
                                                    v
                                      independent no-promotion verifier
```

The former three-file bundle preserved hashes of the four left-side inputs but
not the inputs themselves. The path to the queue was machine-local, and paths
for the other three inputs were not present. A later verifier therefore could
prove internal derived-file consistency but could not independently reconstruct
the benchmark after storage migration or source-host loss.

## Implemented contract

Run-receipt schema `scbe.e92-prospective-run.v2` adds a role-bound
`source_chain_bundle` and the runner writes:

- `SOURCE_QUEUE.json`
- `SOURCE_LABELS.json`
- `SOURCE_PREPARATION_RECEIPT.json`
- `SOURCE_INVENTORY.json`

Each declaration binds the fixed filename, canonical bundled-file SHA-256, and
the original source-file SHA-256. Existing historical source hashes remain in
their original receipt fields.

The independent verifier now:

1. requires all four fixed-role source files;
2. verifies their bundle hashes and original-file hash declarations;
3. independently recomputes the queue content hash;
4. checks queue, labels, catalog boundary, preparation receipt, source inventory,
   and no-promotion declarations;
5. reconstructs every accepted benchmark query from queue plus labels; and
6. rejects a benchmark that does not equal that reconstruction.

The catalog database remains an external immutable input because it can be
large. Its exact file path and SHA-256 were already required and remain checked.

## Capacity, rollback, and controls

- Capacity cost is four JSON evidence copies per completed run, not a second
  catalog database or model checkpoint. This is bounded by the reviewed queue
  and catalog source inventory, and is negligible beside the SQLite catalog.
- Writes remain exclusive and atomic through the existing `.pending` directory
  plus `os.replace` boundary.
- Rollback is one source commit; no migration or destructive rewrite is needed.
- Old v1 smoke bundles remain historical artifacts but are intentionally not
  accepted as portable v2 evidence.
- Promotion, merge, serving, training intake, and weight mutation remain
  `NOT_AUTHORIZED`.

## Verification evidence

- prospective plus benchmark tests: `24 passed`
- broader benchmark/prospective/harvest/watch-audit suite: `40 passed`
- adversarial source-label mutation with recomputed bundle and receipt hashes:
  rejected because the benchmark no longer reconstructs from the source chain
- Python compilation: passed
- Ruff: passed
- Black check: passed
- `git diff --check`: passed

## 2026-11-10 integrity-gated v3 amendment

Run-receipt schema `scbe.e92-prospective-run.v3` adds a fifth role-bound source
file, `SOURCE_CATALOG_INTEGRITY.json`. Before any labels are consumed or retrieval
is scored, the runner now requires a read-only relational-integrity receipt whose
catalog hashes match the frozen database, whose deterministic check set is all
true, and whose independent-semantic-observation count remains zero. The
independent verifier rechecks the bundled receipt and its original-file hash.

The frozen v6 catalog remains preserved and currently fails this new gate because
three normalized negation tokens (`don't`, `can't`, `won't`) retained stale
`semantic:ENTITY` relation memberships beside canonical `NEGATION` token state.
The builder now derives atomic and speech analysis from normalized token identity,
which prevents that drift in future catalogs. Valid punctuation-only section gaps
remain informational rather than integrity failures. No v6 row was edited, and
the current prospective watcher remains collection-only with scoring, training
intake, serving, merge, partial unfreeze, and promotion unauthorized.

## 2026-11-10 corrected-catalog successor gate

`build_prime_token_catalog.py plan-successor` now provides the admission boundary
between an integrity-failed frozen catalog and a corrected successor. The command
is read-only and fails closed unless all of the following remain true:

1. every predecessor output still matches the exact path, byte count, and SHA-256
   recorded by `MANIFEST.json`;
2. a fresh relational-integrity audit exactly reconstructs the supplied audit
   receipt and its failed-check set matches the preregistered reason;
3. every hash-bound source manifest still matches the predecessor manifest;
4. free space covers both the declared reserve and a conservative peak-build
   estimate; and
5. the successor uses a new catalog hash, passes relational integrity, freezes a
   new source-disjoint boundary after the build, and starts again at zero eligible
   prospective candidates. Predecessor candidates are never reusable.

The live v6 plan is recorded at
`C:\dev\clay-training-runs\prime-token-catalog-20261106\catalog-v7-successor-plan-20261110\PLAN.json`.
It verified the sole reviewed failure
`relationship_memberships_exactly_reconstruct`, estimated 1,422,772,329 peak
build bytes, and returned `WAITING_FOR_STORAGE_RESERVE` with a 1,098,115,177-byte
shortfall above the 25 GiB reserve. Catalog build, scoring, training, serving,
merge, partial unfreeze, and promotion therefore remain unauthorized.

