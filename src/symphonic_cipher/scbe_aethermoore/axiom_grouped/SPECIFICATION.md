# SCBE Five-Axiom Mesh and AxiomLens Specification

**Version:** 4.2.1
**Updated:** 2026-07-24
**Status:** executable working specification

## Scope

This specification covers:

- the five structural axioms used to organize Layers 1-14,
- the executable `AxiomLens` graph/neural overlay,
- the relationship to atomic tokenization, Chemical Fusion, and Rhombic
  Fusion,
- the evidence boundaries for security and benchmark claims.

It does not claim universal behavioral safety, runtime parity, physical
chemistry, or a lossless three-dimensional encoding.

## Authorities

- Axiom and overlay definitions:
  `docs/CORE_AXIOMS_CANONICAL_INDEX.md`
- Formula regimes:
  `docs/specs/CANONICAL_FORMULA_REGISTRY.md`
- Layer roles:
  `docs/specs/LAYER_INDEX.md`
- System and evidence status:
  `docs/CANONICAL_SYSTEM_STATE.md`

## Five Structural Axioms

| Axiom | Layers | Executable responsibility |
|---|---:|---|
| Unitarity | 2, 4, 7 | Preserve the declared norm, direction, containment, or invertibility contract for the named transform. |
| Locality | 3, 8 | Keep weighted state and graph relations inside declared metric/neighborhood bounds. |
| Causality | 6, 11, 13 | Preserve directed temporal order and policy-before-decision flow. |
| Symmetry | 5, 9, 10, 12 | Preserve the quantity declared invariant or monotonic for the selected regime. |
| Composition | 1, 14 | Preserve type, ordering, and interface contracts across composed stages. |

These are structural labels with executable checks. They are not quantum
hardware claims.

## AxiomLens Contract

### Inputs

Required:

```text
node_states: N x D finite matrix
```

Optional independent evidence:

```text
edges: E x 2 node indices
reference_states: N x D matrix
timestamps: N-vector
symmetry_states: N x D or K x N x D matrix
composed_states: N x D matrix
```

Edges are undirected for locality and directed `source -> target` for
causality.

### Outputs

The authoritative residual field is:

```text
R in R^(N x 5)
columns = [unitarity, locality, causality, symmetry, composition]
```

The result also contains:

- `node_observed` and `edge_observed`,
- `coverage_by_axiom`, `overall_coverage`, and `evidence_status`,
- per-axiom and weighted state gradients,
- per-axiom and weighted time gradients,
- edge residuals and endpoint deltas,
- bounded compliance values,
- lossy 3D and stereo visualization offsets.

Evidence status is one of:

```text
complete | partial | unobserved
```

Missing evidence produces `null` compliance values in the JSON receipt. It
does not produce a false pass.

### Objective

```text
L_axiom = sum_a lambda_a * L_a
```

The state and time gradients are analytical. Central finite-difference tests
verify both.

### Visualization

The five residual channels are bounded by:

```text
q = 1 - exp(-r)
```

and projected through a fixed `5 x 3` basis for left/right stereo offsets. The
projection is deliberately lossy and must not replace the five-dimensional
receipt in governance or training.

## Formula Regimes

The axiom package can interact with several registered harmonic regimes:

- `BOUNDED_SCORE`,
- `BOUNDED_WALL`,
- `QUADRATIC_EXP_COST`,
- `PI_EXP_COST`.

Callers must name the regime. No unqualified harmonic formula is permitted in
new canonical documentation.

## Token and Bridge Components

### Atomic Tokenization

The current runtime is a finite deterministic approximation:

```text
token x language x context
  -> semantic class
  -> selected element prototype
  -> six tongue-aligned trits
```

It has seven core semantic classes. It is not a learned universal periodic
semantic lattice.

### Chemical Fusion

Chemical Fusion combines tongue trits, bond polarity, instability penalties,
and valence pressure. Its chemical terminology is an engineered analogy over
deterministic arithmetic, not a claim of chemical simulation.

### Rhombic Fusion

Rhombic Fusion is an optional cross-modal consistency bridge. It remains
outside the numbered Layer 1-14 sequence unless a future versioned
specification explicitly promotes it.

## Security and Evidence Boundaries

Supported:

- selected formula properties on stated domains,
- validated shapes, finite values, and bounded state,
- deterministic overlay generation,
- analytical gradient agreement with finite differences,
- explicit handling of missing evidence.

Not established by this specification:

- complete safety for arbitrary autonomous agents,
- cryptographic sealing of every repository entry point,
- equivalence of every Python and TypeScript runtime,
- reproduction of every historical performance claim,
- legal status of repository-recorded patent metadata.

## Implementation

Canonical source:

```text
src/symphonic_cipher/scbe_aethermoore/axiom_grouped/axiom_lens.py
```

Compatibility import:

```text
symphonic_cipher/scbe_aethermoore/axiom_grouped/axiom_lens.py
```

Focused tests:

```text
tests/governance/test_axiom_lens.py
src/symphonic_cipher/scbe_aethermoore/axiom_grouped/tests/test_axiom_grouped.py
tests/governance/test_atomic_tokenization_and_fusion.py
tests/governance/test_rhombic_bridge.py
tests/industry_standard/test_formal_axioms_reference.py
```

Python requirement: 3.11 or newer.
