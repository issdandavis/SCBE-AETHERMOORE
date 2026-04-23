---
title: Tokenizer Sacred Eggs Canonical Reference
type: reference
updated: 2026-04-11
source: local_repo_and_primary_external
tags:
  - tokenizer
  - sacred-eggs
  - canonical-reference
  - runtime-alignment
  - obsidian
---

# Tokenizer Sacred Eggs Canonical Reference

This note is the current sourced reference for the Sacred Tongue tokenizer and Sacred Eggs alignment surface.

It is intentionally split into:
- local canonical sources that already exist in this repo
- current runtime implementations that actually execute
- primary external references for cross-system alignment
- exploratory weighting references already present in the vault

It does **not** treat proposal language, metaphor extensions, or speculative manifold claims as runtime truth.

## 1. Local Canonical Tokenizer Surface

### Primary local references

- `docs/notion/mirror/ss1-tokenizer-protocol-sacred-tongue-integration__191399b1.md`
  - States that SS1 is not a standard NLP tokenizer but a deterministic, bijective binary-to-text encoding.
  - Defines the nibble-map mechanism: `16 prefixes x 16 suffixes = 256 unique tokens` per tongue.
  - States that encoding and decoding are `O(1)` lookup.
  - Defines semantic domain separation across the six tongues.

- `docs/notion/mirror/sacred-tongue-tokenizer-practical-tutorials-implementation-guide__ad687d93.md`
  - Gives the operational tongue roles:
    - `KO` = control / intent / nonce
    - `AV` = transport / context / metadata / AAD
    - `RU` = policy / binding / salt / KDF material
    - `CA` = compute / transform / ciphertext
    - `UM` = security / secrets / redaction
    - `DR` = schema / integrity / tags / signatures
  - Treat this as the strongest local usage guide for actual packet composition.

- `training-data/research_bridge_smoke/avalon-bridge-20260318T091500Z/sources/obsidian/1105025510_tongue-domain-mappings.md`
  - Local mapping note for tongue domains and cross-tongue morphisms.
  - Useful for domain intent, but secondary to the SS1 spec and runtime code.

- `notes/round-table/2026-03-20-phase-tunnel-tongue-mapping.md`
  - Local phase / sector / angular mapping note.
  - Useful for weighting and geometry framing, but not the canonical opcode/runtime source.

### Current runtime tokenization surface

- `python/scbe/atomic_tokenization.py`
  - Current Python runtime tokenizer and atomic state surface.

- `python/scbe/ca_opcode_table.py`
  - Current canonical CA runtime table.

These two runtime files are the safest implementation-level source of truth when local docs and experiments disagree.

## 2. Local Canonical Sacred Eggs Surface

### Primary local references

- `docs/specs/SACRED_EGGS_GENESIS_PROTOCOL.md`
  - Defines a Sacred Egg as a sealed packet carrying a payload plus hatch policy.
  - Explicitly states:
    - payload is never stored or transmitted in plaintext
    - hatch is allowed only when evidence, authority, and context satisfy protocol
    - failure is fail-closed, optionally fail-to-noise
  - Defines the canonical compact SS1 envelope:
    - `SS1|kid=...|salt=RU:<spell-text>|ct=CA:<spell-text>|tag=DR:<spell-text>|aad=AV:<spell-text>|nonce=KO:<spell-text>`
  - Defines repo-canonical field-to-tongue mapping:
    - `KO` = nonce / flow / control
    - `AV` = AAD / context / I/O
    - `RU` = salt / binding / policy
    - `CA` = ciphertext / compute
    - `UM` = redaction / security
    - `DR` = auth tags / schema
  - Requires `shape_id` authentication and tongue consistency checks on hatch.

- `docs/specs/SACRED_EGGS_IMPLEMENTATION_CHECKLIST.md`
  - Defines the intended implementation tasks:
    - `SacredEggPacket`
    - `computeShapeId`
    - `validateShape`
    - `sealEgg`
    - `hatchEgg`
  - Calls for deterministic tests around shape binding, tongue consistency, tamper handling, and fail-to-noise behavior.

- `docs/specs/SACRED_EGGS_RITUAL_DISTRIBUTION.md`
  - Defines the three ritual modes:
    - `solitary`
    - `triadic`
    - `ring_descent`
  - Explicitly says fail-to-noise must not reveal which condition failed.

- `docs/01-architecture/sacred-eggs-systems-model.md`
  - Strongest engineering framing doc.
  - Explicitly states:
    - GeoSeal is only one validator
    - the Egg is the higher-order object
    - tokenizers are semantic traces embedded into the hatch material
    - deeper manifold claims are not yet fully formalized
  - Also defines the practical six-role semantic carrier model:
    - `KO` intent / nonce
    - `AV` metadata / AAD
    - `RU` binding / salt
    - `CA` compute / ciphertext
    - `UM` security / redaction
    - `DR` structure / tag

## 3. Current Runtime Alignment

### Strongest runtime match

- `src/symphonic_cipher/scbe_aethermoore/sacred_egg_integrator.py`
  - Closest runtime alignment to the Sacred Eggs docs.
  - Contains:
    - `primary_tongue`
    - `hatch_condition`
    - `self_tag`
    - `self_shape`
    - ritual modes `solitary`, `triadic`, `ring_descent`
    - fail-to-noise behavior through sealed noise token fallback

### Predicate-gated cryptographic reference

- `src/symphonic_cipher/scbe_aethermoore/sacred_eggs.py`
  - Strongest local predicate-gated AEAD implementation.
  - Encodes hatch predicates for:
    - tongue
    - geometry
    - path
    - quorum
  - Wrong predicate material leads to auth failure without disclosing which predicate was wrong.

### Secondary related surfaces

- `src/sacred_eggs.py`
  - Thin ritual reference layer.
  - Useful, but not the strongest tokenizer-bound Sacred Eggs implementation.

- `src/crypto/sacred_eggs.py`
  - Separate ring/yolk/shell/albumen model.
  - Related, but not the main runtime authority for tokenizer + hatch alignment.

## 4. Cross-System Alignment (Primary External References)

These external references do **not** override the local SCBE design. They are here to ground the cross-language ownership/effects claims against real language/runtime semantics.

### CA / C — manual memory, unowned by default

- C dynamic memory management reference:
  - <https://en.cppreference.com/w/c/memory/malloc>
  - <https://en.cppreference.com/w/c/memory/free>
- `free` explicitly deallocates memory allocated by `malloc/calloc/realloc`, and invalid or repeated frees are undefined behavior.
- This is the correct external grounding for treating C as the least ownership-rich lane in cross-language arbitration.

### KO / Python — runtime-owned, GC-managed objects

- Python garbage collector docs:
  - <https://docs.python.org/3/library/gc.html>
- Python’s GC docs explicitly describe the cycle-detecting collector layered on top of reference counting.
- This grounds the claim that Python’s lane is memory-safe relative to C, but still not semantically authoritative in ownership disputes.

### AV / TypeScript — structural typing

- TypeScript Handbook, type compatibility:
  - <https://www.typescriptlang.org/docs/handbook/type-compatibility.html>
- TypeScript explicitly states that its type compatibility is based on structural subtyping.
- This is the correct external grounding for treating AV as a GC + structural-types lane rather than an ownership-first lane.

### UM / Julia — multiple dispatch

- Julia manual, methods:
  - <https://docs.julialang.org/en/v1/manual/methods/>
- Julia’s methods manual is the primary reference for multiple dispatch.
- This grounds the idea that UM can carry dispatch information as a first-class routing distinction.

### RU / Rust — ownership and borrowing

- The Rust Book, ownership:
  - <https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html>
- The Rust Book explicitly states that ownership enables Rust to make memory-safety guarantees without needing a garbage collector, and ties ownership to borrowing and layout.
- This is the strongest external basis for treating RU as the most expressive ownership lane in arbitration below DR.

### DR / Haskell — pure core with effect-gated monadic surfaces

- Hackage docs:
  - `Control.Monad.ST`: <https://hackage.haskell.org/package/base/docs/Control-Monad-ST.html>
  - `Control.Concurrent.STM`: <https://hackage.haskell.org/package/stm/docs/Control-Concurrent-STM.html>
- These are the strongest direct library references for effect-gated mutable state and transactional state in Haskell.
- They support the narrow claim that DR’s write semantics can be treated as conditionally admitted through effect context rather than raw mutation.

### Practical cross-system conclusion

The most defensible promotion order for Stage 4 arbitration remains:

`DR -> RU -> AV/UM -> KO -> CA`

Reason:
- `DR` carries the strongest effect-context distinction
- `RU` carries the strongest ownership distinction
- `AV` and `UM` carry rich type / dispatch distinctions but not ownership truth
- `KO` is operationally expressive but runtime-owned
- `CA` is lowest-level and least ownership-rich

## 5. Weighted-Control References in the Vault

These are **not** the canonical tokenizer runtime. They are the strongest local references for the claim that the vault already contains phi-weighted steering language.

- `notes/DARPA_CLARA_Proposal_Master.md`
  - line 331: `Six semantic dimensions with golden-ratio-scaled weights (1.00, 1.62, 2.62, 4.24, 6.85, 11.09).`
  - line 467: `6 semantic dimensions with golden-ratio-scaled weights as continuous steering coordinates`

- `notes/aethersearch-architecture.md`
  - line 23: `Sacred Tongues (6D phi-weighted)`
  - line 121: says to replace Charabia with the Sacred Tongues tokenizer already existing in `src/tokenizer/`

### External research reference for the attention analogy

- Vaswani et al., *Attention Is All You Need*:
  - <https://arxiv.org/abs/1706.03762>

This paper is a valid external reference for the general claim that weighted alignment over token representations can simulate attention-like selection behavior.

It is **not** evidence that the current SCBE vault weighting notes already implement transformer attention. The safe claim is narrower:
- the vault already contains weighted semantic steering language
- attention provides a research-backed analogy for weighted selection
- the present runtime still needs explicit implementation if “attention simulation” is meant literally

## 6. Current Canonical Read Order

For tokenizer work:
1. `docs/notion/mirror/ss1-tokenizer-protocol-sacred-tongue-integration__191399b1.md`
2. `docs/notion/mirror/sacred-tongue-tokenizer-practical-tutorials-implementation-guide__ad687d93.md`
3. `python/scbe/atomic_tokenization.py`
4. `python/scbe/ca_opcode_table.py`

For Sacred Eggs work:
1. `docs/specs/SACRED_EGGS_GENESIS_PROTOCOL.md`
2. `docs/specs/SACRED_EGGS_IMPLEMENTATION_CHECKLIST.md`
3. `docs/specs/SACRED_EGGS_RITUAL_DISTRIBUTION.md`
4. `docs/01-architecture/sacred-eggs-systems-model.md`
5. `src/symphonic_cipher/scbe_aethermoore/sacred_egg_integrator.py`
6. `src/symphonic_cipher/scbe_aethermoore/sacred_eggs.py`

## 7. Authority Gaps Still Present

- There is still no single unified tokenizer + Sacred Eggs “one file” canonical source.
- The docs truth and runtime truth are closer than before, but still split.
- The vault contains weighting language, but weighting and attention are not yet the same thing in executable runtime.
- Experimental CA-specific or multipath tables should not be treated as canonical unless they derive from or prove equivalence with the runtime tables.

## 8. Practical Conclusion

If the goal is to align the vault like a brain-style project mind map while keeping it sourced:
- use the local tokenizer docs and Sacred Eggs specs as the canonical center
- treat runtime code as the implementation authority
- use external language docs only to justify cross-language ownership/effects alignment
- treat phi-weighted / attention-like notes as exploratory until a runtime extraction or weighting operator is actually implemented

That keeps the vault useful as a live system map without letting proposal language silently replace executable truth.
