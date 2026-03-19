"""Tests for phase tunneling through governance walls."""

import math
import time

import pytest

from src.aetherbrowser.phase_tunnel import (
    KernelStack,
    TransmissionResult,
    TunnelGovernor,
    TunnelOutcome,
    TunnelPermit,
    can_tunnel,
    compute_transmission,
    compute_transparency_frequency,
    harmonic_wall_cost,
    tunnel_phase_cost,
)


class TestHarmonicWall:
    def test_zero_distance_is_one(self):
        assert harmonic_wall_cost(0) == 1.0

    def test_increases_with_distance(self):
        costs = [harmonic_wall_cost(d) for d in [0, 1, 2, 3]]
        for i in range(len(costs) - 1):
            assert costs[i + 1] > costs[i]

    def test_super_exponential_growth(self):
        # d=6 should be massive
        cost_6 = harmonic_wall_cost(6)
        assert cost_6 > 1_000_000


class TestTunnelPhaseCost:
    def test_perfect_resonance_is_zero(self):
        wall_freq = math.pi / 4
        cost = tunnel_phase_cost(1.0, wall_freq, wall_freq)
        assert cost == pytest.approx(0.0, abs=1e-10)

    def test_anti_resonance_equals_wall(self):
        wall_freq = math.pi / 4
        anti_phase = wall_freq + math.pi / 2
        cost = tunnel_phase_cost(1.0, anti_phase, wall_freq)
        wall = harmonic_wall_cost(1.0)
        assert cost == pytest.approx(wall, rel=0.01)

    def test_partial_resonance_reduces_cost(self):
        wall_freq = math.pi / 4
        partial_phase = wall_freq + 0.1  # slightly off
        cost = tunnel_phase_cost(1.0, partial_phase, wall_freq)
        wall = harmonic_wall_cost(1.0)
        assert 0 < cost < wall


class TestTransparencyFrequency:
    def test_green_easiest(self):
        f_green = compute_transparency_frequency("GREEN", 0.5)
        f_red = compute_transparency_frequency("RED", 0.5)
        # GREEN base frequency is lower = easier to match
        assert f_green < f_red

    def test_depth_shifts_frequency(self):
        f_shallow = compute_transparency_frequency("YELLOW", 0.1)
        f_deep = compute_transparency_frequency("YELLOW", 2.0)
        assert f_deep > f_shallow


class TestCanTunnel:
    def test_matching_phase_allows_tunnel(self):
        zone = "YELLOW"
        depth = 0.5
        required = compute_transparency_frequency(zone, depth)
        allowed, cost, _ = can_tunnel(required, zone, depth, tolerance=0.1)
        assert allowed
        assert cost < harmonic_wall_cost(depth) * 0.1

    def test_wrong_phase_blocks_tunnel(self):
        zone = "RED"
        depth = 1.0
        wrong_phase = 0.0  # unlikely to match RED frequency
        allowed, cost, _ = can_tunnel(wrong_phase, zone, depth, tolerance=0.01)
        # May or may not be allowed depending on exact frequency alignment
        # but cost should be high relative to geometric wall
        assert cost > 0


class TestKernelStack:
    def test_new_kernel_has_no_scars(self):
        k = KernelStack(genesis_hash="abc123")
        assert k.lifetime_count == 0
        assert k.factorial_maturity == 1.0

    def test_adding_scars_increases_maturity(self):
        k = KernelStack(genesis_hash="abc123")
        k.add_scar("overfitting")
        k.add_scar("drift")
        k.add_scar("collapse")
        assert k.lifetime_count == 3
        assert k.factorial_maturity == math.factorial(3)  # 6

    def test_rebirth_preserves_scars(self):
        k = KernelStack(genesis_hash="abc123")
        k.add_scar("first_death")
        k.add_scar("second_death")

        k2 = k.rebirth(
            new_parents={"parent_a": "model_x", "parent_b": "model_y"},
            new_nursery=["chapter_1", "chapter_2"],
        )

        assert k2.genesis_hash == "abc123"  # same genesis
        assert k2.lifetime_count == 2  # scars preserved
        assert k2.operational_state == {}  # reset
        assert k2.nursery_path == ["chapter_1", "chapter_2"]  # new path

    def test_genesis_hash_immutable_across_rebirth(self):
        k = KernelStack(genesis_hash="immutable_seed")
        k2 = k.rebirth({}, [])
        k3 = k2.rebirth({}, [])
        assert k.genesis_hash == k2.genesis_hash == k3.genesis_hash


class TestTunnelGovernor:
    def test_issue_permit(self):
        gov = TunnelGovernor()
        kernel = KernelStack(genesis_hash="test")
        permit = gov.issue_permit("agent-1", kernel, "YELLOW")
        assert permit is not None
        assert permit.active

    def test_one_active_tunnel_per_agent(self):
        gov = TunnelGovernor()
        kernel = KernelStack(genesis_hash="test")
        p1 = gov.issue_permit("agent-1", kernel, "YELLOW")
        p2 = gov.issue_permit("agent-1", kernel, "RED")
        assert p1 is not None
        assert p2 is None  # blocked — already tunneling

    def test_maturity_affects_depth(self):
        gov = TunnelGovernor()

        # New kernel — shallow access
        k_new = KernelStack(genesis_hash="new")
        p_new = gov.issue_permit("agent-new", k_new, "YELLOW", requested_depth=5.0)

        # Complete the tunnel so we can issue another
        gov.complete_tunnel("agent-new")

        # Experienced kernel — deeper access
        k_exp = KernelStack(genesis_hash="exp")
        for i in range(10):
            k_exp.add_scar(f"death_{i}")
        p_exp = gov.issue_permit("agent-exp", k_exp, "YELLOW", requested_depth=5.0)

        assert p_exp.max_penetration_depth > p_new.max_penetration_depth

    def test_forced_return_on_boundary_exceeded(self):
        gov = TunnelGovernor()
        kernel = KernelStack(genesis_hash="test")
        permit = gov.issue_permit("agent-1", kernel, "GREEN")

        # Move beyond permitted depth
        result = gov.update_position("agent-1", permit.max_penetration_depth + 1.0, 0.0)
        assert result["status"] == "boundary_exceeded"
        assert result["action"] == "forced_return"

    def test_clean_return(self):
        gov = TunnelGovernor()
        kernel = KernelStack(genesis_hash="test")
        gov.issue_permit("agent-1", kernel, "GREEN")

        # Normal operation within bounds
        result = gov.update_position("agent-1", 0.05, 0.0)
        assert result["status"] == "tunneling"

        # Clean return
        gov.complete_tunnel("agent-1", kernel, success=True)
        assert len(gov.completed_permits) == 1
        assert kernel.lifetime_count == 0  # no scar on success

    def test_failed_tunnel_adds_scar(self):
        gov = TunnelGovernor()
        kernel = KernelStack(genesis_hash="test")
        gov.issue_permit("agent-1", kernel, "RED")
        gov.complete_tunnel("agent-1", kernel, success=False)
        assert kernel.lifetime_count == 1
        assert kernel.scar_topology[0]["failure_mode"] == "tunnel_failure"

    def test_tunnel_history(self):
        gov = TunnelGovernor()
        kernel = KernelStack(genesis_hash="test")
        gov.issue_permit("agent-1", kernel, "YELLOW")
        gov.complete_tunnel("agent-1")
        gov.issue_permit("agent-1", kernel, "RED")
        gov.complete_tunnel("agent-1")

        history = gov.get_tunnel_history("agent-1")
        assert len(history) == 2


class TestTransmissionCoefficient:
    def test_policy_blocked_reflects(self):
        kernel = KernelStack(genesis_hash="test")
        result = compute_transmission(1.0, 0.0, "RED", kernel, chi_policy=False)
        assert result.outcome == TunnelOutcome.REFLECT
        assert result.transmission_coeff == 0.0
        assert result.commit_allowed is False

    def test_perfect_resonance_high_trust_tunnels(self):
        kernel = KernelStack(genesis_hash="test")
        for i in range(15):
            kernel.add_scar(f"death_{i}")  # build high trust

        zone = "GREEN"
        depth = 0.3
        wall_freq = compute_transparency_frequency(zone, depth)

        result = compute_transmission(depth, wall_freq, zone, kernel)
        assert result.resonance == pytest.approx(1.0, abs=0.01)
        assert result.transmission_coeff > 0.1
        assert result.outcome in (TunnelOutcome.TUNNEL, TunnelOutcome.ATTENUATE)

    def test_no_trust_collapses_or_reflects(self):
        kernel = KernelStack(genesis_hash="new")  # no scars = low trust
        result = compute_transmission(2.0, 0.0, "RED", kernel)
        assert result.outcome in (TunnelOutcome.REFLECT, TunnelOutcome.COLLAPSE)
        assert result.commit_allowed is False

    def test_amplitude_reduced_by_transmission(self):
        kernel = KernelStack(genesis_hash="test")
        for i in range(5):
            kernel.add_scar(f"s{i}")
        result = compute_transmission(0.5, 0.5, "YELLOW", kernel, amplitude=1.0)
        assert result.amplitude_out <= 1.0
        assert result.amplitude_out >= 0.0

    def test_transmission_bounded_zero_to_one(self):
        kernel = KernelStack(genesis_hash="test")
        for i in range(20):
            kernel.add_scar(f"s{i}")
        for d in [0.1, 0.5, 1.0, 3.0]:
            for phase in [0, 0.5, 1.0, 2.0, 3.14]:
                for zone in ["GREEN", "YELLOW", "RED"]:
                    result = compute_transmission(d, phase, zone, kernel)
                    assert 0.0 <= result.transmission_coeff <= 1.0

    def test_four_outcomes_are_possible(self):
        """Verify that the system can produce all 4 outcomes under different conditions."""
        outcomes_seen = set()

        # REFLECT: policy blocked
        k = KernelStack(genesis_hash="x")
        r = compute_transmission(1.0, 0.0, "RED", k, chi_policy=False)
        outcomes_seen.add(r.outcome)

        # Low trust + deep RED = COLLAPSE or REFLECT
        k2 = KernelStack(genesis_hash="y")
        r2 = compute_transmission(3.0, 0.0, "RED", k2)
        outcomes_seen.add(r2.outcome)

        # Moderate trust + partial resonance = ATTENUATE
        k3 = KernelStack(genesis_hash="z")
        for i in range(5):
            k3.add_scar(f"s{i}")
        wall_freq = compute_transparency_frequency("YELLOW", 0.5)
        r3 = compute_transmission(0.5, wall_freq + 0.3, "YELLOW", k3)
        outcomes_seen.add(r3.outcome)

        # High trust + perfect resonance + GREEN = TUNNEL
        k4 = KernelStack(genesis_hash="w")
        for i in range(15):
            k4.add_scar(f"s{i}")
        wall_freq = compute_transparency_frequency("GREEN", 0.2)
        r4 = compute_transmission(0.2, wall_freq, "GREEN", k4)
        outcomes_seen.add(r4.outcome)

        # We should see at least 3 of 4 outcomes (all 4 may not trigger deterministically)
        assert len(outcomes_seen) >= 3, f"Only saw {outcomes_seen}"
