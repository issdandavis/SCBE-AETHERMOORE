# Ancient Algebra to Atomic Tokenizer Bridge

Source: `https://youtu.be/vBwaWRZyIBM`

Local transcript:

- `docs/research/video-transcripts/vBwaWRZyIBM_transcript.txt`
- `docs/research/video-transcripts/vBwaWRZyIBM_transcript.json`

## Why This Matters

The transcript is useful for SCBE because it describes algebra before modern
symbolic notation. That older mode was not "less mathematical"; it used a
different representation contract:

- quantities were not free-floating scalars;
- unknowns were typed species;
- transformations were named procedures;
- proofs were geometric movement traces;
- written records described the process instead of relying on compact symbols.

That maps directly onto an atomic-tokenizer design where an operation is not
just a token string. It is a quantity/species pair with a proof role, transform
role, geometric state, and transport encoding.

## Extracted Concepts

### 1. Quantity-Species Pair

Medieval algebra treated values as a count attached to a kind. The useful
machine form is:

```text
Atom := Quantity x Species
```

Examples:

- `3 roots` is not `3 * x` yet; it is a count of a typed unknown species.
- `1 square` is a different species from `1 root`.
- `39 units` is a count of known unit species.

Tokenizer implication: avoid collapsing all mathematical symbols into naked
scalars. Preserve `quantity`, `species`, and `degree` as separate fields.

### 2. Restoration and Confrontation

The transcript frames early algebra around two named rewrite operations:

- restoration: repair a missing or subtracted quantity by moving it across the
  equality boundary;
- confrontation: cancel or combine like species across the equality boundary.

Tokenizer implication: represent algebraic simplification as explicit
transform atoms, not just final normalized equations.

### 3. Cut-and-Paste Geometry

The Babylonian/Arabic completing-square method is a geometric manipulation:
split, move, copy, complete, compare.

Tokenizer implication: a math token can carry a geometry trace:

```text
split -> move -> complete -> measure -> solve
```

This is valuable for small models because geometric steps are concrete and
local. The model can learn valid transformations without needing large latent
symbolic jumps.

### 4. Discrete Number vs Continuous Magnitude

The transcript repeatedly separates discrete number reasoning from continuous
geometric magnitude reasoning.

Tokenizer implication: add a `domain_mode` bit or enum:

- `DISCRETE_COUNT`
- `CONTINUOUS_MAGNITUDE`
- `BRIDGE_OPERATION`

This prevents a small model from silently mixing incompatible proof modes.

### 5. Rhetorical to Syncopated to Symbolic

The source describes a long transition from words, to partial abbreviations, to
modern symbols.

Tokenizer implication: preserve three views:

- semantic phrase: human/rhetorical description;
- metric payload: structured operation graph;
- transport packet: deterministic encoded form.

This matches `docs/specs/TOKENIZER_EXECUTION_LATTICE_ROLE_v1.md`.

## SCBE Atomic Token Shape

Proposed atom:

```json
{
  "atom_id": "alg.root.0001",
  "surface": "three roots",
  "quantity": 3,
  "species": "ROOT",
  "degree": 1,
  "domain_mode": "DISCRETE_COUNT",
  "operation_role": "TERM",
  "proof_role": "GIVEN",
  "geometry_role": "LENGTH",
  "semantic_class": "ENTITY",
  "tongue_hint": "KO",
  "transport_note": "SS1/bijective encoding is downstream only"
}
```

For quadratic examples:

```json
[
  {"quantity": 1, "species": "SQUARE", "degree": 2},
  {"quantity": 10, "species": "ROOT", "degree": 1},
  {"quantity": 39, "species": "UNIT", "degree": 0}
]
```

This is equivalent to a modern equation only after a normalization transform.
The tokenizer should keep the pre-normalized species structure available.

## Six-Tongue Mapping

This is a metric mapping, not public spelltext:

- KO: literal term identity and stable byte transport.
- AV: quantity/species pairing and transformation affordance.
- RU: proof legality, step ordering, and cancellation rules.
- CA: geometric cut/move/complete/measure trace.
- UM: ambiguity, unknown state, and branch alternatives.
- DR: historical/source lineage and transmission chain.

## Simple AI System Use

This can become a small-model math harness:

1. Convert a word problem into quantity-species atoms.
2. Build an equality graph.
3. Apply restoration/confrontation transforms.
4. If quadratic, generate a cut-and-paste geometry trace.
5. Normalize to modern symbolic form only after the trace is valid.
6. Decode back into human steps.

The point is to give a small model better rails. It works on typed atoms and
legal transformations instead of guessing raw equations from prose.

## Benchmark Idea

Create paired tasks:

- baseline: prompt a small model with the raw word problem;
- atomic mode: convert the same problem into quantity-species atoms plus legal
  transform menu;
- score: correct solution, valid intermediate steps, fewer illegal jumps, and
  faithful explanation.

Good first task:

```text
A square and ten roots equal thirty-nine units.
Find the root by completing the square.
```

Expected atom structure:

```text
1*SQUARE + 10*ROOT = 39*UNIT
```

Expected legal trace:

```text
halve coefficient -> form two 5*ROOT rectangles -> complete 5x5 square
-> add 25 units -> derive completed square area 64 -> root side 8
-> subtract 5 -> ROOT = 3
```

## Boundary

This note does not treat the YouTube transcript as authoritative history by
itself. It captures representation ideas from the transcript for SCBE tokenizer
experiments. Historical claims should be verified against primary or scholarly
sources before being used in public research or patent material.

