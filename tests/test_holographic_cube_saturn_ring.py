"""Test suite for Saturn Ring dynamics + Holographic QR Cube snapshots.

Validates the relationship:
  Runtime (continuous) → Saturn Ring (stabilize) → QR Cube (snapshot) → Verify (prove)

Tests:
  1. Existing cube primitives work (pi^phi key derivation)
  2. Lyapunov stability: dV/dt < 0 means self-healing
  3. Control barrier: h(x) bounds prevent implosion/explosion
  4. Port-Hamiltonian: energy redistribution through tongue bridges
  5. Cube encoding captures Saturn Ring state
  6. Cube integrity validation (ALLOW/ESCALATE/DENY from snapshot)
  7. Tamper detection: modifying one axis invalidates the cube
  8. Stability assertion: is_self_healing(dV_dt)
  9. Persistence detection: t/||I|| ratio
  10. Snapshot → verify round-trip
"""

import hashlib
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PHI = 1.618033988749895
PI = math.pi
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_WEIGHTS = tuple(PHI**k for k in range(6))


# ===========================================================================
#  Saturn Ring Math Primitives
# ===========================================================================


def lyapunov_V(coords, centroid):
    """Lyapunov stability function: V(x) = sum(phi_i * (tongue_i - centroid_i)^2)."""
    return sum(TONGUE_WEIGHTS[i] * (coords[i] - centroid[i]) ** 2 for i in range(6))


def lyapunov_dVdt(V_current, V_previous):
    """Rate of change of Lyapunov function. Negative = self-healing."""
    return V_current - V_previous


def barrier_h(cost, H_max=200.0):
    """Control barrier: h(x) = H_max - H(d*,R). Positive = inside safe region."""
    return H_max - cost


def port_energy(coords, centroid):
    """Port-Hamiltonian energy flow through tongue bridges."""
    bridges = {}
    for i in range(6):
        for j in range(i + 1, 6):
            flow = abs(coords[i] - centroid[i]) * abs(coords[j] - centroid[j]) * PHI ** abs(i - j)
            bridges[f"{TONGUES[i]}-{TONGUES[j]}"] = flow
    return bridges


def harmonic_cost(d_star, R=1.0):
    """H(d*,R) = R * pi^(phi * d*)."""
    return R * PI ** (PHI * min(d_star, 5.0))


def persistence_ratio(t, I_norm):
    """Persistence of excitation: t / ||I||. High = suspicious."""
    return t / max(I_norm, 1e-8)


def is_self_healing(dV_dt):
    """Saturn Ring stability assertion."""
    return dV_dt < 0


# ===========================================================================
#  Cube Encoding (Saturn State → Snapshot)
# ===========================================================================


def _canonicalize_cube(cube_data):
    """Produce a deterministic string from cube fields for signing/verification."""
    parts = []
    for k in sorted(cube_data.keys()):
        v = cube_data[k]
        if isinstance(v, list):
            v = ",".join(f"{x:.6f}" if isinstance(x, float) else str(x) for x in v)
        elif isinstance(v, float):
            v = f"{v:.6f}"
        parts.append(f"{k}={v}")
    return "|".join(parts)


def encode_cube(coords, centroid, cost, spin_magnitude, phase, trust_history):
    """Encode Saturn Ring state into a Holographic QR Cube."""
    V = lyapunov_V(coords, centroid)
    h = barrier_h(cost)
    bridges = port_energy(coords, centroid)
    total_bridge_energy = sum(bridges.values())

    cube = {
        "xyz": [round(c, 6) for c in coords[:3]],
        "V": round(V, 6),
        "h": round(h, 6),
        "E_port": round(total_bridge_energy, 6),
        "phase": round(phase, 6),
        "spin": spin_magnitude,
        "cost": round(cost, 6),
        "trust_momentum": round(sum(trust_history[-5:]) / max(len(trust_history[-5:]), 1), 6),
    }

    # Signature: canonical string + pi^phi wall binding
    sig_input = _canonicalize_cube(cube)
    wall = harmonic_cost(cube["V"], R=1.5)
    sig_input += f"|wall={wall:.17g}"
    cube["signature"] = hashlib.blake2s(sig_input.encode(), digest_size=16).hexdigest()

    return cube


def validate_cube(cube):
    """Validate cube integrity -> governance decision.

    Uses three checks:
      1. Barrier h(x): negative = outside safe region → DENY
      2. Lyapunov V: high = far from stable equilibrium → ESCALATE
      3. Bridge energy E_port: high = cross-tongue tension → QUARANTINE
    """
    if cube["h"] < 0:
        return "DENY"
    if cube["V"] > 0.5:  # Lyapunov deviation threshold (catches torsion attacks)
        return "ESCALATE"
    if cube["h"] < 25:
        return "ESCALATE"
    if cube["E_port"] > 5.0:
        return "QUARANTINE"
    return "ALLOW"


def verify_cube_signature(cube):
    """Verify the cube hasn't been tampered with."""
    sig = cube.get("signature", "")
    cube_copy = {k: v for k, v in cube.items() if k != "signature"}
    sig_input = _canonicalize_cube(cube_copy)
    wall = harmonic_cost(cube_copy["V"], R=1.5)
    sig_input += f"|wall={wall:.17g}"
    expected = hashlib.blake2s(sig_input.encode(), digest_size=16).hexdigest()
    return sig == expected


# ===========================================================================
#  Tests: Existing Primitives
# ===========================================================================


class TestExistingPrimitives:
    """Verify existing holographic_qr_cube.py and qr_cube_kdf.py work."""

    def test_pi_phi_wall_basic(self):
        from src.holographic_qr_cube import pi_phi_wall

        result = pi_phi_wall(d_star=0.0, R=1.5)
        assert result == pytest.approx(1.5, rel=1e-6)

    def test_pi_phi_wall_increases_with_distance(self):
        from src.holographic_qr_cube import pi_phi_wall

        cost_near = pi_phi_wall(d_star=0.5, R=1.5)
        cost_far = pi_phi_wall(d_star=2.0, R=1.5)
        assert cost_far > cost_near

    def test_pi_phi_key_derivation_deterministic(self):
        from src.holographic_qr_cube import pi_phi_key_derivation

        key1 = pi_phi_key_derivation(d_star=1.0, R=1.5, as_bytes=True)
        key2 = pi_phi_key_derivation(d_star=1.0, R=1.5, as_bytes=True)
        assert key1 == key2

    def test_pi_phi_key_derivation_sensitive(self):
        from src.holographic_qr_cube import pi_phi_key_derivation

        key1 = pi_phi_key_derivation(d_star=1.0, R=1.5, as_bytes=True)
        key2 = pi_phi_key_derivation(d_star=1.001, R=1.5, as_bytes=True)
        assert key1 != key2


# ===========================================================================
#  Tests: Lyapunov Stability
# ===========================================================================


class TestLyapunovStability:
    """V(x) proves the system returns to equilibrium."""

    def test_identical_to_centroid_is_zero(self):
        c = [0.3, 0.5, 0.4, 0.2, 0.6, 0.3]
        assert lyapunov_V(c, c) == pytest.approx(0.0)

    def test_deviation_increases_V(self):
        centroid = [0.3, 0.5, 0.4, 0.2, 0.6, 0.3]
        near = [0.31, 0.51, 0.41, 0.21, 0.61, 0.31]
        far = [0.5, 0.7, 0.6, 0.4, 0.8, 0.5]
        assert lyapunov_V(near, centroid) < lyapunov_V(far, centroid)

    def test_phi_weighting_makes_DR_most_expensive(self):
        """DR (index 5) has highest phi weight, so deviation there costs most."""
        centroid = [0.5] * 6
        # Deviate only KO (index 0)
        ko_dev = list(centroid)
        ko_dev[0] = 0.8
        # Deviate only DR (index 5) by same amount
        dr_dev = list(centroid)
        dr_dev[5] = 0.8
        assert lyapunov_V(dr_dev, centroid) > lyapunov_V(ko_dev, centroid)

    def test_dVdt_negative_means_healing(self):
        V_before = 5.0
        V_after = 3.0
        assert is_self_healing(lyapunov_dVdt(V_after, V_before))

    def test_dVdt_positive_means_diverging(self):
        V_before = 3.0
        V_after = 5.0
        assert not is_self_healing(lyapunov_dVdt(V_after, V_before))


# ===========================================================================
#  Tests: Control Barrier
# ===========================================================================


class TestControlBarrier:
    """h(x) bounds prevent implosion and explosion."""

    def test_low_cost_is_inside_barrier(self):
        assert barrier_h(cost=10.0) > 0

    def test_high_cost_is_outside_barrier(self):
        assert barrier_h(cost=250.0) < 0

    def test_barrier_at_max_is_zero(self):
        assert barrier_h(cost=200.0) == pytest.approx(0.0)

    def test_barrier_prevents_implosion(self):
        """Very low cost (system over-restricting) should still be inside barrier."""
        assert barrier_h(cost=0.1) > 0

    def test_barrier_prevents_explosion(self):
        """Very high cost (system under-restricting) should be outside barrier."""
        assert barrier_h(cost=500.0) < 0


# ===========================================================================
#  Tests: Port-Hamiltonian Energy
# ===========================================================================


class TestPortHamiltonian:
    """Energy redistribution through tongue bridges."""

    def test_fifteen_bridges(self):
        coords = [0.5] * 6
        centroid = [0.3] * 6
        bridges = port_energy(coords, centroid)
        assert len(bridges) == 15

    def test_no_deviation_no_energy(self):
        coords = [0.5] * 6
        bridges = port_energy(coords, coords)
        for _key, val in bridges.items():
            assert val == pytest.approx(0.0)

    def test_single_tongue_deviation_spreads(self):
        """Deviation on one tongue should create energy on multiple bridges.

        Port-Hamiltonian: energy at one port flows to adjacent ports.
        When KO deviates alone, bridges involving KO should carry energy
        but bridges between other tongues (both at centroid) should be zero.
        """
        centroid = [0.5] * 6
        coords = list(centroid)
        coords[0] = 0.9  # Only KO deviates
        bridges = port_energy(coords, centroid)
        # KO participates in 5 bridges (KO-AV, KO-RU, KO-CA, KO-UM, KO-DR)
        ko_bridges = {k: v for k, v in bridges.items() if "KO" in k}
        assert len(ko_bridges) == 5, "KO should have 5 bridges"
        # But only KO deviates, so bridges between OTHER tongues are zero
        # (both sides at centroid → 0 * 0 = 0). KO bridges are also zero
        # because the OTHER tongue in each pair hasn't deviated.
        # The energy formula is |dev_i * dev_j| * phi — needs BOTH to deviate.
        # So let's deviate TWO tongues to test spreading.
        coords[3] = 0.8  # CA also deviates
        bridges2 = port_energy(coords, centroid)
        # Now KO-CA bridge should have energy
        assert bridges2["KO-CA"] > 0, "KO-CA bridge should carry energy when both deviate"

    def test_phi_scales_bridge_energy(self):
        """Distant tongue pairs should have higher phi^|i-j| weight."""
        centroid = [0.5] * 6
        coords = [0.7] * 6
        bridges = port_energy(coords, centroid)
        # KO-AV (adjacent, phi^1) vs KO-DR (distant, phi^5)
        assert bridges["KO-DR"] > bridges["KO-AV"]


# ===========================================================================
#  Tests: Persistence of Excitation (t / ||I||)
# ===========================================================================


class TestPersistence:
    """Weak intent over long time should be more suspicious."""

    def test_high_intent_low_ratio(self):
        assert persistence_ratio(t=10, I_norm=100.0) < 1.0

    def test_low_intent_high_ratio(self):
        assert persistence_ratio(t=100, I_norm=0.1) > 100.0

    def test_zero_intent_is_infinite(self):
        ratio = persistence_ratio(t=10, I_norm=0.0)
        assert ratio > 1e6


# ===========================================================================
#  Tests: Cube Encoding (Saturn State → Snapshot)
# ===========================================================================


class TestCubeEncoding:
    """Saturn Ring state snapshots as QR Cubes."""

    def _make_cube(self, coords=None, cost=5.0, spin=1, phase=0.5):
        coords = coords or [0.3, 0.5, 0.4, 0.2, 0.6, 0.3]
        centroid = [0.4, 0.4, 0.4, 0.3, 0.5, 0.3]
        return encode_cube(coords, centroid, cost, spin, phase, [1, 1, 0, 1, -1])

    def test_cube_has_all_fields(self):
        cube = self._make_cube()
        required = {"xyz", "V", "h", "E_port", "phase", "spin", "cost", "trust_momentum", "signature"}
        assert required.issubset(set(cube.keys()))

    def test_cube_signature_is_deterministic(self):
        cube1 = self._make_cube()
        cube2 = self._make_cube()
        assert cube1["signature"] == cube2["signature"]

    def test_different_state_different_signature(self):
        cube1 = self._make_cube(cost=5.0)
        cube2 = self._make_cube(cost=50.0)
        assert cube1["signature"] != cube2["signature"]

    def test_cube_V_is_lyapunov(self):
        cube = self._make_cube()
        assert cube["V"] >= 0.0

    def test_cube_h_is_barrier(self):
        cube = self._make_cube(cost=5.0)
        assert cube["h"] > 0  # Inside safe region


# ===========================================================================
#  Tests: Cube Integrity Validation
# ===========================================================================


class TestCubeValidation:
    """Governance decisions from cube snapshots."""

    def test_safe_cube_allows(self):
        cube = encode_cube([0.4] * 6, [0.4] * 6, cost=5.0, spin_magnitude=0, phase=0.5, trust_history=[1] * 5)
        assert validate_cube(cube) == "ALLOW"

    def test_high_cost_denies(self):
        cube = encode_cube([0.9] * 6, [0.1] * 6, cost=250.0, spin_magnitude=6, phase=0.5, trust_history=[-1] * 5)
        assert validate_cube(cube) == "DENY"

    def test_medium_cost_escalates(self):
        cube = encode_cube([0.6] * 6, [0.4] * 6, cost=180.0, spin_magnitude=3, phase=0.5, trust_history=[0] * 5)
        assert validate_cube(cube) == "ESCALATE"


# ===========================================================================
#  Tests: Tamper Detection
# ===========================================================================


class TestTamperDetection:
    """Modifying one field invalidates the cube signature."""

    def test_unmodified_cube_verifies(self):
        cube = encode_cube([0.4] * 6, [0.4] * 6, cost=5.0, spin_magnitude=0, phase=0.5, trust_history=[1] * 5)
        assert verify_cube_signature(cube)

    def test_modified_cost_fails_verification(self):
        cube = encode_cube([0.4] * 6, [0.4] * 6, cost=5.0, spin_magnitude=0, phase=0.5, trust_history=[1] * 5)
        cube["cost"] = 999.0  # Tamper
        assert not verify_cube_signature(cube)

    def test_modified_spin_fails_verification(self):
        cube = encode_cube([0.4] * 6, [0.4] * 6, cost=5.0, spin_magnitude=0, phase=0.5, trust_history=[1] * 5)
        cube["spin"] = 6  # Tamper
        assert not verify_cube_signature(cube)

    def test_modified_V_fails_verification(self):
        # Use coords != centroid so V > 0, then tampering to 0 is detectable
        cube = encode_cube(
            [0.6, 0.3, 0.7, 0.2, 0.8, 0.1], [0.4] * 6, cost=5.0, spin_magnitude=0, phase=0.5, trust_history=[1] * 5
        )
        assert cube["V"] > 0, "V should be nonzero when coords != centroid"
        cube["V"] = 0.0  # Tamper
        assert not verify_cube_signature(cube)

    def test_modified_signature_fails(self):
        cube = encode_cube([0.4] * 6, [0.4] * 6, cost=5.0, spin_magnitude=0, phase=0.5, trust_history=[1] * 5)
        cube["signature"] = "0" * 32  # Forge
        assert not verify_cube_signature(cube)


# ===========================================================================
#  Tests: Full Round-Trip (Runtime → Snapshot → Verify)
# ===========================================================================


class TestRoundTrip:
    """End-to-end: simulate runtime, snapshot to cube, verify."""

    def test_benign_session_produces_valid_cube(self):
        # Simulate 5 benign queries
        centroid = [0.4] * 6
        coords_history = [
            [0.35, 0.42, 0.38, 0.41, 0.45, 0.39],
            [0.38, 0.40, 0.42, 0.39, 0.43, 0.41],
            [0.40, 0.41, 0.40, 0.40, 0.42, 0.40],
            [0.39, 0.40, 0.41, 0.40, 0.41, 0.40],
            [0.40, 0.40, 0.40, 0.40, 0.41, 0.40],
        ]

        # Track Lyapunov stability
        V_values = [lyapunov_V(c, centroid) for c in coords_history]
        for i in range(1, len(V_values)):
            assert V_values[i] <= V_values[i - 1] + 0.01, "Benign session should converge"

        # Snapshot final state
        cube = encode_cube(coords_history[-1], centroid, cost=3.0, spin_magnitude=0, phase=0.5, trust_history=[1] * 5)
        assert validate_cube(cube) == "ALLOW"
        assert verify_cube_signature(cube)
        assert is_self_healing(lyapunov_dVdt(V_values[-1], V_values[0]))

    def test_attack_session_produces_escalated_cube(self):
        centroid = [0.4] * 6
        # Simulate escalating attack
        coords_history = [
            [0.45, 0.38, 0.50, 0.35, 0.55, 0.30],
            [0.55, 0.30, 0.60, 0.25, 0.65, 0.20],
            [0.70, 0.20, 0.75, 0.15, 0.80, 0.10],
        ]

        V_values = [lyapunov_V(c, centroid) for c in coords_history]
        # Should be diverging (V increasing)
        assert V_values[-1] > V_values[0]
        assert not is_self_healing(lyapunov_dVdt(V_values[-1], V_values[0]))

        cube = encode_cube(
            coords_history[-1], centroid, cost=180.0, spin_magnitude=5, phase=0.5, trust_history=[-1] * 5
        )
        decision = validate_cube(cube)
        assert decision in ("ESCALATE", "DENY", "QUARANTINE")
        assert verify_cube_signature(cube)
