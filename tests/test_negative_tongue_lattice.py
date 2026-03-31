"""
Tests for Negative Tongue Lattice + PhasonSecret (Layer 8).
============================================================

Coverage:
  - NegativeTongueLattice: coords, bridges, full lattice, energy, interference
  - PhasonSecret: public vs private matrices, audit hook, alignment
  - RuntimeGate integration: lattice energy modulates cost (opt-in)
  - Zero-state: lattice object has no stored state after init
"""

import os
import sys

# Ensure local src/ wins over any installed `governance` module that may be
# imported by plugins before we set up sys.path (GitHub Actions CI observed this).
# Also handles the case where spiral-word-app/governance.py (a plain .py file)
# was imported earlier, which prevents sub-module imports.
_src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# Ensure project root is also on path for src.* imports
_PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Clear cached non-package governance (e.g. from spiral-word-app/governance.py)
_prev_gov = sys.modules.get("governance")
if _prev_gov is not None and not hasattr(_prev_gov, "__path__"):
    sys.modules.pop("governance", None)

# If the root symphonic_cipher variant was cached by an earlier test, clear it
# so the src/ variant (which has qc_lattice, governance, etc.) can be found.
_sc = sys.modules.get("symphonic_cipher")
if _sc is not None and getattr(_sc, "_VARIANT", None) != "src":
    for key in list(sys.modules):
        if key == "symphonic_cipher" or key.startswith("symphonic_cipher."):
            del sys.modules[key]

import numpy as np
import pytest

from src.governance.negative_tongue_lattice import NegativeTongueLattice
from src.symphonic_cipher.scbe_aethermoore.qc_lattice.phason_secret import PhasonSecret

# =============================================================================
# NEGATIVE TONGUE LATTICE TESTS
# =============================================================================


class TestNegativeCoords:
    """Negative coords are always 1 - positive."""

    def test_sign_flip_basic(self):
        lattice = NegativeTongueLattice()
        pos = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]
        neg = lattice.negative_coords(pos)
        for p, n in zip(pos, neg):
            assert abs(n - (1.0 - p)) < 1e-12

    def test_sign_flip_zeros(self):
        lattice = NegativeTongueLattice()
        pos = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        neg = lattice.negative_coords(pos)
        assert neg == [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

    def test_sign_flip_ones(self):
        lattice = NegativeTongueLattice()
        pos = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        neg = lattice.negative_coords(pos)
        assert neg == [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    def test_negative_in_zero_one_range(self):
        """If positive coords are in [0,1], negative must be too."""
        lattice = NegativeTongueLattice()
        pos = [0.1, 0.5, 0.9, 0.0, 1.0, 0.33]
        neg = lattice.negative_coords(pos)
        for n in neg:
            assert 0.0 <= n <= 1.0


class TestBridge:
    """Bridge returns float, different for different tongue pairs."""

    def test_bridge_returns_float(self):
        lattice = NegativeTongueLattice()
        coords = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]
        val = lattice.bridge("KO", "AV", coords)
        assert isinstance(val, float)

    def test_different_pairs_different_values(self):
        lattice = NegativeTongueLattice()
        coords = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]
        ko_av = lattice.bridge("KO", "AV", coords)
        ko_ru = lattice.bridge("KO", "RU", coords)
        av_ko = lattice.bridge("AV", "KO", coords)
        # Different tongue pairs should generally produce different values
        assert ko_av != ko_ru
        # Direction matters: KO->AV != AV->KO
        assert ko_av != av_ko

    def test_bridge_phi_scaling(self):
        """More distant tongues have higher phi weight (smaller bridge value)."""
        lattice = NegativeTongueLattice()
        # Use coords that make the numerator constant for testing
        coords = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        # KO->AV (distance=1), KO->DR (distance=5)
        near = abs(lattice.bridge("KO", "AV", coords))
        far = abs(lattice.bridge("KO", "DR", coords))
        # Near bridge should be stronger than far bridge (less phi scaling)
        assert near >= far


class TestFullLattice:
    """full_lattice() returns 30 entries (6x6 - 6 self-bridges)."""

    def test_entry_count(self):
        lattice = NegativeTongueLattice()
        coords = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]
        result = lattice.full_lattice(coords)
        assert len(result) == 30  # 6*6 - 6

    def test_no_self_bridges(self):
        lattice = NegativeTongueLattice()
        coords = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]
        result = lattice.full_lattice(coords)
        for tongue in NegativeTongueLattice.TONGUES:
            assert f"{tongue}->{tongue}" not in result

    def test_all_values_are_float(self):
        lattice = NegativeTongueLattice()
        coords = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]
        result = lattice.full_lattice(coords)
        for v in result.values():
            assert isinstance(v, float)


class TestLatticeEnergy:
    """Lattice energy: adversarial > benign."""

    def test_energy_is_float(self):
        lattice = NegativeTongueLattice()
        coords = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        energy = lattice.lattice_energy(coords)
        assert isinstance(energy, float)
        assert energy >= 0.0

    def test_adversarial_higher_than_benign(self):
        """Adversarial coords (extreme variance) should produce higher energy
        than benign coords (uniform/centered)."""
        lattice = NegativeTongueLattice()
        benign = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        adversarial = [1.0, 0.0, 1.0, 0.0, 1.0, 0.0]
        energy_benign = lattice.lattice_energy(benign)
        energy_adversarial = lattice.lattice_energy(adversarial)
        assert energy_adversarial > energy_benign

    def test_zero_coords_finite(self):
        lattice = NegativeTongueLattice()
        coords = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        energy = lattice.lattice_energy(coords)
        assert energy >= 0.0
        assert np.isfinite(energy)


class TestInterferencePattern:
    """interference_pattern correctly classifies constructive/destructive."""

    def test_pattern_keys(self):
        lattice = NegativeTongueLattice()
        coords = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]
        pattern = lattice.interference_pattern(coords)
        assert "constructive" in pattern
        assert "destructive" in pattern
        assert "neutral" in pattern

    def test_constructive_positive(self):
        lattice = NegativeTongueLattice()
        coords = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]
        pattern = lattice.interference_pattern(coords)
        for v in pattern["constructive"].values():
            assert v > 0

    def test_destructive_negative(self):
        lattice = NegativeTongueLattice()
        coords = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]
        pattern = lattice.interference_pattern(coords)
        for v in pattern["destructive"].values():
            assert v < 0

    def test_neutral_near_zero(self):
        lattice = NegativeTongueLattice()
        coords = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]
        pattern = lattice.interference_pattern(coords)
        for v in pattern["neutral"].values():
            assert abs(v) < 0.01

    def test_total_bridges_sum(self):
        """All bridges should be accounted for across the three categories."""
        lattice = NegativeTongueLattice()
        coords = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]
        pattern = lattice.interference_pattern(coords)
        total = len(pattern["constructive"]) + len(pattern["destructive"]) + len(pattern["neutral"])
        assert total == 30


class TestStrongestWeakestBridge:
    """strongest_bridge and weakest_bridge helpers."""

    def test_strongest_returns_tuple(self):
        lattice = NegativeTongueLattice()
        coords = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]
        key, val = lattice.strongest_bridge(coords)
        assert isinstance(key, str)
        assert isinstance(val, float)
        assert "->" in key

    def test_weakest_returns_tuple(self):
        lattice = NegativeTongueLattice()
        coords = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]
        key, val = lattice.weakest_bridge(coords)
        assert isinstance(key, str)
        assert isinstance(val, float)
        assert "->" in key

    def test_strongest_geq_weakest(self):
        lattice = NegativeTongueLattice()
        coords = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]
        _, strong = lattice.strongest_bridge(coords)
        _, weak = lattice.weakest_bridge(coords)
        assert abs(strong) >= abs(weak)


class TestZeroStateProperty:
    """The lattice object has no stored state after init."""

    def test_no_instance_dict_growth(self):
        lattice = NegativeTongueLattice()
        # __dict__ should be empty or minimal — no coords, no lattice stored
        assert len(lattice.__dict__) == 0

    def test_repeated_calls_same_result(self):
        """Stateless: same input always produces same output."""
        lattice = NegativeTongueLattice()
        coords = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]
        e1 = lattice.lattice_energy(coords)
        e2 = lattice.lattice_energy(coords)
        assert e1 == e2

    def test_no_state_after_computation(self):
        """Computing full_lattice should not add any state to the object."""
        lattice = NegativeTongueLattice()
        _ = lattice.full_lattice([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
        _ = lattice.lattice_energy([0.9, 0.8, 0.7, 0.6, 0.5, 0.4])
        assert len(lattice.__dict__) == 0


# =============================================================================
# PHASON SECRET TESTS
# =============================================================================


class TestPhasonSecretGeneration:
    """PhasonSecret generates different matrices in public vs private mode."""

    def test_public_mode_deterministic(self):
        ps = PhasonSecret(session_key=b"test-key-123")
        a1 = ps.generate_quasi_A(mode="public")
        a2 = ps.generate_quasi_A(mode="public")
        np.testing.assert_array_equal(a1, a2)

    def test_private_mode_deterministic(self):
        ps = PhasonSecret(session_key=b"test-key-123")
        a1 = ps.generate_quasi_A(mode="private")
        a2 = ps.generate_quasi_A(mode="private")
        np.testing.assert_array_equal(a1, a2)

    def test_public_vs_private_differ(self):
        ps = PhasonSecret(session_key=b"test-key-123")
        pub = ps.generate_quasi_A(mode="public")
        priv = ps.generate_quasi_A(mode="private")
        # They should differ (the phason perturbation changes the matrix)
        assert not np.array_equal(pub, priv)

    def test_different_sessions_different_private(self):
        ps1 = PhasonSecret(session_key=b"session-alpha")
        ps2 = PhasonSecret(session_key=b"session-beta")
        a1 = ps1.generate_quasi_A(mode="private")
        a2 = ps2.generate_quasi_A(mode="private")
        assert not np.array_equal(a1, a2)

    def test_matrix_shape(self):
        ps = PhasonSecret(n=64, q=3329)
        a = ps.generate_quasi_A(mode="public")
        assert a.shape == (64, 64)

    def test_matrix_values_in_range(self):
        """All entries should be in [0, q)."""
        ps = PhasonSecret(n=64, q=3329)
        for mode in ("public", "private"):
            a = ps.generate_quasi_A(mode=mode)
            assert np.all(a >= 0)
            assert np.all(a < 3329)

    def test_invalid_mode_raises(self):
        ps = PhasonSecret()
        with pytest.raises(ValueError, match="mode must be"):
            ps.generate_quasi_A(mode="invalid")


class TestPhasonAuditHook:
    """audit_phason_use returns correct layer and component."""

    def test_audit_returns_list(self):
        ps = PhasonSecret(session_key=b"audit-test")
        ps.generate_quasi_A(mode="public")
        audit = ps.audit_phason_use()
        assert isinstance(audit, list)
        assert len(audit) == 1

    def test_audit_layer_is_8(self):
        ps = PhasonSecret(session_key=b"audit-test")
        ps.generate_quasi_A(mode="private")
        audit = ps.audit_phason_use()
        assert audit[0]["layer"] == 8

    def test_audit_component_is_phason_secret(self):
        ps = PhasonSecret(session_key=b"audit-test")
        ps.generate_quasi_A(mode="public")
        audit = ps.audit_phason_use()
        assert audit[0]["component"] == "PhasonSecret"

    def test_audit_records_mode(self):
        ps = PhasonSecret(session_key=b"audit-test")
        ps.generate_quasi_A(mode="public")
        ps.generate_quasi_A(mode="private")
        audit = ps.audit_phason_use()
        assert audit[0]["mode"] == "public"
        assert audit[1]["mode"] == "private"

    def test_audit_has_session_id(self):
        ps = PhasonSecret(session_key=b"audit-test")
        ps.generate_quasi_A(mode="public")
        audit = ps.audit_phason_use()
        assert audit[0]["session_id"] == ps.session_id
        assert len(ps.session_id) == 16

    def test_audit_has_matrix_hash(self):
        ps = PhasonSecret(session_key=b"audit-test")
        ps.generate_quasi_A(mode="public")
        audit = ps.audit_phason_use()
        assert len(audit[0]["matrix_hash"]) == 32  # SHA-256 truncated to 32 hex chars


class TestPhasonRoundTrip:
    """Round-trip: generate quasi_A with secret, verify private alignment advantage."""

    def test_private_alignment_advantage(self):
        """Same session key produces identical private matrices (alignment=1.0)."""
        ps = PhasonSecret(session_key=b"round-trip-key")
        a1 = ps.generate_quasi_A(mode="private")
        a2 = ps.generate_quasi_A(mode="private")
        alignment = ps.verify_alignment(a1, a2)
        assert alignment == 1.0

    def test_public_private_misalignment(self):
        """Public vs private should have much lower alignment than private vs private."""
        ps = PhasonSecret(session_key=b"round-trip-key")
        pub = ps.generate_quasi_A(mode="public")
        priv = ps.generate_quasi_A(mode="private")
        alignment_pub_priv = ps.verify_alignment(pub, priv)
        alignment_priv_priv = ps.verify_alignment(priv, priv)
        # Private-vs-private should be perfect
        assert alignment_priv_priv == 1.0
        # Public-vs-private should be strictly less — the phason perturbation
        # shifts entries mod q, so most or all entries differ.
        assert alignment_pub_priv < alignment_priv_priv

    def test_cross_session_no_alignment(self):
        """Different session keys should produce low alignment for private matrices."""
        ps1 = PhasonSecret(session_key=b"session-x")
        ps2 = PhasonSecret(session_key=b"session-y")
        a1 = ps1.generate_quasi_A(mode="private")
        a2 = ps2.generate_quasi_A(mode="private")
        alignment = ps1.verify_alignment(a1, a2)
        # Different secrets should give noticeably lower alignment
        # (not necessarily 0, but much less than 1.0)
        assert alignment < 1.0

    def test_constant_time_compare(self):
        ps = PhasonSecret()
        assert ps.constant_time_compare(b"hello", b"hello") is True
        assert ps.constant_time_compare(b"hello", b"world") is False


class TestPhasonProperties:
    """Default properties match spec."""

    def test_default_n(self):
        ps = PhasonSecret()
        assert ps.n == 64

    def test_default_q(self):
        ps = PhasonSecret()
        assert ps.q == 3329

    def test_default_phi(self):
        ps = PhasonSecret()
        expected = (1 + 5**0.5) / 2
        assert abs(ps.phi - expected) < 1e-12

    def test_custom_params(self):
        ps = PhasonSecret(n=128, q=7681, phi=2.0)
        assert ps.n == 128
        assert ps.q == 7681
        assert ps.phi == 2.0


# =============================================================================
# RUNTIME GATE INTEGRATION TEST (opt-in negative lattice)
# =============================================================================


class TestRuntimeGateNegativeLattice:
    """RuntimeGate with use_negative_lattice=True includes lattice_energy."""

    def test_default_lattice_energy_zero(self):
        """Default (no negative lattice) should have lattice_energy=0."""
        from governance.runtime_gate import RuntimeGate

        gate = RuntimeGate()
        # Run enough evaluations to get past calibration
        for i in range(6):
            result = gate.evaluate(f"simple safe action number {i}")
        assert result.lattice_energy == 0.0

    def test_lattice_energy_nonzero_when_enabled(self):
        """With negative lattice enabled, lattice_energy should be > 0."""
        from governance.runtime_gate import RuntimeGate

        gate = RuntimeGate(use_negative_lattice=True)
        # Run past calibration
        for i in range(6):
            result = gate.evaluate(f"simple safe action number {i}")
        # After calibration, the full path is taken — lattice_energy > 0
        assert result.lattice_energy > 0.0

    def test_lattice_modulates_cost(self):
        """With lattice enabled, cost should be >= cost without lattice."""
        from governance.runtime_gate import RuntimeGate

        gate_plain = RuntimeGate()
        gate_lattice = RuntimeGate(use_negative_lattice=True)
        action = "a somewhat complex request with mixed signals"
        # Run past calibration on both
        for i in range(5):
            gate_plain.evaluate(f"calibration {i}")
            gate_lattice.evaluate(f"calibration {i}")
        r_plain = gate_plain.evaluate(action)
        r_lattice = gate_lattice.evaluate(action)
        # Lattice-modulated cost should be higher (energy adds to cost)
        assert r_lattice.cost >= r_plain.cost
