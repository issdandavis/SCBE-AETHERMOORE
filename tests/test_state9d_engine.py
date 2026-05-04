"""Tests for the SCBE 9D State Engine.

Coverage:
  - Context vector construction (shape, types, ranges)
  - Shannon entropy computation (boundary, normalization)
  - Time flow (causality, monotonicity, drift bounds)
  - Entropy ODE (steady-state, clipping, initial conditions)
  - Quantum evolution (normalization preservation, unitarity)
  - Full state assembly (integrity, serialization)
"""

import math

import numpy as np
import pytest

from python.scbe.state9d_engine import (
    BETA,
    DELTA_DRIFT_MAX,
    ETA_MAX,
    ETA_MIN,
    ETA_TARGET,
    NUM_BINS,
    OMEGA_TIME,
    PHI,
    TAU_COH,
    assemble_state_vector,
    build_context_vector,
    compute_shannon_entropy,
    evolve_entropy_ode,
    evolve_quantum_state,
    evolve_time,
    quantum_norm,
    time_flow_rate,
    State9D,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class TestConstants:
    def test_phi(self):
        assert PHI == pytest.approx(1.618033988749895, rel=1e-12)

    def test_omega_time(self):
        assert OMEGA_TIME == pytest.approx(2 * math.pi / 60, rel=1e-12)


# ---------------------------------------------------------------------------
# Context Vector
# ---------------------------------------------------------------------------
class TestContextVector:
    def test_shape_and_dtype(self):
        c = build_context_vector(t=0.0)
        assert c.shape == (6,)
        assert c.dtype == object

    def test_v1_identity_oscillation(self):
        c = build_context_vector(t=math.pi / 2)
        assert float(c[0]) == pytest.approx(1.0, abs=1e-12)

        c = build_context_vector(t=-math.pi / 2)
        assert float(c[0]) == pytest.approx(-1.0, abs=1e-12)

    def test_v2_intent_phase(self):
        c = build_context_vector(t=0.0)
        v2 = c[1]
        assert isinstance(v2, (complex, np.complexfloating))
        assert abs(v2) == pytest.approx(1.0, abs=1e-12)
        # e^(i·2π·0.75) = cos(3π/2) + i·sin(3π/2) = 0 - i
        assert v2.real == pytest.approx(0.0, abs=1e-12)
        assert v2.imag == pytest.approx(-1.0, abs=1e-12)

    def test_v3_trajectory_score_clipped(self):
        c = build_context_vector(t=0.0, trajectory_score=1.5)
        assert float(c[2]) == pytest.approx(1.0, abs=1e-12)

        c = build_context_vector(t=0.0, trajectory_score=-0.3)
        assert float(c[2]) == pytest.approx(0.0, abs=1e-12)

    def test_v4_linear_time(self):
        c = build_context_vector(t=123.456)
        assert float(c[3]) == pytest.approx(123.456, abs=1e-12)

    def test_v5_commitment_hash(self):
        c_empty = build_context_vector(t=0.0, commitment_str="")
        assert float(c_empty[4]) == pytest.approx(0.0, abs=1e-12)

        c1 = build_context_vector(t=0.0, commitment_str="hello")
        c2 = build_context_vector(t=0.0, commitment_str="world")
        assert c1[4] != c2[4]
        assert 0.0 <= float(c1[4]) < 1.0
        assert 0.0 <= float(c2[4]) < 1.0

    def test_v6_signature_validity_clipped(self):
        c = build_context_vector(t=0.0, signature_validity=2.0)
        assert float(c[5]) == pytest.approx(1.0, abs=1e-12)

        c = build_context_vector(t=0.0, signature_validity=-1.0)
        assert float(c[5]) == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# Shannon Entropy
# ---------------------------------------------------------------------------
class TestShannonEntropy:
    def test_uniform_distribution(self):
        """A perfectly uniform 6-value vector spread across bins should
        yield entropy close to log2(num_bins) when normalized."""
        c = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0], dtype=object)
        eta = compute_shannon_entropy(c, num_bins=NUM_BINS)
        # 6 points across 16 bins → not all bins filled, but entropy > 0
        assert eta > 1.0

    def test_identical_values(self):
        """All-identical values → 0 entropy."""
        c = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5], dtype=object)
        assert compute_shannon_entropy(c) == pytest.approx(0.0, abs=1e-12)

    def test_complex_magnitude(self):
        """Complex values should be reduced to magnitudes."""
        c = np.array([1.0, 1j, -1.0, -1j, 0.5, 0.5], dtype=object)
        eta = compute_shannon_entropy(c, num_bins=NUM_BINS)
        # All magnitudes are either 1.0 or 0.5 → 2 distinct values
        assert eta >= 0.0

    def test_no_normalize_option(self):
        """With normalize=False, large values dominate the histogram."""
        c = np.array([0.0, 1.0, 2.0, 3.0, 1000.0, 1001.0], dtype=object)
        eta_norm = compute_shannon_entropy(c, normalize=True)
        eta_raw = compute_shannon_entropy(c, normalize=False)
        # Normalized version should see more spread
        assert eta_norm >= eta_raw


# ---------------------------------------------------------------------------
# Time Flow
# ---------------------------------------------------------------------------
class TestTimeFlow:
    def test_causality(self):
        """τ̇(t) must always be > 0 because DELTA_DRIFT_MAX < 1."""
        for t in np.linspace(0, 120, 100):
            assert time_flow_rate(t) > 0.0

    def test_monotonic_increase(self):
        """τ(t) should be monotonically increasing."""
        taus = [evolve_time(t) for t in np.linspace(0, 120, 100)]
        for i in range(1, len(taus)):
            assert taus[i] > taus[i - 1]

    def test_initial_condition(self):
        assert evolve_time(0.0) == pytest.approx(0.0, abs=1e-12)

    def test_drift_bounds(self):
        """τ(t) should stay within [t, t + 2·DELTA_DRIFT_MAX/OMEGA_TIME]."""
        t = 30.0
        tau = evolve_time(t)
        max_drift = 2.0 * DELTA_DRIFT_MAX / OMEGA_TIME
        assert t <= tau <= t + max_drift + 1e-12


# ---------------------------------------------------------------------------
# Entropy ODE
# ---------------------------------------------------------------------------
class TestEntropyODE:
    def test_steady_state_convergence(self):
        """As t → ∞, the transient dies out and η approaches the
        particular solution around ETA_TARGET."""
        eta = evolve_entropy_ode(t=100.0, eta0=0.0)
        assert ETA_MIN <= eta <= ETA_MAX
        assert abs(eta - ETA_TARGET) < 1.0

    def test_initial_condition(self):
        eta = evolve_entropy_ode(t=0.0, eta0=ETA_TARGET)
        # At t=0 with eta0=ETA_TARGET: particular + C should equal ETA_TARGET
        assert eta == pytest.approx(ETA_TARGET, abs=1e-9)

    def test_clipping_low(self):
        eta = evolve_entropy_ode(t=0.0, eta0=-100.0)
        assert eta >= ETA_MIN

    def test_clipping_high(self):
        eta = evolve_entropy_ode(t=0.0, eta0=100.0)
        assert eta <= ETA_MAX


# ---------------------------------------------------------------------------
# Quantum Evolution
# ---------------------------------------------------------------------------
class TestQuantumEvolution:
    def test_normalization_preservation(self):
        """Unitary evolution must preserve |q|²."""
        q0 = 0.6 + 0.8j
        H = 2.5
        for t in [0.0, 0.5, 1.0, 3.14, 10.0]:
            q = evolve_quantum_state(q0, H, t)
            assert quantum_norm(q) == pytest.approx(quantum_norm(q0), abs=1e-12)

    def test_identity_at_zero(self):
        q0 = 1 + 2j
        q = evolve_quantum_state(q0, H=1.0, t=0.0)
        assert q == pytest.approx(q0, abs=1e-12)

    def test_periodicity(self):
        """For H=1, evolution is periodic with period 2π."""
        q0 = 1 + 0j
        q_t = evolve_quantum_state(q0, H=1.0, t=math.pi)
        q_t2 = evolve_quantum_state(q0, H=1.0, t=3 * math.pi)
        assert q_t == pytest.approx(q_t2, abs=1e-12)


# ---------------------------------------------------------------------------
# Full State Assembly
# ---------------------------------------------------------------------------
class TestAssembleStateVector:
    def test_shape_and_dtype(self):
        xi = assemble_state_vector(t=1.0)
        assert xi.shape == (9,)
        assert xi.dtype == object

    def test_layout(self):
        xi = assemble_state_vector(
            t=2.0,
            q0=1 + 0j,
            H=1.0,
            trajectory_score=0.8,
            commitment_str="test",
            signature_validity=0.9,
        )
        # c(t)
        assert isinstance(xi[0], float)  # v1
        assert isinstance(xi[1], (complex, np.complexfloating))  # v2
        assert float(xi[2]) == pytest.approx(0.8, abs=1e-12)
        assert float(xi[3]) == pytest.approx(2.0, abs=1e-12)
        assert 0.0 <= float(xi[4]) < 1.0  # v5 hash
        assert float(xi[5]) == pytest.approx(0.9, abs=1e-12)
        # tau
        assert float(xi[6]) > 2.0
        # eta
        assert 0.0 <= float(xi[7]) <= 6.0
        # q
        assert isinstance(xi[8], (complex, np.complexfloating))
        assert abs(xi[8]) == pytest.approx(1.0, abs=1e-12)

    def test_ode_entropy_path(self):
        xi = assemble_state_vector(t=5.0, use_ode_entropy=True, eta0=3.0)
        eta = float(xi[7])
        assert ETA_MIN <= eta <= ETA_MAX

    def test_different_commitments(self):
        xi1 = assemble_state_vector(t=0.0, commitment_str="alpha")
        xi2 = assemble_state_vector(t=0.0, commitment_str="beta")
        assert xi1[4] != xi2[4]


# ---------------------------------------------------------------------------
# State9D Wrapper
# ---------------------------------------------------------------------------
class TestState9D:
    def test_from_params(self):
        state = State9D.from_params(t=1.5, trajectory_score=0.99)
        assert state.xi.shape == (9,)
        assert state.tau > 1.5
        assert 0.0 <= state.eta <= 6.0
        assert state.is_coherent  # |q|² = 1.0 >= TAU_COH (0.9)

    def test_serialization(self):
        state = State9D.from_params(t=0.0)
        d = state.to_dict()
        assert "context" in d
        assert "tau" in d
        assert "eta" in d
        assert "q" in d
        assert "coherent" in d
        assert len(d["context"]) == 6
        assert isinstance(d["q"]["real"], float)
        assert isinstance(d["q"]["imag"], float)

    def test_invalid_vector(self):
        with pytest.raises(ValueError):
            State9D(np.zeros(8, dtype=object))
        with pytest.raises(ValueError):
            State9D(np.zeros(9, dtype=float))

    def test_coherence_threshold(self):
        # q0 with |q|² < TAU_COH should be incoherent
        q0 = math.sqrt(TAU_COH * 0.5) + 0j  # |q|² = 0.45 < 0.9
        state = State9D.from_params(t=0.0, q0=q0)
        assert not state.is_coherent
