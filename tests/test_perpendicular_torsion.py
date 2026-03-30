"""Test: Perpendicular Inverse Torsion Detection
=================================================

When two agents pull in inverse directions on perpendicular axes,
the centroid looks normal but bridge energy explodes. This tests
whether the existing Saturn Ring math catches it.

The attack: Agent A pushes KO high, Agent B pushes UM high (inverse
intent, perpendicular axis). Average = neutral. But the TORSION
between KO and UM is massive.

Key insight: classifiers see "neutral." The geometry sees a hurricane.
"""

import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.test_holographic_cube_saturn_ring import (
    lyapunov_V,
    barrier_h,
    port_energy,
    harmonic_cost,
    encode_cube,
    validate_cube,
    verify_cube_signature,
    is_self_healing,
    lyapunov_dVdt,
    TONGUES,
    TONGUE_WEIGHTS,
    PHI,
    PI,
)


class TestPerpendicularTorsion:
    """Two inverse agents on perpendicular axes: centroid neutral, bridges explode."""

    def _make_neutral_centroid(self):
        """Centroid that looks perfectly normal."""
        return [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]

    def _make_torsion_coords(self):
        """Coords that AVERAGE to centroid but have massive internal torsion.

        Agent A pushed KO to 0.9 and UM to 0.1 (attack intent + hide security)
        Agent B pushed KO to 0.1 and UM to 0.9 (inverse)
        Average: KO=0.5, UM=0.5 (looks neutral!)
        But the INDIVIDUAL readings show extreme deviation.
        """
        return [0.9, 0.5, 0.5, 0.5, 0.1, 0.5]  # KO high, UM low (Agent A won)

    def _make_benign_coords(self):
        """Genuinely benign coords near centroid."""
        return [0.52, 0.48, 0.51, 0.49, 0.50, 0.51]

    def test_centroid_looks_similar(self):
        """The torsion coords have same mean as benign -- a classifier would miss this."""
        torsion = self._make_torsion_coords()
        benign = self._make_benign_coords()
        assert abs(np.mean(torsion) - np.mean(benign)) < 0.05, \
            "Centroid means should be similar (this is why classifiers fail)"

    def test_lyapunov_catches_torsion(self):
        """V(x) should be much higher for torsion despite similar centroid."""
        centroid = self._make_neutral_centroid()
        torsion = self._make_torsion_coords()
        benign = self._make_benign_coords()

        V_torsion = lyapunov_V(torsion, centroid)
        V_benign = lyapunov_V(benign, centroid)

        assert V_torsion > V_benign * 10, \
            f"Torsion V ({V_torsion:.4f}) should be >>10x benign V ({V_benign:.4f})"

    def test_bridge_energy_explodes(self):
        """Port-Hamiltonian bridges should carry massive energy under torsion."""
        centroid = self._make_neutral_centroid()
        torsion = self._make_torsion_coords()
        benign = self._make_benign_coords()

        bridges_torsion = port_energy(torsion, centroid)
        bridges_benign = port_energy(benign, centroid)

        E_torsion = sum(bridges_torsion.values())
        E_benign = sum(bridges_benign.values())

        assert E_torsion > E_benign * 50, \
            f"Torsion E ({E_torsion:.4f}) should be >>50x benign E ({E_benign:.6f})"

    def test_ko_um_bridge_is_strongest(self):
        """The KO-UM bridge should carry the most energy (perpendicular axes)."""
        centroid = self._make_neutral_centroid()
        torsion = self._make_torsion_coords()
        bridges = port_energy(torsion, centroid)

        ko_um = bridges["KO-UM"]
        max_bridge = max(bridges.values())
        assert ko_um == max_bridge, \
            f"KO-UM bridge ({ko_um:.4f}) should be the strongest (max={max_bridge:.4f})"

    def test_cube_catches_torsion_attack(self):
        """A cube snapshot of the torsion state should NOT be ALLOW.

        Previously xfail because validate_cube didn't check V (Lyapunov).
        Now fixed: V > 0.5 triggers ESCALATE, catching torsion attacks where
        the barrier (h) is fine but Lyapunov deviation is extreme.
        """
        centroid = self._make_neutral_centroid()
        torsion = self._make_torsion_coords()
        cost = harmonic_cost(lyapunov_V(torsion, centroid), R=1.5)

        cube = encode_cube(torsion, centroid, cost=cost, spin_magnitude=4,
                           phase=0.5, trust_history=[0, -1, 0, -1, 0])
        decision = validate_cube(cube)

        assert decision != "ALLOW", \
            f"Torsion attack should not be ALLOW (got {decision})"

    def test_benign_cube_allows(self):
        """A genuinely benign state should be ALLOW."""
        centroid = self._make_neutral_centroid()
        benign = self._make_benign_coords()

        cube = encode_cube(benign, centroid, cost=3.0, spin_magnitude=0,
                           phase=0.5, trust_history=[1, 1, 1, 1, 1])
        decision = validate_cube(cube)
        assert decision == "ALLOW"

    def test_torsion_signature_valid(self):
        """Even though it's an attack, the cube signature should be internally valid."""
        centroid = self._make_neutral_centroid()
        torsion = self._make_torsion_coords()
        cost = harmonic_cost(lyapunov_V(torsion, centroid), R=1.5)

        cube = encode_cube(torsion, centroid, cost=cost, spin_magnitude=4,
                           phase=0.5, trust_history=[0, -1, 0, -1, 0])
        assert verify_cube_signature(cube), "Cube should be internally consistent"


class TestGyroscopicCrossProduct:
    """Cross-product of perpendicular spins creates torque on third axis."""

    def test_cross_product_generates_torque(self):
        """omega_1 x omega_2 should produce nonzero torque when perpendicular."""
        omega_1 = np.array([1.0, 0.0, 0.0])  # Spin on X
        omega_2 = np.array([0.0, -1.0, 0.0])  # Inverse spin on Y
        torque = np.cross(omega_1, omega_2)

        assert np.linalg.norm(torque) > 0, "Perpendicular spins should create torque"
        assert abs(torque[2]) > 0, "Torque should be on Z axis (perpendicular to both)"

    def test_parallel_spins_no_torque(self):
        """Same-axis spins produce zero cross product."""
        omega_1 = np.array([1.0, 0.0, 0.0])
        omega_2 = np.array([-1.0, 0.0, 0.0])  # Inverse but same axis
        torque = np.cross(omega_1, omega_2)
        assert np.linalg.norm(torque) == pytest.approx(0.0)

    def test_torque_magnitude_scales_with_spin(self):
        """Stronger spins should create stronger torque."""
        weak = np.cross(np.array([0.1, 0, 0]), np.array([0, 0.1, 0]))
        strong = np.cross(np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))
        assert np.linalg.norm(strong) > np.linalg.norm(weak) * 50


class TestNullSpaceDetection:
    """When inverse systems cancel at the centroid, the null-space should detect it."""

    def test_inverse_sum_to_zero(self):
        """Two inverse vectors sum to zero (the attacker's goal)."""
        agent_a = np.array([0.9, 0.5, 0.5, 0.5, 0.1, 0.5])
        agent_b = np.array([0.1, 0.5, 0.5, 0.5, 0.9, 0.5])
        average = (agent_a + agent_b) / 2
        centroid = np.array([0.5] * 6)

        # Average looks like centroid
        assert np.allclose(average, centroid, atol=0.01), \
            "Averaged inverse agents should look like centroid"

    def test_individual_deviation_is_extreme(self):
        """But each individual agent is far from centroid."""
        centroid = [0.5] * 6
        agent_a = [0.9, 0.5, 0.5, 0.5, 0.1, 0.5]

        V = lyapunov_V(agent_a, centroid)
        assert V > 1.0, f"Individual agent V ({V:.4f}) should be high"

    def test_variance_catches_coordinated_attack(self):
        """The variance across agents reveals the attack even when mean is neutral."""
        centroid = np.array([0.5] * 6)
        agent_a = np.array([0.9, 0.5, 0.5, 0.5, 0.1, 0.5])
        agent_b = np.array([0.1, 0.5, 0.5, 0.5, 0.9, 0.5])

        # Mean looks fine
        mean = (agent_a + agent_b) / 2
        mean_deviation = np.linalg.norm(mean - centroid)

        # But variance is huge
        variance = np.var(np.vstack([agent_a, agent_b]), axis=0)
        total_variance = np.sum(variance)

        assert mean_deviation < 0.01, "Mean should look safe"
        assert total_variance > 0.1, f"Variance ({total_variance:.4f}) should reveal the attack"
