# Prime-token material case boundary — 2026-11-11

Status: `CASE_MECHANICS_TESTED_MATERIAL_DATA_NOT_IMPORTED`

## Producer boundary

`python/scbe/prime_token_material_cases.py` prepares the preregistered material
case lanes without starting an optimizer. Query inputs are rebuilt from query
text and private-session provenance only. Catalog source identity, source
family, review stratum, output token, and split remain target metadata and do
not enter the six-view packet.

The writer requires all of these authorities before creating a new bundle:

- the reviewed benchmark;
- the verified source-family audit;
- the exact hash-bound review queue;
- the watcher-produced closed-source snapshot whose live paths, sizes, mtimes,
  session identities, and catalog boundary still match;
- separately sourced ordinary and retention JSONL lanes.

The queue sessions must be a subset of the closed-source snapshot. The producer
therefore cannot turn an arbitrary queue `session_ids` list into evidence that a
still-open conversation is closed.

## Split and target contract

Catalog families and query-session families form a bipartite graph. Connected
components are indivisible split units. The bounded exhaustive planner refuses
fewer than three components, empty train/validation/final-test lanes, a final
test below the declared minimum, or source/family concentration above its
preregistered bound.

The output vocabulary is frozen before material labels as the Cartesian product
of manifest-bound catalog families and the four fixed review strata. The runtime
independently checks that each case target token is exactly the token declared
for its `(catalog family, function stratum)` pair, that the target source and
content hash occur in the verified source-family audit, and that every non-output
target remains the original query byte.

`CASES_MANIFEST.json` binds the exact source manifest, split manifest, evaluator
receipt, and all five lane files. The runtime rechecks lane counts, catalog
families, query-session families, source separation, and packet-free
ordinary/retention separation. Mixing a cases manifest with another source or
split manifest fails before model loading.

## Output and authority

The builder writes through a new `.pending` directory and atomically renames it
only after every artifact hash is available. It refuses an existing final or
pending path and preserves a failed pending directory for forensic inspection.
Every receipt keeps training, promotion, partial unfreezing, and tool dispatch
disabled.

## Verification

The focused producer/runtime suite passes `16/16`. The complete prime-token,
prospective-watcher, source-family-gate, release, material-runtime, evidence,
catalog, and benchmark suite passes `120/120` on Python 3.12.10. Black targeting
Python 3.12 and Ruff both pass. No material benchmark, optimizer, parent weight,
adapter weight, or human release authorization was consumed by these tests.
