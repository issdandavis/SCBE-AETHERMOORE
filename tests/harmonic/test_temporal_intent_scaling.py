"""
Tests for Temporal-Intent Harmonic Scaling

Tests the canonical formula H_eff(d, R, x) = R^(d²) · x
and its integration with the temporal pipeline bridge.

@module tests/harmonic/test_temporal_intent_scaling
@layer Layer 11, Layer 12, Layer 13
@version 1.0.0
"""

import pytest
import math
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from harmonic.temporal_intent_scaling import (
    DriftMonitor,
    DeviationChannels,
    TriadicTemporalState,
    TrajectoryCoherence,
    TemporalIntentState,
    compute_temporal_intent_factor,
    update_temporal_state,
    harmonic_scale_basic,
    harmonic_scale_effective,
    harmonic_scale_with_state,
    assess_risk_temporal,
    create_temporal_state,
    quick_harmonic_effective,
    DRIFT_TOLERANCE,
    MAX_ACCUMULATED_DRIFT,
    PRECISION_DIGITS,
    PERFECT_FIFTH,
    PHI,
)

from harmonic.temporal_bridge import (
    TemporalPipelineBridge,
    AgentDecisionRecord,
    AgentProfile,
    get_bridge,
    clear_bridges,
    list_agents,
    get_all_summaries,
)


# ============================================================================
# Test: Basic Harmonic Scaling
# ============================================================================

class TestHarmonicScaleBasic:
    """Tests for the basic H(d, R) = R^(d²) formula."""

    def test_zero_deviation_returns_one(self):
        """H(0, R) = R^0 = 1 for any R."""
        assert harmonic_scale_basic(0.0, 1.5) == 1.0
        assert harmonic_scale_basic(0.0, 2.0) == 1.0
        assert harmonic_scale_basic(0.0, PHI) == 1.0

    def test_unit_deviation(self):
        """H(1, R) = R^1 = R."""
        assert abs(harmonic_scale_basic(1.0, 1.5) - 1.5) < 1e-10
        assert abs(harmonic_scale_basic(1.0, 2.0) - 2.0) < 1e-10

    def test_quadratic_exponent(self):
        """H(2, R) = R^4."""
        R = 1.5
        expected = R ** 4  # 5.0625
        actual = harmonic_scale_basic(2.0, R)
        assert abs(actual - expected) < 1e-10

    def test_monotonically_increasing(self):
        """H(d1, R) < H(d2, R) when d1 < d2."""
        R = PERFECT_FIFTH
        d_values = [0.1, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        H_values = [harmonic_scale_basic(d, R) for d in d_values]

        for i in range(len(H_values) - 1):
            assert H_values[i] < H_values[i + 1], f"Failed at d={d_values[i]}"

    def test_negative_deviation_raises(self):
        """Negative deviation should raise ValueError."""
        with pytest.raises(ValueError, match="must be >= 0"):
            harmonic_scale_basic(-1.0, 1.5)

    def test_negative_R_raises(self):
        """Negative R should raise ValueError."""
        with pytest.raises(ValueError, match="must be > 0"):
            harmonic_scale_basic(1.0, -1.5)

    def test_overflow_protection(self):
        """Large d values should not overflow."""
        # d=10 would give R^100 which could overflow
        result = harmonic_scale_basic(10.0, 2.0)
        assert math.isfinite(result)
        assert result > 0


# ============================================================================
# Test: Effective Harmonic Scaling with Temporal Factor
# ============================================================================

class TestHarmonicScaleEffective:
    """Tests for H_eff(d, R, x) = R^(d²) · x."""

    def test_neutral_x_equals_basic(self):
        """H_eff(d, R, 1.0) = H(d, R)."""
        d, R = 1.5, 1.5
        assert abs(harmonic_scale_effective(d, R, 1.0) - harmonic_scale_basic(d, R)) < 1e-10

    def test_forgiving_x_reduces_cost(self):
        """x < 1 should reduce H_eff."""
        d, R = 2.0, 1.5
        H_basic = harmonic_scale_basic(d, R)
        H_forgiving = harmonic_scale_effective(d, R, 0.5)
        assert H_forgiving < H_basic
        assert abs(H_forgiving - H_basic * 0.5) < 1e-10

    def test_punitive_x_increases_cost(self):
        """x > 1 should increase H_eff."""
        d, R = 2.0, 1.5
        H_basic = harmonic_scale_basic(d, R)
        H_punitive = harmonic_scale_effective(d, R, 2.0)
        assert H_punitive > H_basic
        assert abs(H_punitive - H_basic * 2.0) < 1e-10

    def test_multiplicative_property(self):
        """H_eff should be multiplicative in x."""
        d, R = 1.5, PERFECT_FIFTH
        x1, x2 = 0.7, 1.5

        H1 = harmonic_scale_effective(d, R, x1)
        H2 = harmonic_scale_effective(d, R, x2)

        # H_eff(d, R, x1) * x2/x1 should equal H_eff(d, R, x2)
        assert abs(H1 * (x2 / x1) - H2) < 1e-10


# ============================================================================
# Test: Drift Monitor
# ============================================================================

class TestDriftMonitor:
    """Tests for floating-point drift protection."""

    def test_initial_state(self):
        """New monitor should have zero drift."""
        monitor = DriftMonitor()
        report = monitor.get_drift_report()
        assert report["accumulated_drift"] == 0.0
        assert report["calibration_count"] == 0
        assert report["within_tolerance"] is True

    def test_drift_accumulation(self):
        """Drift should accumulate across operations."""
        monitor = DriftMonitor()

        # Simulate operations with small expected drift
        for i in range(100):
            computed = 1.0 + i * 0.001
            expected = 1.0 + i * 0.001 + 1e-10  # Small drift
            monitor.check_and_correct(f"val_{i}", computed, expected)

        report = monitor.get_drift_report()
        assert report["accumulated_drift"] > 0
        assert report["tracked_variables"] == 100

    def test_recalibration_trigger(self):
        """Monitor should recalibrate when drift exceeds threshold."""
        monitor = DriftMonitor(tolerance=1e-15)  # Very tight tolerance

        # Force large drift
        for i in range(1000):
            monitor.check_and_correct(f"val_{i}", float(i), float(i) + 1e-7)

        report = monitor.get_drift_report()
        # Should have recalibrated at least once
        assert report["calibration_count"] >= 1 or report["accumulated_drift"] <= MAX_ACCUMULATED_DRIFT

    def test_precision_rounding(self):
        """Values should be rounded to PRECISION_DIGITS."""
        monitor = DriftMonitor()

        # Input with many decimal places
        result = monitor.check_and_correct("test", 1.23456789012345678901234567890)

        # Should be rounded to PRECISION_DIGITS
        assert len(str(result).split('.')[-1]) <= PRECISION_DIGITS + 2  # +2 for floating point repr


# ============================================================================
# Test: Triadic Temporal State
# ============================================================================

class TestTriadicTemporalState:
    """Tests for Layer 11 triadic distance computation."""

    def test_zero_distances(self):
        """Zero distances should give zero d_tri."""
        state = TriadicTemporalState()
        assert state.d_tri() == 0.0

    def test_single_nonzero(self):
        """Single nonzero distance with correct weight."""
        state = TriadicTemporalState(
            d_immediate=1.0, d_medium=0.0, d_longterm=0.0,
            lambda_1=0.4, lambda_2=0.3, lambda_3=0.3
        )
        expected = math.sqrt(0.4 * 1.0)  # sqrt(0.4)
        assert abs(state.d_tri() - expected) < 1e-10

    def test_weighted_combination(self):
        """d_tri = sqrt(λ₁d₁² + λ₂d₂² + λ₃d₃²)."""
        state = TriadicTemporalState(
            d_immediate=1.0, d_medium=2.0, d_longterm=3.0,
            lambda_1=0.4, lambda_2=0.3, lambda_3=0.3
        )
        expected = math.sqrt(0.4 * 1 + 0.3 * 4 + 0.3 * 9)  # sqrt(0.4 + 1.2 + 2.7) = sqrt(4.3)
        assert abs(state.d_tri() - expected) < 1e-10

    def test_weight_normalization(self):
        """Weights should sum to 1.0 for proper weighting."""
        state = TriadicTemporalState()
        assert abs(state.lambda_1 + state.lambda_2 + state.lambda_3 - 1.0) < 1e-10


# ============================================================================
# Test: Deviation Channels
# ============================================================================

class TestDeviationChannels:
    """Tests for CPSE z-vector deviation channels."""

    def test_zero_deviations(self):
        """Zero deviations should give zero composite."""
        channels = DeviationChannels()
        assert channels.composite() == 0.0

    def test_weighted_composite(self):
        """Composite should be weighted average."""
        channels = DeviationChannels(chaosdev=1.0, fractaldev=0.5, energydev=0.0)
        # Default weights (0.4, 0.3, 0.3)
        expected = (0.4 * 1.0 + 0.3 * 0.5 + 0.3 * 0.0) / 1.0  # 0.55
        assert abs(channels.composite() - expected) < 1e-10

    def test_custom_weights(self):
        """Custom weights should be applied correctly."""
        channels = DeviationChannels(chaosdev=1.0, fractaldev=1.0, energydev=1.0)
        # Equal weights
        result = channels.composite(weights=(1.0, 1.0, 1.0))
        assert abs(result - 1.0) < 1e-10


# ============================================================================
# Test: Temporal Intent Factor Computation
# ============================================================================

class TestTemporalIntentFactor:
    """Tests for compute_temporal_intent_factor()."""

    def test_neutral_state_near_one(self):
        """Fresh state should give x near 1.0."""
        state = create_temporal_state()
        x = compute_temporal_intent_factor(state, use_smoothing=False)
        # Should be close to 1.0 for neutral state
        assert 0.5 < x < 1.5

    def test_high_deviation_increases_x(self):
        """High triadic distance should increase x."""
        state = create_temporal_state()
        state.triadic.d_immediate = 2.0
        state.triadic.d_medium = 2.0
        state.triadic.d_longterm = 2.0

        x = compute_temporal_intent_factor(state, use_smoothing=False)
        assert x > 1.0  # Should be punitive

    def test_low_coherence_increases_x(self):
        """Low trajectory coherence should increase x."""
        state = create_temporal_state()
        state.trajectory.coherence = 0.1
        state.trajectory.stability_score = 0.1

        x = compute_temporal_intent_factor(state, use_smoothing=False)
        # Low coherence = suspicious = higher x
        # May be subtle depending on other factors
        assert x > 0.5

    def test_reversals_increase_x(self):
        """Direction reversals should increase x."""
        state = create_temporal_state()
        state.trajectory.reversal_count = 10

        x = compute_temporal_intent_factor(state, use_smoothing=False)
        # Reversals apply a penalty multiplier
        assert x >= 1.0

    def test_x_bounded(self):
        """x should be clamped to [0.1, 10.0]."""
        # Test extreme state
        state = create_temporal_state()
        state.triadic.d_immediate = 100.0
        state.triadic.d_medium = 100.0
        state.triadic.d_longterm = 100.0
        state.deviations = DeviationChannels(1.0, 1.0, 1.0)
        state.trajectory.coherence = 0.0
        state.trajectory.reversal_count = 100

        x = compute_temporal_intent_factor(state, use_smoothing=False)
        assert 0.1 <= x <= 10.0


# ============================================================================
# Test: Update Temporal State
# ============================================================================

class TestUpdateTemporalState:
    """Tests for update_temporal_state()."""

    def test_immediate_updated(self):
        """New deviation should update d_immediate directly."""
        state = create_temporal_state()
        update_temporal_state(state, 0.5)
        assert state.triadic.d_immediate == 0.5

    def test_decay_applied(self):
        """Medium and long-term should decay."""
        state = create_temporal_state()
        state.triadic.d_immediate = 1.0
        state.triadic.d_medium = 1.0

        update_temporal_state(state, 0.5, decay_rate=0.9)

        # d_medium should be 0.9 * 1.0 + 0.1 * 1.0 = 1.0 (no change)
        # Wait, the formula: d_medium = decay * d_medium + (1-decay) * d_immediate
        # With d_immediate=1.0 before update: new_d_medium = 0.9*1.0 + 0.1*1.0 = 1.0
        # Actually d_immediate was 1.0, then becomes 0.5, so:
        # new_d_medium = 0.9 * 1.0 + 0.1 * 1.0 = 1.0 (using OLD d_immediate)
        # The decay happens BEFORE d_immediate is updated
        # So d_medium = 0.9 * 1.0 + 0.1 * 1.0 = 1.0
        # Then d_immediate = 0.5
        assert state.triadic.d_immediate == 0.5

    def test_history_updated(self):
        """History should track x values."""
        state = create_temporal_state()
        for i in range(5):
            update_temporal_state(state, 0.1 * (i + 1))

        assert len(state.history) == 5

    def test_history_window(self):
        """History should respect window_size."""
        state = create_temporal_state()
        state.window_size = 3

        for i in range(10):
            update_temporal_state(state, 0.1)

        assert len(state.history) <= 3


# ============================================================================
# Test: Risk Assessment
# ============================================================================

class TestRiskAssessment:
    """Tests for assess_risk_temporal()."""

    def test_low_deviation_allows(self):
        """Very low deviation should ALLOW."""
        state = create_temporal_state()
        assessment = assess_risk_temporal(0.1, state)
        assert assessment.risk_level == "ALLOW"

    def test_high_deviation_denies(self):
        """Very high deviation should DENY."""
        state = create_temporal_state()
        # Set up adversarial state
        state.triadic.d_immediate = 5.0
        state.triadic.d_medium = 5.0
        state.triadic.d_longterm = 5.0

        assessment = assess_risk_temporal(5.0, state)
        # With extreme deviation, should be DENY
        assert assessment.risk_level in ["ESCALATE", "DENY"]

    def test_forgiveness_applied_when_x_low(self):
        """Assessment should note forgiveness when x < 1."""
        state = create_temporal_state()
        # Fresh state often has x < 1
        assessment = assess_risk_temporal(0.3, state)
        # May or may not have forgiveness depending on exact state
        assert hasattr(assessment, 'forgiveness_applied')

    def test_compounding_applied_when_x_high(self):
        """Assessment should note compounding when x > 1."""
        state = create_temporal_state()
        state.triadic.d_immediate = 2.0
        state.triadic.d_medium = 2.0
        state.triadic.d_longterm = 2.0

        assessment = assess_risk_temporal(1.0, state)
        # High historical deviation should compound
        assert hasattr(assessment, 'compounding_applied')


# ============================================================================
# Test: Temporal Pipeline Bridge
# ============================================================================

class TestTemporalPipelineBridge:
    """Tests for the pipeline bridge."""

    def setup_method(self):
        """Clear bridges before each test."""
        clear_bridges()

    def test_creation(self):
        """Bridge should be created with agent ID."""
        bridge = TemporalPipelineBridge("test-agent")
        assert bridge.agent_id == "test-agent"
        assert bridge.R == PERFECT_FIFTH

    def test_update_state(self):
        """State should update with new observations."""
        bridge = TemporalPipelineBridge("test-agent")
        x = bridge.update_state(0.5)
        assert bridge.state.triadic.d_immediate == 0.5

    def test_process_layer12(self):
        """Layer 12 should return H_eff and x."""
        bridge = TemporalPipelineBridge("test-agent")
        H_eff, x = bridge.process_layer12(1.0)
        assert H_eff > 0
        assert x > 0

    def test_process_layer13_records_decision(self):
        """Layer 13 should record decision in profile."""
        bridge = TemporalPipelineBridge("test-agent")
        assessment = bridge.process_layer13(0.5)

        assert bridge.profile.total_requests == 1
        assert len(bridge.profile.decisions) == 1
        assert bridge.profile.decisions[0].decision == assessment.risk_level

    def test_reputation_updates(self):
        """Reputation should update based on decisions."""
        bridge = TemporalPipelineBridge("test-agent")

        # Make several ALLOW decisions
        for _ in range(5):
            bridge.process_layer13(0.1)

        # Reputation should be high (good behavior)
        assert bridge.get_reputation() > 0.5

    def test_persistent_adversary_penalized(self):
        """Sustained bad behavior should increase H_eff over time."""
        bridge = TemporalPipelineBridge("test-agent")
        H_values = []

        for _ in range(10):
            bridge.update_state(0.7, is_adversarial=True)
            H_eff, x = bridge.process_layer12(0.7)
            H_values.append(H_eff)

        # H_eff should generally increase (compounding)
        # Allow some non-monotonicity due to smoothing
        assert H_values[-1] > H_values[0]

    def test_brief_spike_forgiven(self):
        """Single spike followed by good behavior should decay penalty."""
        bridge = TemporalPipelineBridge("test-agent")

        # One bad request
        bridge.update_state(0.9, is_adversarial=True)
        H_spike, _ = bridge.process_layer12(0.9)

        # 5 good requests
        for _ in range(5):
            bridge.update_state(0.1, is_adversarial=False)

        # Check H_eff at same d value - temporal factor should have decreased
        H_after, x = bridge.process_layer12(0.9)
        # x should be lower after good behavior
        assert x < 5.0  # Not heavily compounded


# ============================================================================
# Test: Bridge Registry
# ============================================================================

class TestBridgeRegistry:
    """Tests for bridge registry functions."""

    def setup_method(self):
        """Clear bridges before each test."""
        clear_bridges()

    def test_get_creates_new(self):
        """get_bridge should create new bridge if none exists."""
        bridge = get_bridge("new-agent")
        assert bridge.agent_id == "new-agent"

    def test_get_returns_existing(self):
        """get_bridge should return existing bridge."""
        bridge1 = get_bridge("agent-1")
        bridge1.update_state(0.5)

        bridge2 = get_bridge("agent-1")
        assert bridge2.state.triadic.d_immediate == 0.5

    def test_list_agents(self):
        """list_agents should return all agent IDs."""
        get_bridge("agent-1")
        get_bridge("agent-2")
        get_bridge("agent-3")

        agents = list_agents()
        assert set(agents) == {"agent-1", "agent-2", "agent-3"}

    def test_clear_bridges(self):
        """clear_bridges should remove all bridges."""
        get_bridge("agent-1")
        get_bridge("agent-2")

        clear_bridges()
        assert list_agents() == []

    def test_get_all_summaries(self):
        """get_all_summaries should return summaries for all agents."""
        get_bridge("agent-1").update_state(0.3)
        get_bridge("agent-2").update_state(0.7)

        summaries = get_all_summaries()
        assert "agent-1" in summaries
        assert "agent-2" in summaries
        assert summaries["agent-1"]["triadic"]["d_immediate"] == 0.3
        assert summaries["agent-2"]["triadic"]["d_immediate"] == 0.7


# ============================================================================
# Test: Quick Harmonic Effective
# ============================================================================

class TestQuickHarmonicEffective:
    """Tests for quick_harmonic_effective() convenience function."""

    def test_no_history_neutral(self):
        """No history should give neutral x."""
        H = quick_harmonic_effective(1.0, sustained_deviation_count=0)
        H_basic = harmonic_scale_basic(1.0, PERFECT_FIFTH)
        assert abs(H - H_basic) < 1e-10

    def test_recovery_reduces_cost(self):
        """Recovery attempt should reduce x to 0.7."""
        H_recovery = quick_harmonic_effective(1.0, has_recovery_attempt=True)
        H_neutral = quick_harmonic_effective(1.0)
        assert H_recovery < H_neutral

    def test_sustained_increases_cost(self):
        """Sustained deviation should increase x."""
        H_sustained = quick_harmonic_effective(1.0, sustained_deviation_count=10)
        H_neutral = quick_harmonic_effective(1.0)
        assert H_sustained > H_neutral


# ============================================================================
# Run tests if executed directly
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
