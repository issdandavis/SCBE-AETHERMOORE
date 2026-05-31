# Design Document: SCBE Axiom Core

## Overview

This design implements the unified SCBE (Spectral Context-Bound Encryption) system combining a 14-layer hyperbolic geometry pipeline (Python) with cryptographic envelope operations (TypeScript). The mathematical core computes risk governance decisions via Poincaré ball embeddings, while the cryptographic layer secures message passing.

The system satisfies axioms A1-A12 which guarantee:

- Well-defined geometric operations (A1-A5)
- Correct transform properties (A6-A8)
- Bounded signal features (A9-A11)
- Monotone risk functional (A12)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SCBE Unified System                          │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Python Mathematical Core                        │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │   │
│  │  │ L1-L3   │→ │ L4-L7   │→ │ L8-L11  │→ │ L12-L14 │        │   │
│  │  │ Context │  │Hyperbolic│  │Coherence│  │  Risk   │        │   │
│  │  │Transform│  │ Geometry │  │ Signals │  │Decision │        │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│                    Risk Decision (ALLOW/QUARANTINE/DENY)            │
│                              ↓                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │           TypeScript Cryptographic Envelope                  │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │   │
│  │  │   KMS    │  │  Nonce   │  │  AES-GCM │  │  Replay  │    │   │
│  │  │  HKDF    │  │ Manager  │  │ Encrypt  │  │  Guard   │    │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Python Mathematical Core

#### SCBEConfig (Configuration Dataclass)

```python
@dataclass
class SCBEConfig:
    D: int              # Complex dimension (A1)
    K: int              # Number of realms (A8)
    alpha: float        # Embedding scale (A4)
    eps_ball: float     # Clamping margin (A4)
    eps: float          # Denominator floor (A9)
    b_min: float        # Breathing min (A6)
    b_max: float        # Breathing max (A6)
    lambda1-3: float    # Triadic weights (A11)
    w_d,w_c,w_s,w_τ,w_a: float  # Risk weights (A12)
    R: float            # Harmonic base (A12)
    theta1, theta2: float  # Decision thresholds (A12)
```

#### HyperbolicOps (Static Methods)

```python
class HyperbolicOps:
    @staticmethod
    def poincare_embed(x: ndarray, alpha: float) -> ndarray  # A4

    @staticmethod
    def clamp(u: ndarray, eps_ball: float) -> ndarray  # A4

    @staticmethod
    def hyperbolic_distance(u: ndarray, v: ndarray, eps: float) -> float  # A5

    @staticmethod
    def mobius_add(u: ndarray, v: ndarray, eps: float) -> ndarray  # A5/A7

    @staticmethod
    def breathing_transform(u: ndarray, b: float) -> ndarray  # A6

    @staticmethod
    def phase_transform(u: ndarray, a: ndarray, Q: ndarray) -> ndarray  # A7
```

#### QuasiDimensionalOps (Static Methods)

```python
class QuasiDimensionalOps:
    @staticmethod
    def slice_2d(x: ndarray, k: int) -> ndarray  # A13: Extract k-th 2D slice

    @staticmethod
    def stereographic_project(uv: ndarray) -> ndarray  # A13: ℝ² → S²

    @staticmethod
    def stereographic_inverse(xyz: ndarray) -> complex  # A13: S² \ {N} → ℂ

    @staticmethod
    def multi_sphere_distance(x: ndarray, weights: ndarray, Q: int) -> float  # A13

    @staticmethod
    def is_near_north_pole(xyz: ndarray, tol: float) -> bool  # A13: Boundary check

    @staticmethod
    def cross_ratio(z1: complex, z2: complex, z3: complex, z4: complex) -> complex  # A14

    @staticmethod
    def conformal_factor(u: ndarray) -> float  # A14: λ(u) = 2/(1-‖u‖²)
```

#### SCBESystem (14-Layer Pipeline)

```python
class SCBESystem:
    def __init__(self, config: SCBEConfig)

    # Layers 1-3: Context Transform
    def layer1_complex_context(amplitudes, phases) -> ndarray
    def layer2_realification(c: ndarray) -> ndarray
    def layer3_weighted_transform(x: ndarray) -> ndarray

    # Layers 4-7: Hyperbolic Geometry
    def layer4_poincare_embedding(x_G: ndarray) -> ndarray
    def layer5_mobius_stabilization(u: ndarray, realm_idx: int) -> ndarray
    def layer6_breathing(u: ndarray, b: float) -> ndarray
    def layer7_phase_transform(u: ndarray, a: ndarray, phase: float) -> ndarray

    # Layers 8-11: Coherence Signals
    def layer8_realm_distance(u: ndarray) -> Tuple[float, ndarray]
    def layer9_spectral_coherence(telemetry: ndarray) -> float
    def layer10_spin_coherence(phases: ndarray) -> float
    def layer11_behavioral_trust(x: ndarray) -> float

    # Layers 12-14: Risk Decision
    def layer12_harmonic_scaling(d_star: float) -> float
    def layer13_composite_risk(...) -> Tuple[float, float, Decision]
    def layer14_audio_coherence(audio: ndarray) -> float

    # Full Pipeline
    def process_context(...) -> Dict
```

### TypeScript Cryptographic Envelope

#### Envelope Interface

```typescript
interface Envelope {
  aad: AAD; // Additional Authenticated Data
  kid: string; // Key ID
  nonce: string; // Base64url 96-bit
  tag: string; // Base64url 128-bit
  ciphertext: string; // Base64url encrypted body
}

interface AAD {
  envelope_version: string;
  env: string;
  provider_id: string;
  model_id: string;
  intent_id: string;
  phase: string;
  ts: number;
  ttl: number;
  content_type: string;
  schema_hash: string;
  canonical_body_hash: string;
  request_id: string;
  replay_nonce: string;
  risk_decision?: string; // NEW: Risk metadata
  risk_value?: number; // NEW: Risk value
}
```

#### Risk-Gated Envelope Creation

```typescript
async function createGatedEnvelope(
  params: CreateParams,
  riskResult: RiskResult
): Promise<Envelope | null> {
  if (riskResult.decision === 'DENY') {
    return null; // Reject
  }

  const envelope = await createEnvelope({
    ...params,
    // Include risk in AAD
  });

  if (riskResult.decision === 'QUARANTINE') {
    envelope.aad.audit_flag = true;
  }

  return envelope;
}
```

## Data Models

### Configuration Schema (JSON)

```json
{
    "D": 6,
    "K": 4,
    "alpha": 1.0,
    "eps_ball": 0.01,
    "eps": 1e-5,
    "b_min": 0.5,
    "b_max": 2.0,
    "lambda1": 0.33,
    "lambda2": 0.34,
    "lambda3": 0.33,
    "d_scale": 1.0,
    "w_d": 0.20,
    "w_c": 0.20,
    "w_s": 0.20,
    "w_tau": 0.20,
    "w_a": 0.20,
    "R": 2.718281828,
    "theta1": 0.33,
    "theta2": 0.67,
    "realm_centers": [[0,0,...], [0.1,0.1,...], ...],
    "quasi_dimensional": {
        "Q": 3,
        "sphere_weights": [0.4, 0.35, 0.25],
        "boundary_threshold": 1e6,
        "north_pole_tolerance": 1e-8
    }
}
```

### Pipeline Result Schema

```json
{
  "risk_base": 0.35,
  "risk_prime": 0.42,
  "decision": "QUARANTINE",
  "coherence": {
    "C_spin": 0.85,
    "S_spec": 0.72,
    "tau_trust": 0.68,
    "S_audio": 0.91
  },
  "d_star": 0.28,
  "d_tri_norm": 0.31,
  "u_final_norm": 0.87
}
```

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Realification Isometry

_For any_ complex vector c ∈ ℂ^D, the realification map Φ₁ shall preserve the norm: ‖Φ₁(c)‖*ℝ = ‖c‖*ℂ

**Validates: Requirements 1.2**

### Property 2: Realification Dimension

_For any_ complex vector c ∈ ℂ^D, the realification map shall produce a real vector of dimension 2D with components ordered as (Re(z₁),...,Re(z_D),Im(z₁),...,Im(z_D))

**Validates: Requirements 1.1, 1.3**

### Property 3: Poincaré Embedding Boundedness

_For any_ real vector x ∈ ℝ^n and any α > 0, the Poincaré embedding Ψ*α(x) shall satisfy ‖Ψ*α(x)‖ < 1 (strictly inside unit ball)

**Validates: Requirements 3.1, 3.3**

### Property 4: Clamping Correctness

_For any_ point u ∈ ℝ^n and ε ∈ (0,1):

- If ‖u‖ ≤ 1-ε, then Π_ε(u) = u (unchanged)
- If ‖u‖ > 1-ε, then ‖Π*ε(u)‖ = 1-ε and Π*ε(u) is collinear with u

**Validates: Requirements 3.4, 3.5**

### Property 5: Hyperbolic Distance Symmetry

_For any_ two points u, v in the clamped ball 𝔹^n\_{1-ε}, the hyperbolic distance shall be symmetric: d_H(u,v) = d_H(v,u)

**Validates: Requirements 4.4**

### Property 6: Hyperbolic Distance Denominator Bound

_For any_ two points u, v in 𝔹^n\_{1-ε}, the denominator (1-‖u‖²)(1-‖v‖²) shall be bounded below by ε² · (2-ε)² > 0

**Validates: Requirements 4.3**

### Property 7: Breathing Ball Preservation

_For any_ point u ∈ 𝔹^n and any breathing parameter b ∈ [b_min, b_max], the breathing transform T_breath(u; b) shall remain in 𝔹^n

**Validates: Requirements 5.4**

### Property 8: Breathing Non-Isometry

_For any_ two distinct points u, v ∈ 𝔹^n and breathing parameter b ≠ 1, the breathing transform shall change hyperbolic distances: d_H(T_breath(u), T_breath(v)) ≠ d_H(u, v)

**Validates: Requirements 5.5**

### Property 9: Phase Transform Isometry

_For any_ two points u, v ∈ 𝔹^n, translation a ∈ 𝔹^n, and orthogonal Q ∈ O(n), the phase transform shall preserve hyperbolic distance: d_H(T_phase(u), T_phase(v)) = d_H(u, v)

**Validates: Requirements 6.4, 6.5**

### Property 10: Realm Center Boundedness

_For all_ realm centers μ_k (k=1,...,K), after initialization the system shall ensure ‖μ_k‖ ≤ 1-ε_ball

**Validates: Requirements 7.1, 12.4**

### Property 11: Coherence Boundedness

_For any_ valid input signals, all coherence features shall be bounded in [0,1]:

- S_spec(t) ∈ [0,1]
- S_audio(t) ∈ [0,1]
- C_spin(t) ∈ [0,1]
- τ(t) ∈ [0,1]

**Validates: Requirements 9.1, 9.2, 9.3, 9.4**

### Property 12: Risk Monotonicity

_For any_ fixed values of other inputs, the amplified risk Risk' shall be:

- Monotonically decreasing in each coherence signal (higher coherence → lower risk)
- Monotonically increasing in d̃_tri (higher deviation → higher risk)

**Validates: Requirements 11.3, 11.4, 13.6**

### Property 13: Risk Weights Sum

_For any_ valid configuration, the risk weights shall satisfy: w*d + w_c + w_s + w*τ + w_a = 1

**Validates: Requirements 11.1**

### Property 14: Decision Threshold Correctness

_For any_ computed Risk' value:

- Risk' < θ₁ → Decision = ALLOW
- θ₁ ≤ Risk' < θ₂ → Decision = QUARANTINE
- Risk' ≥ θ₂ → Decision = DENY

**Validates: Requirements 11.6, 11.7, 11.8**

### Property 15: Configuration Round-Trip

_For any_ valid configuration Θ satisfying all axiom constraints, serializing to JSON then deserializing shall produce an equivalent configuration

**Validates: Requirements 15.1**

### Property 16: Pipeline Determinism

_For any_ fixed configuration Θ and input (amplitudes, phases, telemetry, audio), executing the 14-layer pipeline twice shall produce identical results

**Validates: Requirements 16.4**

### Property 17: Envelope Risk Gating

_For any_ risk decision:

- ALLOW → envelope creation permitted
- QUARANTINE → envelope created with audit_flag = true
- DENY → envelope creation rejected (returns null/error)

**Validates: Requirements 14.1, 14.2, 14.3**

### Property 18: Stereographic Round-Trip

_For any_ 2D point (u,v) ∈ ℝ² with finite norm, the stereographic projection round-trip shall be identity: F⁻¹(F(u,v)) = (u,v) up to numerical tolerance

**Validates: Requirements 17.2, 17.3, 17.7**

### Property 19: Multi-Sphere Distance Aggregation

_For any_ state vector x ∈ ℝ^{2D} and sphere weights w_k, the multi-sphere distance d_multi(x) shall equal Σ_k w_k · d_S²(F(Σ_k(x)), origin_k)

**Validates: Requirements 17.5**

### Property 20: Sphere Weights Sum

_For any_ valid quasi-dimensional configuration, the sphere weights shall satisfy: w_k ≥ 0 for all k, and Σw_k = 1

**Validates: Requirements 17.6**

### Property 21: Multi-Sphere Risk Monotonicity

_For any_ fixed values of other inputs, the risk functional shall be monotonically increasing in d_multi: higher multi-sphere distance → higher risk

**Validates: Requirements 17.10**

### Property 22: Möbius Transform Commutativity

_For any_ point u ∈ 𝔹^n, translation a ∈ 𝔹^n, and orthogonal Q ∈ O(n), the Möbius transforms shall commute between representations: F(M_B(u; a, Q)) = M_S(F(u); T) where T is the corresponding PSL(2,ℂ) element

**Validates: Requirements 18.3**

### Property 23: Cross-Ratio Invariance

_For any_ four distinct points z₁, z₂, z₃, z₄ ∈ ℂ̂ and any Möbius transform M, the cross-ratio shall be preserved: CR(M(z₁), M(z₂), M(z₃), M(z₄)) = CR(z₁, z₂, z₃, z₄)

**Validates: Requirements 18.4**

### Property 24: Realm Distance Representation Consistency

_For any_ state u ∈ 𝔹^n and realm center μ_k, computing the hyperbolic distance in the Poincaré ball shall equal the corresponding spherical distance after stereographic projection

**Validates: Requirements 18.5**

## Error Handling

### Configuration Validation Errors

- `InvalidDimension`: D < 1 or K < 1
- `InvalidEpsilon`: eps_ball ∉ (0,1) or eps ≤ 0
- `InvalidBreathingBounds`: b_min > b_max or b_min ≤ 0
- `InvalidWeights`: weights don't sum to 1 or any weight < 0
- `InvalidThresholds`: θ₁ ≥ θ₂
- `InvalidRealmCenter`: ‖μ_k‖ ≥ 1-ε_ball

### Runtime Errors

- `NumericalInstability`: Denominator approaches zero despite ε floor
- `LayerFailure`: Any layer throws exception → halt pipeline
- `EnvelopeRejected`: Risk decision is DENY

### Error Response Format

```python
class SCBEError(Exception):
    def __init__(self, code: str, message: str, layer: Optional[int] = None):
        self.code = code
        self.message = message
        self.layer = layer
```

## Testing Strategy

### Property-Based Testing (Hypothesis)

All correctness properties will be tested using the `hypothesis` library with minimum 100 iterations per property.

```python
from hypothesis import given, strategies as st, settings

@settings(max_examples=100)
@given(st.complex_numbers(allow_nan=False, allow_infinity=False))
def test_realification_isometry(c):
    """Property 1: Realification preserves norm"""
    # Feature: scbe-axiom-core, Property 1: Realification Isometry
    x = realify(c)
    assert abs(np.linalg.norm(x) - abs(c)) < 1e-10
```

### Unit Tests

Unit tests cover specific examples and edge cases:

- Zero vector handling (x=0, u=0)
- Boundary conditions (‖u‖ = 1-ε exactly)
- Configuration validation errors
- Known mathematical identities

### Integration Tests

- Full 14-layer pipeline execution
- Risk-gated envelope creation flow
- Round-trip serialization
- Performance budget verification

### Test Organization

```
tests/
├── test_hyperbolic_ops.py      # Properties 3-9
├── test_quasi_dimensional.py   # Properties 18-24 (NEW)
├── test_coherence.py           # Property 11
├── test_risk_functional.py     # Properties 12-14, 21
├── test_serialization.py       # Property 15
├── test_pipeline.py            # Property 16
├── test_integration.py         # Property 17
└── test_config_validation.py   # Configuration errors
```
