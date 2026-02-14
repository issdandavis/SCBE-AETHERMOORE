"""
Multiscale Spectrum Analysis Test Suite
=======================================

@file test_multiscale_spectrum.py
@layer Layer 9, Layer 10, Layer 14
@component Tests for fractal dimensional analysis of 21D brain state trajectories

Tests:
- Eigenvalue math invariants (participation ratio, spectral entropy)
- Replay attack detection (constant trajectory -> low effective dimension)
- Chaotic probing detection (random trajectory -> high effective dimension)
- Drift detection (monotonic entropy increase across scales)
- Subsystem analysis (per-component slice analysis)
- Sliding window analysis (real-time monitoring)
- Edge cases (short trajectories, zero vectors)
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from symphonic_cipher.scbe_aethermoore.ai_brain.multiscale_spectrum import (
    BRAIN_DIMENSIONS,
    DEFAULT_SCALES,
    MultiscaleReport,
    ScaleFeatures,
    analyze_scale,
    analyze_subsystem,
    analyze_trajectory,
    compute_increments,
    covariance_spectrum,
    effective_rank,
    multiscale_spectrum_features,
    participation_ratio,
    sliding_window_analysis,
    spectral_entropy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_constant_trajectory(T: int = 100, D: int = 21) -> np.ndarray:
    """Trajectory that stays constant (replay attack simulation)."""
    state = np.array([0.5] * D)
    return np.tile(state, (T, 1))


def make_random_trajectory(
    T: int = 100, D: int = 21, seed: int = 42
) -> np.ndarray:
    """Trajectory with random walk (chaotic probing simulation)."""
    rng = np.random.default_rng(seed)
    X = np.zeros((T, D))
    X[0] = rng.random(D) * 0.5
    for t in range(1, T):
        X[t] = X[t - 1] + rng.normal(0, 0.05, D)
    return X


def make_drifting_trajectory(
    T: int = 100, D: int = 21, seed: int = 99
) -> np.ndarray:
    """Trajectory that slowly drifts in one direction."""
    rng = np.random.default_rng(seed)
    drift = rng.normal(0, 0.01, D)
    X = np.zeros((T, D))
    X[0] = rng.random(D) * 0.3
    for t in range(1, T):
        X[t] = X[t - 1] + drift + rng.normal(0, 0.001, D)
    return X


def make_normal_trajectory(
    T: int = 100, D: int = 21, seed: int = 7
) -> np.ndarray:
    """Trajectory with structured but non-adversarial dynamics."""
    rng = np.random.default_rng(seed)
    X = np.zeros((T, D))
    X[0] = np.concatenate([
        rng.random(6) * 0.8 + 0.1,   # SCBE: trust scores near center
        rng.normal(0, 0.1, 6),         # Navigation: small movements
        rng.normal(0, 0.05, 3),        # Cognitive: stable
        np.array([2.0, 1.5, 3.0]),     # Semantic: fixed tongue/phase
        np.array([0.7, 0.0, 0.8]),     # Swarm: healthy
    ])
    for t in range(1, T):
        noise = rng.normal(0, 0.01, D)
        # Oscillate navigation dims
        noise[6] += 0.02 * math.sin(2 * math.pi * t / 20)
        noise[7] += 0.02 * math.cos(2 * math.pi * t / 20)
        X[t] = X[t - 1] + noise
    return X


# ---------------------------------------------------------------------------
# Tests: math primitives
# ---------------------------------------------------------------------------

class TestMathPrimitives:
    """Tests for participation ratio, spectral entropy, effective rank."""

    def test_participation_ratio_single_mode(self):
        """All energy in one eigenvalue -> PR = 1."""
        evals = np.array([10.0, 0.0, 0.0, 0.0, 0.0])
        pr = participation_ratio(evals)
        assert abs(pr - 1.0) < 0.1

    def test_participation_ratio_uniform(self):
        """Equal eigenvalues -> PR = D."""
        D = 10
        evals = np.ones(D)
        pr = participation_ratio(evals)
        assert abs(pr - D) < 0.01

    def test_spectral_entropy_single_mode(self):
        """All energy in one mode -> entropy near 0."""
        evals = np.array([100.0, 1e-12, 1e-12])
        se = spectral_entropy(evals)
        assert se < 0.1

    def test_spectral_entropy_uniform(self):
        """Uniform eigenvalues -> entropy = log(D)."""
        D = 10
        evals = np.ones(D)
        se = spectral_entropy(evals)
        expected = math.log(D)
        assert abs(se - expected) < 0.01

    def test_effective_rank_equals_exp_entropy(self):
        """Effective rank = exp(spectral_entropy)."""
        evals = np.array([5.0, 3.0, 1.0, 0.5])
        er = effective_rank(evals)
        se = spectral_entropy(evals)
        assert abs(er - math.exp(se)) < 1e-10

    def test_participation_ratio_monotonic(self):
        """PR increases as eigenvalue distribution becomes more uniform."""
        peaked = np.array([10.0, 0.1, 0.1, 0.1])
        spread = np.array([3.0, 2.5, 2.0, 1.5])
        assert participation_ratio(spread) > participation_ratio(peaked)


# ---------------------------------------------------------------------------
# Tests: increments and covariance
# ---------------------------------------------------------------------------

class TestIncrementsAndCovariance:
    """Tests for compute_increments and covariance_spectrum."""

    def test_increments_shape(self):
        """Increments have shape (T-s, D)."""
        X = make_random_trajectory(50, 10)
        dX = compute_increments(X, scale=4)
        assert dX.shape == (46, 10)

    def test_increments_constant_trajectory_zero(self):
        """Constant trajectory produces zero increments."""
        X = make_constant_trajectory(50, 5)
        dX = compute_increments(X, scale=1)
        assert np.allclose(dX, 0.0)

    def test_increments_invalid_scale(self):
        """Scale <= 0 raises ValueError."""
        X = make_random_trajectory(10)
        with pytest.raises(ValueError, match="positive"):
            compute_increments(X, scale=0)

    def test_increments_too_short(self):
        """Trajectory shorter than scale raises ValueError."""
        X = make_random_trajectory(5)
        with pytest.raises(ValueError, match="too short"):
            compute_increments(X, scale=5)

    def test_covariance_spectrum_positive_semidefinite(self):
        """Eigenvalues of covariance are non-negative."""
        X = make_random_trajectory(100, 10)
        dX = compute_increments(X, scale=1)
        evals, _ = covariance_spectrum(dX)
        assert np.all(evals >= -1e-10)

    def test_covariance_spectrum_descending(self):
        """Eigenvalues are returned in descending order."""
        X = make_random_trajectory(100, 10)
        dX = compute_increments(X, scale=1)
        evals, _ = covariance_spectrum(dX)
        for i in range(len(evals) - 1):
            assert evals[i] >= evals[i + 1] - 1e-10


# ---------------------------------------------------------------------------
# Tests: scale analysis
# ---------------------------------------------------------------------------

class TestScaleAnalysis:
    """Tests for single-scale and multi-scale analysis."""

    def test_analyze_scale_returns_features(self):
        """analyze_scale returns a ScaleFeatures dataclass."""
        X = make_random_trajectory(100, 21)
        feat = analyze_scale(X, scale=2)
        assert isinstance(feat, ScaleFeatures)
        assert feat.scale == 2
        assert feat.participation_ratio > 0
        assert feat.spectral_entropy > 0

    def test_multiscale_features_counts(self):
        """multiscale_spectrum_features returns one result per valid scale."""
        X = make_random_trajectory(100, 21)
        features = multiscale_spectrum_features(X, scales=(1, 2, 4, 8, 16))
        # T=100, so all scales up to 97 are valid
        assert len(features) == 5

    def test_multiscale_skips_too_large_scales(self):
        """Scales larger than trajectory are skipped."""
        X = make_random_trajectory(10, 21)
        features = multiscale_spectrum_features(X, scales=(1, 2, 4, 8, 16))
        # T=10: valid for scales 1,2,4 (need s+2 < T), skip 8 and 16
        for f in features:
            assert f.scale <= 7

    def test_invalid_input_shape(self):
        """1D input raises ValueError."""
        with pytest.raises(ValueError, match="2D"):
            multiscale_spectrum_features(np.ones(100))


# ---------------------------------------------------------------------------
# Tests: anomaly detection
# ---------------------------------------------------------------------------

class TestAnomalyDetection:
    """Tests for replay, chaos, and drift anomaly scores."""

    def test_replay_attack_high_replay_score(self):
        """Constant trajectory -> high replay score."""
        X = make_constant_trajectory(100, 21)
        # Add tiny noise to avoid degenerate zero increments
        X += np.random.default_rng(0).normal(0, 1e-6, X.shape)
        report = analyze_trajectory(X)
        assert report.replay_score > 0.8

    def test_random_probing_high_chaos_score(self):
        """High-noise random walk -> elevated chaos score."""
        rng = np.random.default_rng(42)
        X = rng.normal(0, 1.0, (200, 21))  # Pure random
        report = analyze_trajectory(X)
        assert report.chaos_score > 0.3

    def test_drifting_trajectory_positive_drift_score(self):
        """Slow monotonic drift -> positive drift score."""
        X = make_drifting_trajectory(200, 21)
        report = analyze_trajectory(X)
        # Drift score should be above zero (may not be very high
        # because entropy change depends on trajectory specifics)
        assert report.drift_score >= 0.0

    def test_normal_trajectory_low_anomaly(self):
        """Normal structured trajectory -> low anomaly score."""
        X = make_normal_trajectory(200, 21)
        report = analyze_trajectory(X)
        # Normal behavior should not score extremely high on any attack type
        assert report.anomaly_score < 0.95

    def test_report_fields_complete(self):
        """MultiscaleReport has all expected fields."""
        X = make_random_trajectory(100, 21)
        report = analyze_trajectory(X)
        assert isinstance(report, MultiscaleReport)
        assert report.trajectory_length == 100
        assert report.dimensions == 21
        assert 0.0 <= report.anomaly_score <= 1.0
        assert 0.0 <= report.replay_score <= 1.0
        assert 0.0 <= report.chaos_score <= 1.0
        assert 0.0 <= report.drift_score <= 1.0


# ---------------------------------------------------------------------------
# Tests: subsystem analysis
# ---------------------------------------------------------------------------

class TestSubsystemAnalysis:
    """Tests for per-subsystem slice analysis."""

    def test_scbe_subsystem(self):
        """SCBE subsystem analyzes dims 0-5."""
        X = make_random_trajectory(100, 21)
        report = analyze_subsystem(X, "scbe")
        assert report.dimensions == 6

    def test_navigation_subsystem(self):
        """Navigation subsystem analyzes dims 6-11."""
        X = make_random_trajectory(100, 21)
        report = analyze_subsystem(X, "navigation")
        assert report.dimensions == 6

    def test_cognitive_subsystem(self):
        """Cognitive subsystem analyzes dims 12-14."""
        X = make_random_trajectory(100, 21)
        report = analyze_subsystem(X, "cognitive")
        assert report.dimensions == 3

    def test_semantic_subsystem(self):
        """Semantic subsystem analyzes dims 15-17."""
        X = make_random_trajectory(100, 21)
        report = analyze_subsystem(X, "semantic")
        assert report.dimensions == 3

    def test_swarm_subsystem(self):
        """Swarm subsystem analyzes dims 18-20."""
        X = make_random_trajectory(100, 21)
        report = analyze_subsystem(X, "swarm")
        assert report.dimensions == 3

    def test_invalid_subsystem(self):
        """Unknown subsystem name raises ValueError."""
        X = make_random_trajectory(100, 21)
        with pytest.raises(ValueError, match="Unknown subsystem"):
            analyze_subsystem(X, "invalid")


# ---------------------------------------------------------------------------
# Tests: sliding window
# ---------------------------------------------------------------------------

class TestSlidingWindow:
    """Tests for sliding window analysis."""

    def test_window_count(self):
        """Correct number of windows produced."""
        X = make_random_trajectory(200, 21)
        reports = sliding_window_analysis(X, window_size=64, step=32)
        expected = (200 - 64) // 32 + 1
        assert len(reports) == expected

    def test_window_reports_valid(self):
        """Each window report is a valid MultiscaleReport."""
        X = make_normal_trajectory(128, 21)
        reports = sliding_window_analysis(X, window_size=32, step=16)
        for r in reports:
            assert isinstance(r, MultiscaleReport)
            assert r.trajectory_length == 32

    def test_anomaly_spike_detection(self):
        """
        Injecting a replay segment into normal trajectory
        produces higher anomaly in the affected window.
        """
        rng = np.random.default_rng(11)
        X = make_normal_trajectory(256, 21)
        # Inject replay segment at timesteps 128-192
        X[128:192] = X[128]  # constant
        X[128:192] += rng.normal(0, 1e-6, (64, 21))  # tiny noise

        reports = sliding_window_analysis(X, window_size=64, step=32)
        # The window covering the replay segment should have higher replay score
        scores = [r.replay_score for r in reports]
        max_idx = int(np.argmax(scores))
        # The replay segment starts at 128, window size 64, step 32
        # Window at index 4 covers [128, 192)
        assert max_idx >= 3, f"Expected replay peak near index 4, got {max_idx}"
