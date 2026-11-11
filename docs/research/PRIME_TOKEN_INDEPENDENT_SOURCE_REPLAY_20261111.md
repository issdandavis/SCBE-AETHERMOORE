# Prime-token independent source replay — 2026-11-11

Status: `SOURCE_RECONSTRUCTION_MECHANICS_TESTED_NO_MATERIAL_RUN`

## Closed evidence gap

The earlier replay rebuilt packet tensors and reopened adapter checkpoints, but
its held cases and target arrays came from `payload["replay_cases"]`, produced by
the same material runtime being checked. That was artifact consistency, not
independent target reconstruction.

The replay entry point now refuses that edge. It first reads the hash-pinned
runtime configuration and independently reconstructs held cases through:

```text
SOURCE_MANIFEST
  -> pinned benchmark + source-family audit
  -> pinned review queue + closed-source snapshot
  -> exact split/case/evaluator manifests
  -> benchmark query bytes and private-session provenance
  -> canonical source family + reviewed function class
  -> unique evaluator token
  -> independently rebuilt packet record, target array, and held case
  -> independent packet projection + read-only checkpoint + raw logits/NLL
```

`python/scbe/prime_token_material_runtime.py` no longer returns
`replay_cases`. The independent runner therefore cannot silently fall back to a
producer-built target array.

## Reconstruction authority

`python/scbe/prime_token_independent_replay.py` independently verifies:

- absolute paths and SHA-256 values for the benchmark, source-family audit,
  review queue, closed-source snapshot, ordinary source, and retention source;
- queue/snapshot/manifest agreement on closed session identities;
- exact source, split, cases, and evaluator manifest cross-hashes;
- the three-lane catalog-family/query-session split and lane declarations;
- query text and source URI against the pinned benchmark;
- packet bytes, ownership, six-view record, and packet-input identity rebuilt
  without the producer packet builder;
- target source and family from the benchmark source suffix plus the canonical
  source-family audit;
- function class from reviewed benchmark metadata;
- target token from the unique evaluator `(family, function)` map;
- producer case metadata and arrays against independently reconstructed values.

The replay receipt states that producer runtime cases and producer targets were
not consumed. The evidence aggregator now requires this receipt and cross-checks
its source, split, cases, and evaluator hashes against each run identity.

## Independent arithmetic

Replay still performs a full-vocabulary argmax. It now also records the raw
target logit and independently computes full-vocabulary target negative log
likelihood as:

```text
NLL(y) = logsumexp(logits) - logits[y]
```

The aggregator requires finite, non-negative per-example NLL values and an
exact matching aggregate. These are replay diagnostics; accuracy,
relationship, and function remain the preregistered promotion coordinates.

## Negative controls and scope

Tests reject:

- a producer target array changed while all file hashes are refreshed;
- producer function metadata changed while all file hashes are refreshed;
- a held session removed from the closed-session authority;
- a replay result that omits independent source reconstruction;
- source/split/cases/evaluator identity drift.

The focused source/runtime/replay/evidence suite passes `41/41`; the complete
prime-token/release regression suite passes `125/125`. This is mechanics
evidence using synthetic fixtures plus one real builder-to-replay integration
fixture. No prospective material data, model checkpoint, optimizer, promotion,
partial unfreeze, or tool dispatcher was opened.

The tested implementation is commit
`5d4c8a0f04a5f8eb33166de1dec5c44a8154ced7`. Its immutable external receipt is
`INDEPENDENT_SOURCE_REPLAY_IMPLEMENTATION_TEST_RECEIPT_V1.json`, SHA-256
`fbd7b4243d0b6ea83af6cde15a947dbcc55ccfed08f90c675f1d305432721e7c`.

The release-binding hardening is commit
`9480ca1fe7600e8868a07959f08ca022a9c62b98`. The admissible immutable receipt
is `INDEPENDENT_SOURCE_REPLAY_IMPLEMENTATION_TEST_RECEIPT_V2.json`, SHA-256
`269fea799989fdc06f4604f2b05b42a9a4dd1797a0283ca5ba0265b60f31b2a7`.
Its gate status is `TESTED`; its authority fields independently keep promotion,
partial unfreeze, optimization, and tool dispatch false. The release auditor
now rejects an accepted immutable state status that differs from the status in
the hashed JSON receipt. The expanded prime-token/release suite passes
`127/127`.
