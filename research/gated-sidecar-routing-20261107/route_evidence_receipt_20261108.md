# Late-output route evidence receipt — 2026-11-08

## Implemented boundary

`python/scbe/prime_token_benchmark.py` now exposes
`build_late_output_route_evidence()`, with an immutable CLI surface at
`scripts/tokenizer/build_route_evidence.py`.

The receipt is offline evaluation telemetry. It records, per emitted section:

- lexical rank and fixed `k=60` reciprocal-rank contribution;
- auxiliary rank and fixed reciprocal-rank contribution;
- total fusion score and lexical/auxiliary/tie winner;
- aligned output rank and the raw output rank under three shuffled bindings;
- aligned output rank and the raw output rank under three deterministic,
  size-matched random-rank fusion controls;
- the signed aligned advantage for each shuffle;
- a primary trit derived from auxiliary-minus-lexical contribution; and
- a mirror trit derived from mean aligned-versus-shuffled rank advantage.

The raw values remain beside every trit. No trit is treated as a probability,
governance decision, token weight, hidden activation, or promotion signal.
The builder also reruns lexical-only retrieval and proves exact output identity
for queries with no explicit auxiliary marker.

The random control preserves the same lexical candidate set, result limit,
fixed `k=60` fusion arithmetic, and explicit-route eligibility as the candidate.
It replaces only the eligible auxiliary ordering with a SHA-256-seeded random
permutation. If no auxiliary route is eligible, it reproduces lexical output
exactly instead of injecting an unfair random lane.

## Fail-closed evidence gate

The builder runs `audit_benchmark_disjointness()` before retrieval and refuses
any benchmark with an exact source, byte, section, or normalized-token-stream
collision. It requires at least three distinct shuffle seeds and hashes the
catalog at both boundaries.

The existing 31-query independent-request benchmark cannot be used against the
current v6 catalog:

- catalog: `catalog-v6-codex-user-20261107/catalog.sqlite3`
- catalog SHA-256: `1839d609bc8e7263263e4c83d1bac2c3645285a9a664abfc6e9f292cc0b2fba0`
- benchmark SHA-256: `886cef763c7e2eafdae338e40f0b53c0b8fce52086f110065b0461577a7e380d`
- audit: `EXACT_LEAKAGE_DETECTED`
- collisions: `31 / 31`

This is expected because the current catalog includes those historical user
requests. Reusing that benchmark would measure memorized catalog identity, not
source-disjoint retrieval.

## Prospective state

The post-freeze watcher remains correctly closed:

- watcher: `WAITING_FOR_POST_FREEZE_CLOSED_SESSION`
- preparer: `WAITING_FOR_PROSPECTIVE_QUEUE`
- minimum capability floor: 30 reviewed queries

No capability result was emitted and no model, package, deployment, tokenizer,
probability table, serving pointer, or weight was promoted.

## Verification

- `python -m pytest tests/tokenizer/test_prime_token_benchmark.py -q`
  - `17 passed`
- `python -m py_compile python/scbe/prime_token_benchmark.py scripts/tokenizer/build_route_evidence.py`
  - passed
- `git diff --check`
  - passed

The tests prove deterministic receipt structure, raw-value retention beside
trits, three-seed shuffled and size-matched random controls, exact lexical
identity for no-marker queries, and fail-closed rejection of exact catalog
leakage.
