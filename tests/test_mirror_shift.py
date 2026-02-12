"""
Mirror Shift + Refactor Align Test Suite
=========================================

@file test_mirror_shift.py
@layer Layer 5, Layer 6, Layer 7, Layer 9
@component Tests for dual-channel mirror analysis + constraint alignment

Tests:
- Ternary quantization (dead zone, sign detection)
- Dual ternary channel computation (parallel vs perpendicular)
- Mirror shift operator (identity, full swap, partial mixing)
- Mirror asymmetry scoring
- Refactor align (POCS constraint projection)
  - Bounds clamping
  - Tongue index snapping
  - Phase angle wrapping
  - Poincaré containment
- Combined transition analysis
- Property: alignment is idempotent (align(align(x)) == align(x))
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from symphonic_cipher.scbe_aethermoore.ai_brain.mirror_shift import (
    BRAIN_DIMENSIONS,
    CONSTRAINT_BOUNDS,
    PARALLEL_DIMS,
    PERP_DIMS,
    AlignmentResult,
    MirrorAnalysis,
    MirrorShiftResult,
    analyze_transition,
    compute_dual_ternary,
    dual_ternary_trajectory,
    mirror_asymmetry_score,
    mirror_shift,
    quantize_ternary,
    refactor_align,
)
from symphonic_cipher.scbe_aethermoore.ai_brain.unified_state import (
    UnifiedBrainState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_valid_state(seed: int = 0) -> np.ndarray:
    """Create a valid 21D brain state vector that satisfies all constraints.

    Keeps values small enough that the Poincaré embedding stays
    well inside max_radius=0.95 (raw norm < ~3.0 maps to tanh(1.5) ≈ 0.905).
    """
    rng = np.random.default_rng(seed)
    x = np.zeros(BRAIN_DIMENSIONS)
    # SCBE Context [0:6]: trust scores in [0, 1]
    x[0:6] = rng.random(6) * 0.6 + 0.2
    # Navigation [6:12]: small positions
    x[6:9] = rng.normal(0, 0.05, 3)
    x[9] = rng.random() * 0.3  # time (small)
    x[10:12] = rng.random(2) * 0.5 + 0.2  # priority, confidence
    # Cognitive [12:15]
    x[12:15] = rng.normal(0, 0.02, 3)
    # Semantic [15:18]: tongue index (integer 0-1), phase (small), weight (small)
    # Keep tongue index ≤ 1 so total raw norm stays < 3.6 (Poincaré safe)
    x[15] = float(rng.integers(0, 2))
    x[16] = rng.random() * 0.5  # phase [0, 0.5] (small)
    x[17] = 0.3 + rng.random() * 0.3  # weight [0.3, 0.6] (small)
    # Swarm [18:21]
    x[18] = rng.random() * 0.5 + 0.2  # trust_score
    x[19] = 0.0  # byzantine_votes
    x[20] = rng.random() * 0.5 + 0.2  # spectral_coherence
    return x


def make_invalid_state() -> np.ndarray:
    """Create a state with constraint violations."""
    x = np.zeros(BRAIN_DIMENSIONS)
    x[0] = 1.5    # device_trust > 1
    x[1] = -0.3   # location_trust < 0
    x[5] = 2.0    # intent_alignment > 1
    x[15] = 3.7   # active_tongue not integer
    x[16] = 8.0   # phase_angle > 2*pi
    x[18] = 1.2   # trust_score > 1
    x[20] = -0.1  # spectral_coherence < 0
    return x


# ---------------------------------------------------------------------------
# Tests: ternary quantization
# ---------------------------------------------------------------------------

class TestTernaryQuantization:
    """Tests for quantize_ternary."""

    def test_positive_values(self):
        """Values above epsilon quantize to +1."""
        z = np.array([0.1, 0.5, 1.0])
        q = quantize_ternary(z, epsilon=0.01)
        assert np.all(q == 1)

    def test_negative_values(self):
        """Values below -epsilon quantize to -1."""
        z = np.array([-0.1, -0.5, -1.0])
        q = quantize_ternary(z, epsilon=0.01)
        assert np.all(q == -1)

    def test_dead_zone(self):
        """Values within [-epsilon, epsilon] quantize to 0."""
        z = np.array([0.005, -0.005, 0.0])
        q = quantize_ternary(z, epsilon=0.01)
        assert np.all(q == 0)

    def test_mixed_values(self):
        """Mixed values quantize correctly."""
        z = np.array([0.5, -0.3, 0.001, -0.001, 0.02])
        q = quantize_ternary(z, epsilon=0.01)
        expected = np.array([1, -1, 0, 0, 1])
        np.testing.assert_array_equal(q, expected)

    def test_output_dtype(self):
        """Output is int8."""
        q = quantize_ternary(np.array([0.5, -0.5, 0.0]))
        assert q.dtype == np.int8


# ---------------------------------------------------------------------------
# Tests: dual ternary channels
# ---------------------------------------------------------------------------

class TestDualTernary:
    """Tests for compute_dual_ternary and dual_ternary_trajectory."""

    def test_channel_dimensions(self):
        """Parallel channel has 9 dims, perpendicular has 12 dims."""
        x_curr = make_valid_state(1)
        x_prev = make_valid_state(2)
        par, perp = compute_dual_ternary(x_curr, x_prev)
        assert len(par) == len(PARALLEL_DIMS)  # 9
        assert len(perp) == len(PERP_DIMS)     # 12

    def test_identical_states_zero_channels(self):
        """Identical states produce all-zero ternary channels."""
        x = make_valid_state()
        par, perp = compute_dual_ternary(x, x)
        assert np.all(par == 0)
        assert np.all(perp == 0)

    def test_trajectory_output_shape(self):
        """Trajectory dual ternary has correct shapes."""
        rng = np.random.default_rng(0)
        T = 50
        trajectory = np.stack([make_valid_state(i) for i in range(T)])
        par_stream, perp_stream = dual_ternary_trajectory(trajectory)
        assert par_stream.shape == (T - 1, len(PARALLEL_DIMS))
        assert perp_stream.shape == (T - 1, len(PERP_DIMS))

    def test_trajectory_values_ternary(self):
        """All values in trajectory streams are in {-1, 0, 1}."""
        trajectory = np.stack([make_valid_state(i) for i in range(30)])
        par_stream, perp_stream = dual_ternary_trajectory(trajectory)
        assert set(np.unique(par_stream)).issubset({-1, 0, 1})
        assert set(np.unique(perp_stream)).issubset({-1, 0, 1})

    def test_trajectory_wrong_shape_raises(self):
        """Wrong trajectory shape raises ValueError."""
        with pytest.raises(ValueError, match="Expected"):
            dual_ternary_trajectory(np.ones((10, 5)))


# ---------------------------------------------------------------------------
# Tests: mirror shift operator
# ---------------------------------------------------------------------------

class TestMirrorShift:
    """Tests for the mirror shift operator."""

    def test_identity_at_zero(self):
        """phi=0 is the identity transform."""
        par = np.array([1.0, -1.0, 0.0, 1.0])
        perp = np.array([0.0, 1.0, -1.0])
        result = mirror_shift(par, perp, phi=0.0)
        np.testing.assert_allclose(result.shifted_parallel, par, atol=1e-10)
        np.testing.assert_allclose(result.shifted_perp, perp, atol=1e-10)

    def test_full_swap_at_pi_over_2(self):
        """phi=pi/2 swaps the channels."""
        par = np.array([1.0, 0.0, 0.0])
        perp = np.array([0.0, 0.0, 1.0])
        result = mirror_shift(par, perp, phi=math.pi / 2)
        # sin(pi/2)=1, cos(pi/2)=0 -> a' = b, b' = a
        np.testing.assert_allclose(
            result.shifted_parallel, perp, atol=1e-10
        )
        np.testing.assert_allclose(
            result.shifted_perp, par, atol=1e-10
        )

    def test_asymmetry_score_balanced(self):
        """Equal-energy channels have low asymmetry."""
        par = np.array([1.0, -1.0, 1.0])
        perp = np.array([1.0, 1.0, -1.0])
        result = mirror_shift(par, perp, phi=0.0)
        assert result.asymmetry_score < 0.01

    def test_asymmetry_score_unbalanced(self):
        """One-sided channels have high asymmetry."""
        par = np.array([1.0, 1.0, 1.0])
        perp = np.array([0.0, 0.0, 0.0])
        result = mirror_shift(par, perp, phi=0.0)
        assert result.asymmetry_score > 0.9

    def test_mixing_angle_preserved(self):
        """Mixing angle is stored in the result."""
        result = mirror_shift(np.ones(3), np.ones(3), phi=0.42)
        assert abs(result.mixing_angle - 0.42) < 1e-10


# ---------------------------------------------------------------------------
# Tests: mirror asymmetry score
# ---------------------------------------------------------------------------

class TestMirrorAsymmetry:
    """Tests for mirror_asymmetry_score on streams."""

    def test_balanced_streams(self):
        """Streams with equal total energy have asymmetry near 0."""
        # Use same number of nonzeros so total squared magnitudes match
        par = np.array([[1, -1, 0, 1], [0, 1, -1, 0], [1, 0, -1, 1]])
        perp = np.array([[1, 0, -1, 1], [-1, 1, 0, -1], [0, 1, -1, 0]])
        # Energy: par=8, perp=8 -> balanced
        score = mirror_asymmetry_score(par, perp)
        assert score < 0.01

    def test_one_sided_stream(self):
        """Only parallel channel active -> asymmetry = 1."""
        par = np.array([[1, 1, 1], [1, 1, 1]])
        perp = np.array([[0, 0, 0, 0], [0, 0, 0, 0]])
        score = mirror_asymmetry_score(par, perp)
        assert abs(score - 1.0) < 0.01


# ---------------------------------------------------------------------------
# Tests: refactor align
# ---------------------------------------------------------------------------

class TestRefactorAlign:
    """Tests for POCS-style constraint projection."""

    def test_valid_state_unchanged(self):
        """A valid state requires no corrections."""
        x = make_valid_state(0)
        result = refactor_align(x)
        assert result.corrections_applied == 0
        np.testing.assert_allclose(result.aligned_state, x, atol=1e-8)

    def test_bounds_clamped(self):
        """Out-of-range values are clamped to bounds."""
        x = make_invalid_state()
        result = refactor_align(x)
        # device_trust should be clamped to 1.0
        assert result.aligned_state[0] <= 1.0
        # location_trust should be clamped to 0.0
        assert result.aligned_state[1] >= 0.0
        # intent_alignment clamped to 1.0
        assert result.aligned_state[5] <= 1.0
        assert result.corrections_applied > 0

    def test_tongue_index_snapped(self):
        """Non-integer tongue index is snapped to nearest int."""
        x = np.zeros(BRAIN_DIMENSIONS)
        x[0:6] = 0.5  # valid SCBE
        x[15] = 2.7   # Should snap to 3
        x[17] = 1.0   # tongue weight
        result = refactor_align(x)
        assert result.aligned_state[15] == 3.0

    def test_phase_wrapped(self):
        """Phase angle > 2*pi is wrapped."""
        x = make_valid_state()
        x[16] = 8.0  # > 2*pi
        result = refactor_align(x)
        assert 0.0 <= result.aligned_state[16] < 2 * math.pi

    def test_trust_clamped(self):
        """Trust and coherence values outside [0, 1] are clamped."""
        x = make_valid_state()
        x[18] = 1.5  # trust_score > 1
        x[20] = -0.2  # spectral_coherence < 0
        result = refactor_align(x)
        assert result.aligned_state[18] <= 1.0
        assert result.aligned_state[20] >= 0.0

    def test_poincare_radius_bounded(self):
        """Aligned state has Poincaré radius < max."""
        x = make_valid_state()
        result = refactor_align(x, poincare_max=0.95)
        assert result.poincare_radius < 1.0

    def test_alignment_idempotent(self):
        """Aligning an already-aligned state produces the same output."""
        x = make_invalid_state()
        result1 = refactor_align(x)
        result2 = refactor_align(result1.aligned_state)
        # The aligned state should be stable (same output on second pass)
        np.testing.assert_allclose(
            result1.aligned_state, result2.aligned_state, atol=1e-6
        )

    def test_wrong_dimension_raises(self):
        """Non-21D vector raises ValueError."""
        with pytest.raises(ValueError, match="21D"):
            refactor_align(np.ones(10))

    def test_max_correction_reported(self):
        """max_correction reflects a large correction was applied."""
        x = make_valid_state()
        x[0] = 5.0  # device_trust = 5 -> clamped to 1
        result = refactor_align(x)
        # Poincaré containment may scale first, but correction is still large
        assert result.max_correction >= 2.0
        assert result.corrections_applied > 0


# ---------------------------------------------------------------------------
# Tests: combined transition analysis
# ---------------------------------------------------------------------------

class TestTransitionAnalysis:
    """Tests for the analyze_transition adapter."""

    def test_returns_mirror_analysis(self):
        """analyze_transition returns a MirrorAnalysis."""
        x_prev = make_valid_state(0)
        x_curr = make_valid_state(1)
        result = analyze_transition(x_curr, x_prev)
        assert isinstance(result, MirrorAnalysis)

    def test_ternary_channels_shape(self):
        """Parallel and perp channels have correct dimensions."""
        x_prev = make_valid_state(0)
        x_curr = make_valid_state(1)
        result = analyze_transition(x_curr, x_prev)
        assert len(result.parallel_ternary) == len(PARALLEL_DIMS)
        assert len(result.perp_ternary) == len(PERP_DIMS)

    def test_asymmetry_in_range(self):
        """Asymmetry score is in [0, 1]."""
        x_prev = make_valid_state(0)
        x_curr = make_valid_state(1)
        result = analyze_transition(x_curr, x_prev)
        assert 0.0 <= result.asymmetry_score <= 1.0

    def test_complexity_in_range(self):
        """Complexity score is in [0, 1]."""
        x_prev = make_valid_state(0)
        x_curr = make_valid_state(1)
        result = analyze_transition(x_curr, x_prev)
        assert 0.0 <= result.complexity_score <= 1.0

    def test_identical_states_zero_complexity(self):
        """Identical states produce zero complexity (with alignment disabled)."""
        x = make_valid_state(0)
        result = analyze_transition(x, x, epsilon=0.01, align=False)
        assert result.complexity_score == 0.0

    def test_alignment_applied_when_requested(self):
        """With align=True, corrections may be applied."""
        x = make_invalid_state()
        x_prev = make_valid_state(0)
        result = analyze_transition(x, x_prev, align=True)
        assert result.corrections > 0

    def test_no_alignment_when_disabled(self):
        """With align=False, no corrections are applied."""
        x = make_invalid_state()
        x_prev = make_valid_state(0)
        result = analyze_transition(x, x_prev, align=False)
        assert result.corrections == 0


# ---------------------------------------------------------------------------
# Tests: integration with UnifiedBrainState
# ---------------------------------------------------------------------------

class TestUnifiedBrainStateIntegration:
    """Tests that mirror shift works with UnifiedBrainState objects."""

    def test_from_brain_state_to_ternary(self):
        """UnifiedBrainState.to_vector() feeds into dual ternary."""
        from symphonic_cipher.scbe_aethermoore.ai_brain.unified_state import (
            NavigationVector,
            SwarmCoordination,
        )

        state1 = UnifiedBrainState.safe_origin()
        state2 = UnifiedBrainState.safe_origin()
        # Modify navigation directly on the dataclass
        state2.navigation = NavigationVector(
            x=0.1, y=-0.05, z=0.0, time=0.0, priority=0.5, confidence=1.0
        )
        state2.swarm_coordination = SwarmCoordination(
            trust_score=0.3, byzantine_votes=0.0, spectral_coherence=1.0
        )

        v1 = np.array(state1.to_vector())
        v2 = np.array(state2.to_vector())
        par, perp = compute_dual_ternary(v2, v1, epsilon=0.01)

        # Navigation change should show up in parallel channel
        assert np.any(par != 0)

    def test_align_preserves_brain_state_reconstructability(self):
        """Aligned state can be reconstructed into a valid UnifiedBrainState."""
        x = make_invalid_state()
        result = refactor_align(x)
        # Should not raise
        state = UnifiedBrainState.from_vector(result.aligned_state.tolist())
        assert state is not None
        # Reconstructed vector should match aligned state
        reconstructed = np.array(state.to_vector())
        np.testing.assert_allclose(
            reconstructed, result.aligned_state, atol=1e-10
        )
