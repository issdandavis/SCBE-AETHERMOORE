"""Tests for the thermal mirror probe — mirage spectral mapping on weight matrices."""

import numpy as np
import pytest

from scripts.thermal_mirror_probe import (
    TEMPERATURE_SOURCES,
    ThermalProbeResult,
    analyze_thermal,
    spectral_measure_2d,
    temperature_col_norm,
    temperature_diagonal,
    temperature_elementwise,
    temperature_row_norm,
    thermal_deform,
)


class TestSpectralMeasure2D:
    def test_zero_matrix_returns_zero(self):
        W = np.zeros((8, 8))
        result = spectral_measure_2d(W)
        assert result.s_spec == 0.0
        assert result.energy_total == 0.0

    def test_identity_has_structure(self):
        W = np.eye(16)
        result = spectral_measure_2d(W)
        assert result.s_spec > 0
        assert result.energy_total > 0

    def test_random_matrix_has_low_s_spec(self):
        rng = np.random.default_rng(42)
        W = rng.standard_normal((64, 64))
        result = spectral_measure_2d(W)
        # Random matrices should have low peak concentration
        assert result.s_spec < 0.01

    def test_constant_matrix_has_high_s_spec(self):
        W = np.full((16, 16), 3.0)
        result = spectral_measure_2d(W)
        # Constant matrix has all energy in DC bin
        assert result.s_spec == pytest.approx(1.0, abs=0.001)


class TestTemperatureFields:
    def test_row_norm_shape_preserved(self):
        W = np.random.randn(32, 64)
        T = temperature_row_norm(W)
        assert T.shape == W.shape

    def test_col_norm_shape_preserved(self):
        W = np.random.randn(32, 64)
        T = temperature_col_norm(W)
        assert T.shape == W.shape

    def test_elementwise_shape_preserved(self):
        W = np.random.randn(32, 64)
        T = temperature_elementwise(W)
        assert T.shape == W.shape

    def test_diagonal_shape_preserved(self):
        W = np.random.randn(32, 64)
        T = temperature_diagonal(W)
        assert T.shape == W.shape

    def test_all_temperatures_normalized_to_01(self):
        rng = np.random.default_rng(7)
        W = rng.standard_normal((16, 16)) * 10
        for name, func in TEMPERATURE_SOURCES.items():
            T = func(W)
            assert T.min() >= -1e-10, f"{name} has negative values"
            assert T.max() <= 1.0 + 1e-10, f"{name} exceeds 1.0"

    def test_zero_matrix_gives_zero_temperature(self):
        W = np.zeros((8, 8))
        for name, func in TEMPERATURE_SOURCES.items():
            T = func(W)
            assert np.allclose(T, 0), f"{name} nonzero for zero matrix"


class TestThermalDeform:
    def test_alpha_zero_is_identity(self):
        W = np.random.randn(16, 16)
        T = temperature_row_norm(W)
        result = thermal_deform(W, T, alpha=0.0)
        np.testing.assert_array_almost_equal(result, W)

    def test_higher_alpha_suppresses_more(self):
        rng = np.random.default_rng(42)
        W = rng.standard_normal((32, 32))
        T = temperature_row_norm(W)
        low = thermal_deform(W, T, alpha=1.0)
        high = thermal_deform(W, T, alpha=10.0)
        # Higher alpha should suppress more energy
        assert np.abs(high).sum() < np.abs(low).sum()

    def test_deformation_preserves_shape(self):
        W = np.random.randn(16, 32)
        T = temperature_elementwise(W)
        result = thermal_deform(W, T, alpha=2.0)
        assert result.shape == W.shape


class TestNullHypothesis:
    """Thermal mirror should have no spectral effect on random matrices."""

    def test_random_matrix_thermal_ratio_near_one(self):
        rng = np.random.default_rng(99)
        ratios = []
        for _ in range(10):
            W = rng.standard_normal((64, 64))
            orig = spectral_measure_2d(W)
            T = temperature_row_norm(W)
            deformed = spectral_measure_2d(thermal_deform(W, T, alpha=2.0))
            if orig.s_spec > 1e-15:
                ratios.append(deformed.s_spec / orig.s_spec)
        mean_ratio = np.mean(ratios)
        # Random matrices should show ratio ~1.0 (within 5%)
        assert 0.95 < mean_ratio < 1.05, f"Null hypothesis violated: ratio={mean_ratio}"


class TestAnalyzeThermal:
    def test_returns_correct_dataclass(self):
        W = np.random.randn(16, 16)
        result = analyze_thermal(
            W, layer=0, weight_type="Q", alpha=2.0, temp_source="row_norm"
        )
        assert isinstance(result, ThermalProbeResult)
        assert result.layer == 0
        assert result.weight_type == "Q"
        assert result.alpha == 2.0
        assert result.temperature_source == "row_norm"

    def test_suppression_ratio_between_zero_and_one(self):
        rng = np.random.default_rng(42)
        W = rng.standard_normal((32, 32))
        result = analyze_thermal(
            W, layer=0, weight_type="Q", alpha=5.0, temp_source="elementwise"
        )
        assert 0 < result.suppression_ratio <= 1.0

    def test_temperature_stats_present(self):
        W = np.random.randn(16, 16)
        result = analyze_thermal(
            W, layer=0, weight_type="V", alpha=1.0, temp_source="col_norm"
        )
        assert "mean" in result.temperature_stats
        assert "std" in result.temperature_stats
        assert "max" in result.temperature_stats
        assert "min" in result.temperature_stats
