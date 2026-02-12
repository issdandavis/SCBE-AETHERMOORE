"""
Tests for PQ Cymatic Governance Adapter
========================================

Tests the 6-state micro-state algebra (chemistry-inspired dual ternary),
persistent asymmetry tracking, flux contraction, and L13 governance decisions.

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
from symphonic_cipher.scbe_aethermoore.ai_brain.governance_adapter import (
    MicroStateType,
    MicroStateCensus,
    census_from_ternary,
    check_valence,
    AsymmetryTracker,
    flux_contract,
    GovernanceVerdict,
    evaluate_governance,
    evaluate_trajectory_governance,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_valid_state(seed: int = 0) -> np.ndarray:
    """Create a valid 21D brain state vector."""
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
    """Create the safe origin vector."""
    return np.array(UnifiedBrainState.safe_origin().to_vector())


def make_asymmetric_state(seed: int = 42) -> np.ndarray:
    """Create a state with high channel asymmetry.

    Pushes only the parallel channel (navigation + cognitive)
    while keeping perpendicular channel near origin.
    """
    x = make_safe_origin()
    rng = np.random.default_rng(seed)
    # Big navigation changes
    x[6:9] = rng.normal(0, 0.3, 3)
    x[12:15] = rng.normal(0, 0.2, 3)
    return x


def make_trajectory(n_steps: int = 50, seed: int = 0) -> np.ndarray:
    """Create a smooth random trajectory."""
    rng = np.random.default_rng(seed)
    base = make_valid_state(seed)
    trajectory = np.zeros((n_steps, BRAIN_DIMENSIONS))
    trajectory[0] = base
    for t in range(1, n_steps):
        noise = rng.normal(0, 0.005, BRAIN_DIMENSIONS)
        trajectory[t] = trajectory[t - 1] + noise
        # Keep SCBE trust scores in bounds
        trajectory[t, 0:6] = np.clip(trajectory[t, 0:6], 0.01, 0.99)
        trajectory[t, 18] = np.clip(trajectory[t, 18], 0.01, 0.99)
        trajectory[t, 20] = np.clip(trajectory[t, 20], 0.01, 0.99)
    return trajectory


# ---------------------------------------------------------------------------
# Tests: MicroStateCensus (6-state particle algebra)
# ---------------------------------------------------------------------------

class TestMicroStateCensus:
    """Tests for the 6-state micro-state census."""

    def test_all_neutral(self):
        """All-neutral census has zero charge everywhere."""
        par = np.zeros(9, dtype=np.int8)
        perp = np.zeros(12, dtype=np.int8)
        census = census_from_ternary(par, perp)
        assert census.par_neutral == 9
        assert census.perp_neutral == 12
        assert census.parallel_charge == 0
        assert census.perp_charge == 0
        assert census.total_charge == 0
        assert census.is_neutral
        assert census.active_count == 0

    def test_balanced_charges(self):
        """Equal activations and inhibitions = neutral atom."""
        par = np.array([1, -1, 0, 1, -1, 0, 0, 0, 0], dtype=np.int8)
        perp = np.array([1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=np.int8)
        census = census_from_ternary(par, perp)
        assert census.parallel_charge == 0
        assert census.perp_charge == 0
        assert census.is_neutral
        assert census.ionization_level == 0.0

    def test_positive_charge(self):
        """All activations = fully ionized."""
        par = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0], dtype=np.int8)
        perp = np.zeros(12, dtype=np.int8)
        census = census_from_ternary(par, perp)
        assert census.parallel_charge == 5
        assert census.total_charge == 5
        assert not census.is_neutral
        assert census.ionization_level == 1.0

    def test_channel_imbalance(self):
        """Charge in only one channel = high imbalance."""
        par = np.array([1, 1, 1, 0, 0, 0, 0, 0, 0], dtype=np.int8)
        perp = np.array([-1, -1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=np.int8)
        census = census_from_ternary(par, perp)
        # par_charge = 3, perp_charge = -3, total = 0 (neutral!)
        assert census.is_neutral
        # But channels are imbalanced: |3 - (-3)| / 6 = 1.0
        assert census.charge_imbalance == 1.0

    def test_to_dict(self):
        """Census serializes to a dict with all 6 keys."""
        par = np.array([1, 0, -1], dtype=np.int8)
        perp = np.array([1, 0, -1, 0], dtype=np.int8)
        census = census_from_ternary(par, perp)
        d = census.to_dict()
        assert set(d.keys()) == {"par+", "par0", "par-", "perp+", "perp0", "perp-"}
        assert d["par+"] == 1
        assert d["par-"] == 1
        assert d["perp0"] == 2

    def test_six_micro_state_types(self):
        """All 6 micro-state types exist in the enum."""
        types = list(MicroStateType)
        assert len(types) == 6
        values = {t.value for t in types}
        assert values == {"par+", "par0", "par-", "perp+", "perp0", "perp-"}


# ---------------------------------------------------------------------------
# Tests: Valence rules
# ---------------------------------------------------------------------------

class TestValenceRules:
    """Tests for chemistry-inspired valence checking."""

    def test_neutral_balanced_passes(self):
        """Neutral balanced census passes all valence rules."""
        census = MicroStateCensus(
            par_activate=2, par_neutral=5, par_inhibit=2,
            perp_activate=3, perp_neutral=6, perp_inhibit=3,
        )
        ok, violations = check_valence(census)
        assert ok
        assert violations == []

    def test_charge_excess_fails(self):
        """Too much net charge triggers charge_excess violation."""
        census = MicroStateCensus(
            par_activate=8, par_neutral=1, par_inhibit=0,
            perp_activate=10, perp_neutral=2, perp_inhibit=0,
        )
        ok, violations = check_valence(census)
        assert not ok
        assert "charge_excess" in violations

    def test_channel_imbalance_fails(self):
        """Extreme channel imbalance triggers violation."""
        census = MicroStateCensus(
            par_activate=5, par_neutral=4, par_inhibit=0,
            perp_activate=0, perp_neutral=12, perp_inhibit=0,
        )
        ok, violations = check_valence(census)
        assert not ok
        assert "channel_imbalance" in violations

    def test_static_fails(self):
        """Zero activity triggers static violation (replay attack)."""
        census = MicroStateCensus(
            par_activate=0, par_neutral=9, par_inhibit=0,
            perp_activate=0, perp_neutral=12, perp_inhibit=0,
        )
        ok, violations = check_valence(census)
        assert not ok
        assert "static" in violations

    def test_overactive_fails(self):
        """Almost all dimensions active triggers overactive violation."""
        census = MicroStateCensus(
            par_activate=5, par_neutral=0, par_inhibit=4,
            perp_activate=6, perp_neutral=0, perp_inhibit=6,
        )
        ok, violations = check_valence(census)
        assert not ok
        assert "overactive" in violations


# ---------------------------------------------------------------------------
# Tests: AsymmetryTracker
# ---------------------------------------------------------------------------

class TestAsymmetryTracker:
    """Tests for sliding-window asymmetry persistence detection."""

    def test_empty_tracker(self):
        """New tracker has zero persistence."""
        tracker = AsymmetryTracker(window_size=5, threshold=0.3)
        assert tracker.persistence_count == 0
        assert tracker.persistence_ratio == 0.0
        assert not tracker.should_contract
        assert tracker.average_asymmetry == 0.0

    def test_below_threshold(self):
        """Readings below threshold don't accumulate persistence."""
        tracker = AsymmetryTracker(window_size=5, threshold=0.3)
        for _ in range(5):
            tracker.record(0.1)
        assert tracker.persistence_count == 0
        assert not tracker.should_contract

    def test_above_threshold_persists(self):
        """Consecutive readings above threshold accumulate."""
        tracker = AsymmetryTracker(window_size=8, threshold=0.3)
        for _ in range(5):
            tracker.record(0.5)
        assert tracker.persistence_count == 5
        assert tracker.should_contract  # >= 3

    def test_broken_persistence(self):
        """A reading below threshold resets the consecutive count."""
        tracker = AsymmetryTracker(window_size=8, threshold=0.3)
        tracker.record(0.5)
        tracker.record(0.5)
        tracker.record(0.1)  # breaks the streak
        tracker.record(0.5)
        assert tracker.persistence_count == 1  # only the last one
        assert not tracker.should_contract

    def test_window_slides(self):
        """Old readings fall off the sliding window."""
        tracker = AsymmetryTracker(window_size=3, threshold=0.3)
        tracker.record(0.5)
        tracker.record(0.5)
        tracker.record(0.5)
        assert tracker.persistence_count == 3
        tracker.record(0.1)  # pushes out oldest 0.5
        assert tracker.persistence_count == 0

    def test_persistence_ratio(self):
        """Ratio counts fraction of window above threshold."""
        tracker = AsymmetryTracker(window_size=4, threshold=0.3)
        tracker.record(0.5)
        tracker.record(0.1)
        tracker.record(0.5)
        tracker.record(0.5)
        assert tracker.persistence_ratio == 0.75

    def test_reset(self):
        """Reset clears the history."""
        tracker = AsymmetryTracker(window_size=5, threshold=0.3)
        for _ in range(5):
            tracker.record(0.8)
        tracker.reset()
        assert tracker.persistence_count == 0
        assert tracker.average_asymmetry == 0.0

    def test_invalid_window_size(self):
        """Window size < 1 raises ValueError."""
        with pytest.raises(ValueError):
            AsymmetryTracker(window_size=0)


# ---------------------------------------------------------------------------
# Tests: Flux contraction
# ---------------------------------------------------------------------------

class TestFluxContraction:
    """Tests for flux contraction toward safe origin."""

    def test_zero_contraction(self):
        """Zero contraction returns the original state."""
        x = make_valid_state(0)
        result = flux_contract(x, contraction_strength=0.0)
        np.testing.assert_allclose(result, x)

    def test_full_contraction(self):
        """Full contraction snaps to safe origin."""
        x = make_valid_state(0)
        origin = make_safe_origin()
        result = flux_contract(x, contraction_strength=1.0)
        np.testing.assert_allclose(result, origin)

    def test_partial_contraction(self):
        """Partial contraction moves toward origin proportionally."""
        x = make_valid_state(0)
        origin = make_safe_origin()
        result = flux_contract(x, contraction_strength=0.5)
        expected = 0.5 * x + 0.5 * origin
        np.testing.assert_allclose(result, expected)

    def test_contraction_reduces_distance(self):
        """Contracted state is closer to safe origin."""
        x = make_valid_state(0)
        origin = make_safe_origin()
        result = flux_contract(x, contraction_strength=0.3)
        d_before = np.linalg.norm(x - origin)
        d_after = np.linalg.norm(result - origin)
        assert d_after < d_before

    def test_contraction_clamped(self):
        """Contraction strength > 1 is clamped to 1."""
        x = make_valid_state(0)
        origin = make_safe_origin()
        result = flux_contract(x, contraction_strength=2.0)
        np.testing.assert_allclose(result, origin)


# ---------------------------------------------------------------------------
# Tests: Governance decisions (ALLOW / QUARANTINE / ESCALATE / DENY)
# ---------------------------------------------------------------------------

class TestGovernanceDecisions:
    """Tests for L13 risk decision logic."""

    def test_safe_state_allow(self):
        """Two similar valid states should produce ALLOW."""
        x_prev = make_valid_state(0)
        x_curr = make_valid_state(0)
        # Tiny perturbation
        x_curr = x_curr + np.random.default_rng(1).normal(0, 0.001, BRAIN_DIMENSIONS)
        verdict = evaluate_governance(x_curr, x_prev, align=True)
        assert verdict.decision == "ALLOW"
        assert verdict.combined_score < 0.3

    def test_first_observation_allow(self):
        """First observation (no x_prev) defaults to ALLOW."""
        x = make_valid_state(0)
        verdict = evaluate_governance(x, x_prev=None, align=True)
        assert verdict.decision == "ALLOW"
        assert verdict.micro_census.active_count == 0  # all neutral

    def test_verdict_has_all_fields(self):
        """GovernanceVerdict contains all expected diagnostic fields."""
        x = make_valid_state(0)
        verdict = evaluate_governance(x, x_prev=None)
        assert hasattr(verdict, "decision")
        assert hasattr(verdict, "mirror_asymmetry")
        assert hasattr(verdict, "fractal_anomaly")
        assert hasattr(verdict, "charge_imbalance")
        assert hasattr(verdict, "combined_score")
        assert hasattr(verdict, "micro_census")
        assert hasattr(verdict, "valence_valid")
        assert hasattr(verdict, "valence_violations")
        assert hasattr(verdict, "flux_contracted")
        assert hasattr(verdict, "updated_state")
        assert hasattr(verdict, "persistence_count")

    def test_wrong_dimension_raises(self):
        """Non-21D vector raises ValueError."""
        with pytest.raises(ValueError, match="21D"):
            evaluate_governance(np.ones(10))

    def test_scores_in_range(self):
        """All scores are in [0, 1]."""
        x_prev = make_valid_state(0)
        x_curr = make_valid_state(1)
        verdict = evaluate_governance(x_curr, x_prev)
        assert 0.0 <= verdict.mirror_asymmetry <= 1.0
        assert 0.0 <= verdict.fractal_anomaly <= 1.0
        assert 0.0 <= verdict.charge_imbalance <= 1.0
        assert 0.0 <= verdict.combined_score <= 1.0

    def test_alignment_applied(self):
        """With align=True, corrections are reported."""
        x = make_valid_state(0)
        x[0] = 5.0  # device_trust out of bounds
        verdict = evaluate_governance(x, align=True)
        assert verdict.alignment_corrections > 0


# ---------------------------------------------------------------------------
# Tests: Persistent asymmetry -> flux contraction -> escalation
# ---------------------------------------------------------------------------

class TestPersistentAsymmetry:
    """Tests for the asymmetry -> contraction -> escalation pipeline."""

    def test_persistent_asymmetry_triggers_contraction(self):
        """High asymmetry for 3+ steps triggers flux contraction."""
        tracker = AsymmetryTracker(window_size=8, threshold=0.2)
        origin = make_safe_origin()
        x_prev = origin.copy()

        # Simulate 4 steps with high parallel-only changes
        for i in range(4):
            x_curr = origin.copy()
            x_curr[6:9] += 0.3 * (i + 1)  # big navigation changes
            verdict = evaluate_governance(
                x_curr, x_prev, tracker=tracker,
                contraction_strength=0.3,
            )
            x_prev = x_curr

        # After 3+ persistent high-asymmetry readings, contraction should fire
        assert tracker.persistence_count >= 3
        # The last verdict should have triggered contraction
        assert verdict.flux_contracted

    def test_no_contraction_without_persistence(self):
        """Sporadic asymmetry does NOT trigger contraction."""
        tracker = AsymmetryTracker(window_size=8, threshold=0.3)
        origin = make_safe_origin()

        # Alternating: high asymmetry, then normal
        for i in range(6):
            x = origin.copy()
            if i % 2 == 0:
                x[6:9] += 0.3  # parallel push
            verdict = evaluate_governance(
                x, origin, tracker=tracker,
            )

        assert not verdict.flux_contracted

    def test_contraction_pulls_toward_origin(self):
        """After flux contraction, updated state is closer to safe origin."""
        tracker = AsymmetryTracker(window_size=8, threshold=0.1)
        origin = make_safe_origin()

        # Force persistent asymmetry
        for _ in range(4):
            tracker.record(0.8)

        x = make_valid_state(5)
        verdict = evaluate_governance(
            x, origin, tracker=tracker, contraction_strength=0.5,
        )
        assert verdict.flux_contracted
        d_original = np.linalg.norm(x - origin)
        d_contracted = np.linalg.norm(verdict.updated_state - origin)
        assert d_contracted < d_original


# ---------------------------------------------------------------------------
# Tests: Trajectory governance
# ---------------------------------------------------------------------------

class TestTrajectoryGovernance:
    """Tests for evaluate_trajectory_governance."""

    def test_smooth_trajectory_decisions(self):
        """Smooth trajectory produces valid decisions (not all DENY)."""
        traj = make_trajectory(n_steps=20, seed=0)
        # Use small epsilon so tiny noise registers as ternary activity
        verdicts = evaluate_trajectory_governance(traj, epsilon=0.001)
        assert len(verdicts) == 20
        # Verify all decisions are valid L13 tiers
        valid_decisions = {"ALLOW", "QUARANTINE", "ESCALATE", "DENY"}
        for v in verdicts:
            assert v.decision in valid_decisions
        # A smooth trajectory shouldn't be all-DENY
        deny_count = sum(1 for v in verdicts if v.decision == "DENY")
        assert deny_count < len(verdicts)

    def test_trajectory_length_matches(self):
        """Output length matches trajectory length."""
        traj = make_trajectory(n_steps=10, seed=1)
        verdicts = evaluate_trajectory_governance(traj)
        assert len(verdicts) == 10

    def test_first_step_has_no_prev(self):
        """First verdict has all-neutral census (no previous state)."""
        traj = make_trajectory(n_steps=5, seed=2)
        verdicts = evaluate_trajectory_governance(traj)
        assert verdicts[0].micro_census.active_count == 0

    def test_wrong_shape_raises(self):
        """Non-(T, 21) trajectory raises ValueError."""
        with pytest.raises(ValueError):
            evaluate_trajectory_governance(np.ones((10, 5)))

    def test_tracker_accumulates(self):
        """Tracker persistence increases across trajectory."""
        tracker = AsymmetryTracker(window_size=20, threshold=0.01)
        # Create a trajectory with constant small changes
        origin = make_safe_origin()
        traj = np.tile(origin, (10, 1))
        # Add progressive parallel-only drift
        for t in range(1, 10):
            traj[t, 6:9] += 0.05 * t

        verdicts = evaluate_trajectory_governance(
            traj, tracker=tracker, epsilon=0.001,
        )
        # Persistence should grow over time
        last_persistence = verdicts[-1].persistence_count
        assert last_persistence >= 2


# ---------------------------------------------------------------------------
# Tests: Integration with other ai_brain modules
# ---------------------------------------------------------------------------

class TestIntegration:
    """Integration tests with mirror_shift and multiscale_spectrum."""

    def test_with_trajectory_fractal_analysis(self):
        """Providing trajectory enables fractal anomaly scoring."""
        traj = make_trajectory(n_steps=30, seed=0)
        verdict = evaluate_governance(
            x_curr=traj[-1],
            x_prev=traj[-2],
            trajectory=traj,
        )
        # fractal_anomaly should be computed (may or may not be > 0)
        assert verdict.fractal_anomaly >= 0.0

    def test_without_trajectory_zero_fractal(self):
        """Without trajectory, fractal anomaly is 0."""
        x = make_valid_state(0)
        verdict = evaluate_governance(x, x_prev=None, trajectory=None)
        assert verdict.fractal_anomaly == 0.0

    def test_census_matches_ternary(self):
        """Census counts match what compute_dual_ternary produces."""
        from symphonic_cipher.scbe_aethermoore.ai_brain.mirror_shift import (
            compute_dual_ternary,
        )
        x_prev = make_valid_state(0)
        x_curr = make_valid_state(1)
        par, perp = compute_dual_ternary(x_curr, x_prev, epsilon=0.01)
        census = census_from_ternary(par, perp)

        # Verify counts add up
        assert (census.par_activate + census.par_neutral + census.par_inhibit
                == len(par))
        assert (census.perp_activate + census.perp_neutral + census.perp_inhibit
                == len(perp))

    def test_brain_state_roundtrip(self):
        """GovernanceVerdict.updated_state can be fed back to UnifiedBrainState."""
        x = make_valid_state(0)
        x[0] = 1.5  # out of bounds -> will be corrected
        verdict = evaluate_governance(x, align=True)
        state = UnifiedBrainState.from_vector(verdict.updated_state.tolist())
        assert state is not None
        reconstructed = np.array(state.to_vector())
        np.testing.assert_allclose(
            reconstructed, verdict.updated_state, atol=1e-10
        )
