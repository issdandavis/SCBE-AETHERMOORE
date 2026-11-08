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

