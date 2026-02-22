---
name: scbe-governance-gate
description: Evaluate the Grand Unified Governance function G(xi, i, poly) that makes ALLOW/DENY/QUARANTINE decisions based on the full 9D state, intent, and polyhedral topology. Use when implementing or modifying the governance decision pipeline, adding new constraint checks, or debugging access decisions.
---

# SCBE Governance Gate

Use this skill to implement and reason about the Grand Unified Governance function that is the core decision engine of SCBE-AETHERMOORE.

## Function Signature

```
G(xi, intent, poly_topology) → (decision, reason)
```

- **xi**: 9D state vector [c(t), τ(t), η(t), q(t)]
- **intent**: float — recovered intent value from audio layer
- **poly_topology**: dict with V, E, F — vertex/edge/face counts
- **Returns**: ("ALLOW"|"DENY"|"QUARANTINE", reason_string)

## Decision Hierarchy (Ordered by Priority)

### 1. Topological Check (QUARANTINE)
```
χ = V - E + F
if χ ≠ 2 → QUARANTINE "Topological Fracture"
```
- Euler characteristic must equal 2 (closed orientable surface).
- Example valid topology: Cube (V=8, E=12, F=6 → χ=2).

### 2. Entropy Bounds (QUARANTINE)
```
if η < ETA_MIN(2.0) or η > ETA_MAX(6.0) → QUARANTINE "Entropy Anomaly"
```
- Entropy must stay within [2.0, 6.0] range.
- Uses real part of η (guards against complex dtype propagation).

### 3. Time Causality (QUARANTINE)
```
if τ̇ ≤ 0 → QUARANTINE "Causality Violation"
```
- Time must flow forward. Reversal is a hard block.

### 4. Quantum State (QUARANTINE)
```
if fidelity < 0.9 or von_neumann_entropy > 0.2 → QUARANTINE "Quantum Decoherence"
```
- Quantum coherence must be maintained.

### 5. Harmonic & Geometric Coherence (ALLOW/DENY)
```
if coherence ≥ TAU_COH(0.9) AND d_triadic ≤ EPSILON(1.5) AND H(d) ≤ H_MAX(10.0):
    → ALLOW "Harmonic Resonance Confirmed"
else:
    → DENY "Incoherent State"
```

## Derived Metrics

| Metric              | Source                   | Threshold          |
|---------------------|--------------------------|-------------------|
| Coherence (coh)     | Intent phase alignment   | ≥ 0.9 (TAU_COH)  |
| Triadic Divergence  | Metric tensor            | ≤ 1.5 (EPSILON)   |
| Harmonic Cost H(d)  | Harmonic series          | ≤ 10.0 (H_MAX)    |
| Curvature (κ)       | Manifold geometry        | ≤ 0.1 (KAPPA_MAX) |
| Lyapunov (λ)        | Stability analysis       | ≤ 0.001           |

## Six Sacred Tongues (Domain Separation)

```
TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_WEIGHTS = [PHI^k for k in 0..5]
```

## Modality Masks

| Mode     | Harmonics Used |
|----------|---------------|
| STRICT   | [1, 3, 5]    |
| ADAPTIVE | [1, 2, 3, 4, 5] |
| PROBE    | [1]           |

## Workflow

1. Unpack 9D state vector into c(t), τ, η, q components.
2. Cast η to real (guard against complex dtype).
3. Run checks in priority order: topology → entropy → causality → quantum → harmonic.
4. Return first failing QUARANTINE or the final ALLOW/DENY.

## Guardrails

1. Check order is strict — QUARANTINE checks must precede ALLOW/DENY.
2. Euler characteristic χ=2 is non-negotiable for closed surfaces.
3. Never skip the causality check (τ̇ > 0).
4. The coherence threshold TAU_COH=0.9 is a locked constant.
5. All QUARANTINE events should trigger alerts in production.
