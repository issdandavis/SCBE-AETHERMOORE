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

## Independent prospective-verifier hardening

The sealed E92 verifier now independently requires the declared control seeds
(`11, 29, 47` by default), exact run counts, result/receipt seed agreement,
result-limit agreement, benchmark query provenance, and per-outcome bindings to
the benchmark query source, review stratum, and relevant source suffix. The CLI
accepts explicit expected seeds only for deliberately declared alternate test
runs.

Two adversarial tests rewrite either the declared seeds or a per-query source
and then recompute both the result hash and run-receipt content hash. Both
forgeries are still rejected. This closes an internal-consistency loophole
without changing retrieval, catalog, package defaults, model state, or serving.

- combined tokenizer and prospective suite: `23 passed`;
- Python compile: passed;
- Ruff: passed;
- `git diff --check`: passed.

## Portable prospective source-chain bundle

The E92 run contract is now `scbe.e92-prospective-run.v2`. A completed bundle
includes immutable JSON copies of the post-freeze queue, independent labels,
preparation receipt, and catalog source inventory. The run receipt binds each
copy by fixed role, filename, canonical bundle hash, and original source-file
hash.

The independent verifier reconstructs every accepted benchmark query from that
raw chain and rejects any mismatch. An adversarial test changes a source label,
recomputes the bundled-label hash, and recomputes the run-receipt content hash;
the verifier still rejects it because the derived benchmark no longer follows
from the source evidence.

This closes the storage-portability gap without changing retrieval scores,
catalog content, model weights, package defaults, serving, or promotion.
Detailed map:
`prospective_bundle_source_chain_system_map_20261108.md`.

- prospective plus benchmark suite: `24 passed`;
- broader benchmark/prospective/harvest/watch-audit suite: `40 passed`;
- Python compile: passed;
- Ruff: passed;
- Black check: passed;
- `git diff --check`: passed;
- promotion: `NOT_AUTHORIZED`.

## Live-chain revalidation — 2026-11-08 20:20 PST

The independent watcher-chain verifier was rerun against the current v6
catalog, source-session-disjoint watcher pin/status, preparer pin/status, and
empty review-packet boundary. It returned `VERIFIED_WAITING_NO_SCORING` with
zero errors and audit SHA-256
`a32344757b409a02e496fe0c7405e7f666adc5cae0c1e32468e318529b3109f0`.

The watcher reported one open post-freeze session, zero closed post-freeze
sources, and zero admissible candidates against the unchanged 30-query floor.
No session body was opened by the audit; no label, benchmark, result, training
intake, probability update, serving change, merge, or promotion was authorized.
Focused watcher and signed-radix verification passed `49/49` tests.
