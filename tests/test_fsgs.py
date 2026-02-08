"""
Tests for Four-State Governance Symbol (FSGS) Hybrid Dynamical System
======================================================================

Tests the 4-symbol control alphabet {+1, -1, +0, -0}, hybrid automaton
mode transitions, trust tube projection, and control sequence analysis.

@layer Layer 12, Layer 13
@tier L2-unit, L3-integration
"""

import math

import numpy as np
import pytest

from symphonic_cipher.scbe_aethermoore.ai_brain.unified_state import (
    BRAIN_DIMENSIONS,
    UnifiedBrainState,
)
from symphonic_cipher.scbe_aethermoore.ai_brain.fsgs import (
    GovernanceSymbol,
    GovernanceMode,
    HybridState,
    StepResult,
    symbol_from_bits,
    mode_transition,
    default_direction_field,
    poincare_gain,
    tube_project,
    hybrid_step,
    verdict_to_symbol,
    analyze_control_sequence,
    simulate_trajectory,
    ControlSequenceStats,
    TrajectorySimulation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_valid_state(seed: int = 0) -> np.ndarray:
    """Create a valid 21D brain state vector with safe Poincaré radius."""
    rng = np.random.default_rng(seed)
    x = np.zeros(BRAIN_DIMENSIONS)
    x[0:6] = rng.random(6) * 0.6 + 0.2
    x[6:9] = rng.normal(0, 0.05, 3)
    x[9] = rng.random() * 0.3
    x[10:12] = rng.random(2) * 0.5 + 0.2
    x[12:15] = rng.normal(0, 0.02, 3)
    x[15] = float(rng.integers(0, 2))
    x[16] = rng.random() * 0.5
    x[17] = 0.3 + rng.random() * 0.3
    x[18] = rng.random() * 0.5 + 0.2
    x[19] = 0.0
    x[20] = rng.random() * 0.5 + 0.2
    return x


def make_safe_origin() -> np.ndarray:
    return np.array(UnifiedBrainState.safe_origin().to_vector())


def make_hybrid_state(seed: int = 0) -> HybridState:
    return HybridState(x=make_valid_state(seed), q=GovernanceMode.RUN, step=0)


# ---------------------------------------------------------------------------
# Tests: 4-symbol algebra
# ---------------------------------------------------------------------------

class TestGovernanceSymbol:
    """Tests for the 4-state governance symbol {+1, -1, +0, -0}."""

    def test_four_symbols_exist(self):
        """All 4 symbols are distinct."""
        symbols = list(GovernanceSymbol)
        assert len(symbols) == 4

    def test_plus_one_properties(self):
        """(+1) has impulse, positive sign."""
        s = GovernanceSymbol.PLUS_ONE
        assert s.magnitude == 1
        assert s.sign_bit == 1
        assert s.sign == 1.0
        assert s.has_impulse
        assert s.is_positive

    def test_minus_one_properties(self):
        """(-1) has impulse, negative sign."""
        s = GovernanceSymbol.MINUS_ONE
        assert s.magnitude == 1
        assert s.sign_bit == 0
        assert s.sign == -1.0
        assert s.has_impulse
        assert not s.is_positive

    def test_plus_zero_properties(self):
        """(+0) has no impulse, positive posture."""
        s = GovernanceSymbol.PLUS_ZERO
        assert s.magnitude == 0
        assert s.sign_bit == 1
        assert s.sign == 1.0
        assert not s.has_impulse
        assert s.is_positive

    def test_minus_zero_properties(self):
        """(-0) has no impulse, negative posture (hold/quarantine)."""
        s = GovernanceSymbol.MINUS_ZERO
        assert s.magnitude == 0
        assert s.sign_bit == 0
        assert s.sign == -1.0
        assert not s.has_impulse
        assert not s.is_positive

    def test_symbol_from_bits(self):
        """symbol_from_bits correctly constructs symbols."""
        assert symbol_from_bits(1, 1) == GovernanceSymbol.PLUS_ONE
        assert symbol_from_bits(1, 0) == GovernanceSymbol.MINUS_ONE
        assert symbol_from_bits(0, 1) == GovernanceSymbol.PLUS_ZERO
        assert symbol_from_bits(0, 0) == GovernanceSymbol.MINUS_ZERO

    def test_repr_readable(self):
        """Symbols have human-readable repr."""
        assert "+1" in repr(GovernanceSymbol.PLUS_ONE)
        assert "-0" in repr(GovernanceSymbol.MINUS_ZERO)


# ---------------------------------------------------------------------------
# Tests: Governance modes
# ---------------------------------------------------------------------------

class TestGovernanceMode:
    """Tests for the 4-mode discrete automaton."""

    def test_four_modes_exist(self):
        """All 4 governance modes exist."""
        modes = list(GovernanceMode)
        assert len(modes) == 4
        assert set(m.value for m in modes) == {"RUN", "HOLD", "QUAR", "ROLLBACK"}


# ---------------------------------------------------------------------------
# Tests: Mode transitions δ(q, σ, x)
# ---------------------------------------------------------------------------

class TestModeTransition:
    """Tests for the mode transition function."""

    def test_plus_one_goes_to_run(self):
        """(+1) always transitions to RUN."""
        x = make_valid_state()
        for q in GovernanceMode:
            assert mode_transition(q, GovernanceSymbol.PLUS_ONE, x) == GovernanceMode.RUN

    def test_minus_one_goes_to_rollback(self):
        """(-1) always transitions to ROLLBACK."""
        x = make_valid_state()
        for q in GovernanceMode:
            assert mode_transition(q, GovernanceSymbol.MINUS_ONE, x) == GovernanceMode.ROLLBACK

    def test_plus_zero_stays_in_mode(self):
        """(+0) stays in current mode (except ROLLBACK → RUN)."""
        x = make_valid_state()
        assert mode_transition(GovernanceMode.RUN, GovernanceSymbol.PLUS_ZERO, x) == GovernanceMode.RUN
        assert mode_transition(GovernanceMode.HOLD, GovernanceSymbol.PLUS_ZERO, x) == GovernanceMode.HOLD
        assert mode_transition(GovernanceMode.QUAR, GovernanceSymbol.PLUS_ZERO, x) == GovernanceMode.QUAR
        # ROLLBACK + (+0) → RUN (exit rollback on idle-continue)
        assert mode_transition(GovernanceMode.ROLLBACK, GovernanceSymbol.PLUS_ZERO, x) == GovernanceMode.RUN

    def test_minus_zero_low_risk_hold(self):
        """(-0) with low risk → HOLD."""
        x = make_valid_state()
        result = mode_transition(GovernanceMode.RUN, GovernanceSymbol.MINUS_ZERO, x, risk_score=0.3)
        assert result == GovernanceMode.HOLD

    def test_minus_zero_high_risk_quar(self):
        """(-0) with high risk → QUAR."""
        x = make_valid_state()
        result = mode_transition(GovernanceMode.RUN, GovernanceSymbol.MINUS_ZERO, x, risk_score=0.7)
        assert result == GovernanceMode.QUAR


# ---------------------------------------------------------------------------
# Tests: Direction field and gain
# ---------------------------------------------------------------------------

class TestDirectionAndGain:
    """Tests for direction field d(x) and gain α(x)."""

    def test_direction_is_unit_vector(self):
        """Default direction field returns a unit vector."""
        x = make_valid_state(0)
        d = default_direction_field(x)
        norm = np.linalg.norm(d)
        assert abs(norm - 1.0) < 1e-6 or norm < 1e-10  # zero if at origin

    def test_direction_points_toward_origin(self):
        """Direction field points toward safe origin."""
        x = make_valid_state(0)
        origin = make_safe_origin()
        d = default_direction_field(x)
        # Moving along d should decrease distance to origin
        x_moved = x + 0.01 * d
        assert np.linalg.norm(x_moved - origin) < np.linalg.norm(x - origin)

    def test_direction_zero_at_origin(self):
        """At the safe origin, direction field is zero."""
        origin = make_safe_origin()
        d = default_direction_field(origin)
        assert np.linalg.norm(d) < 1e-10

    def test_gain_positive(self):
        """Gain function returns positive value."""
        x = make_valid_state(0)
        alpha = poincare_gain(x)
        assert alpha > 0

    def test_gain_decreases_near_boundary(self):
        """Gain decreases as state approaches Poincaré boundary."""
        x_near = make_valid_state(0)
        x_far = x_near.copy()
        # Push state further from origin to increase Poincaré radius
        x_far *= 2.0
        alpha_near = poincare_gain(x_near)
        alpha_far = poincare_gain(x_far)
        # Further from origin → closer to boundary → smaller gain
        assert alpha_far < alpha_near


# ---------------------------------------------------------------------------
# Tests: Trust tube projection
# ---------------------------------------------------------------------------

class TestTubeProject:
    """Tests for trust tube projection Π_T."""

    def test_valid_state_unchanged(self):
        """Valid state inside tube should pass through with minimal change."""
        x = make_valid_state(0)
        x_proj, result = tube_project(x)
        # Should be close to original (only minor corrections)
        assert np.linalg.norm(x_proj - x) < 1.0

    def test_out_of_bounds_clamped(self):
        """Out-of-bounds state gets projected back into tube."""
        x = make_valid_state(0)
        x[0] = 5.0  # device_trust way out of [0, 1]
        x_proj, result = tube_project(x)
        assert 0.0 <= x_proj[0] <= 1.0
        assert result.corrections_applied > 0


# ---------------------------------------------------------------------------
# Tests: Hybrid step
# ---------------------------------------------------------------------------

class TestHybridStep:
    """Tests for the core hybrid step function."""

    def test_plus_one_moves_state(self):
        """(+1) forward impulse changes the continuous state."""
        state = make_hybrid_state(0)
        x_before = state.x.copy()
        result = hybrid_step(state, GovernanceSymbol.PLUS_ONE, base_alpha=0.1)
        # State should have changed (impulse applied)
        assert not np.allclose(result.state.x, x_before, atol=1e-8)
        assert result.state.q == GovernanceMode.RUN
        assert result.impulse_magnitude > 0
        assert result.state.step == 1

    def test_minus_one_moves_state(self):
        """(-1) reverse impulse changes state in opposite direction."""
        state = make_hybrid_state(0)
        result = hybrid_step(state, GovernanceSymbol.MINUS_ONE, base_alpha=0.1)
        assert result.state.q == GovernanceMode.ROLLBACK
        assert result.impulse_magnitude > 0

    def test_plus_zero_no_movement(self):
        """(+0) doesn't move the continuous state (no impulse)."""
        state = make_hybrid_state(0)
        x_before = state.x.copy()
        result = hybrid_step(state, GovernanceSymbol.PLUS_ZERO, base_alpha=0.1)
        # m=0 so impulse_magnitude should be 0
        assert result.impulse_magnitude == 0.0
        # Mode stays (RUN → RUN)
        assert result.state.q == GovernanceMode.RUN

    def test_minus_zero_no_movement_but_reanchors(self):
        """(-0) doesn't move state but triggers re-anchoring."""
        state = make_hybrid_state(0)
        result = hybrid_step(
            state, GovernanceSymbol.MINUS_ZERO,
            base_alpha=0.1, risk_score=0.3,
        )
        assert result.impulse_magnitude == 0.0
        assert result.re_anchored
        # Mode transitions to HOLD (risk < 0.5)
        assert result.state.q == GovernanceMode.HOLD

    def test_minus_zero_high_risk_quarantines(self):
        """(-0) with high risk transitions to QUAR mode."""
        state = make_hybrid_state(0)
        result = hybrid_step(
            state, GovernanceSymbol.MINUS_ZERO,
            base_alpha=0.1, risk_score=0.8,
        )
        assert result.state.q == GovernanceMode.QUAR
        assert result.re_anchored

    def test_step_increments(self):
        """Each hybrid step increments the step counter."""
        state = make_hybrid_state(0)
        r1 = hybrid_step(state, GovernanceSymbol.PLUS_ONE)
        r2 = hybrid_step(r1.state, GovernanceSymbol.PLUS_ONE)
        assert r1.state.step == 1
        assert r2.state.step == 2

    def test_opposite_symbols_diverge(self):
        """(+1) and (-1) produce different states."""
        state = make_hybrid_state(0)
        r_plus = hybrid_step(state, GovernanceSymbol.PLUS_ONE, base_alpha=0.1)
        r_minus = hybrid_step(state, GovernanceSymbol.MINUS_ONE, base_alpha=0.1)
        assert not np.allclose(r_plus.state.x, r_minus.state.x, atol=1e-6)


# ---------------------------------------------------------------------------
# Tests: Verdict → symbol mapping
# ---------------------------------------------------------------------------

class TestVerdictMapping:
    """Tests for mapping L13 governance decisions to FSGS symbols."""

    def test_allow_maps_to_plus_one(self):
        assert verdict_to_symbol("ALLOW") == GovernanceSymbol.PLUS_ONE

    def test_quarantine_maps_to_minus_zero(self):
        assert verdict_to_symbol("QUARANTINE") == GovernanceSymbol.MINUS_ZERO

    def test_escalate_maps_to_minus_zero(self):
        assert verdict_to_symbol("ESCALATE") == GovernanceSymbol.MINUS_ZERO

    def test_deny_maps_to_minus_one(self):
        assert verdict_to_symbol("DENY") == GovernanceSymbol.MINUS_ONE

    def test_unknown_maps_to_plus_zero(self):
        assert verdict_to_symbol("UNKNOWN") == GovernanceSymbol.PLUS_ZERO


# ---------------------------------------------------------------------------
# Tests: Control sequence analysis
# ---------------------------------------------------------------------------

class TestControlSequenceAnalysis:
    """Tests for analyzing control symbol sequences."""

    def test_empty_sequence(self):
        """Empty sequence returns zero stats."""
        stats = analyze_control_sequence([])
        assert stats.length == 0
        assert stats.transition_count == 0
        assert stats.hold_ratio == 0.0
        assert stats.rollback_ratio == 0.0

    def test_all_plus_one(self):
        """All (+1) = pure RUN mode, no transitions."""
        symbols = [GovernanceSymbol.PLUS_ONE] * 10
        stats = analyze_control_sequence(symbols)
        assert stats.symbol_counts["+1"] == 10
        assert stats.symbol_counts["-0"] == 0
        assert stats.transition_count == 0
        assert stats.hold_ratio == 0.0
        assert stats.rollback_ratio == 0.0

    def test_alternating_symbols(self):
        """Alternating +1 and -1 produces high transition rate."""
        symbols = [GovernanceSymbol.PLUS_ONE, GovernanceSymbol.MINUS_ONE] * 5
        stats = analyze_control_sequence(symbols)
        assert stats.symbol_counts["+1"] == 5
        assert stats.symbol_counts["-1"] == 5
        assert stats.transition_count == 9  # every step is a transition
        assert stats.transition_rate > 0.9

    def test_dwell_times_computed(self):
        """Mode dwell times are correctly computed."""
        # 3x RUN, 2x HOLD, 3x RUN
        symbols = (
            [GovernanceSymbol.PLUS_ONE] * 3
            + [GovernanceSymbol.MINUS_ZERO] * 2
            + [GovernanceSymbol.PLUS_ONE] * 3
        )
        stats = analyze_control_sequence(symbols)
        # Should have multiple dwell periods
        total_dwells = sum(len(v) for v in stats.mode_dwell_times.values())
        assert total_dwells >= 2

    def test_hold_ratio_correct(self):
        """Hold ratio reflects time in HOLD/QUAR modes."""
        symbols = (
            [GovernanceSymbol.PLUS_ONE] * 5
            + [GovernanceSymbol.MINUS_ZERO] * 5
        )
        stats = analyze_control_sequence(symbols)
        # Last 5 steps should be in HOLD → hold_ratio = 5/10 = 0.5
        assert stats.hold_ratio == pytest.approx(0.5, abs=0.01)

    def test_rollback_ratio_correct(self):
        """Rollback ratio reflects time in ROLLBACK mode."""
        symbols = (
            [GovernanceSymbol.PLUS_ONE] * 5
            + [GovernanceSymbol.MINUS_ONE] * 5
        )
        stats = analyze_control_sequence(symbols)
        assert stats.rollback_ratio == pytest.approx(0.5, abs=0.01)


# ---------------------------------------------------------------------------
# Tests: Full trajectory simulation
# ---------------------------------------------------------------------------

class TestTrajectorySimulation:
    """Tests for running FSGS over a full trajectory."""

    def test_simulation_length(self):
        """Simulation produces one StepResult per symbol."""
        state = make_hybrid_state(0)
        symbols = [GovernanceSymbol.PLUS_ONE] * 5
        sim = simulate_trajectory(state, symbols)
        assert len(sim.steps) == 5
        assert sim.final_state.step == 5

    def test_simulation_mode_consistency(self):
        """Final state mode matches the last symbol's transition."""
        state = make_hybrid_state(0)
        symbols = [
            GovernanceSymbol.PLUS_ONE,
            GovernanceSymbol.PLUS_ONE,
            GovernanceSymbol.MINUS_ONE,  # last → ROLLBACK
        ]
        sim = simulate_trajectory(state, symbols)
        assert sim.final_state.q == GovernanceMode.ROLLBACK

    def test_simulation_control_stats(self):
        """Simulation produces control sequence statistics."""
        state = make_hybrid_state(0)
        symbols = [GovernanceSymbol.PLUS_ONE] * 3 + [GovernanceSymbol.MINUS_ZERO] * 2
        sim = simulate_trajectory(state, symbols)
        assert sim.control_stats.length == 5
        assert sim.control_stats.symbol_counts["+1"] == 3
        assert sim.control_stats.symbol_counts["-0"] == 2

    def test_run_hold_run_pattern(self):
        """RUN → HOLD → RUN pattern: re-anchoring then recovery."""
        state = make_hybrid_state(0)
        symbols = [
            GovernanceSymbol.PLUS_ONE,   # RUN
            GovernanceSymbol.PLUS_ONE,   # RUN
            GovernanceSymbol.MINUS_ZERO, # HOLD (re-anchor)
            GovernanceSymbol.MINUS_ZERO, # HOLD (re-anchor)
            GovernanceSymbol.PLUS_ONE,   # back to RUN
        ]
        sim = simulate_trajectory(state, symbols)
        modes = [s.state.q for s in sim.steps]
        assert modes[0] == GovernanceMode.RUN
        assert modes[2] == GovernanceMode.HOLD
        assert modes[4] == GovernanceMode.RUN

    def test_deny_sequence_rollback(self):
        """Sequence of (-1) keeps the system in ROLLBACK."""
        state = make_hybrid_state(0)
        symbols = [GovernanceSymbol.MINUS_ONE] * 5
        sim = simulate_trajectory(state, symbols)
        for step in sim.steps:
            assert step.state.q == GovernanceMode.ROLLBACK
        assert sim.control_stats.rollback_ratio == 1.0

    def test_custom_direction_fn(self):
        """Custom direction function is used for impulse."""
        state = make_hybrid_state(0)
        # Custom direction: always push dim 0
        custom_dir = lambda x: np.eye(BRAIN_DIMENSIONS)[0]
        result = hybrid_step(
            state, GovernanceSymbol.PLUS_ONE,
            direction_fn=custom_dir, base_alpha=0.5,
        )
        # Dim 0 should have changed more than others
        diff = result.state.x - state.x
        assert abs(diff[0]) > abs(diff[1])


# ---------------------------------------------------------------------------
# Tests: Integration with governance adapter
# ---------------------------------------------------------------------------

class TestFSGSIntegration:
    """Integration tests connecting FSGS to governance adapter."""

    def test_verdict_to_symbol_to_step(self):
        """Full pipeline: verdict → symbol → hybrid step."""
        state = make_hybrid_state(0)

        # Simulate ALLOW verdict
        sigma = verdict_to_symbol("ALLOW")
        result = hybrid_step(state, sigma)
        assert result.state.q == GovernanceMode.RUN
        assert result.impulse_magnitude > 0

    def test_quarantine_reanchors(self):
        """QUARANTINE verdict → -0 → re-anchor + HOLD mode."""
        state = make_hybrid_state(0)
        sigma = verdict_to_symbol("QUARANTINE")
        result = hybrid_step(state, sigma, risk_score=0.3)
        assert result.re_anchored
        assert result.state.q == GovernanceMode.HOLD

    def test_deny_rollback(self):
        """DENY verdict → -1 → ROLLBACK mode."""
        state = make_hybrid_state(0)
        sigma = verdict_to_symbol("DENY")
        result = hybrid_step(state, sigma)
        assert result.state.q == GovernanceMode.ROLLBACK

    def test_hybrid_state_stays_valid(self):
        """After any sequence of symbols, state remains valid (inside tube)."""
        state = make_hybrid_state(0)
        rng = np.random.default_rng(42)
        all_symbols = list(GovernanceSymbol)
        symbols = [all_symbols[rng.integers(0, 4)] for _ in range(20)]
        sim = simulate_trajectory(state, symbols, base_alpha=0.05)

        # Final state should be inside trust tube bounds
        x_final = sim.final_state.x
        # SCBE trust scores in [0, 1]
        assert all(0.0 <= x_final[i] <= 1.0 for i in range(6))
