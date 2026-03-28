# Foam Overlay for the Tri-Manifold Lattice

Status: experimental overlay, documentation-level only  
Date: 2026-03-25  
Scope: applies to the tri-manifold lattice lane only  
Non-goal: this file does not claim the entire repo already implements a unified foam physics engine

## Hypothesis

The `tri-manifold lattice` can be interpreted as a time-layered stability field:

- immediate manifold = fast surface rearrangement
- memory manifold = slower bulk persistence
- governance manifold = deep structural resistance

Under this interpretation, corpus ablation or semantic drift should change not only core clusters but also the boundary stability between them.

## Expected gain

1. give the lattice lane a physically intuitive documentation layer
2. define a measurable boundary-stability probe for representation experiments
3. avoid collapsing unrelated `triadic` formulas into one overloaded metaphor

## Explicit failure modes

1. metaphor creep
- foam language starts being treated as a proof of implementation

2. formula collapse
- `d_tri_window3`, `d_tri_temporal4`, and `d_tri_phi3` are treated as the same primitive

3. telemetry overreach
- telemetry slots are described as literal pressure/tension/curvature without explicit mapping

4. experiment drift
- tangential probe definitions are changed after seeing results

## Safe mapping

| Tri-manifold lattice term | Foam overlay term | Safe interpretation |
| --- | --- | --- |
| immediate window | surface bubbles | fast rearrangement, sensitive to recent drift |
| memory window | deep bubbles | slower persistence, requires more pressure to move |
| governance window | bedrock foam | deepest structural lane, strongest inertia |
| `d_tri_window3` | multi-timescale foam displacement | combined shift across the three temporal layers |
| `harmonic_cost_lattice` | amplified rearrangement cost | cost of sustained shift after dimensional scaling |
| temporal anomaly `|d1 - d_g| / d_g` | surface-bedrock shear | short-term behavior diverging from deep structure |
| temporal resonance | foam coherence | agreement across layers |

## What this overlay does not claim

It does not claim that:

1. Plateau laws are already a canonical runtime primitive
2. all telemetry slots already equal physical foam variables
3. the kernel wall formula and lattice scale are the same object
4. the causality-axiom Layer 11 distance is already foam math

## Tangential probe mapping

For anchor concept `a_i`:

- `core neighbors` = inside-bubble semantic mass
- `tangent band` = boundary-adjacent semantic routes
- `bridge tangents` = paths crossing into other domain clusters

This makes the first probe:

```text
core(a_i) = top-k_core neighbors
tangent(a_i) = ranks (k_core + 1) ... k_tangent
```

Then compare between runs:

```text
core_overlap(a_i)
tangent_overlap(a_i)
bridge_loss(a_i)
Delta_A,i = ||A_i^(control) - A_i^(ablated)||_F
```

Interpretation:

- stable core, stable tangent = deep structural retention
- stable core, unstable tangent = boundary restructuring
- unstable core, unstable tangent = full cluster shift

## Local quadratic boundary probe

For each anchor `a_i`, fit a local quadratic field:

```text
q_i(x) = (x - mu_i)^T A_i (x - mu_i)
```

Constraints:

- `A_i = A_i^T`
- `A_i` positive semidefinite when possible

Use:

- dominant eigenvectors = steep core directions
- flatter eigen-directions = likely tangential pathways

This is the mathematically safe version of the “Plateau border” idea.

## Tangential operator coefficients (added 2026-03-26)

From Grok collaboration: formal decomposition of state updates into normal (class-changing)
and tangential (class-preserving) components on constraint shells.

See: `docs/theories-untested/TANGENTIAL_OPERATOR_COEFFICIENTS.md` for full formalization.

Key connection: the PHDM module (phdm_module.py L434-442) already performs this
decomposition for curvature computation. The tangential coefficients name the weights
explicitly and map them to governance semantics.

## Multi-scale grapheme wave lattice (added 2026-03-26, theory-only)

Letters as circular substrate: l_i = a_i * e^(i*theta_i) where amplitude = importance,
phase = position on circle. Circular phasing aligns with 60-degree tongue intervals.

Four synthesis layers:
1. Letter layer: circular phase, charge, positional bias
2. Chain layer: words as ordered letter chains with spectral signatures
3. Morpheme layer: stable semantic units (roots, suffixes)
4. Semantic layer: concept embeddings, discourse roles

Status: documentation-level only. No implementation exists.

## String operator algebra (added 2026-03-26, theory-only)

Manages discrete topological transitions (bubble merge, bubble pop) in the foam.
Under unitary evolution, ensures the foam shifts to new equilibrium while maintaining
isotopy invariance (local weight wiggles don't disrupt underlying topology).

Status: conceptual. Maps to existing Sacred Egg genesis/mutation gates but no
formal string operator code exists.

## 21D canonical state as foam telemetry (added 2026-03-26)

| Dimensions | Component | Foam Equivalent |
|-----------|-----------|-----------------|
| 1-6 | Tongue position | Bubble center coordinates (60-degree phase) |
| 7-12 | Phase alignment | Membrane orientation, handoff state |
| 13-21 | Telemetry | Pressure, tension, curvature, entropy |

Dims 13-21 act as physical sensors. If pressure/tension exceeds thresholds,
string operator triggers rebalance before representational failure.

Connection: triangulated_phdm.py already has 21D state. The foam interpretation
gives physical meaning to the telemetry dimensions.

## Recommended experiment lane

### Run matrix

Use two model families and keep all non-corpus controls fixed.

1. family A control
2. family A canon-ablated
3. family B control
4. family B canon-ablated

Optional control:

5. family A canon-ablated plus matched replacement corpus
6. family B canon-ablated plus matched replacement corpus

### Shared controls

1. anchor vocabulary
2. probe set
3. tokenizer policy within each family
4. token budget
5. training steps
6. graph construction rule
7. tangent-band definition
8. local probe regularization

## 21D state alignment

For current repo work, use the live `state21_v1` schema rather than introducing a second 21D map.

Recommended experiment packet projection:

| State slot group | Overlay role |
| --- | --- |
| `s[0:6]` tongue position | bubble-center coordinates |
| `s[6:12]` tongue phase | boundary orientation / membrane angle |
| `s[12:21]` telemetry | stability and health channels |

Most relevant telemetry slots:

| Slot | Use in this experiment |
| --- | --- |
| `s[14] coherence_spectral` | spectrum consistency |
| `s[15] coherence_spin` | phase consistency |
| `s[16] coherence_triadic` | multi-timescale agreement |
| `s[17] d_star` | effective deviation from safe structure |
| `s[18] h_eff` | effective wall-amplified cost |
| `s[19] risk_score` | final gated risk signal |
| `s[20] trust_score` | trust retention |

## Gate defaults

| Gate | Pass condition |
| --- | --- |
| `G0` spec gate | symbols, corpus rules, and metrics frozen before training |
| `G1` probe gate | local quadratic probe stable on a pilot anchor set |
| `G2` lesion gate | ablation produces measurable tangent or bridge change |
| `G3` coherence gate | run stays interpretable without collapsing unrelated triadic formulas |
| `G4` promotion gate | experimental overlay remains doc-scoped until code paths are explicitly mapped |

## Recommended next code move

Do not rename runtime formulas yet.

First:

1. keep the registry stable
2. build the tangent/curvature evaluation script
3. collect evidence from the ablation runs
4. only then decide whether any foam terminology belongs in production docs or code comments

## Minimal claim

The safe claim is:

`the tri-manifold lattice admits a useful foam-style interpretation for temporal stability analysis`

The unsafe claim is:

`the whole SCBE system is already a unified foam-physics implementation`
