# Tokenizer Execution Lattice Role v1

Status: authoritative implementation boundary

Owner: SCBE-AETHERMOORE

## Definition

The SCBE tokenizer is a multi-purpose semantic execution lattice for expressing, routing, transforming, and reversibly reconstructing operations across language, code, domain, binary, and agent workflow lanes.

It is not a security tokenizer and it is not a security boundary.

## Boundary

The tokenizer does not authorize, encrypt, seal, permit, sandbox, or verify execution by itself. Security belongs to the layers that control and prove behavior:

- governance gates
- crypto/sealing
- capability controls
- execution policy
- verification layers

The tokenizer makes operations understandable, executable, routeable, and reversible across domains. Other layers decide whether those operations are allowed, sealed, executed, or trusted.

## Tokenizer Responsibilities

The tokenizer owns these jobs:

- cross-language mapping
- cross-domain mapping
- message + code co-representation
- intent-preserving transformation
- bijective reversibility
- shared base understanding across lanes

This means a coding operation, workflow message, domain packet, conlang phrase, binary transport record, or agent instruction can map down to a common representation without pretending that all surfaces are the same thing.

## Three-Layer Contract

Every implementation that touches Sacred Tongues, SS1, code packets, agent routing, or training records must preserve this split:

1. semantic phrase: the human or canon-facing meaning layer, including lore-authentic phrases, code intent, domain intent, or workflow intent.
2. metric payload: the structured tongue weighting, phase, authority, intent, relation, transform, or geometry payload activated by the phrase.
3. transport packet: the deterministic SS1, binary, hexadecimal, sealed, hashed, or serialized encoding used to move, audit, or reconstruct the payload.

Round-trip correctness is necessary but not sufficient. A transport packet can be reversible and still be wrong for public display, canon language, or training semantics if it collapses these layers.

## Practical Runtime Split

Use this short rule when designing code:

- Crypto secures it.
- Governance permits it.
- Capability controls limit it.
- Execution policy decides what can run.
- Verification proves what happened.
- The tokenizer makes it understandable, executable, and reversible across domains.

## Design Rules

1. Do not describe this layer as a security tokenizer.
2. Do not use tokenizer reversibility as proof that an action is safe.
3. Do not collapse SS1 transport spelltext into canonical public language.
4. Do not collapse a semantic phrase, metric payload, and transport packet into one unlabeled field.
5. If a language lens is missing, mark the gap through the shared IR, metric payload, binary transport, or command matrix instead of inventing unsupported code.
6. If code, message, or domain intent is transformed, preserve trace metadata such as source path, source hash, token hash, concept id, lens id, and route id where available.
7. If an operation crosses into execution, call the governance, capability, policy, and verification layers explicitly.
8. If an operation crosses into public writing or training data, keep canon-first wording separate from transport-first encoding.

## Canonical Jobs

### Semantic Base Layer

Every language surface maps to a deeper common meaning layer. The goal is not syntax-to-syntax translation only. The goal is operation to intent, intent to relation, relation to transform, and transform back to an inspectable surface.

### Execution Coordination Layer

Agents can coordinate across coding languages, conlangs, binary transport, domain packets, and workflow/system messages without losing the underlying operation. This is routing and representation alignment, not permission.

### Bijective Reconstruction Layer

The mapping should support lowering code, message, or domain intent into canonical structures, moving it across tongues and lanes, and reconstructing it back with traceable reversibility.

## Implementation Anchors

Primary code and data surfaces:

- `src/tokenizer/ss1.ts`
- `src/crypto/sacred_tongues.py`
- `src/crypto/sacred_tongue_payload_bijection.py`
- `src/coding_spine/shared_ir.py`
- `scripts/benchmark/build_representation_kaleidoscope.py`
- `scripts/system/code_slice_geometry.py`
- `scripts/build_coding_system_full_sft.py`
- `docs/TONGUE_CODING_LANGUAGE_MAP.md`
- `docs/specs/SEMANTIC_SEPARATION_CONTROLLED_BLENDING_2026-04-25.md`
- `docs/specs/LAYERED_GEOMETRY_SEMANTIC_PACKING_NOTE_2026-04-25.md`

## One-Sentence Contract

The tokenizer is the canonical cross-domain agent substrate for expressing, routing, executing, and reversibly reconstructing operations across system lanes, while security remains the job of governance, crypto, capability controls, execution policy, and verification.
