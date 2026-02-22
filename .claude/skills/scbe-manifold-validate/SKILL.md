---
name: scbe-manifold-validate
description: Validate geometric integrity on the 9D Quantum Hyperbolic Manifold Memory using toroidal Riemannian distance, the Snap Protocol, and ManifoldController logic. Use when checking write permissions, computing divergence between state points, or enforcing the geometric epsilon threshold.
---

# SCBE Manifold Validate

Use this skill to enforce geometric governance on state transitions within the SCBE-AETHERMOORE manifold.

## Core Concepts

### ManifoldController Parameters
- `R_major = 10.0` — Torus major radius
- `r_minor = 2.0` — Torus minor radius
- `epsilon = 1.5` — Geometric Snap Threshold (EPSILON)

### Coordinate Mapping
- Domain string → SHA-256 → stable angle θ ∈ [0, 2π]
- Sequence string → SHA-256 → stable angle φ ∈ [0, 2π]
- Every interaction maps to toroidal coordinates (θ, φ)

### Riemannian Distance (Torus Metric)
```
ds² = (R + r·cos(θ))²·dφ² + r²·dθ²
```
- Angular distance uses shortest-path: `min(|a₁ - a₂|, 2π - |a₁ - a₂|)`
- Average θ used for metric tensor evaluation

### Snap Protocol (Write Validation)
- First write always succeeds (no previous state to compare)
- Subsequent writes: compute `geometric_divergence(p_prev, p_new)`
- If distance ≤ epsilon → `WRITE_SUCCESS`
- If distance > epsilon → `WRITE_FAIL` with `GEOMETRIC_SNAP_DETECTED`

## Workflow

1. Receive the previous fact (with stored θ, φ) and new fact (domain, content).
2. Map the new fact to toroidal coordinates via `stable_hash`.
3. Compute Riemannian distance on the torus between previous and new coordinates.
4. Compare distance against epsilon threshold.
5. Return success with coordinates or failure with divergence details.

## Invariants

1. `stable_hash` must be deterministic — same input always yields same angle.
2. Distance is always non-negative and symmetric.
3. Epsilon = 1.5 is the canonical threshold; do not change without architectural review.
4. The torus metric `(R + r·cos(θ))²` couples φ-distance to θ-position.

## Output Contract

1. Result dict with `status` ("WRITE_SUCCESS" or "WRITE_FAIL").
2. On success: `distance` and `coordinates` (θ, φ).
3. On failure: `error`, `divergence`, and `threshold`.

## Guardrails

1. Never bypass the snap check for convenience.
2. Preserve the SHA-256 → [0, 2π] mapping exactly.
3. Do not approximate the torus metric with Euclidean distance.
4. Log all WRITE_FAIL events for audit.
