# Dual-trit phase / hyper-torus search map

Status: **mapped before build**. This is a toy-search measurement surface. It
does not alter GeoSeal, ML-KEM, ML-DSA, a key generator, or a neural model.

The bounded inventory is recorded in
[`dual_trit_torus_inventory_20260907.json`](../research/evidence/dual_trit_torus_inventory_20260907.json).
The relevant implementation was already distributed across SCBE and Loom, so
the experiment reuses those pieces instead of defining another geometry stack.

## Existing components checked

| Existing component | Role in this experiment | Decision |
| --- | --- | --- |
| `src/crypto/integer_phase_shards.py::rotate_phase30` | Exact multiplication by a formal 12th root of unity | Reused for mirrored 30-degree phase orbits |
| `src/symphonic_cipher/scbe_aethermoore/ai_brain/dual_ternary.py::FULL_STATE_SPACE` | All nine `{-1,0,+1}²` primary/mirror states | Reused as the phase-state authority |
| `python/scbe/torus.py::hypercube_neighbors` | Exact one-bit support changes | Reused for fallback neighbor generation |
| `C:\dev\loom\clay_relation_hypergraph.py` | `D4 semidirect Z3²`, relation reverse, 144 anchored representations | Pinned as the existing relational design authority; no cross-repository runtime dependency added |
| `python/scbe/rubix_cubit.py` | Exact 4D quarter turns and receipts | Verified control primitive; coordinate permutations alone provide no LWE objective heuristic |
| `src/symphonic_cipher/harmonic_scaling_law.py::HyperTorusManifold` | Signed forward/backward/frozen torus modes | Kept out of the search core because its Riemannian metric is floating point and governance-oriented |
| `src/cognitive_governance/hypercube_geometry.py` | Nested 54-face governance boundaries | Kept out: it controls permeability and risk, not a candidate-secret objective |
| `src/crypto/hyperpath_finder.py` | A* over floating Poincare/octree voxels | Kept out: A* needs a goal-directed admissible heuristic, which geometric trit distance does not supply here |
| `src/crypto/dual_lattice.py` and `dual_lattice_integration.py` | Tongue, PQC, phase, and governance composition | Checked; these are integration/governance surfaces, not an algebraic lattice-reduction search |
| `C:\dev\loom\clay_activation_desmos.py::phase_shifted_quine_rows` | 14-layer, 64-opcode phase/hypertorus projections and focal loss | Kept as visualization provenance; its floating visual loss cannot prune exact LWE candidates |
| `src/crypto/toy_lwe_box_field.py` | Exact toy objective, exhaustive truth, and safe modular interval bound | Reused as the measurement authority and strong control |

## Missing bounded surface

The reusable components did not yet answer the concrete question: can a
360-slot dual-trit phase field, followed by a hyper-torus/hypercube foothold
search, identify a tiny planted LWE secret better than matched controls?

The added surface is deliberately narrow:

```text
all nine dual-trit states
    + exact mirrored 30-degree cyclotomic rotations
    -> 360 unique complete candidate probes
    -> exact integer toy-LWE objective
    -> optional best-first C3^d trit-torus expansion
       (support Q_d edges + direct sign seam)
```

“360” means 360 deterministic labelled probes. There is no canonical set of
360 one-degree directions in an eight-dimensional ternary cube. The report
counts phase-projection collisions instead of hiding them.

## Controls and stop rules

Each heuristic gets exactly 360 objective evaluations:

1. dual-trit phase probes;
2. uniform random probes;
3. 64 phase probes followed by trit-torus best-first expansion;
4. 64 random probes followed by the same expansion;
5. center-origin followed by the same expansion.

Exhaustive search over all `3^8 = 6,561` candidates supplies ground truth. The
existing safe interval-bound search must agree exactly. Candidate proposals,
duplicates, frontier expansions, objective calls, exact hits, objective gap,
and Hamming distance to the optimum are all recorded. The geometry never
prunes a region. A measured advantage requires the phase method to beat both
the matched random control and the unstructured start by more than two
population standard deviations across paired seeds.

This benchmark may reject a search heuristic. It cannot validate or invalidate
the broader governance, tokenizer, braid, wafer, or patent architecture.
