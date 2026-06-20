"""Same-pole repulsor — proofs of the invariants, not vibes.

Every test pins a property the prototype only *claimed*: exact+global transparency, GENUINE
divergence at the gate (no epsilon cap), the analytic force matching numerical differentiation of
the real Layer-5 distance, force pointing away (hundreds of points), the real ALLOW->DENY decision
flip through live L12/L13, intent grounded in the hardened Sacred Eggs ring gate (cross-checked
against live ring_descent and proven non-destructive), isometry-invariance that catches Euclidean
leakage, gate-by-argmax, intent clamping, and lambda=0 = off.

@layer Layer 5, Layer 8, Layer 12, Layer 13
@component Same-Pole Repulsor Tests
"""

import math
import secrets

import numpy as np
import pytest

from src.symphonic_cipher.scbe_aethermoore.layers.fourteen_layer_pipeline import (
    generate_realm_centers,
    layer_5_hyperbolic_distance,
    layer_8_multi_well,
    layer_12_harmonic_scaling,
    mobius_addition,
)
from src.symphonic_cipher.scbe_aethermoore.layers.same_pole_repulsor import (
    LAMBDA_DEFAULT,
    effective_realm_distance,
    gate_center,
    governed_decision,
    grad_d_H,
    green_potential,
    intent_from_egg,
    repulsor_force,
    repulsor_potential,
)


@pytest.fixture
def centers():
    return generate_realm_centers(2, 5)


@pytest.fixture
def gate(centers):
    mu, _ = gate_center(centers)
    return mu


@pytest.fixture
def gate_idx(centers):
    _, idx = gate_center(centers)
    return idx


def _inside(u) -> bool:
    return float(np.dot(u, u)) < 0.97


# --------------------------------------------------------------------- transparency (exact, global)
def test_transparency_is_exact_and_global(centers, gate, gate_idx):
    rng = np.random.default_rng(0)
    checked = 0
    for _ in range(120):
        u = rng.uniform(-0.92, 0.92, size=2)
        if not _inside(u):
            continue
        checked += 1
        assert repulsor_potential(u, gate, 0.0) == 0.0
        assert np.array_equal(repulsor_force(u, gate, 0.0), np.zeros(2))
        d_star, _ = layer_8_multi_well(u, centers)
        d_eff, _ = effective_realm_distance(u, centers, gate_idx, 0.0)
        assert d_eff == d_star  # exact
        assert layer_12_harmonic_scaling(d_eff, 0.0) == layer_12_harmonic_scaling(d_star, 0.0)
    assert checked > 40


def test_lambda_zero_is_off(centers, gate, gate_idx):
    rng = np.random.default_rng(1)
    for _ in range(40):
        u = rng.uniform(-0.9, 0.9, size=2)
        if not _inside(u):
            continue
        assert repulsor_potential(u, gate, 1.0, lambda_=0.0) == 0.0
        d_star, _ = layer_8_multi_well(u, centers)
        assert effective_realm_distance(u, centers, gate_idx, 1.0, lambda_=0.0)[0] == d_star


# --------------------------------------------------------------------- GENUINE divergence (no epsilon)
def test_divergence_at_contact_no_epsilon(gate):
    # G_H itself diverges.
    assert green_potential(1e-9) > 20.0
    assert math.isinf(green_potential(0.0))

    deltas = [1e-1, 1e-3, 1e-6, 1e-9]
    phis = [repulsor_potential(gate + np.array([dx, 0.0]), gate, 1.0) for dx in deltas]
    # strictly increasing as we approach the gate (delta shrinks)
    assert all(phis[i] < phis[i + 1] for i in range(len(phis) - 1))
    assert phis[-1] > 20.0  # unbounded, not a lambda/eps cap

    # Force magnitude blows up: a 1/(d+eps) prototype would cap; this must exceed 1e7.
    f = repulsor_force(gate + np.array([1e-8, 0.0]), gate, 1.0)
    assert np.linalg.norm(f) > 1e7


def test_force_zero_exactly_at_gate(gate):
    # At u == gate the radial potential is stationary -> no garbage finite-difference vector.
    assert np.array_equal(repulsor_force(gate, gate, 1.0), np.zeros(2))


# --------------------------------------------------------------------- force direction (hundreds of points)
def test_force_points_away_everywhere(centers):
    mu, _ = gate_center(centers)
    rng = np.random.default_rng(7)
    n = 0
    while n < 500:
        theta = rng.uniform(0, 2 * np.pi)
        r = rng.uniform(0.02, 0.30)  # Euclidean ring; keeps d_H modest and u inside
        u = mu + r * np.array([math.cos(theta), math.sin(theta)])
        if not _inside(u):
            continue
        n += 1
        f = repulsor_force(u, mu, 1.0)
        assert float(np.dot(f, u - mu)) > 0.0  # away from the gate, every single point


def test_force_is_prefactor_times_grad(gate):
    u = gate + np.array([0.13, 0.05])
    d = layer_5_hyperbolic_distance(u, gate)
    prefactor = LAMBDA_DEFAULT * 1.0 / math.sinh(d)
    assert prefactor > 0.0  # away-sign proven analytically, not by sampling luck
    expected = prefactor * grad_d_H(u, gate)
    assert np.allclose(repulsor_force(u, gate, 1.0), expected, atol=1e-9)


# --------------------------------------------------------------------- analytic gradient is correct
def test_grad_dH_matches_numerical():
    rng = np.random.default_rng(11)
    h = 1e-6
    max_err = 0.0
    checked = 0
    while checked < 300:
        u = rng.uniform(-0.85, 0.85, size=2)
        v = rng.uniform(-0.85, 0.85, size=2)
        if not (_inside(u) and _inside(v)):
            continue
        if np.linalg.norm(u - v) < 0.08:  # avoid the cusp where numerical itself is poor
            continue
        checked += 1
        g = grad_d_H(u, v)
        num = np.zeros(2)
        for i in range(2):
            up = u.copy()
            um = u.copy()
            up[i] += h
            um[i] -= h
            num[i] = (layer_5_hyperbolic_distance(up, v) - layer_5_hyperbolic_distance(um, v)) / (2 * h)
        max_err = max(max_err, float(np.linalg.norm(g - num)))
    assert max_err < 1e-5, f"analytic grad drifted: max_err={max_err}"


# --------------------------------------------------------------------- potential tracks d_H, not Euclidean
def test_potential_tracks_hyperbolic_not_euclidean(gate):
    """Two points with ~equal Euclidean distance to the gate but different ||u|| -> different d_H.

    A Euclidean implementation would give equal potential; the hyperbolic one must not.
    """
    base = gate / np.linalg.norm(gate)  # unit direction
    # Same Euclidean offset 0.15 from the gate, but one toward the boundary, one toward origin.
    u_out = gate + 0.15 * base
    u_in = gate - 0.15 * base
    eu_out = np.linalg.norm(u_out - gate)
    eu_in = np.linalg.norm(u_in - gate)
    assert abs(eu_out - eu_in) < 1e-12  # equal Euclidean distance to the gate
    d_out = layer_5_hyperbolic_distance(u_out, gate)
    d_in = layer_5_hyperbolic_distance(u_in, gate)
    assert abs(d_out - d_in) > 1e-3  # but different hyperbolic distance
    # potential must follow d_H ordering (nearer in d_H -> larger potential), not Euclidean.
    nearer, farther = (u_out, u_in) if d_out < d_in else (u_in, u_out)
    assert repulsor_potential(nearer, gate, 1.0) > repulsor_potential(farther, gate, 1.0)


# --------------------------------------------------------------------- monotone, linear, clamped intent
def test_monotone_and_linear_in_intent(gate):
    p = np.array([0.0, 0.0])
    v_full = repulsor_potential(p, gate, 1.0)
    assert repulsor_potential(p, gate, 0.0) == 0.0
    assert repulsor_potential(p, gate, 0.25) < repulsor_potential(p, gate, 0.5) < v_full
    assert repulsor_potential(p, gate, 0.5) == pytest.approx(0.5 * v_full)


def test_intent_is_clamped(gate):
    p = gate + np.array([0.1, 0.0])
    assert repulsor_potential(p, gate, 5.0) == repulsor_potential(p, gate, 1.0)  # >1 clamps to 1
    assert repulsor_potential(p, gate, -3.0) == 0.0  # <0 clamps to 0


# --------------------------------------------------------------------- never weakens; bounded cost
def test_effective_distance_inflates_iff_unauthorized(centers, gate, gate_idx):
    rng = np.random.default_rng(3)
    checked = 0
    for _ in range(80):
        u = rng.uniform(-0.9, 0.9, size=2)
        if not _inside(u):
            continue
        checked += 1
        d_star, _ = layer_8_multi_well(u, centers)
        assert effective_realm_distance(u, centers, gate_idx, 1.0)[0] > d_star
        assert effective_realm_distance(u, centers, gate_idx, 0.0)[0] == d_star
    assert checked > 30


def test_cost_stays_in_unit_interval(centers, gate, gate_idx):
    rng = np.random.default_rng(4)
    for _ in range(60):
        u = rng.uniform(-0.9, 0.9, size=2)
        if not _inside(u):
            continue
        for intent in (0.0, 0.5, 1.0):
            d_eff, _ = effective_realm_distance(u, centers, gate_idx, intent)
            h = layer_12_harmonic_scaling(d_eff, 0.0)
            assert 0.0 < h <= 1.0


# --------------------------------------------------------------------- the payoff: real decision flip
def test_decision_flips_for_unauthorized_at_the_gate(centers, gate, gate_idx):
    u = gate * 0.92  # sitting in the gate well -> low base d*
    base_d, _ = layer_8_multi_well(u, centers)
    assert base_d < 0.5  # the gate looks perfectly safe by geometry alone
    assert governed_decision(u, centers, gate_idx, intent=0.0).decision == "ALLOW"
    assert governed_decision(u, centers, gate_idx, intent=1.0).decision == "DENY"


def test_end_to_end_grounded_decision(centers, gate, gate_idx):
    """Build a real egg; the yolk-holder is waved through, the intruder is denied."""
    from src.crypto.sacred_eggs import EggRing, SacredEgg

    yolk = secrets.token_bytes(32)
    egg = SacredEgg.create(context="core-gate", ring=EggRing.OUTER, yolk=yolk)
    u = gate * 0.94  # near the gate

    i_auth = intent_from_egg(yolk, egg, u, gate)
    i_intruder = intent_from_egg(secrets.token_bytes(32), egg, u, gate)
    assert i_auth == 0.0
    assert i_intruder > 0.0

    assert governed_decision(u, centers, gate_idx, i_auth).decision == "ALLOW"
    assert governed_decision(u, centers, gate_idx, i_intruder).decision == "DENY"


# --------------------------------------------------------------------- intent grounded in the real ring gate
def test_intent_zero_everywhere_for_the_yolk_holder(centers, gate):
    from src.crypto.sacred_eggs import EggRing, SacredEgg

    yolk = secrets.token_bytes(32)
    egg = SacredEgg.create(context="vault", ring=EggRing.OUTER, yolk=yolk)
    rng = np.random.default_rng(9)
    for _ in range(50):
        u = rng.uniform(-0.9, 0.9, size=2)
        if not _inside(u):
            continue
        assert intent_from_egg(yolk, egg, u, gate) == 0.0  # g=0 forces I=0 at every u


def test_intent_grounded_and_agrees_with_live_ring_descent(gate):
    from src.crypto.sacred_eggs import EggRing, SacredEgg, SacredRituals

    yolk = secrets.token_bytes(32)
    egg = SacredEgg.create(context="vault", ring=EggRing.OUTER, yolk=yolk)
    u_near = gate * 0.9

    # one-byte flip of the yolk is rejected (compare_digest sensitivity) -> intent > 0
    bad = bytearray(yolk)
    bad[0] ^= 0x01
    assert intent_from_egg(bytes(bad), egg, u_near, gate) > 0.0
    assert intent_from_egg(yolk, egg, u_near, gate) == 0.0

    # cross-bind: the SAME secret that makes the REAL ring_descent succeed yields intent 0;
    # a wrong secret that triggers the REAL fail-closed denial yields intent > 0.
    assert SacredRituals.ring_descent(egg, EggRing.INNER, yolk) is not None  # opened
    egg2 = SacredEgg.create(context="vault", ring=EggRing.OUTER, yolk=secrets.token_bytes(32))
    wrong = secrets.token_bytes(32)
    assert intent_from_egg(wrong, egg2, u_near, gate) > 0.0
    with pytest.raises(PermissionError):
        SacredRituals.ring_descent(egg2, EggRing.INNER, wrong)


def test_possesses_yolk_is_nondestructive():
    from src.crypto.sacred_eggs import EggRing, SacredEgg, possesses_yolk

    yolk = secrets.token_bytes(32)
    egg = SacredEgg.create(context="vault", ring=EggRing.OUTER, yolk=yolk)
    shell_before, ring_before = egg.shell_hash, egg.ring
    assert possesses_yolk(secrets.token_bytes(32), egg.get_shell(), egg.context) is False
    assert egg.shell_hash == shell_before  # no fail_to_noise, no mutation
    assert egg.ring == ring_before
    assert possesses_yolk(yolk, egg.get_shell(), egg.context) is True


# --------------------------------------------------------------------- gate is argmax; isometry-invariant
def test_gate_idx_is_argmax_not_hardcoded(centers):
    assert gate_center(centers)[1] == 3  # default weights -> realm 3 (weight 1.5)
    retuned = (1.0, 9.0, 0.8, 1.5, 1.1)  # now realm 1 is the most-governing
    assert gate_center(centers, retuned)[1] == 1
    assert np.allclose(gate_center(centers, retuned)[0], np.asarray(centers[1], dtype=float))


def test_isometry_invariance_catches_euclidean_leakage(gate):
    """Mobius translation preserves d_H but NOT Euclidean distance: the potential must be invariant."""
    a = np.array([0.21, -0.17])  # a nonzero gyro-translation
    u = gate + np.array([0.12, 0.04])

    tu = mobius_addition(a, u)
    tg = mobius_addition(a, gate)
    # sanity: it really changed the Euclidean picture but preserved the hyperbolic distance
    assert abs(np.linalg.norm(tu - tg) - np.linalg.norm(u - gate)) > 1e-3
    assert abs(layer_5_hyperbolic_distance(tu, tg) - layer_5_hyperbolic_distance(u, gate)) < 1e-9
    # the potential depends only on d_H, so it is unchanged:
    assert repulsor_potential(tu, tg, 1.0) == pytest.approx(repulsor_potential(u, gate, 1.0), abs=1e-9)
