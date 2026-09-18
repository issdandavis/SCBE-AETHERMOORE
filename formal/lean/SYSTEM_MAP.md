# Formalization map: SCBE layers and contracts

This scoped map extends `../../SYSTEM_MAP.md` and
`../../docs/specs/CANONICAL_FORMULA_REGISTRY.md`. It follows `PY_FULL14` unless a
row names another source. `TS_PIPELINE14`, `PY_REFERENCE14` and the public scan
surface remain separate profiles. Their Layer 11 formulas are not equivalent.

```mermaid
flowchart TD
    B[Finite bytes] --> T[Six tongue vocabularies]
    T --> C[Context encoder: provenance and dimensions]
    C --> W[L3 positive phi weighting]
    W --> E[L4 open-ball embedding]
    E --> G[L5 Poincare distance argument]
    G --> D[L6-L11 deformation, realm and coherence evidence]
    D --> H[L12 bounded safety score]
    H --> P[L13 policy decision]
    P --> A[All mandatory decisions composed without weakening]
    CFG[Trusted directed CFG] --> EDGE[Exact directed-edge check]
    GEO[Geometric route proposal] -. ranking only .-> EDGE
    EDGE --> EXEC[Guarded execution]
    A --> EXEC
    A --> R[Final ALLOW admits reference candidate]
    EXEC --> LOG[L14 and audit receipt]
    H -. distinct formula .-> COST[Patent exponential cost: separate regime]
```

Arrows describe intended contracts, not a claim that every path is connected in
the deployed product. The executable audit traces the named Python sources.

## Layer inventory

`F` below abbreviates
`src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py`.

| Layer | Actual component / input → output | Proof or remaining obligation |
|---|---|---|
| 1 | `F:layer_1_complex_context`; identity/intent/trajectory/time/commitment/signature → complex coordinates | No provenance or signature-verification proof. Numeric features are not cryptographic identities. |
| 2 | `F:layer_2_realify`; complex → real coordinates | Real/imaginary layout and inverse not yet formalized. |
| 3 | `F:layer_3_weighted`; real coordinates → weighted coordinates | Lean proves positive phi powers and positivity of a weighted quadratic energy for positive weights. No numerical kernel proof. |
| 4 | `F:layer_4_poincare`; weighted coordinates → ball coordinates | Open-ball premise is explicit in geometry theorems. Tanh saturation and clamping remain unproved. |
| 5 | `F:layer_5_hyperbolic_distance`; two ball points → distance | Lean: positive denominator, argument >=1, symmetry, diagonal argument. Python: 64 interior samples, 192 checks. Full metric proof open. |
| 6 | `F:layer_6_breathing`; point/time → radially deformed point | Measured counterexample to header's isometry assertion. Zero-factor invertibility case needs a declared policy. |
| 7 | `F:layer_7_phase`; point/phase/translation → transformed point | Prove translation/rotation domain constraints and metric behavior separately from breathing. |
| 8 | `F:layer_8_multi_well`; point/realm centers → minimum distance/index | Well-defined finite centers and domain validation not yet formalized. |
| 9 | `F:layer_9_spectral_coherence`; signal → coherence | Sampling/FFT normalization, empty signal and bounds need a named contract. |
| 10 | `F:layer_10_spin_coherence`; phase evidence → coherence | Optional 47D backend and fallback differ. No parity theorem. |
| 11 | `F:layer_11_triadic_distance`; geometry/time/entropy/fidelity → aggregate | Actual full-profile formula differs from TS/reference profiles. State validity and norm contract open. |
| 12 | `F:layer_12_harmonic_scaling`; distance/phase → `1/(1+d+2p)` | Lean positivity, upper bound and monotonicity. Runtime invalid-input audit passes only on local repairs. |
| 13 | `F:layer_13_decision`; scores/thresholds → risk assessment | Lean evidence-risk bounds and abstract restriction composition. Exact branch thresholds and IEEE behavior need further refinement. |
| 14 | `F:layer_14_audio_axis`; audio/context → telemetry | No audio, timing, receipt-authenticity or side-channel theorem. |

## Interfaces outside the numbered layers

| Boundary | Source and connection | Status |
|---|---|---|
| Reversible tongue data | `src/crypto/sacred_tongues.py`; byte ↔ vocabulary tables | General sequence laws proved under equivalences; exported table dimensions proved; concrete table uniqueness and round trips tested. Semantic understanding and constant-time execution are separate. |
| Directed program routes | `src/symphonic_cipher/topological_cfi.py`; CFG → initialized transition checker | Abstract legal-path and fuel theorems proved. Local repaired checker matches bounded enumeration; GitHub snapshot does not. |
| Decision wrapper | `src/symphonic_cipher/scbe_aethermoore/full_system.py`; L13 + other checks → final decision | Restriction composition proved abstractly; wrapper tested across four modes, cold/warm starts and four input decisions. |
| Reference admission | Same wrapper; final decision + candidate → stored reference | Abstract refusal preservation proved; no whole Python state-machine proof. |
| Runtime gate / GeoSeal | `src/governance/runtime_gate.py`, `src/crypto/geoseal_execution_gate.py` where present | Adjacent consumers requiring principal/resource/context/replay contracts. Not certified by this suite. |
| PHDM / manifold state | `src/harmonic/`, package `unified.py`, `ManifoldController` | Supplies geometry and state diagnostics. No global stability or containment proof. |
| Clay, Loom/Rubix, Hydra and tools | Learners/proposers and adapters consuming shared encodings | Must pass proposals through the authoritative checks; training correctness is not assumed. No worker or model was changed here. |
| Patent cost regime | Registered `QUADRATIC_EXP_COST` and local draft equation `R^(d^2)` | Exact-real monotonic cost proved independently of the L12 score. |

## Authority, resources and rollback

The Lean definitions are the proof authority; immutable source hashes identify
the implementation being compared. A Git commit alone is insufficient for a
dirty tree. A Python pass is finite evidence, not a proof of all inputs.

Work is isolated under `formal/lean` on a worktree based on GitHub main. Existing
local repairs, patent originals, training code, weights and data remain in their
own locations. Rollback removes this isolated proof project/branch; it requires
no model rollback and no runtime migration. Toolchain and Mathlib caches are
rebuildable and ignored by Git. Proof checking is CPU-only with two Lean threads.

New claims must state the quantity, domain, profile, proof assumptions, source
correspondence and counterexamples before receiving a stronger evidence label.
