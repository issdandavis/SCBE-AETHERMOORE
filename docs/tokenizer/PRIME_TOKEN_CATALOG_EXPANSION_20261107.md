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

## Structural source gate

Commit `d4a7f82ea` adds a deterministic pre-score audit for catalog integrity,
source diversity, explicit rights labels, per-source six-view coverage, and
source concentration. The audit fails closed and is covered by both passing and
adversarial fixtures.

The frozen 33-source catalog returned `STRUCTURAL_GATE_PASS`:

- catalog hash matched `MANIFEST.json`;
- 10 academic, 12 documentation, and 11 publication sources;
- 33 explicit MIT labels and zero unknown licenses;
- every source contains lexical, five-W, speech, atomic, prime, and source
  features;
- the largest source contributes 214 of 1,246 sections, or `0.17175`, below the
  frozen `0.40` concentration ceiling.

Receipt:
`C:/dev/clay-training-runs/prime-token-catalog-20261106/catalog-v4-rights-20261107/SOURCE_AUDIT.json`

Receipt SHA-256:
`e94b84d6cd901c8985f78243dc4ff380526382bfbe2886bea4cc8c109678560d`

This passes only the catalog-structure prerequisite. It does not replace the
missing independently authored query pool and is not a retrieval result.

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

## Internal Loom source restoration

The original pilot's `wall_5w.py` and `clay_sieve.py` sources live in the
user-owned Loom repository, which has no repository license. They were therefore
not relabeled as MIT. Their current bytes and file histories were verified, then
bound in a separate local manifest under the user's explicit internal-research
authorization. That manifest expressly does not authorize redistribution.

Internal source-manifest SHA-256:
`d88e758254efdc444c57aebd63a2e2b5f10b68fbc696a76cb8dc956f64e0ef97`

The combined development catalog is at:
`C:/dev/clay-training-runs/prime-token-catalog-20261106/catalog-v5-rights-20261107/`

- Sources: 35 (10 academic, 2 code, 12 documentation, 11 publication)
- Sections: 1,299
- Word occurrences: 32,810
- Relationship memberships: 61,305
- Rights labels: 33 MIT, 2 owner-authorized internal research, 0 unknown
- Catalog SHA-256:
  `fc3e8d03ae01f57b38494a16822b4f0d01eb2287327dc83245ee5aa9f5fdd733`
- Manifest SHA-256:
  `7dbbbbc41846dcb29265c3f2757c6e860abab32951e6b2adf5173c3399e389b3`
- Structural-audit SHA-256:
  `d5b994e0cc6301b0ba9e1be262e1b3a0191bef72da7996d1c1305512fb7c533e`

All five generated-output hashes matched the manifest. The structural gate
passed all checks, and the largest source now contributes `0.16474` of sections.
This v5 artifact supersedes v4 only as the current development candidate. It has
not been scored, promoted, packaged, deployed, or connected to a probability
sidecar or neural checkpoint.
