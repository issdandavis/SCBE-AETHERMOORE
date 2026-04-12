---
title: Transport Tokenizer - SS1 and Sacred Tongues
type: reference
updated: 2026-04-11
source: repo_snapshot
tags:
  - tokenizer
  - ss1
  - sacred-tongues
  - transport
  - bijection
---

# Transport Tokenizer - SS1 and Sacred Tongues

This is the live byte/token transport layer.

It is deterministic, table-driven, and bijective. It is not the same layer as the 8-vector atomic op features.

## Runtime Sources

- `src/tokenizer/ss1.ts`
- `src/crypto/sacred_tongues.py`

## What It Does

- splits each byte into `highNibble` and `lowNibble`
- maps `16 prefixes x 16 suffixes = 256 tokens` per tongue
- produces reversible tongue-local spell-text transport
- supports detection, envelope construction, and section-aware routing

## Important Runtime Anchors

### TypeScript

- `VOCABULARIES`
- `encodeByte`
- `decodeByte`
- `blend`
- `createSS1Envelope`
- `detectTongue`

### Python

- `SECTION_TONGUES`
- `SacredTongueTokenizer`
- `_build_tables`
- `compute_harmonic_fingerprint`
- `validate_section_integrity`

## Tongue Roles

- `KO` -> control / intent / nonce
- `AV` -> transport / context / metadata / AAD
- `RU` -> policy / binding / salt / KDF material
- `CA` -> compute / transform / ciphertext
- `UM` -> security / secrets / redaction
- `DR` -> schema / integrity / tags / signatures

## Related Notes

- [[Langues and Related Fields]]
- [[Tokenizer Sacred Eggs Canonical Reference]]
- [[Atomic Op Features - 8 Vector]]

## Snapshot Notes

- This layer is already implemented in both TS and Python.
- The repo has actual runtime tables, not just theory or placeholder specs.
