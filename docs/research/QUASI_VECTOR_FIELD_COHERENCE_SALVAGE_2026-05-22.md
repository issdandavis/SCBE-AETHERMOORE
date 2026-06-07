# Quasi-Vector Field Coherence Salvage Note

Status: experimental salvage / claim boundary  
Date: 2026-05-22  
Source line: Quasi Vector Spin Voxels / Magnetics notes  
Current code anchor: `src/storage/spin_voxel.py`, `tests/test_spin_voxel.py`, `docs/specs/QUASI_VECTOR_SPIN_VOXELS_MAZE_RND.md`

## 1. Purpose

This note salvages the concrete, testable parts of the Quasi Vector / Spin Voxels line while fencing off unsupported physics and cryptographic claims.

The production-safe interpretation is:

```text
spin voxel = vector-field coherence probe
```

not:

```text
spin voxel = magnetic material, spintronic security, or quantum-resistance primitive
```

## 2. Keep

### 2.1 Field Coherence

The implemented coherence metric:

```text
C_field = ||sum_i v_i|| / (sum_i ||v_i|| + epsilon)
```

is a normalized resultant length over a local vector field.

Interpretation:

| Value | Meaning |
|---|---|
| near 1 | vectors are aligned |
| near 0 | vectors cancel or are isotropically disordered |

This is usable as a drift/routing signal. It does not need spintronics language.

Repo anchor:

- `src/storage/spin_voxel.py::spin_coherence`
- `tests/test_spin_voxel.py::test_spin_coherence_alignment_vs_disorder`

### 2.2 Boundary As High Local Gradient

The implemented disorder metric:

```text
D_field = mean_(i,j in E) (1 - normalized(v_i) dot normalized(v_j))
```

is an aggregate local angular-difference score.

Interpretation:

```text
field boundary = region where neighboring vectors disagree sharply
```

This supports the useful idea that boundaries can emerge from field gradients rather than explicit fences.

Repo anchor:

- `src/storage/spin_voxel.py::spin_disorder`
- `tests/test_spin_voxel.py::test_harmonic_cost_increases_with_disorder`

### 2.3 Norm-Preserving Phase Rotation

The implemented `apply_phason()` currently functions as a deterministic z-axis rotation with phi-spaced angle selection.

Production-safe interpretation:

```text
phase rotation = deterministic perturbation / invariance probe
```

not:

```text
phason dynamics defeat Grover or create cryptographic protection
```

Repo anchor:

- `src/storage/spin_voxel.py::apply_phason`
- `tests/test_spin_voxel.py::test_phason_rotation_preserves_norm`

### 2.4 Multi-Clock T-Phase

The strongest salvage from the old note is the multi-clock idea:

```text
the same deviation metric can be amplified differently depending on the active runtime clock
```

Existing clock names:

- `fast`
- `memory`
- `governance`
- `circadian`
- `set`

Safer external wording:

```text
scheduled context rotation
```

instead of claiming biological circadian behavior.

Repo anchor:

- `src/harmonic/temporalPhase.ts`
- `tests/L2-unit/temporalPhase.unit.test.ts`

## 3. Cut Or Archive

These claims should remain archived as metaphor/research notes unless they are rebuilt from tested primitives:

| Old claim | Decision | Reason |
|---|---|---|
| intent vectors are physical spins | cut | same vector shape does not imply same physics |
| Heisenberg Hamiltonian governs intent | cut | no physical exchange interaction or joule-valued coupling exists |
| topological spin protection gives cryptographic security | cut | topological protection in materials is not adversarial computational security |
| phasons or rough cost functions defeat Grover | cut | Grover applies to unstructured oracle search; smoothness is not the defense |
| magnonic qubits for SCBE governance | archive | hardware research metaphor, not current software claim |
| skyrmion/vortex key placement | archive | security remains the hash/key primitive, not simulated geometry |
| `H0 = 1000` as typical physical scale | cut | free normalization constant without derivation |

## 4. Formula Boundary

The canonical production harmonic wall remains separate from this R&D adapter.

Production-safe:

```text
H(d, R) = R^(d^2)
```

Experimental only:

```text
H_sv = R^(d^2) * (T_phase / ||I||) * (1 + alpha * penalty_field)
```

Where:

```text
penalty_field = max(0, D_field + soft_field_bias)
```

The experimental form must not be used in patent, proposal, or production docs as a stronger canonical wall unless:

1. `penalty_field` is rewritten without physical spin claims,
2. free parameters are justified by measurable calibration,
3. benchmarks show stable value over the base harmonic wall,
4. latency and false-positive rates remain bounded,
5. tests demonstrate the exact promotion behavior.

## 5. Rename Guidance

Preferred terms:

| Prefer | Avoid in production |
|---|---|
| field coherence | spin coherence |
| angular disorder | spin disorder |
| vector-field boundary | domain wall |
| scheduled context rotation | circadian rhythm |
| deterministic phase perturbation | phason security |
| read-side reranker | write-path security primitive |

It is acceptable for code paths to keep historical names temporarily if renaming would churn tests. Public docs and new specs should use the safer terms.

## 6. Build Card

```json
{
  "schema_version": "scbe-doc-build-card-v1",
  "title": "Quasi Vector Field Coherence",
  "source_path": "docs/specs/QUASI_VECTOR_SPIN_VOXELS_MAZE_RND.md",
  "status": "partial",
  "core_claim": "Local vector-field coherence and angular disorder can serve as experimental read-side routing signals for MAZE without invoking physical magnetism.",
  "repo_anchors": [
    "src/storage/spin_voxel.py",
    "tests/test_spin_voxel.py",
    "src/harmonic/temporalPhase.ts",
    "tests/L2-unit/temporalPhase.unit.test.ts"
  ],
  "risk_class": "research-only",
  "first_slice": {
    "goal": "Rename documentation and output labels toward field coherence while preserving backward-compatible code names",
    "files": [
      "docs/specs/QUASI_VECTOR_SPIN_VOXELS_MAZE_RND.md",
      "docs/research/QUASI_VECTOR_FIELD_COHERENCE_SALVAGE_2026-05-22.md"
    ],
    "tests": [
      "python -m pytest tests/test_spin_voxel.py -q",
      "npm test -- temporalPhase"
    ],
    "acceptance": [
      "no production claim of magnetic/topological/quantum security",
      "field coherence/disorder metrics remain test-covered",
      "multi-clock T-phase remains framed as scheduled context rotation"
    ]
  },
  "do_not_build_yet": [
    "spintronics security claims",
    "Grover defeat claims",
    "patent continuation language based on magnetics",
    "write-path dependency on field-coherence score"
  ]
}
```

## 7. Short Verdict

Keep the vector-field math. Keep the multi-clock runtime idea. Keep the tests.

Do not keep the claim that governance vectors inherit condensed-matter physics or cryptographic security properties from magnetism.

## 8. Null-Gated Update

Current probe:

- `scripts/eval/spin_voxel_null_gate.py`
- `tests/eval/test_spin_voxel_null_gate.py`
- `artifacts/eval/spin_voxel_null_gate_v1.json`

The probe uses same-inventory paired fields: one smooth ring ordering and one
half-turn boundary ordering. The null shuffles each sample's vectors, preserving
spin count, unit magnitudes, and exact vector inventory while destroying local
neighborhood topology.

Run summary:

```text
verdict: FIELD_TOPOLOGY_SIGNAL
real_auc: 1.000000
shuffle_inventory_null_auc_p95: 0.588129
delta_real_minus_null95: 0.411871
smooth_median_multiplier: 1.001685
boundary_median_multiplier: 1.688272
```

Claim boundary:

```text
This validates angular-neighborhood topology as a controlled read-side field
signal. It does not validate magnetism, topological protection, quantum
resilience, or production security.
```
