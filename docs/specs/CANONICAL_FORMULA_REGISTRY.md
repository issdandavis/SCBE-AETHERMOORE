# SCBE-AETHERMOORE: Canonical Formula Registry

**Version**: 1.0.0
**Lock Date**: 2026-04-05
**Authority**: This document is the SINGLE SOURCE OF TRUTH for all mathematical formulas in the 14-layer pipeline. Any formula in code, docs, patents, or training data that contradicts this registry is WRONG and must be updated.

**Rule**: No formula in this document may be changed without incrementing the version and documenting the change in the changelog at the bottom.

---

## Layer 1: Kernel Initialization (Composition Axiom)

**Purpose**: Bootstrap cryptographic identity via post-quantum primitives.

```
I = E(pk_KEM) || Sign(SK_DSA, hash(pk_KEM))
```

| Parameter | Value | Tunable |
|-----------|-------|---------|
| KEM algorithm | ML-KEM-768 (Kyber) | No |
| DSA algorithm | ML-DSA-65 (Dilithium) | No |
| Hash | SHA3-256 | No |

**Implementation**: `packages/kernel/src/index.ts`
**Status**: LOCKED

---

## Layer 2: 21D State Manifold & Realification (Unitarity Axiom)

**Purpose**: Define the product metric over the full state space.

```
d_M(a,b)² = w_h · d_hyp(u_a, u_b)² + w_t · d_torus(θ_a, θ_b)² + (z_a - z_b)ᵀ · W_z · (z_a - z_b)
```

Where:
- `u ∈ B⁶` — tongue positions in Poincare ball (s[0..5])
- `θ ∈ T⁶` — tongue phases on torus (s[6..11])
- `z ∈ R⁹` — governance telemetry (s[12..20])

Sub-metrics:
```
d_hyp(u,v) = arcosh(1 + 2‖u-v‖² / ((1-‖u‖²)(1-‖v‖²)))
d_torus(θ_a, θ_b) = Σ_l min(|θ_a^l - θ_b^l|, 2π - |θ_a^l - θ_b^l|)
```

| Parameter | Default | Tunable |
|-----------|---------|---------|
| w_h (hyperbolic weight) | 1.0 | Yes |
| w_t (torus weight) | 0.5 | Yes |
| W_z (9x9 telemetry matrix) | diag(1,...,1) | Yes |

**Implementation**: `src/ai_brain/unified-state.ts`, `docs/specs/STATE_MANIFOLD_21D_PRODUCT_METRIC.md`
**Status**: LOCKED

---

## Layer 3: Langues Weighted Transform (Locality Axiom)

**Purpose**: Compute the 6-tongue energy functional with phase-shifted exponential breathing.

```
L(x,t) = Σ_{l=1}^{6} w_l · exp(β_l · (d_l + sin(ω_l · t + φ_l)))
```

Where:
- `w_l = φ^(l-1)` — golden ratio weights: [1.00, 1.62, 2.62, 4.24, 6.85, 11.09]
- `β_l = β_base · φ^(l · 0.5)` — per-tongue sensitivity
- `ω_l = 2πl/6` — phase frequency
- `φ_l = 2πl/6` — initial phase offset
- `d_l` — distance in tongue dimension l

| Parameter | Default | Tunable |
|-----------|---------|---------|
| β_base | 1.0 | Yes |
| Amplitude A | 0.1 | Yes |
| φ (golden ratio) | 1.6180339887... | No (constant) |

**Implementation**: `packages/kernel/src/languesMetric.ts` (L104-115), `docs/LANGUES_WEIGHTING_SYSTEM.md`
**Status**: LOCKED

---

## Layer 4: Poincare Embedding (Unitarity Axiom)

**Purpose**: Embed state into the Poincare ball with norm preservation.

```
embed(x) = tanh(α · ‖x‖) · (x / ‖x‖)
```

Constraint: `‖embed(x)‖ < 1 - ε_ball` (strict interior)

| Parameter | Default | Tunable |
|-----------|---------|---------|
| α (embedding scale) | 1.0 | Yes |
| ε_ball (boundary margin) | 1e-5 | Yes |

**Implementation**: `packages/kernel/src/hyperbolic.ts`
**Status**: LOCKED

---

## Layer 5: Hyperbolic Distance (Symmetry Axiom)

**Purpose**: Compute geodesic distance in the Poincare ball. This is the INVARIANT of the system.

```
d_ℍ(u,v) = arcosh(1 + 2‖u-v‖² / ((1-‖u‖²)(1-‖v‖²)))
```

Properties (all proven):
- d_ℍ(u,v) ≥ 0 (non-negativity)
- d_ℍ(u,v) = 0 ⟺ u = v (identity of indiscernibles)
- d_ℍ(u,v) = d_ℍ(v,u) (symmetry)
- d_ℍ(u,w) ≤ d_ℍ(u,v) + d_ℍ(v,w) (triangle inequality)
- d_ℍ → ∞ as ‖u‖ → 1 or ‖v‖ → 1 (boundary divergence)

| Parameter | Default | Tunable |
|-----------|---------|---------|
| None | — | No (pure metric) |

**Implementation**: `packages/kernel/src/hyperbolic.ts` (L153-159)
**Status**: LOCKED — INVARIANT, NEVER MODIFY

---

## Layer 6: Breathing Transform (Causality Axiom)

**Purpose**: Radial modulation that allows controlled oscillation within the ball.

```
B(p, t) = tanh(‖p‖ + A · sin(ω · t)) · (p / ‖p‖)
```

Constraint: Output always strictly inside ball (`tanh` guarantees this).

| Parameter | Default | Tunable |
|-----------|---------|---------|
| A (amplitude) | 0.05 | Yes, A ∈ [0, 0.1] |
| ω (frequency) | 2π/60 | Yes |

**Implementation**: `packages/kernel/src/hyperbolic.ts` (L429-496)
**Status**: LOCKED

---

## Layer 7: Mobius Phase Rotation (Unitarity Axiom)

**Purpose**: Rotate state in a selected 2D plane via Givens rotation (isometry of Poincare ball).

```
[p'_i]   [cos(θ)  -sin(θ)] [p_i]
[p'_j] = [sin(θ)   cos(θ)] [p_j]
```

Mobius transformation form:
```
T(z, a) = (z - a) / (1 - conj(a) · z)
```

| Parameter | Default | Tunable |
|-----------|---------|---------|
| θ (rotation angle) | varies per layer pass | Yes |
| Plane (i,j) selection | (0,1) | Yes |

**Implementation**: `packages/kernel/src/hyperbolic.ts` (L530-531)
**Status**: LOCKED

---

## Layer 8: Multi-Well Realms / Hamiltonian CFI (Locality Axiom)

**Purpose**: Define K trust realms as Gaussian potential wells in the Poincare ball.

```
V(p) = Σ_{i=1}^{K} w_i · exp(-‖p - c_i‖² / (2σ_i²))
```

Realm assignment: `realm(p) = argmax_i V_i(p)`

| Parameter | Default | Tunable |
|-----------|---------|---------|
| K (number of realms) | 4 | Yes |
| w_i (well weights) | [1.0, 0.7, 0.4, 0.1] | Yes |
| c_i (well centers) | origin-centered, φ-spaced | Yes |
| σ_i (Gaussian widths) | 0.3 | Yes |

**Implementation**: `packages/kernel/src/hamiltonianCFI.ts`, `packages/kernel/src/hyperbolic.ts` (L588)
**Status**: LOCKED

---

## Layer 9: Spectral Coherence / FFT (Symmetry Axiom)

**Purpose**: Compute frequency-domain coherence via power spectrum analysis.

```
P_a[k] = |FFT(signal)[k]|² / N

S_spec = E_low / (E_low + E_high + ε)
```

Where:
- `E_low = Σ_{k ∈ K_low} P_a[k]` — low-frequency energy
- `E_high = Σ_{k ∈ K_high} P_a[k]` — high-frequency energy
- `K_high` = top `hf_frac` of frequency bins

| Parameter | Default | Tunable |
|-----------|---------|---------|
| N (FFT window) | 256 | Yes |
| hf_frac (HF cutoff) | 0.3 | Yes |
| ε (stability) | 1e-12 | No |

**Implementation**: `src/spectral/index.ts` (L55-114)
**Status**: LOCKED

---

## Layer 10: Spin Coherence (Symmetry Axiom)

**Purpose**: Measure alignment coherence across tongue dimensions.

```
C_spin = (1/6) · Σ_{l=1}^{6} cos(Δθ_l)
```

Where `Δθ_l = θ_l^current - θ_l^reference` is the phase deviation per tongue.

| Parameter | Default | Tunable |
|-----------|---------|---------|
| Reference phases | [0, 0, 0, 0, 0, 0] | Yes |

**Implementation**: `src/spectral/index.ts`
**Status**: LOCKED

---

## Layer 11: Triadic Temporal Distance (Causality Axiom)

**Purpose**: Compute time-ordered distance with causal consistency enforcement.

```
d_tri(t_1, t_2, t_3) = d_ℍ(p(t_1), p(t_2)) + d_ℍ(p(t_2), p(t_3)) - d_ℍ(p(t_1), p(t_3))
```

Normalized: `d̃_tri = d_tri / d_scale`

Causal constraint: `t_1 < t_2 < t_3` (strict temporal ordering)

| Parameter | Default | Tunable |
|-----------|---------|---------|
| d_scale (normalization) | 1.0 | Yes |
| Window (temporal lookback) | 3 samples | Yes |

**Implementation**: `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/causality_axiom.py`
**Status**: LOCKED

---

## Layer 12: Harmonic Wall (Symmetry Axiom)

**Purpose**: THE exponential cost scaling barrier. Makes adversarial behavior super-exponentially expensive.

### Single-Tongue Wall
```
H_l(d*, R) = R^((φ^l · d*)²)     for l ∈ {0,1,2,3,4,5}
```

### Unified Wall (all 6 tongues coupled)
```
H(d*, R) = R^((φ · d*)²)
```

### Toroidal Resonant Cavity (full coupling)

The 6 tongue walls couple through the Fibonacci recurrence (φ² = φ + 1):
```
H_{l+2} ↔ H_{l+1} + H_l    (cross-coupled through T⁶ = T²₁ × T²₂ × T²₃)
```

Cross-coupling terms: C(6,2) = 15 pairs from the 47D complex manifold.

Maximum combined cavity multiplier:
```
H_cavity(d*, R) = R^(φ¹⁰ · d*²) = R^(122.99 · d*²)
```

### Cost Table (R = e)

| d* | H = R^(d*²) | H = R^((φd*)²) | H_cavity = R^(122.99·d*²) |
|----|-------------|-----------------|---------------------------|
| 0.0 | 1.00× | 1.00× | 1.00× |
| 0.5 | 1.28× | 1.92× | 3.53×10¹³ |
| 1.0 | 2.72× | 13.7× | 2.60×10⁵³ |
| 1.5 | 9.49× | 233× | — |
| 2.0 | 54.6× | 35,341× | — |
| 2.5 | 518× | 4.68×10⁶ | — |
| 3.0 | 8,103× | 5.08×10⁹ | — |

Where R > 1 (default R = e ≈ 2.718).

| Parameter | Default | Tunable |
|-----------|---------|---------|
| R (harmonic base) | e ≈ 2.718 | Yes, R > 1 |
| φ (golden ratio) | 1.6180339887... | No (constant) |
| d* (normalized distance) | computed from L5 | No (derived) |

**Implementation**: `packages/kernel/src/harmonicScaling.ts` — UPDATED to `R^((φ·d*)²)` (April 2026)
**Status**: LOCKED — Formula canonical, code aligned

---

## Layer 13: Risk Decision (Causality Axiom)

**Purpose**: Aggregate all risk dimensions and apply the harmonic wall as a MULTIPLICATIVE amplifier.

```
Risk' = (w_d · d̃_tri + w_c · (1 - C_spin) + w_s · (1 - S_spec) + w_τ · (1 - τ) + w_a · (1 - S_audio)) × H(d*, R)
```

Decision thresholds:
```
Risk' < θ₁        → ALLOW
θ₁ ≤ Risk' < θ₂   → QUARANTINE
θ₂ ≤ Risk' < θ₃   → ESCALATE
Risk' ≥ θ₃         → DENY
```

| Parameter | Default | Tunable |
|-----------|---------|---------|
| w_d (triadic weight) | 0.2 | Yes |
| w_c (spin coherence weight) | 0.2 | Yes |
| w_s (spectral weight) | 0.2 | Yes |
| w_τ (trust weight) | 0.2 | Yes |
| w_a (audio weight) | 0.2 | Yes |
| θ₁ (ALLOW ceiling) | 0.3 | Yes |
| θ₂ (QUARANTINE ceiling) | 0.7 | Yes |
| θ₃ (DENY floor) | 0.9 | Yes |

**Implementation**: Risk computation across pipeline — MUST BE UPDATED from additive `base + (1-H)*0.10` to multiplicative `base × H`
**Status**: LOCKED — Formula canonical, code needs alignment

---

## Layer 14: Audio Axis / FFT Telemetry (Composition Axiom)

**Purpose**: Compute audio-domain features for multi-modal integrity.

### Frame Energy
```
E_a = log(ε + Σ_n a[n]²)
```

### Spectral Centroid
```
C_a = (Σ_k f_k · P_a[k]) / (Σ_k P_a[k] + ε)
```

### Spectral Flux
```
F_a = √(Σ_k (√P_a[k] - √P_a^prev[k])²)
```

### High-Frequency Ratio
```
r_HF = (Σ_{k ∈ K_high} P_a[k]) / (Σ_k P_a[k] + ε)
```

### Audio Stability Score
```
S_audio = 1 - r_HF
```

### Composite L14 Stability (with harmonic enforcement)
```
S_L14 = α·(1 - r_HF) + β·C_transfer + γ·(1 - rejection_ratio) + δ·harmonic_coherence
```

Where:
- `C_transfer` = signal transfer coherence
- `rejection_ratio` = interference rejection via notch filter
- `harmonic_coherence` = alignment with 6-tongue reference modes

| Parameter | Default | Tunable |
|-----------|---------|---------|
| ε (stability) | 1e-12 | No |
| Frame size | 256 samples | Yes |
| K_high boundary | top 30% | Yes |
| α, β, γ, δ (composite weights) | 0.25 each | Yes |

**Implementation**: `packages/kernel/src/audioAxis.ts` (L27-38, L103, L121, L136-140)
**Status**: LOCKED

---

## Cross-Layer Invariants

These properties must hold across ALL layers:

### I1: Unitarity Conservation
```
‖T(x)‖ ≤ ‖x‖    for all transformations T in L2, L4, L7
```

### I2: Ball Containment
```
‖p‖ < 1 - ε_ball    at every layer boundary
```

### I3: Monotonic Cost
```
d* ↑  ⟹  H(d*, R) ↑    (cost always increases with distance)
```

### I4: Causal Ordering
```
t_1 < t_2 < t_3    in all triadic evaluations
```

### I5: Weight Normalization
```
Σ w_i = 1.0    for all risk dimension weights
```

### I6: Golden Ratio Consistency
```
w_l = φ^(l-1)    for tongue weights across L3, L12, and toroidal coupling
```

---

## Toroidal Resonant Cavity (Cross-Layer Structure)

This is NOT a single layer — it's the emergent structure from L12 walls coupling through the T⁶ torus of L2.

### Plane Assignments
```
Plane 1 (horizontal):  KO (l=0, φ⁰) × AV (l=1, φ¹)  → T²₁
Plane 2 (vertical):    RU (l=2, φ²) × CA (l=3, φ³)  → T²₂
Plane 3 (tangential):  UM (l=4, φ⁴) × DR (l=5, φ⁵)  → T²₃
```

### Fibonacci Cascade Coupling
```
H_{l+2} ↔ H_{l+1} + H_l    (because φ² = φ + 1)

RU locks onto (KO + AV)
CA locks onto (AV + RU)
UM locks onto (RU + CA)
DR locks onto (CA + UM)
```

### 47D Cross-Coupling Decomposition
```
6 real dimensions        (individual tongues)
15 pair couplings        C(6,2) cross-terms
20 triple couplings      C(6,3) interference volumes
6 self-imaginary dims    per-tongue internal rotation
─────────────────────
47 total dimensions      = 47 Realities
```

### Security Equivalence
```
At d* = 1, R = e:
  Single wall:       e^1      = 2.72×         (trivial)
  φ-scaled wall:     e^(φ²)   = 13.7×         (moderate)
  Full cavity:       e^122.99  = 2.6 × 10⁵³    (176-bit equivalent)
```

**Status**: LOCKED — Formalized, awaiting code implementation

---

## Axiom-Layer Map (Reference)

| Axiom | Layers | What It Constrains |
|-------|--------|--------------------|
| **Unitarity** | L2, L4, L7 | Norm preservation through all transforms |
| **Locality** | L3, L8 | Neighborhood-dependent metrics (exponential, Gaussian) |
| **Causality** | L6, L11, L13 | Temporal ordering, risk aggregation |
| **Symmetry** | L5, L9, L10, L12 | Metric properties, gauge invariance |
| **Composition** | L1, L14 | Cryptographic init, multi-modal integration |

---

## Changelog

| Version | Date | Change | Author |
|---------|------|--------|--------|
| 1.0.0 | 2026-04-05 | Initial locked registry — all 14 layers + toroidal cavity | I. Davis |

---

## Implementation Alignment Checklist

| Layer | Formula Locked | Code Matches | Fix Required |
|-------|---------------|-------------|-------------|
| L1 | Yes | Yes | — |
| L2 | Yes | Yes | — |
| L3 | Yes | Yes | — |
| L4 | Yes | Yes | — |
| L5 | Yes | Yes | — |
| L6 | Yes | Yes | — |
| L7 | Yes | Yes | — |
| L8 | Yes | Yes | — |
| L9 | Yes | Yes | — |
| L10 | Yes | Yes | — |
| L11 | Yes | Yes | — |
| L12 | Yes | Yes | Updated April 2026 |
| L13 | Yes | Yes | 4-tier with ESCALATE |
| L14 | Yes | Yes | — |
| Cavity | Yes | **NO** | Not yet implemented |
