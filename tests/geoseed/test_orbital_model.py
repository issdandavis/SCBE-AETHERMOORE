"""
Tests for GeoSeed Hyperbolic Orbital Model.

Core invariants under test:
  1. CA tongue sits at Poincaré r = 1/φ (exact to float precision)
  2. All inter-shell geodesic gaps are equal (= ln(φ) / 2 per step... wait, = ln(φ))
  3. All adjacent phi-ratios equal φ
  4. Laplace-Beltrami eigenvalues follow -(l+1)²
  5. Magnetic sub-state counts follow 2l+1
  6. Total m-states = 36 across 6 tongues
  7. Sacred Egg nodes: exactly 21 per shell, all inside Poincaré ball (|r|<1)
  8. Shell radii strictly increasing
  9. KO (n=0) at the ball centre (r=0)
 10. Geodesic distance is uniform across all 5 adjacent pairs

These tests are model-independent: they verify the geometric/mathematical
structure of the GeoSeed orbital mapping regardless of how the wavefunction
density is computed (stdlib or scipy).
"""

import math
import pytest

PHI = (1.0 + math.sqrt(5.0)) / 2.0
LN_PHI = math.log(PHI)


# ── Import under test ─────────────────────────────────────────────────────────


def _import():
    """Import orbital_model regardless of scipy availability."""
    try:
        from src.geoseed.orbital_model import (
            build_geoseed_orbitals,
            orbital_summary,
            phi_to_poincare_r,
            hyperbolic_distance,
            laplace_beltrami_eigenvalue,
            sacred_egg_nodes,
            TONGUES,
            PHI as MODEL_PHI,
        )

        return {
            "build": build_geoseed_orbitals,
            "summary": orbital_summary,
            "phi_to_r": phi_to_poincare_r,
            "hyp_dist": hyperbolic_distance,
            "lb_eigen": laplace_beltrami_eigenvalue,
            "egg_nodes": sacred_egg_nodes,
            "tongues": TONGUES,
            "phi": MODEL_PHI,
        }
    except ImportError as e:
        pytest.skip(f"orbital_model import failed: {e}")


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def mod():
    return _import()


@pytest.fixture(scope="module")
def orbitals(mod):
    return mod["build"]()


@pytest.fixture(scope="module")
def summary(mod):
    return mod["summary"]()


# ── 1. Golden ratio checkpoint ────────────────────────────────────────────────


def test_ca_tongue_at_one_over_phi(orbitals):
    """CA (Cassisivadan, l=3) must sit exactly at r = 1/φ in the Poincaré ball."""
    ca = orbitals[3]
    assert ca.abbr == "CA", f"Expected CA at index 3, got {ca.abbr}"
    assert ca.l == 3
    assert abs(ca.poincare_r - 1.0 / PHI) < 1e-9, f"CA poincare_r={ca.poincare_r} ≠ 1/φ={1/PHI}"


def test_summary_golden_checkpoint(summary):
    assert summary["golden_ratio_checkpoint"]["exact"] is True


def test_phi_value_matches(mod):
    assert abs(mod["phi"] - PHI) < 1e-12


# ── 2. Uniform inter-shell geodesic gap ───────────────────────────────────────


def test_inter_shell_gaps_are_uniform(summary):
    """All 5 adjacent-shell geodesic distances must be identical."""
    gaps = summary["inter_shell_gaps"]
    assert len(gaps) == 5
    distances = [g["geodesic_distance"] for g in gaps]
    first = distances[0]
    for i, d in enumerate(distances):
        assert abs(d - first) < 1e-9, f"Gap {i} distance {d} ≠ gap 0 distance {first} — uniform spacing broken"


def test_inter_shell_gap_equals_ln_phi(summary):
    """Each geodesic step = ln(φ) (the hyperbolic step size for tanh(n·ln(φ)/2))."""
    gaps = summary["inter_shell_gaps"]
    step = gaps[0]["geodesic_distance"]
    assert abs(step - LN_PHI) < 1e-6, f"Gap {step} ≠ ln(φ)={LN_PHI:.6f}"


def test_inter_shell_phi_ratios_all_equal_phi(summary):
    """Adjacent shell phi-weight ratios must all equal φ."""
    for g in summary["inter_shell_gaps"]:
        assert abs(g["phi_ratio"] - PHI) < 1e-6, f"{g['from']}→{g['to']} phi_ratio={g['phi_ratio']} ≠ φ={PHI}"


# ── 3. Laplace-Beltrami eigenvalues ──────────────────────────────────────────


@pytest.mark.parametrize(
    "l,expected",
    [
        (0, -1.0),
        (1, -4.0),
        (2, -9.0),
        (3, -16.0),
        (4, -25.0),
        (5, -36.0),
    ],
)
def test_lb_eigenvalue(mod, l, expected):
    """LB eigenvalue on H³ = -(l+1)²."""
    assert mod["lb_eigen"](l) == expected


def test_orbital_lb_eigenvalues(orbitals):
    for o in orbitals:
        expected = -float((o.l + 1) ** 2)
        assert o.lb_eigenvalue == expected, f"{o.abbr} LB eigenvalue {o.lb_eigenvalue} ≠ {expected}"


# ── 4. Magnetic sub-state counts ─────────────────────────────────────────────


def test_m_states_per_orbital(orbitals):
    """Each orbital must have 2l+1 magnetic sub-states."""
    for o in orbitals:
        expected = 2 * o.l + 1
        assert o.m_states == expected, f"{o.abbr} m_states={o.m_states} ≠ 2l+1={expected}"


def test_total_m_states_equals_36(summary):
    """1+3+5+7+9+11 = 36 total magnetic sub-states."""
    assert summary["total_m_states"] == 36


def test_m_states_sequence(orbitals):
    """m-states must be 1, 3, 5, 7, 9, 11."""
    assert [o.m_states for o in orbitals] == [1, 3, 5, 7, 9, 11]


# ── 5. Tongue ordering and radial geometry ────────────────────────────────────


def test_tongues_in_phi_order(orbitals):
    """Tongues must be ordered KO→AV→RU→CA→UM→DR."""
    abbrs = [o.abbr for o in orbitals]
    assert abbrs == ["KO", "AV", "RU", "CA", "UM", "DR"]


def test_ko_at_centre(orbitals):
    """KO (n=0) must be at the ball centre r=0."""
    ko = orbitals[0]
    assert ko.poincare_r == 0.0
    assert ko.hyperbolic_rho == 0.0


def test_poincare_r_strictly_increasing(orbitals):
    """Shell radii must increase strictly outward."""
    rs = [o.poincare_r for o in orbitals]
    for i in range(1, len(rs)):
        assert rs[i] > rs[i - 1], f"Shell {i} r={rs[i]} not > shell {i-1} r={rs[i-1]}"


def test_all_shells_inside_poincare_ball(orbitals):
    """All shells must sit strictly inside the unit ball (r < 1)."""
    for o in orbitals:
        assert o.poincare_r < 1.0, f"{o.abbr} poincare_r={o.poincare_r} ≥ 1"


def test_dr_outermost_shell(orbitals):
    """DR (Draumric) must be the outermost shell."""
    rs = [o.poincare_r for o in orbitals]
    assert rs[-1] == max(rs)


# ── 6. Sacred Egg nodes ───────────────────────────────────────────────────────


def test_egg_node_count_per_shell(orbitals):
    """Each shell must have exactly 21 Sacred Egg nodes."""
    for o in orbitals:
        assert len(o.egg_nodes) == 21, f"{o.abbr} has {len(o.egg_nodes)} egg nodes, expected 21"


def test_egg_nodes_inside_poincare_ball(orbitals):
    """All egg nodes must lie inside the Poincaré ball (Euclidean |r| < 1)."""
    for o in orbitals:
        for x, y, z in o.egg_nodes:
            r = math.sqrt(x**2 + y**2 + z**2)
            assert r < 1.0 + 1e-9, f"{o.abbr} egg node at r={r:.6f} outside unit ball"


def test_egg_nodes_at_correct_shell_radius(orbitals):
    """Egg nodes must lie on their shell's Poincaré sphere (r ≈ poincare_r)."""
    for o in orbitals:
        if o.poincare_r == 0.0:
            continue  # KO is at centre — all eggs at origin
        for x, y, z in o.egg_nodes:
            r = math.sqrt(x**2 + y**2 + z**2)
            assert abs(r - o.poincare_r) < 1e-9, f"{o.abbr} egg node r={r:.9f} ≠ shell r={o.poincare_r:.9f}"


def test_ko_eggs_at_origin(orbitals):
    """KO eggs must all be at the origin."""
    ko = orbitals[0]
    for x, y, z in ko.egg_nodes:
        assert x == 0.0 and y == 0.0 and z == 0.0


# ── 7. Hyperbolic distance helper ─────────────────────────────────────────────


def test_hyperbolic_distance_zero_to_zero(mod):
    assert mod["hyp_dist"](0.0, 0.0) == 0.0


def test_hyperbolic_distance_symmetric(mod):
    d1 = mod["hyp_dist"](0.2, 0.6)
    d2 = mod["hyp_dist"](0.6, 0.2)
    assert abs(d1 - d2) < 1e-12


def test_hyperbolic_distance_grows_near_boundary(mod):
    """Points near the boundary are farther apart than points near the centre."""
    d_near = mod["hyp_dist"](0.1, 0.2)
    d_far = mod["hyp_dist"](0.8, 0.9)
    assert d_far > d_near


# ── 8. phi_to_poincare_r mapping ──────────────────────────────────────────────


@pytest.mark.parametrize("n", [0, 1, 2, 3, 4, 5])
def test_phi_to_poincare_r_in_unit_interval(mod, n):
    r = mod["phi_to_r"](n)
    assert 0.0 <= r < 1.0, f"phi_to_poincare_r({n}) = {r} outside [0,1)"


def test_phi_to_poincare_r_n0_is_zero(mod):
    assert mod["phi_to_r"](0) == 0.0


def test_phi_to_poincare_r_n3_is_one_over_phi(mod):
    r = mod["phi_to_r"](3)
    assert abs(r - 1.0 / PHI) < 1e-9


# ── 9. Schema version ─────────────────────────────────────────────────────────


def test_summary_schema_version(summary):
    assert summary["schema_version"] == "geoseed_orbital_v1"


def test_summary_manifold(summary):
    assert "H3" in summary["manifold"] or "Poincare" in summary["manifold"]
