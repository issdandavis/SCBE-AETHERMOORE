# Prime Token Catalog v6 Disjointness Audit — 2026-11-07

Status: `V6_SCORE_BLOCKED_PENDING_PROSPECTIVE_HOLDOUT`

## Boundary

Catalog v6 was frozen at `2026-11-07T09:36:44.690035Z` with catalog SHA-256
`1839d609bc8e7263263e4c83d1bac2c3645285a9a664abfc6e9f292cc0b2fba0`.
Its 2,119 internal conversation sources were harvested from a previously
inactive Codex session, so expanding the catalog could consume queries that had
served as holdouts for earlier catalog versions.

Commit `c0b4ee810` makes that condition fail closed before retrieval runs. The
evaluator now checks each query against catalog source URIs, source-content and
section-text hashes, and normalized source/section token-stream hashes. New
reviewed benchmarks also bind each query's exact SHA-256. `--audit-only` emits a
receipt containing IDs and hashes but does not execute or score retrieval.

## Runtime receipts

Receipts are in
`C:/dev/clay-training-runs/prime-token-catalog-20261106/catalog-v6-disjoint-audit-20261107/`.

| Benchmark | Queries | Exact/normalized collisions | Receipt SHA-256 |
|---|---:|---:|---|
| Curated v1 | 11 | 0 | `7d8f530c05a64e4bff81cdbfd89a81faad8fc369b029bc01a474baf3ee930403` |
| Independent requests | 31 | 31 | `56c5989a9bc3a013b867ce926134ab96af0ef862395aad365bb047c42bc8a229` |
| Lexical-first holdout | 31 | 31 | `3fc66fd236b263de4b99436757c5e1ab0f76d11a65532bb35f74d21ee267d47c` |
| Voice v2 holdout | 34 | 0 | `c2eee9563e6d231bd2b4d36ce0db34aee5c4b7499ed85f9361c5dc703c77e336` |

Both 31-query private-session sets are fully present in v6 and cannot be used
to score it. A deliberate non-audit invocation against the contaminated
independent-request set exited with code 1 during validation and created no
result file.

The two zero-collision sets are also not a new v6 capability holdout. Curated v1
contains only 11 authored paraphrases and is below the 30-query floor. Voice v2
was already scored during candidate development, predates the v6 freeze, and is
a one-relevant-source ceiling test. Zero exact identity collision is necessary,
not sufficient evidence of independence.

## Next admissible score

A v6 capability score requires a newly exported, scrubbed, user-authored pool
strictly after `2026-11-07T09:36:44.690035Z`. It must pass the exact/normalized
identity audit, preserve source-record separation, and satisfy the frozen
minimum of 30 accepted requests, at least three strata, at least six relevant
catalog sources, and no source above 40 percent. Only then may the existing
lexical, no-intervention, route-null, shuffled-binding, macro-source, and
two-pooled-standard-deviation gates run once.

Commit `713195820` makes the prospective boundary executable. The query
harvester accepts `--after-catalog-manifest`, derives the exclusive cutoff from
the manifest, and binds both the manifest and catalog hashes into the review
queue. The reviewed benchmark carries that boundary forward, and the evaluator
refuses to run it against any other catalog hash. This replaces manual cutoff
copying for the next collection.

The first manifest-bound collection ran against the verified 2,119-row Codex
corpus and returned zero candidates, because every retained row predates v6.
That is the expected fail-closed result, not an evaluation failure. The empty
queue is at
`C:/dev/clay-training-runs/prime-token-catalog-20261106/catalog-v6-prospective-queue-20261107/REVIEW_QUEUE.json`,
with queue SHA-256
`7619edd410757c18a28284bbc8306c22bd3ef7bcb828e6d38b82f456b73a340f`
and file SHA-256
`7da3d28b09ceb9ebdd84dee5c8b66b98d74d124cf7bc3a827b10716e2efdb5d9`.

No retrieval score, probability update, deployment change, tokenizer change,
or neural-weight promotion was produced by this audit.
