---
title: Tokenizer Source Snapshot - 2026-04-11
type: source-snapshot
updated: 2026-04-11
source: repo_snapshot
tags:
  - tokenizer
  - snapshot
  - provenance
  - langues
  - spiral-ring
---

# Tokenizer Source Snapshot - 2026-04-11

This note is a time-shot of the live tokenizer-adjacent source surfaces in the repo.

Use it as provenance:
- what existed at snapshot time
- which layer each file belongs to
- which vault note should be read beside it

It is not a canonical replacement for the source files.

## Runtime Surfaces

| Layer | Source Path | Primary Role | Vault Companion |
|---|---|---|---|
| Transport tokenizer | `src/tokenizer/ss1.ts` | TS byte-to-token transport, tongue detection, envelope helpers | [[Transport Tokenizer - SS1 and Sacred Tongues]] |
| Transport tokenizer | `src/crypto/sacred_tongues.py` | Python tokenizer, section routing, harmonic fingerprint, integrity checks | [[Transport Tokenizer - SS1 and Sacred Tongues]] |
| Atomic op features | `src/symphonic/multipath/_trit_common.py` | Trit tables, `(64, 8)` atomic feature vectors, atomic stream | [[Atomic Op Features - 8 Vector]] |
| Adaptive routing | `src/symphonic/multipath/op_binary.py` | Phi-discount cost, usage-ledger remap, inverse-complexity routing | [[Adaptive Routing - Op Binary]] |
| Temporal ring geometry | `src/symphonic_cipher/scbe_aethermoore/ede/spiral_ring.py` | Ring/spiral state evolution adjacent to tokenizer stack | [[Spiral Ring - Temporal Geometry]] |
| Langues metric bridge | `packages/kernel/src/languesMetric.ts` | Langues tensor / weighting implementation | [[Langues and Related Fields]] |
| Canon bridge | `docs/LANGUES_WEIGHTING_SYSTEM.md` | Canon semantics and weighting language | [[Langues and Related Fields]] |
| Consolidated repo note | `docs/specs/TOKENIZER_ATOMIC_STACK_FULL.md` | One-file repo-side summary of the stack | [[Tokenizer Vault Index]] |

## Known Layer Boundaries

- `ss1.ts` and `sacred_tongues.py` are transport/tokenizer surfaces.
- `_trit_common.py` is not transport; it is the atomic op-feature lattice.
- `op_binary.py` is not the tokenizer; it is adaptive routing over op tables.
- `spiral_ring.py` is adjacent geometry, not a tokenizer implementation.
- `languesMetric.ts` and `LANGUES_WEIGHTING_SYSTEM.md` are upstream semantic weighting surfaces.

## Existing Vault Neighborhood

- [[Tokenizer Vault Index]]
- [[Transport Tokenizer - SS1 and Sacred Tongues]]
- [[Atomic Op Features - 8 Vector]]
- [[Adaptive Routing - Op Binary]]
- [[Spiral Ring - Temporal Geometry]]
- [[Langues and Related Fields]]
- [[Tokenizer Sacred Eggs Canonical Reference]]
- [[SCBE-AETHERMOORE AI Mind Map]]
- [[2026-03-20-phase-tunnel-tongue-mapping]]
- [[Phi Spiral]]

## Snapshot Metadata

- Repo root: `C:\Users\issda\SCBE-AETHERMOORE`
- Vault root: `C:\Users\issda\SCBE-AETHERMOORE\notes`
- Snapshot date: `2026-04-11`
- Intent: preserve graphable provenance without modifying source docs or runtime files
