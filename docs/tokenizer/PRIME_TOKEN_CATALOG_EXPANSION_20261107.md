# Prime Token Catalog Rights-Bound Expansion — 2026-11-07

Status: `DEVELOPMENT_CATALOG_BUILT_NO_SCORE_NO_PROMOTION`

## Purpose

The explicit-route collection accepted only 16 of 60 reviewed requests, below
its frozen 30-query floor. This follow-on broadens attributed local source
coverage before any new independent holdout is authored. It does not relabel or
score the consumed 60-request review set.

Source selection used the stated architecture, activation, gating, routing,
six-tongue, publication, benchmark, and local-research goals plus repository
maps. It did not use rejected holdout query text. All 60 reviewed requests are
now development-consumed and permanently ineligible for a later holdout.

## Reproducible ingest boundary

Commit `b7bea8f4c` adds a strict source-manifest ingest path. Every source must
declare an exact path, SHA-256, source kind, license, and rights basis. The
builder validates the complete manifest before ingestion, refuses unknown
commercial-rights metadata or hash drift, and records the source-manifest hash
in the output receipt.

The frozen input manifest is
`research/tokenizer/prime_token_catalog_sources_v2.json`, SHA-256
`d672e85838c21d7f51670d84a24a1b7fa879d4a912488ab5befb6c9bfd109186`.
It contains 33 repository sources:

- 10 academic;
- 12 documentation;
- 11 publication;
- 33 MIT labels and zero unknown license labels.

The rights basis is the repository-root MIT license. Its scope must still be
confirmed before distributing source text outside the repository. The two
cross-repository Loom code sources from the earlier pilot are not in this build;
they require their own explicit rights classification first.

## Build receipt

Runtime directory:
`C:/dev/clay-training-runs/prime-token-catalog-20261106/catalog-v4-rights-20261107/`

- Sources: 33
- Sections: 1,246
- Word occurrences: 28,561
- Relationship memberships: 57,280
- Manifest SHA-256:
  `f2a9fc55f11c5ebeff17c047894770a7fc5bb855448328e35f2ce4c8bd676340`
- Catalog SHA-256:
  `dcebf23c68bcd9a8b727f7a84eba9fc3e8f5ef6e45a823f467b9f05217822de3`
- Frozen tokenizer SHA-256:
  `6c14a5cd26188678f920273cff49483f535e340caa98e3a7eb4d3285286c37c6`

Every output hash in `MANIFEST.json` was independently recomputed and matched.

## Claim boundary and next gate

No retrieval evaluation, probability-sidecar update, serving change, tokenizer
change, deployment, or neural-weight change was performed. The earlier
11-source catalog and all prior benchmark receipts remain unchanged.

The next admissible capability test requires:

1. classifying any desired cross-repository source rights;
2. freezing the final expanded catalog hash;
3. collecting a new independently authored, source-record-disjoint query pool;
4. applying the existing route-null, lexical/no-intervention, shuffled-binding,
   multi-source diversity, and two-pooled-standard-deviation gates once.

Until then this catalog is a deterministic development artifact only.
