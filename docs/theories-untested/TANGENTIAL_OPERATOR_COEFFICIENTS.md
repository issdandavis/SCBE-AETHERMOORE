# Tangential Operator Coefficients

**Status**: theories-untested
**Source**: Grok collaboration session, 2026-03-26
**Related code**: `src/symphonic_cipher/scbe_aethermoore/phdm_module.py` (L434-442, curvature decomposition)

## Core Idea

Any state update F(x) on a constraint manifold can be split into:
- **Normal component** T_perp: pushes across a boundary / surface (class change)
- **Tangential component** T_par: moves along the surface (in-class reorientation)

The tangential operator coefficients alpha_i are the weights that determine how
a state turns or flows along a constraint surface WITHOUT leaving the semantic
or structural class defined by the governing form.

## Formal Definition

Given constraint shell M_c = {q : Q_tilde(q) = c} and state update field F(q):

    T_tan(q) = F(q) - <F(q), grad(Q_tilde(q))> / ||grad(Q_tilde(q))||^2 * grad(Q_tilde(q))

Expanded in tangent basis tau_1, tau_2, ..., tau_k:

    T_tan(q) = sum_i alpha_i(q) * tau_i(q)

The scalars alpha_i(q) are the tangential operator coefficients.

## In the SCBE Quadratic Ternary System

Compound state: q = (x, y, z)
Quadratic form: Q(q) = ax^2 + by^2 + cz^2 + dxy + eyz + fzx
Level sets: Q(q) = constant (constraint surfaces)

For a cyclic turning operator T(x,y,z) = (y,z,x):
- Tangential coefficients tell how much of the turn stays on the same quadratic shell
- Normal coefficients control boundary crossing

## Semantic Interpretation

| Component | Controls | Example |
|-----------|----------|---------|
| Normal coefficients | Class change, breach, collapse | Moving from ALLOW to DENY |
| Tangential coefficients | In-class reorientation, emphasis shift | Rotating between RU-heavy and KO-heavy within same trust level |

## Connection to Existing Code

The PHDM module already does tangential/normal decomposition for curvature:

```python
# phdm_module.py L434-442
tangent = gamma_prime / norm_prime
tangential_component = np.dot(gamma_double_prime, tangent) * tangent
normal_component = gamma_double_prime - tangential_component
kappa = np.linalg.norm(normal_component) / (norm_prime**2)
```

This is the same mathematical operation. The new framing names the coefficients
explicitly and connects them to governance semantics.

## Connection to Runtime Gate

In `src/governance/runtime_gate.py`, the 6D tongue coordinate vector and its
spin quantization already implicitly decompose into normal (distance from centroid)
and tangential (rotation within the tongue space). The harmonic cost is the normal
component cost. The tangential coefficients would measure HOW the vector rotates
within the allowed region.

## Connection to Phi-Poincare Shells

In `src/primitives/phi_poincare.py`, each phi shell is a constraint surface.
Movement between shells = normal (costs increase exponentially via harmonic wall).
Movement along a shell = tangential (free rotation within that trust level).

The Fibonacci consensus ladder quantizes the normal direction.
Tangential coefficients would quantize the rotational freedom within each shell.

## Potential Implementation

```python
def tangential_decomposition(v: np.ndarray, grad_q: np.ndarray) -> tuple:
    """Split vector v into tangential and normal components relative to grad_q."""
    normal_proj = np.dot(v, grad_q) / np.dot(grad_q, grad_q) * grad_q
    tangential = v - normal_proj
    return tangential, normal_proj
```

This is already partially implemented in the PHDM curvature code.
Full integration would wire it into the runtime gate's tongue coordinate analysis.

## What This Does NOT Claim

- Does not claim the foam metaphor is validated
- Does not claim tangential coefficients are already in the runtime pipeline
- Does not claim this replaces the harmonic wall cost function
- Claims only that the decomposition is mathematically clean and maps naturally
  to existing code structures
