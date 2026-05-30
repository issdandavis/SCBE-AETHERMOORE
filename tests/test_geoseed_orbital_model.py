from __future__ import annotations

import math

import pytest

from src.geoseed.orbital_model import (
    PHI,
    build_geoseed_orbitals,
    hyperbolic_distance,
    inter_shell_geodesic,
    orbital_summary,
    phi_to_poincare_r,
)
from scripts.research.render_geoseed_orbitals import build_html


def test_ca_shell_sits_at_inverse_phi_checkpoint() -> None:
    ca_radius = phi_to_poincare_r(3)
    assert ca_radius == pytest.approx(1.0 / PHI, abs=1e-12)


def test_adjacent_shells_have_uniform_hyperbolic_gap() -> None:
    orbitals = build_geoseed_orbitals()
    expected = math.log(PHI)
    distances = [
        hyperbolic_distance(left.poincare_r, right.poincare_r)
        for left, right in zip(orbitals, orbitals[1:])
    ]
    assert distances == pytest.approx([expected] * 5, abs=1e-12)


def test_orbital_state_ladder_matches_odd_sequence() -> None:
    orbitals = build_geoseed_orbitals()
    assert [orbital.orbital_type for orbital in orbitals] == ["s", "p", "d", "f", "g", "h"]
    assert [orbital.m_states for orbital in orbitals] == [1, 3, 5, 7, 9, 11]
    assert sum(orbital.m_states for orbital in orbitals) == 36


def test_sacred_egg_nodes_stay_inside_poincare_ball() -> None:
    for orbital in build_geoseed_orbitals():
        assert len(orbital.egg_nodes) == 21
        for x, y, z in orbital.egg_nodes:
            assert math.sqrt(x * x + y * y + z * z) < 1.0 or orbital.phi_index == 0


def test_summary_is_explicit_about_scope_and_gap() -> None:
    summary = orbital_summary(include_profiles=True)
    assert summary["schema_version"] == "geoseed_orbital_v1"
    assert "not a physical atomic-orbital claim" in summary["model_scope"]
    assert summary["golden_ratio_checkpoint"]["exact_within_1e_12"] is True
    assert summary["inter_shell_gaps"] == inter_shell_geodesic()
    assert set(summary["density_profiles"]) == {"KO", "AV", "RU", "CA", "UM", "DR"}


def test_visual_report_contains_core_invariants() -> None:
    html = build_html()
    assert "GeoSeed Orbital Model" in html
    assert "0.481211825" in html
    assert "r=0.618033989=1/phi" in html
    assert "Total m-states" in html
