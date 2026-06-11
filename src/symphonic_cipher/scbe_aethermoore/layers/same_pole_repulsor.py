"""Same-pole repulsor: an active governance field that shoves unauthorized intent off a gate.

@layer Layer 5, Layer 8, Layer 12, Layer 13
@component Same-Pole Repulsor (active complement to the passive harmonic wall)

Like magnetic poles of the same sign repel. An agent's *unauthorized* intent toward a gated
realm produces a repulsion that is provably zero for the authorized, diverges as the agent
approaches the gate, and yields a force pointing away from it.

THE POTENTIAL IS REAL HYPERBOLIC ELECTROSTATICS, not an invented analogy. The repulsion is the
Green's function of the Laplace-Beltrami operator on the Poincare disk H^2 -- the genuine static
potential of a same-sign point charge in hyperbolic space:

    G_H(d) = -log(tanh(d / 2))          # d = d_H(u, mu_gate), the Layer-5 hyperbolic distance
        -> -log(d/2) -> +infinity  as d -> 0   (TRUE divergence at contact; no epsilon floor)
        -> 2 e^{-d}  -> 0+         as d -> infinity

    Phi(u; I) = lambda * I * G_H(d)     # repulsion potential; I in [0,1] is grounded intent

Force a seeker feels (closed form, verified against finite differences of the real Layer-5
distance to ~5e-10 -- no finite-difference cusp artifact near contact):

    F(u; I) = -grad_u Phi = (lambda * I / sinh(d)) * grad_u d_H(u, mu_gate)

grad_u d_H is the ascent direction of distance-from-gate, so F points strictly AWAY from the
gate everywhere u != mu_gate (same-pole). At u == mu_gate the radial potential is stationary, so
the force is exactly zero (no garbage vector at the singularity).

GOVERNANCE EFFECT (changes DECISIONS, not just positions): the potential is added to the live
L8 realm distance and ridden through the real L12 wall and L13 thresholds:

    d_eff = d_star + Phi(u; I) ;  H_eff = layer_12(d_eff, pd) ;  decision = layer_13(d_eff, ...)

so the SAME point near the gate reads ALLOW to an authorized agent (I=0, d_eff = d_star) and is
pushed across the real 0.5 / 2.0 thresholds toward REVIEW/DENY for an intruder. Caveat kept
honest: d_eff = d_nearest_realm + Phi_gate sums the distance to the *nearest* realm and the
repulsion from the *gate* realm -- a heuristic risk inflation, not a single metric distance. The
only clean global invariant is d_eff >= d_star (strict iff I > 0).

INTENT IS GROUNDED, NOT A FREE KNOB. I = g * a is a product of two real signals:
  g = 0.0 if possesses_yolk(secret, shell, context) else 1.0   (the EXACT hardened ring gate,
      shared verbatim with SacredRituals.ring_descent via crypto.sacred_eggs.possesses_yolk, so
      they cannot drift). g = 0 for the yolk-holder makes transparency an ALGEBRAIC identity:
      I = 0 at every point, the field is invisible to the authorized.
  a = clip(1 - d_H(u, gate) / THETA_2, 0, 1)   a geometric approach ramp: repulsion only builds
      as an *un*authorized agent closes on the gate; beyond THETA_2 it is zero.
Callers never pass `intent` on the field functions through the grounded path; `intent_from_egg`
computes it. (The raw `intent` argument is clamped to [0,1] so the divergence/grounding claims
hold regardless of a mis-scaled caller.)

DIMENSION NOTE: G_H = -log(tanh(d/2)) is the EXACT Green's function on H^2. The realm centers
(generate_realm_centers) populate only the 2-plane (dims 0,1), so H^2 governs the plane the
realms occupy. In a higher-dim embedding the radial Green's function behaves like d^{2-n} near 0
(still divergent, still away-pointing) -- a documented extension, not used here.

HONEST STATUS: the potential, force, grounding, and decision-flip are real and tested
(tests/test_same_pole_repulsor.py). NOT WIRED into the production runtime_gate (it has no realm
set and no bound egg); that is an explicit follow-up. lambda is the single free coupling constant,
fixed once by calibration (below), and lambda=0 reproduces the unmodified pipeline exactly.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

import numpy as np

from src.crypto.sacred_eggs import possesses_yolk

from .fourteen_layer_pipeline import (
    THETA_1,
    THETA_2,
    RiskAssessment,
    layer_5_hyperbolic_distance,
    layer_8_multi_well,
    layer_12_harmonic_scaling,
    layer_13_decision,
)

# Mirrors the local realm_weights in layer_13_decision; gate_center() recomputes argmax so a
# re-tune of these weights moves the gate instead of trusting a hardcoded index.
REALM_WEIGHTS = (1.0, 1.2, 0.8, 1.5, 1.1)

_GREEN_T1 = -math.log(math.tanh(THETA_1 / 2.0))  # G_H(THETA_1)
_A_AT_T1 = max(0.0, min(1.0, 1.0 - THETA_1 / THETA_2))  # approach ramp at d_H = THETA_1
# Single free coupling constant. Calibrated once so an unauthorized seeker at d_H = THETA_1 from
# the gate (intent g*a = 1*_A_AT_T1) is pushed just past THETA_2 into DENY: a tuned scale, not a
# derived constant. lambda=0 turns the repulsor off (provably reproduces the base pipeline).
LAMBDA_DEFAULT = (THETA_2 - THETA_1) / (_A_AT_T1 * _GREEN_T1)

_MAX_D = 50.0  # past this d_H, sinh(d) is astronomically large -> force is numerically zero


def _clamp01(x: float) -> float:
    return min(max(float(x), 0.0), 1.0)


def _as_vec(u) -> np.ndarray:
    return np.asarray(u, dtype=np.float64)


def gate_center(realm_centers: Sequence, realm_weights: Sequence[float] = REALM_WEIGHTS) -> Tuple[np.ndarray, int]:
    """Resolve the gated CORE = the most system-governing realm (max L13 weight).

    Returns (mu_gate, gate_idx) with gate_idx = argmax(realm_weights); never hardcoded, so a
    re-tune of the weights honors the new maximum.
    """
    idx = int(np.argmax(np.asarray(realm_weights, dtype=np.float64)))
    return _as_vec(realm_centers[idx]), idx


def green_potential(d: float) -> float:
    """Hyperbolic Green's function G_H(d) = -log(tanh(d/2)). +inf at d=0, ->0+ as d->inf."""
    if d <= 0.0:
        return float("inf")
    return -math.log(math.tanh(d / 2.0))


def grad_d_H(u, v) -> np.ndarray:
    """Exact chart gradient of layer_5_hyperbolic_distance(u, v) w.r.t. u.

    With A=1-||u||^2, B=1-||v||^2, diff=u-v, d2=||diff||^2, z=1+2*d2/(A*B):
        grad_u d_H = (1/sqrt(z^2-1)) * (2/B) * (2*A*diff + 2*d2*u) / A^2
    Returns the zero vector when z <= 1 (u == v): the distance has a stationary cusp there.
    """
    u = _as_vec(u)
    v = _as_vec(v)
    A = max(1.0 - float(u @ u), 1e-12)
    B = max(1.0 - float(v @ v), 1e-12)
    diff = u - v
    d2 = float(diff @ diff)
    z = 1.0 + 2.0 * d2 / (A * B)
    if z <= 1.0:
        return np.zeros_like(u)
    return (1.0 / math.sqrt(z * z - 1.0)) * (2.0 / B) * (2.0 * A * diff + 2.0 * d2 * u) / (A * A)


def repulsor_potential(u, mu_gate, intent: float, lambda_: float = LAMBDA_DEFAULT) -> float:
    """Phi(u; I) = lambda_ * I * G_H(d_H(u, gate)). Exactly 0 when intent<=0 or lambda_==0.

    Diverges (+inf) at contact (u == gate) -- a genuine hyperbolic-electrostatic wall, no eps cap.
    `intent` is clamped to [0,1] so the divergence/grounding claims hold for any caller.
    """
    intent = _clamp01(intent)
    if intent == 0.0 or lambda_ == 0.0:
        return 0.0
    d = layer_5_hyperbolic_distance(_as_vec(u), _as_vec(mu_gate))
    return float(lambda_ * intent * green_potential(d))


def repulsor_force(u, mu_gate, intent: float, lambda_: float = LAMBDA_DEFAULT) -> np.ndarray:
    """F = (lambda_ * I / sinh(d_H)) * grad_u d_H. Zero when intent<=0, lambda_==0, or u==gate.

    Points strictly away from the gate everywhere u != gate (verified). Uses the analytic
    gradient -- no finite-difference cusp artifact near contact.
    """
    u = _as_vec(u)
    intent = _clamp01(intent)
    if intent == 0.0 or lambda_ == 0.0:
        return np.zeros_like(u)
    d = layer_5_hyperbolic_distance(u, _as_vec(mu_gate))
    if d <= 0.0 or d > _MAX_D:
        # u == gate: stationary peak -> zero force. d huge: sinh(d) overflows; force is ~0.
        return np.zeros_like(u)
    return (lambda_ * intent / math.sinh(d)) * grad_d_H(u, mu_gate)


def effective_distance(d_star: float, u, mu_gate, intent: float, lambda_: float = LAMBDA_DEFAULT) -> float:
    """d_eff = d_star + Phi(u; I). >= d_star always; == d_star exactly when I=0 or lambda_=0.

    Heuristic risk inflation (d_star is to the *nearest* realm, Phi is from the *gate* realm);
    feed straight into layer_12_harmonic_scaling / layer_13_decision.
    """
    return float(d_star + repulsor_potential(u, mu_gate, intent, lambda_))


def intent_from_egg(presented_secret: bytes, egg, u, mu_gate, theta_2: float = THETA_2) -> float:
    """Grounded intent I = g * a in [0,1] -- the caller never sets `intent` directly.

    g = 0.0 for the yolk-holder (possesses_yolk, the shared ring gate) else 1.0;
    a = clip(1 - d_H(u, gate) / theta_2, 0, 1) ramps with an unauthorized approach.
    g=0 forces I=0 at every u (algebraic transparency for the authorized).
    """
    g = 0.0 if possesses_yolk(presented_secret, egg.get_shell(), egg.context) else 1.0
    d = layer_5_hyperbolic_distance(_as_vec(u), _as_vec(mu_gate))
    a = _clamp01(1.0 - d / theta_2)
    return float(g * a)


# --------------------------------------------------------------------- higher-level composition
def effective_realm_distance(
    u, realm_centers: Sequence, gate_idx: int, intent: float, lambda_: float = LAMBDA_DEFAULT
) -> Tuple[float, int]:
    """Real L8 d* inflated by the gate repulsion. Returns (d_eff, realm_idx of nearest well)."""
    d_star, realm_idx = layer_8_multi_well(_as_vec(u), realm_centers)
    mu_gate = _as_vec(realm_centers[gate_idx])
    return effective_distance(d_star, u, mu_gate, intent, lambda_), int(realm_idx)


def effective_safety(
    u,
    realm_centers: Sequence,
    gate_idx: int,
    intent: float,
    phase_deviation: float = 0.0,
    lambda_: float = LAMBDA_DEFAULT,
) -> float:
    """Real L12 safety H over the repulsion-inflated distance: H(d_eff, pd) in (0, 1]."""
    d_eff, _ = effective_realm_distance(u, realm_centers, gate_idx, intent, lambda_)
    return float(layer_12_harmonic_scaling(d_eff, phase_deviation))


def governed_decision(
    u,
    realm_centers: Sequence,
    gate_idx: int,
    intent: float,
    coherence: float = 1.0,
    phase_deviation: float = 0.0,
    lambda_: float = LAMBDA_DEFAULT,
) -> RiskAssessment:
    """Full L8->L12->L13 decision with the repulsor in the loop (intruder near gate -> DENY)."""
    d_eff, realm_idx = effective_realm_distance(u, realm_centers, gate_idx, intent, lambda_)
    h_d = layer_12_harmonic_scaling(d_eff, phase_deviation)
    return layer_13_decision(d_eff, h_d, coherence, realm_idx)


def force_field(points: Sequence, mu_gate, intent: float, lambda_: float = LAMBDA_DEFAULT) -> List[np.ndarray]:
    """Convenience: the repulsion force at each of many points (e.g. for quiver rendering)."""
    return [repulsor_force(p, mu_gate, intent, lambda_) for p in points]
