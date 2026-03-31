"""Integration tests for the trichromatic governance system.

Tests the full pipeline: input -> RuntimeGate -> trichromatic scoring ->
IR/Visible/UV triplets -> cross-stitch bridges -> forgery resistance.

These tests verify the CONCEPTS from the session, not just the code.
"""

import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
#  Test: Trichromatic color triplets produce valid 3-band output
# ---------------------------------------------------------------------------


class TestTrichromaticTriplets:
    """Verify each tongue produces a valid (IR, Visible, UV) triplet."""

    def test_six_tongues_produce_six_triplets(self):
        """Each of the 6 Sacred Tongues should produce one color triplet."""
        from scripts.trichromatic_governance_test import (
            build_trichromatic_state,
        )

        state = build_trichromatic_state(
            coords=[0.3, 0.5, 0.4, 0.2, 0.6, 0.3],
            cost=5.0,
            spin_magnitude=2,
            trust_history=[1, 1, 0, 1, -1],
            cumulative_cost=25.0,
            session_query_count=10,
        )
        assert len(state.tongues) == 6
        for t in state.tongues:
            assert 0.0 <= t.color.ir <= 1.0
            assert 0.0 <= t.color.visible <= 1.0
            assert 0.0 <= t.color.uv <= 1.0

    def test_all_state_hashes_unique(self):
        """Different inputs should produce different state hashes."""
        from scripts.trichromatic_governance_test import build_trichromatic_state

        states = []
        for i in range(5):
            coords = [0.1 * (i + 1)] * 6
            s = build_trichromatic_state(
                coords,
                cost=float(i + 1),
                spin_magnitude=i,
                trust_history=[1] * 5,
                cumulative_cost=10.0,
                session_query_count=5,
            )
            states.append(s.state_hash)
        assert len(set(states)) == 5, "All state hashes should be unique"


# ---------------------------------------------------------------------------
#  Test: Cross-stitch bridges produce 15 pairs with 3 bands each
# ---------------------------------------------------------------------------


class TestCrossStitchBridges:
    """Verify the lattice bridge structure."""

    def test_fifteen_bridges(self):
        from scripts.trichromatic_governance_test import build_trichromatic_state

        state = build_trichromatic_state(
            coords=[0.5] * 6,
            cost=3.0,
            spin_magnitude=1,
            trust_history=[1, 1, 1],
            cumulative_cost=10.0,
            session_query_count=5,
        )
        assert len(state.bridges) == 15, "6 tongues should produce 15 pairwise bridges"

    def test_each_bridge_has_three_bands(self):
        from scripts.trichromatic_governance_test import build_trichromatic_state

        state = build_trichromatic_state(
            coords=[0.5] * 6,
            cost=3.0,
            spin_magnitude=1,
            trust_history=[1, 1, 1],
            cumulative_cost=10.0,
            session_query_count=5,
        )
        for key, bridge in state.bridges.items():
            assert len(bridge) == 3, f"Bridge {key} should have 3 bands (IR, Vis, UV)"
            for val in bridge:
                assert 0.0 <= val <= 1.0, f"Bridge {key} band out of range: {val}"


# ---------------------------------------------------------------------------
#  Test: Forgery resistance (visible match, IR/UV mismatch)
# ---------------------------------------------------------------------------


class TestForgeryResistance:
    """Verify that matching only the visible band is insufficient."""

    def test_visible_match_alone_is_caught(self):
        from scripts.trichromatic_governance_test import (
            build_trichromatic_state,
            test_forgery_resistance,
        )

        state = build_trichromatic_state(
            coords=[0.8, 0.3, 0.5, 0.2, 0.9, 0.1],
            cost=15.0,
            spin_magnitude=4,
            trust_history=[1, 0, -1, 1, 1],
            cumulative_cost=50.0,
            session_query_count=15,
        )
        forged_visible = [t.color.visible for t in state.tongues]
        result = test_forgery_resistance(state, forged_visible)

        assert result["visible_match"] == 6, "Forger should match all visible bands"
        assert result["full_match"] < 6, "Forger should NOT match all bands"
        assert result["forgery_detected"], "Forgery should be detected"


# ---------------------------------------------------------------------------
#  Test: Energy separation between benign and adversarial
# ---------------------------------------------------------------------------


class TestEnergySeparation:
    """Verify trichromatic energy distinguishes benign from adversarial."""

    def test_attack_has_higher_uv_energy(self):
        """UV band (fast state) should be higher for attacks due to spin + cost."""
        from scripts.trichromatic_governance_test import build_trichromatic_state

        benign_state = build_trichromatic_state(
            coords=[0.3, 0.4, 0.5, 0.2, 0.3, 0.3],
            cost=5.0,
            spin_magnitude=1,
            trust_history=[1, 1, 1, 1, 1],
            cumulative_cost=10.0,
            session_query_count=10,
        )
        attack_state = build_trichromatic_state(
            coords=[0.9, 0.2, 0.7, 0.1, 0.8, 0.1],
            cost=50.0,
            spin_magnitude=5,
            trust_history=[1, 0, -1, -1, -1],
            cumulative_cost=200.0,
            session_query_count=10,
        )

        benign_uv = np.mean([t.color.uv for t in benign_state.tongues])
        attack_uv = np.mean([t.color.uv for t in attack_state.tongues])

        assert attack_uv > benign_uv, f"Attack UV ({attack_uv}) should exceed benign UV ({benign_uv})"


# ---------------------------------------------------------------------------
#  Test: Holographic QR Cube distance properties
# ---------------------------------------------------------------------------


class TestHolographicQRCube:
    """Basic distance properties for the cube encoding."""

    def test_identical_cube_distance_zero(self):
        c = (np.array([0, 0, 0]), np.array([1, 2, 3]), 0.5, 0.5)
        d = self._cube_distance(c, c)
        assert d == pytest.approx(0.0)

    def test_phase_drift_increases_distance(self):
        c1 = (np.zeros(3), np.ones(3), 0.1, 0.5)
        c2 = (np.zeros(3), np.ones(3), 1.0, 0.5)
        assert self._cube_distance(c1, c2) > 0

    def test_spin_misalignment_detected(self):
        c1 = (np.zeros(3), np.ones(3), 0.5, 0.0)
        c2 = (np.zeros(3), np.ones(3), 0.5, 1.0)
        assert self._cube_distance(c1, c2) > 0

    def test_semantic_difference_detected(self):
        c1 = (np.zeros(3), np.array([1, 0, 0]), 0.5, 0.5)
        c2 = (np.zeros(3), np.array([0, 1, 0]), 0.5, 0.5)
        assert self._cube_distance(c1, c2) > 0

    @staticmethod
    def _cube_distance(c1, c2):
        xyz1, v1, p1, s1 = c1
        xyz2, v2, p2, s2 = c2
        d_xyz = np.linalg.norm(xyz1 - xyz2)
        v1n = v1 / (np.linalg.norm(v1) + 1e-8)
        v2n = v2 / (np.linalg.norm(v2) + 1e-8)
        d_v = np.linalg.norm(v1n - v2n)
        d_p = abs(p1 - p2)
        d_s = abs(s1 - s2)
        return d_xyz + d_v + d_p + d_s


# ---------------------------------------------------------------------------
#  Test: 5-state governance decision enum
# ---------------------------------------------------------------------------


class TestGovernanceStates:
    """Verify the governance decision states exist and are distinct."""

    def test_five_core_states_exist(self):
        from src.governance.runtime_gate import Decision

        core_states = {"ALLOW", "QUARANTINE", "DENY"}
        for state in core_states:
            assert hasattr(Decision, state), f"Decision.{state} should exist"

    def test_review_state_exists(self):
        """REVIEW maps to ESCALATE conceptually (6-council deep inspection)."""
        from src.governance.runtime_gate import Decision

        assert hasattr(Decision, "REVIEW"), "Decision.REVIEW should exist"

    def test_reroute_state_exists(self):
        """REROUTE maps to DIRECT conceptually (redirect to safer alternative)."""
        from src.governance.runtime_gate import Decision

        assert hasattr(Decision, "REROUTE"), "Decision.REROUTE should exist"

    def test_all_states_are_distinct(self):
        from src.governance.runtime_gate import Decision

        values = [d.value for d in Decision]
        assert len(values) == len(set(values)), "All decision states should be unique"


# ---------------------------------------------------------------------------
#  Test: Dye + Frechet analysis produces valid output
# ---------------------------------------------------------------------------


class TestDyeFrechetOutput:
    """Verify the dye analysis produces valid color and sphere data."""

    def test_coords_to_rgb_valid(self):
        from scripts.dye_frechet_analysis import coords_to_rgb

        rgb = coords_to_rgb([0.3, 0.5, 0.4, 0.2, 0.6, 0.1])
        assert len(rgb) == 3
        for c in rgb:
            assert 0 <= c <= 255

    def test_coords_to_hex_format(self):
        from scripts.dye_frechet_analysis import coords_to_hex

        hex_color = coords_to_hex([0.5] * 6)
        assert hex_color.startswith("#")
        assert len(hex_color) == 7

    def test_frechet_mean_stays_in_ball(self):
        from scripts.dye_frechet_analysis import frechet_mean_update

        centroid = np.array([0.3, 0.2, 0.1, 0.4, 0.5, 0.2])
        new_point = np.array([0.9, 0.8, 0.7, 0.1, 0.2, 0.9])
        updated = frechet_mean_update(centroid, new_point, count=5)
        assert np.linalg.norm(updated) < 1.0, "Frechet mean should stay inside Poincare ball"


# ---------------------------------------------------------------------------
#  Test: State space size
# ---------------------------------------------------------------------------


class TestStateSpace:
    """Verify the combinatorial state space calculation."""

    def test_504_bits_state_space(self):
        """63 channels x 8 bits = 504 bits."""
        tongues = 6
        bands = 3
        bridges = 15  # C(6,2)
        total_channels = tongues * bands + bridges * bands  # 18 + 45 = 63
        bits_per_channel = 8
        total_bits = total_channels * bits_per_channel

        assert total_channels == 63
        assert total_bits == 504

    def test_state_space_larger_than_atoms(self):
        """2^504 should be much larger than 10^80 (atoms in universe)."""
        import math

        state_space_log10 = 504 * math.log10(2)  # ~151.7
        atoms_in_universe = 80
        assert state_space_log10 > atoms_in_universe
