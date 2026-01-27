#!/usr/bin/env python3
"""
AETHERMOORE Mathematical Foundations - Test Suite
=================================================
Validates all mathematical primitives for AI swarm governance.

Run: pytest tests/test_aethermoore_math.py -v
"""

import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.aethermoore_math import (
    # Constants
    COX_CONSTANT,
    MARS_FREQUENCY_HZ,
    MARS_TICK_MS,
    Q16_16_SCALE,
    # Hyperbolic
    hyperbolic_distance,
    trust_cost,
    # Lorentz
    lorentz_factor,
    dilated_path_cost,
    threat_velocity,
    # Soliton
    nlse_soliton,
    # Fixed Point
    Q16_16,
    # Swarm
    swarm_consensus_time,
    byzantine_rounds,
    tick_synchronization,
)
from src.aethermoore_math.swarm import (
    byzantine_threshold,
    SwarmTopology,
    simulate_consensus,
)
from src.aethermoore_math.fixed_point import q16_sqrt, Q16_ONE, Q16_PI


# ==============================================================================
# TEST: CONSTANTS
# ==============================================================================

class TestConstants:
    """Test fundamental AETHERMOORE constants."""

    def test_cox_constant_self_consistent(self):
        """Cox constant must satisfy c = e^(π/c)."""
        c = COX_CONSTANT
        expected = np.exp(np.pi / c)
        assert abs(c - expected) < 1e-10, f"Cox constant not self-consistent: {c} vs {expected}"

    def test_cox_constant_approximate_value(self):
        """Cox constant should be approximately 2.926."""
        assert 2.925 < COX_CONSTANT < 2.927

    def test_mars_frequency_derivation(self):
        """Mars frequency must be derived from orbital period."""
        orbital_period_days = 686.98
        orbital_period_seconds = orbital_period_days * 86400
        octave = 33
        expected = (1.0 / orbital_period_seconds) * (2 ** octave)
        assert abs(MARS_FREQUENCY_HZ - expected) < 0.01

    def test_mars_frequency_grid_decoupled(self):
        """Mars frequency must not be harmonic with 50/60 Hz."""
        ratio_50 = MARS_FREQUENCY_HZ / 50
        ratio_60 = MARS_FREQUENCY_HZ / 60
        # Should not be close to an integer
        assert abs(ratio_50 - round(ratio_50)) > 0.1
        assert abs(ratio_60 - round(ratio_60)) > 0.1

    def test_mars_tick_duration(self):
        """Mars tick should be approximately 6.9 ms."""
        assert 6.5 < MARS_TICK_MS < 7.5


# ==============================================================================
# TEST: HYPERBOLIC GEOMETRY
# ==============================================================================

class TestHyperbolicGeometry:
    """Test hyperbolic distance and trust routing."""

    def test_hyperbolic_distance_identity(self):
        """Distance from point to itself is zero."""
        d = hyperbolic_distance(1.0, 0.0, 1.0, 0.0)
        assert abs(d) < 1e-10

    def test_hyperbolic_distance_symmetry(self):
        """Distance must be symmetric."""
        d1 = hyperbolic_distance(1.0, 0.0, 2.0, np.pi/4)
        d2 = hyperbolic_distance(2.0, np.pi/4, 1.0, 0.0)
        assert abs(d1 - d2) < 1e-10

    def test_hyperbolic_distance_grows_with_radius(self):
        """Distance should grow exponentially with radius."""
        d_near = hyperbolic_distance(0.5, 0, 0.5, np.pi)
        d_mid = hyperbolic_distance(2.0, 0, 2.0, np.pi)
        d_far = hyperbolic_distance(4.0, 0, 4.0, np.pi)

        assert d_mid > d_near
        assert d_far > d_mid
        # Exponential growth
        assert d_far / d_mid > d_mid / d_near

    def test_trust_cost_increases_with_distance(self):
        """Trust cost must increase with agent distance from center."""
        cost_core = trust_cost(0.5, 0.5, 0.0)
        cost_mid = trust_cost(2.0, 2.0, 0.0)
        cost_edge = trust_cost(4.0, 4.0, 0.0)

        assert cost_mid > cost_core
        assert cost_edge > cost_mid


# ==============================================================================
# TEST: LORENTZ FACTOR
# ==============================================================================

class TestLorentzFactor:
    """Test relativistic path dilation."""

    def test_lorentz_at_rest(self):
        """Lorentz factor is 1 when v=0."""
        assert lorentz_factor(0.0) == 1.0

    def test_lorentz_increases_with_velocity(self):
        """Lorentz factor increases with velocity."""
        g1 = lorentz_factor(0.5)
        g2 = lorentz_factor(0.9)
        g3 = lorentz_factor(0.99)

        assert g1 < g2 < g3

    def test_lorentz_at_c(self):
        """Lorentz factor is infinite at v=c."""
        assert lorentz_factor(1.0) == float('inf')

    def test_lorentz_known_values(self):
        """Test against known relativistic values."""
        # At v = 0.6c, γ = 1.25
        assert abs(lorentz_factor(0.6) - 1.25) < 0.01
        # At v = 0.8c, γ ≈ 1.667
        assert abs(lorentz_factor(0.8) - 5/3) < 0.01

    def test_dilated_path_cost(self):
        """Path cost must be dilated by Lorentz factor."""
        base = 10.0
        # Safe agent: minimal dilation
        assert abs(dilated_path_cost(base, 0.0) - base) < 0.01
        # Suspicious agent: significant dilation
        assert dilated_path_cost(base, 0.9) > base * 2
        # Attack: extreme dilation
        assert dilated_path_cost(base, 0.99) > base * 7

    def test_threat_velocity_bounds(self):
        """Threat velocity must be in [0, 1)."""
        v = threat_velocity(1.0, 1.0, 0.0)  # Max threat
        assert 0 <= v < 1.0


# ==============================================================================
# TEST: SOLITON PROPAGATION
# ==============================================================================

class TestSoliton:
    """Test soliton-based message integrity."""

    def test_soliton_peak_preserved(self):
        """Soliton peak amplitude must be preserved over time."""
        x = np.linspace(-10, 10, 500)

        u0 = nlse_soliton(x, 0.0)
        u1 = nlse_soliton(x, 1.0)
        u2 = nlse_soliton(x, 5.0)

        peak0 = np.max(np.abs(u0))
        peak1 = np.max(np.abs(u1))
        peak2 = np.max(np.abs(u2))

        assert abs(peak0 - peak1) < 0.01
        assert abs(peak0 - peak2) < 0.01

    def test_soliton_width_preserved(self):
        """Soliton FWHM must be preserved over time."""
        x = np.linspace(-10, 10, 500)

        def get_fwhm(u):
            amp = np.abs(u)
            half_max = np.max(amp) / 2
            above = amp > half_max
            if np.any(above):
                return x[above][-1] - x[above][0]
            return 0

        fwhm0 = get_fwhm(nlse_soliton(x, 0.0))
        fwhm1 = get_fwhm(nlse_soliton(x, 5.0))

        assert abs(fwhm0 - fwhm1) < 0.1


# ==============================================================================
# TEST: Q16.16 FIXED POINT
# ==============================================================================

class TestFixedPoint:
    """Test deterministic fixed-point arithmetic."""

    def test_q16_conversion_roundtrip(self):
        """Float -> Q16.16 -> float should be close."""
        values = [0.0, 1.0, -1.0, 3.14159, -2.71828, 100.5, -100.5]
        for v in values:
            q = Q16_16.from_float(v)
            result = q.to_float()
            # Q16.16 precision is ~1/65536
            assert abs(result - v) < 0.0001

    def test_q16_addition(self):
        """Q16.16 addition must be correct."""
        a = Q16_16.from_float(3.14159)
        b = Q16_16.from_float(2.71828)
        c = a + b
        expected = 3.14159 + 2.71828
        assert abs(c.to_float() - expected) < 0.001

    def test_q16_multiplication(self):
        """Q16.16 multiplication must be correct."""
        a = Q16_16.from_float(3.0)
        b = Q16_16.from_float(4.0)
        c = a * b
        assert abs(c.to_float() - 12.0) < 0.001

    def test_q16_division(self):
        """Q16.16 division must be correct."""
        a = Q16_16.from_float(10.0)
        b = Q16_16.from_float(4.0)
        c = a / b
        assert abs(c.to_float() - 2.5) < 0.001

    def test_q16_determinism(self):
        """Same calculation must produce identical results."""
        results = set()
        for _ in range(1000):
            x = Q16_16.from_float(1.23456)
            y = Q16_16.from_float(7.89012)
            z = (x * y) + x
            results.add(z.raw)

        assert len(results) == 1, "Q16.16 not deterministic!"

    def test_q16_sqrt(self):
        """Q16.16 square root must be approximately correct."""
        x = Q16_16.from_float(16.0)
        result = q16_sqrt(x)
        assert abs(result.to_float() - 4.0) < 0.01

    def test_q16_serialization(self):
        """Q16.16 must serialize/deserialize correctly."""
        original = Q16_16.from_float(123.456)
        serialized = original.to_bytes()
        restored = Q16_16.from_bytes(serialized)
        assert original == restored


# ==============================================================================
# TEST: SWARM CONSENSUS
# ==============================================================================

class TestSwarmConsensus:
    """Test AI swarm coordination timing."""

    def test_byzantine_threshold(self):
        """Byzantine threshold must be < n/3."""
        assert byzantine_threshold(10) == 3
        assert byzantine_threshold(100) == 33
        assert byzantine_threshold(1000) == 333

    def test_byzantine_rounds(self):
        """Byzantine consensus requires at least 3 rounds."""
        assert byzantine_rounds(10) >= 3
        assert byzantine_rounds(100) >= 3

    def test_swarm_consensus_time_reasonable(self):
        """Swarm consensus must complete in reasonable time."""
        # 100 drones should reach consensus in < 500ms
        time_100 = swarm_consensus_time(100)
        assert time_100 < 500

        # 1000 drones should still be < 1 second
        time_1000 = swarm_consensus_time(1000)
        assert time_1000 < 1000

    def test_tick_synchronization(self):
        """Tick sync must return valid tick number and wait time."""
        tick_num, wait_ms = tick_synchronization(1000.0)

        assert tick_num >= 0
        assert 0 <= wait_ms <= MARS_TICK_MS

    def test_swarm_topology_commander_at_center(self):
        """Commander (agent 0) must be at hyperbolic center."""
        topo = SwarmTopology.create(100)
        r, theta = topo.get_agent_position(0)
        assert r == 0.0

    def test_swarm_topology_workers_at_periphery(self):
        """Workers must be further from center than commanders."""
        topo = SwarmTopology.create(100)

        commander_r, _ = topo.get_agent_position(1)
        worker_r, _ = topo.get_agent_position(50)

        assert worker_r > commander_r

    def test_simulate_consensus_possible(self):
        """Consensus must be possible with f < n/3 faulty."""
        topo = SwarmTopology.create(100)
        result = simulate_consensus(topo, faulty_ids=[1, 2, 3])

        assert result['can_reach_consensus'] is True
        assert result['consensus_time_ms'] < float('inf')

    def test_simulate_consensus_impossible(self):
        """Consensus must be impossible with f >= n/3 faulty."""
        topo = SwarmTopology.create(10)
        # 4 faulty out of 10 = 40% > 33%
        result = simulate_consensus(topo, faulty_ids=[1, 2, 3, 4])

        assert result['can_reach_consensus'] is False


# ==============================================================================
# TEST: INTEGRATED SWARM SCENARIO
# ==============================================================================

class TestIntegratedSwarm:
    """End-to-end swarm governance tests."""

    def test_1000_drone_fleet_consensus(self):
        """1000-drone fleet must reach consensus in < 1 second."""
        n = 1000
        topo = SwarmTopology.create(n)

        # Allow 10% faulty (well under 33% threshold)
        faulty = list(range(1, 101))  # 100 faulty

        result = simulate_consensus(topo, faulty_ids=faulty)

        assert result['can_reach_consensus'] is True
        assert result['consensus_time_ms'] < 1000

    def test_threat_dilation_quarantines_attacker(self):
        """High threat agent must experience extreme path dilation."""
        # Normal agent: threat = 0.1
        normal_cost = dilated_path_cost(10.0, 0.1)

        # Attacker: threat = 0.99
        attacker_cost = dilated_path_cost(10.0, 0.99)

        # Attacker should be >7x slower
        assert attacker_cost / normal_cost > 7

    def test_hyperbolic_trust_hierarchy(self):
        """Agents further from center must have higher trust cost."""
        # Core agent accessing resource
        core_cost = trust_cost(0.5, 1.0, 0.0)

        # Edge agent accessing same resource
        edge_cost = trust_cost(3.0, 1.0, 0.0)

        assert edge_cost > core_cost

    def test_fixed_point_consensus_agreement(self):
        """All agents must compute identical Q16.16 results."""
        # Simulate 100 agents computing the same value
        results = []
        for agent_id in range(100):
            x = Q16_16.from_float(MARS_FREQUENCY_HZ)
            y = Q16_16.from_float(COX_CONSTANT)
            z = x * y
            results.append(z.raw)

        # All must be identical
        assert len(set(results)) == 1


# ==============================================================================
# RUN STANDALONE
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
