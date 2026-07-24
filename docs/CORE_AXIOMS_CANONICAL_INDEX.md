# SCBE Core Axioms: Canonical Index

**Status:** executable reference index
**Updated:** 2026-07-24
**Scope:** the five structural axioms, their 14-layer mapping, and the
`AxiomLens` diagnostic overlay

This page is the canonical starting point for claims about SCBE axioms. It
separates mathematical properties, implementation behavior, measured benchmark
results, design hypotheses, and metaphors. Those categories must not be used
interchangeably.

## Claim Labels

| Label | Meaning |
|---|---|
| **Invariant** | A property derived for a named formula on a stated input domain. |
| **Implementation guarantee** | Behavior enforced by validation and executable tests. |
| **Measured** | A result tied to a named dataset, configuration, and result artifact. |
| **Design hypothesis** | A proposed mechanism that still requires a controlled evaluation. |
| **Metaphor** | An explanatory image, not evidence or a security property. |

The phrases "geometric cage," "chemical bond," and "3D glasses" are useful
metaphors. They do not establish complete behavioral containment, chemical
validity, or a lossless three-dimensional representation.

## The Five-Axiom Mesh

The five structural axioms organize the 14 numbered pipeline layers:

| Axiom | Layers | Executable interpretation |
|---|---:|---|
| **Unitarity** | 2, 4, 7 | Preserve the declared norm, direction, or invertible representation appropriate to the transform. |
| **Locality** | 3, 8 | Keep operations within declared spatial, metric, and neighborhood bounds. |
| **Causality** | 6, 11, 13 | Preserve temporal order and prevent later state from being used as earlier evidence. |
| **Symmetry** | 5, 9, 10, 12 | Preserve the quantity declared invariant under the tested transform or ordering. |
| **Composition** | 1, 14 | Preserve type, ordering, and contract compatibility across composed layers. |

Canonical implementation:
`src/symphonic_cipher/scbe_aethermoore/axiom_grouped/`.

These are structural constraints over named transforms. They do **not** prove
that every possible agent action is safe. Behavioral coverage remains an
empirical evaluation problem.

## Three Different Axiom Surfaces

The repository contains three related but different uses of the word "axiom":

1. **Five structural axioms:** the mesh above, used to organize L1-L14.
2. **Operational axioms A0-A7:** deterministic execution, bounded state, policy
   before actuation, capability isolation, fail-to-noise, cryptographic
   separation, provenance, and recoverability. These are indexed in
   `config/scbe_core_axioms_v1.yaml`.
3. **Formal behavior tests FA1-FA12:** formula-level properties exercised by
   tests such as `tests/industry_standard/test_formal_axioms_reference.py`.

An operational rule or a passing formula test must not be reported as proof of
all five structural axioms unless its mapping and input domain are explicit.

## AxiomLens: Five-Dimensional Node Overlay

`AxiomLens` is a non-mutating diagnostic view over any graph or neural node
matrix. It leaves the underlying network intact and computes an independent
five-axis field:

```text
R in R^(N x 5)
columns = [unitarity, locality, causality, symmetry, composition]
```

Each value is a non-negative residual. Zero means the supplied evidence agrees
with that axiom's declared relation. A missing reference is recorded as
**unobserved**, never as an automatic pass.

Receipts include per-axis coverage, overall coverage, and an evidence status
of `complete`, `partial`, or `unobserved`. Strict JSON receipts encode unknown
compliance as `null`.

Let `x_i` be the current state of node `i`, `x_i^0` its reference state,
`E` the graph edges, `t_i` a timestamp, `s_i^(k)` a symmetry-aligned view, and
`c_i` an independently composed target.

### Residuals

```text
Unitarity:
r_U(i) = ((||x_i|| - ||x_i^0||) / max(||x_i^0||, s_0))^2

Locality for edge e=(i,j):
r_L(e) = (
  max(0, ||x_i-x_j|| - ||x_i^0-x_j^0|| - epsilon_L)
  / max(||x_i^0-x_j^0||, s_0)
)^2

Causality for directed edge i->j:
r_C(e) = (max(0, t_i + delta_t - t_j) / s_t)^2

Symmetry:
r_S(i) = mean_k [
  ||x_i-s_i^(k)||^2 / max(||s_i^(k)||^2, s_0^2)
]

Composition:
r_P(i) = ||x_i-c_i||^2 / max(||c_i||^2, s_0^2)
```

The weighted diagnostic objective is:

```text
L_axiom = sum_a lambda_a L_a
g_x = gradient_x L_axiom
g_t = partial_t L_axiom
```

The implementation returns both the per-axiom analytical gradients and the
weighted combined gradients. Finite-difference tests verify both state and time
derivatives.

### High-Dimensional and Stereo Views

The authoritative result remains the `N x 5` field. For visualization only,
the bounded severity `q_i = 1 - exp(-r_i)` is projected through a fixed
`5 x 3` basis:

```text
offset_i = (lambda elementwise-multiplied by q_i) B
left_i.x  = offset_i.x - separation * ||lambda * q_i||
right_i.x = offset_i.x + separation * ||lambda * q_i||
```

The left/right offsets provide a stereo or "3D glasses" view of which axioms
create depth at each node. This projection is intentionally lossy. Decisions,
training receipts, and audits must retain the full five-axis field and
observation mask.

Implementation:
`src/symphonic_cipher/scbe_aethermoore/axiom_grouped/axiom_lens.py`.

Tests:
`tests/governance/test_axiom_lens.py`.

## Canonical 14-Layer Mapping

| Layer | Runtime role | Structural axiom |
|---:|---|---|
| 1 | Complex context state | Composition |
| 2 | Realification | Unitarity |
| 3 | SPD weighted transform | Locality |
| 4 | Poincare-ball embedding | Unitarity |
| 5 | Hyperbolic distance | Symmetry |
| 6 | Breathing transform | Causality |
| 7 | Phase transform | Unitarity |
| 8 | Minimum distance to realm centers | Locality |
| 9 | Spectral coherence | Symmetry |
| 10 | Spin coherence | Symmetry |
| 11 | Triadic temporal aggregation | Causality |
| 12 | Harmonic score or explicitly tagged wall regime | Symmetry |
| 13 | Risk decision | Causality |
| 14 | Audio telemetry/output axis | Composition |

Some runtimes expose an optional Layer 0 intent preprocessor and optional
between-layer bridges such as MMX or Rhombic Fusion. They are not additional
members of the numbered L1-L14 mesh unless a versioned specification explicitly
promotes them.

## Harmonic Formula Regimes

The repository contains multiple harmonic formulas. Every result and document
must identify its regime:

| Regime | Formula | Use |
|---|---|---|
| `BOUNDED_SCORE` | `H_score = 1/(1+d+2*phaseDeviation)` | Current Python reference and TypeScript `pipeline14` L12 safety score. |
| `BOUNDED_WALL` | `H_wall = 1 + alpha*tanh(beta*d*)` | Bounded risk multiplier in theorem-oriented modules. |
| `QUADRATIC_EXP_COST` | `H_cost = R^(d^2)` or the explicitly named phi-scaled variant | Public cost helper and stress surfaces; not interchangeable with `H_score`. |
| `PI_EXP_COST` | `H_pi = R*pi^(phi*d)` | Resource and access-cost surfaces; not interchangeable with `H_score`. |

The formula regime is part of provenance. A benchmark produced with one regime
cannot validate another without a separate run.

## Atomic and Rhombic Components

The implemented atomic tokenizer is a finite, deterministic semantic
approximation:

```text
phi_runtime: token x language x context -> semantic class -> element prototype
```

It currently uses seven core semantic classes and selected periodic properties
to produce six tongue-aligned trits. It is **not** a universal semantic periodic
table and is not learned from all languages.

Chemical Fusion implements the documented reconstruction vote:

```text
R_k =
  sum_i w_i*tau_(i,k)
  + sum_(i,j) lambda_(i,j)*(chi_i-chi_j)
  - sum_(i,j) gamma*lambda_(i,j)*abs(chi_i-chi_j)
  + sum_i rho_i*v_i
```

Rhombic Fusion is an optional cross-modal consistency score implemented in
`python/scbe/rhombic_bridge.py`. It is a bridge between feature surfaces and
governance, not a numbered layer and not evidence that every runtime routes all
inputs through it.

## Evidence and Reproducibility

- Python package requirement: Python 3.11 or newer.
- Core Python dependency for this lens: NumPy.
- The five-axiom, atomic-tokenization, chemical-fusion, and Rhombic tests are
  executable locally.
- The repository reports an F1 of `0.813` for a semantic-projector evaluation,
  but that number must remain labeled **reported** until a single versioned
  result artifact, exact corpus, and command reproduce it from the current
  commit.
- The committed standalone benchmark artifact
  `benchmarks/results/scbe_benchmark_local_20260405_103757.json` is a different
  560-case benchmark and reports different metrics. It is not evidence for the
  `0.813` result.
- Repository files state provisional application `63/961,403`. This index
  records that repository claim; it is not an independent legal-status
  verification.

The supported claim is: selected mathematical properties and implementation
contracts are reproducible under stated assumptions. Full independent
replication of every security, benchmark, and ontology claim is not yet
established.
