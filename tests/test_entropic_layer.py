"""
Tests for EntropicLayer: escape detection, adaptive-k, and expansion tracking.
"""

import math
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.ai_brain.entropic_layer import (
    EntropicLayer,
    EntropicConfig,
    EntropicState,
    EscapeAssessment,
    DEFAULT_MAX_VOLUME,
    MIN_K,
    MAX_K,
    _gamma,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_state(position, velocity):
    return EntropicState(position=position, velocity=velocity)


def origin_state(dim=6):
    return make_state([0.0] * dim, [0.0] * dim)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_default_config(self):
        layer = EntropicLayer()
        config = layer.get_config()
        assert config.max_volume == DEFAULT_MAX_VOLUME
        assert config.base_k == 5
        assert config.c_quantum == 1.0
        assert config.n0 == 100

    def test_custom_config(self):
        config = EntropicConfig(max_volume=500, base_k=10)
        layer = EntropicLayer(config)
        assert layer.config.max_volume == 500
        assert layer.config.base_k == 10
        assert layer.config.c_quantum == 1.0  # default preserved

    def test_runtime_update(self):
        layer = EntropicLayer()
        layer.update_config(max_volume=999)
        assert layer.config.max_volume == 999

    def test_config_copy(self):
        layer = EntropicLayer()
        c1 = layer.get_config()
        layer.update_config(max_volume=123)
        c2 = layer.get_config()
        assert c1.max_volume == DEFAULT_MAX_VOLUME
        assert c2.max_volume == 123


# ---------------------------------------------------------------------------
# Expansion Volume
# ---------------------------------------------------------------------------


class TestExpansionVolume:
    def test_zero_at_origin(self):
        layer = EntropicLayer()
        vol = layer.compute_expansion_volume([0, 0, 0, 0, 0, 0])
        assert vol == 0.0

    def test_increases_with_radius(self):
        layer = EntropicLayer()
        vol1 = layer.compute_expansion_volume([0.1, 0, 0, 0, 0, 0])
        vol2 = layer.compute_expansion_volume([0.5, 0, 0, 0, 0, 0])
        vol3 = layer.compute_expansion_volume([0.9, 0, 0, 0, 0, 0])
        assert vol2 > vol1
        assert vol3 > vol2

    def test_positive_for_nonzero(self):
        layer = EntropicLayer()
        vol = layer.compute_expansion_volume([0.3, 0.2, 0.1, 0.0, 0.0, 0.0])
        assert vol > 0

    def test_different_dimensions(self):
        layer = EntropicLayer()
        vol2d = layer.compute_expansion_volume([0.5, 0.5])
        vol3d = layer.compute_expansion_volume([0.5, 0.5, 0.5])
        vol6d = layer.compute_expansion_volume([0.3, 0.3, 0.3, 0.3, 0.3, 0.3])
        assert vol2d > 0
        assert vol3d > 0
        assert vol6d > 0

    def test_exponential_growth(self):
        layer = EntropicLayer()
        vol1 = layer.compute_expansion_volume([0.1, 0, 0, 0, 0, 0])
        vol2 = layer.compute_expansion_volume([1.0, 0, 0, 0, 0, 0])
        ratio = vol2 / vol1
        assert ratio > 100  # exponential growth

    def test_no_overflow_large_radius(self):
        layer = EntropicLayer()
        vol = layer.compute_expansion_volume([10, 0, 0, 0, 0, 0])
        assert math.isfinite(vol)


# ---------------------------------------------------------------------------
# Escape Detection
# ---------------------------------------------------------------------------


class TestEscapeDetection:
    def test_no_escape_at_origin(self):
        layer = EntropicLayer()
        assessment = layer.detect_escape(origin_state())
        assert assessment.escaped is False
        assert assessment.volume == 0
        assert assessment.radial_velocity == 0

    def test_volume_escape(self):
        config = EntropicConfig(max_volume=0.001)
        layer = EntropicLayer(config)
        state = make_state([0.5, 0.5, 0.5, 0.5, 0.5, 0.5], [0, 0, 0, 0, 0, 0])
        assessment = layer.detect_escape(state)
        assert assessment.escaped is True
        assert assessment.volume > 0.001
        assert assessment.volume_ratio > 1.0

    def test_velocity_escape(self):
        config = EntropicConfig(c_quantum=0.01, n0=100)
        layer = EntropicLayer(config)
        state = make_state([0.5, 0, 0, 0, 0, 0], [10.0, 0, 0, 0, 0, 0])
        assessment = layer.detect_escape(state)
        assert assessment.radial_velocity > 0
        assert assessment.escaped is True

    def test_no_escape_small_state(self):
        layer = EntropicLayer()
        state = make_state(
            [0.01, 0.01, 0.01, 0.01, 0.01, 0.01],
            [0.001, 0.001, 0.001, 0.001, 0.001, 0.001],
        )
        assessment = layer.detect_escape(state)
        assert assessment.escaped is False

    def test_escape_velocity_bound_formula(self):
        config = EntropicConfig(c_quantum=2.0, n0=16)
        layer = EntropicLayer(config)
        assessment = layer.detect_escape(origin_state())
        # bound = 2 * 2.0 / sqrt(16) = 4.0 / 4.0 = 1.0
        assert abs(assessment.escape_velocity_bound - 1.0) < 1e-6

    def test_tangential_velocity(self):
        layer = EntropicLayer()
        state = make_state([0.5, 0, 0, 0, 0, 0], [0, 1.0, 0, 0, 0, 0])
        assessment = layer.detect_escape(state)
        assert abs(assessment.radial_velocity) < 1e-6

    def test_negative_radial_velocity(self):
        layer = EntropicLayer()
        state = make_state([0.5, 0, 0, 0, 0, 0], [-1.0, 0, 0, 0, 0, 0])
        assessment = layer.detect_escape(state)
        assert assessment.radial_velocity < 0


# ---------------------------------------------------------------------------
# Adaptive K
# ---------------------------------------------------------------------------


class TestAdaptiveK:
    def test_zero_coherence(self):
        layer = EntropicLayer(EntropicConfig(base_k=5))
        assert layer.adaptive_k(0) == 1

    def test_full_coherence(self):
        layer = EntropicLayer(EntropicConfig(base_k=5))
        assert layer.adaptive_k(1.0) == 6

    def test_clamps_negative(self):
        layer = EntropicLayer(EntropicConfig(base_k=5))
        assert layer.adaptive_k(-0.5) == 1

    def test_clamps_above_one(self):
        layer = EntropicLayer(EntropicConfig(base_k=5))
        assert layer.adaptive_k(2.0) == 6

    def test_respects_min_k(self):
        layer = EntropicLayer(EntropicConfig(base_k=0))
        k = layer.adaptive_k(0.5)
        assert k >= MIN_K

    def test_respects_max_k(self):
        layer = EntropicLayer(EntropicConfig(base_k=100))
        k = layer.adaptive_k(1.0)
        assert k <= MAX_K

    def test_monotonically_increasing(self):
        layer = EntropicLayer(EntropicConfig(base_k=10))
        prev_k = 0
        for c in [i * 0.1 for i in range(11)]:
            k = layer.adaptive_k(c)
            assert k >= prev_k
            prev_k = k

    def test_integer_values(self):
        layer = EntropicLayer(EntropicConfig(base_k=7))
        for c in [i * 0.05 for i in range(21)]:
            k = layer.adaptive_k(c)
            assert isinstance(k, int)


# ---------------------------------------------------------------------------
# Escape Velocity Bound
# ---------------------------------------------------------------------------


class TestEscapeVelocityBound:
    def test_satisfied_high_k(self):
        config = EntropicConfig(c_quantum=1.0, n0=100)
        layer = EntropicLayer(config)
        # bound = 2 * 1.0 / sqrt(100) = 0.2
        assert layer.escape_velocity_bound_satisfied(1) is True

    def test_not_satisfied_low_k(self):
        config = EntropicConfig(c_quantum=10.0, n0=1)
        layer = EntropicLayer(config)
        # bound = 2 * 10.0 / sqrt(1) = 20.0
        assert layer.escape_velocity_bound_satisfied(5) is False

    def test_boundary_case(self):
        config = EntropicConfig(c_quantum=3.0, n0=9)
        layer = EntropicLayer(config)
        # bound = 2 * 3.0 / sqrt(9) = 2.0
        assert layer.escape_velocity_bound_satisfied(2) is False  # k = bound, not >
        assert layer.escape_velocity_bound_satisfied(3) is True


# ---------------------------------------------------------------------------
# Integration scenarios
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_safe_state_with_adaptive_k(self):
        layer = EntropicLayer(EntropicConfig(base_k=10, c_quantum=1.0, n0=100))
        assessment = layer.detect_escape(origin_state())
        k = layer.adaptive_k(0.5)
        satisfied = layer.escape_velocity_bound_satisfied(k)

        assert assessment.escaped is False
        assert k >= 1
        assert satisfied is True  # k=6 > 0.2

    def test_volume_explosion_detected(self):
        config = EntropicConfig(max_volume=1e-10)
        layer = EntropicLayer(config)
        state = make_state([0.1, 0.1, 0.1, 0.1, 0.1, 0.1], [0, 0, 0, 0, 0, 0])
        assessment = layer.detect_escape(state)
        assert assessment.escaped is True
        assert assessment.volume_ratio > 1.0


# ---------------------------------------------------------------------------
# Gamma function
# ---------------------------------------------------------------------------


class TestGamma:
    def test_integer_values(self):
        assert _gamma(1) == 1.0
        assert _gamma(2) == 1.0
        assert _gamma(3) == 2.0
        assert _gamma(4) == 6.0

    def test_half_integer_values(self):
        assert abs(_gamma(0.5) - math.sqrt(math.pi)) < 1e-10
        assert abs(_gamma(1.5) - math.sqrt(math.pi) / 2) < 1e-10

    def test_stirling_approximation(self):
        # For large values, Stirling's should be reasonable
        result = _gamma(5.0)
        assert result > 0


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_default_max_volume(self):
        assert DEFAULT_MAX_VOLUME == 1e6

    def test_k_bounds(self):
        assert MIN_K == 1
        assert MAX_K == 50
