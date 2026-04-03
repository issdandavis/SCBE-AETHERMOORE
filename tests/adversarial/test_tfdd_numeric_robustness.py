"""Adversarial Numeric Robustness Tests for TFDD + World Tree Metric.

Tests NaN propagation, infinity overflow, boundary precision,
monotonicity, convexity, and layer independence.

These are red-team validation tests — they attack the math itself.
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.symphonic_cipher.scbe_aethermoore.axiom_grouped.geodesic_gateways import (
    WorldTreeMetric,
    HyperspacePoint,
    IdealState,
    TFDD,
    discouragement_function,
    discouragement_derivative,
    positivity_weight,
    emotional_valence,
    egg_activation,
    RiemannSpectralPrior,
    LyapunovMonitor,
    hausdorff_roughness,
)
from src.symphonic_cipher.scbe_aethermoore.axiom_grouped.langues_metric import (
    langues_value,
    LanguesMetric,
    FluxingLanguesMetric,
)


class TestNaNGuards:
    """NaN inputs must never propagate through the system."""

    def test_discouragement_nan_input(self):
        result = discouragement_function(float("nan"))
        assert math.isfinite(result), f"NaN propagated: {result}"

    def test_discouragement_derivative_nan(self):
        result = discouragement_derivative(float("nan"))
        assert math.isfinite(result), f"NaN propagated: {result}"

    def test_positivity_weight_nan(self):
        result = positivity_weight(float("nan"))
        assert math.isfinite(result), f"NaN propagated: {result}"

    def test_langues_value_nan(self):
        result = langues_value(float("nan"))
        assert math.isfinite(result), f"NaN propagated: {result}"

    def test_egg_activation_nan(self):
        result = egg_activation(float("nan"))
        assert math.isfinite(result), f"NaN propagated: {result}"

    def test_riemann_prior_nan(self):
        rh = RiemannSpectralPrior()
        result = rh.compute(float("nan"))
        assert math.isfinite(result), f"NaN propagated: {result}"


class TestInfinityGuards:
    """Infinity inputs must be clamped, not overflow."""

    def test_discouragement_neg_inf(self):
        result = discouragement_function(float("-inf"))
        assert math.isfinite(result), f"Overflow: {result}"
        assert result > 0, "Must remain positive"

    def test_discouragement_pos_inf(self):
        result = discouragement_function(float("inf"))
        assert math.isfinite(result), f"Overflow: {result}"

    def test_discouragement_derivative_neg_inf(self):
        result = discouragement_derivative(float("-inf"))
        assert math.isfinite(result), f"Overflow: {result}"

    def test_langues_value_inf(self):
        result = langues_value(float("inf"))
        assert result == pytest.approx(0.0, abs=1e-10)

    def test_langues_value_neg(self):
        # Negative L should still produce finite value
        result = langues_value(-1.0)
        assert math.isfinite(result)


class TestMonotonicity:
    """TFDD must be strictly monotonically decreasing as E increases."""

    def test_tfdd_monotonic_negative_range(self):
        values = [discouragement_function(e) for e in [-10, -5, -2, -1, -0.5, 0]]
        for i in range(len(values) - 1):
            assert values[i] >= values[i + 1], (
                f"Monotonicity violated: D({-10 + i*2}) = {values[i]} < D({-10 + (i+1)*2}) = {values[i+1]}"
            )

    def test_tfdd_flat_in_positive_range(self):
        """D(e) should be constant (= w) for all e >= 0."""
        values = [discouragement_function(e) for e in [0, 0.5, 1, 5, 100]]
        for v in values:
            assert v == pytest.approx(1.0, rel=1e-10), f"Not flat in positive range: {v}"

    def test_langues_value_monotonic(self):
        """Value must decrease as cost increases."""
        costs = [0, 1, 5, 10, 50, 100, 1000]
        values = [langues_value(c) for c in costs]
        for i in range(len(values) - 1):
            assert values[i] > values[i + 1], (
                f"Value not decreasing: V({costs[i]})={values[i]} >= V({costs[i+1]})={values[i+1]}"
            )


class TestBoundaryBehavior:
    """Test behavior at critical boundaries."""

    def test_discouragement_at_zero(self):
        """Smooth transition at e=0."""
        below = discouragement_function(-0.001)
        at = discouragement_function(0.0)
        above = discouragement_function(0.001)
        assert below > at, "Below zero should cost more"
        assert at == above, "At and above zero should be equal (baseline)"

    def test_langues_value_at_zero(self):
        assert langues_value(0.0) == 1.0

    def test_langues_value_approaches_zero(self):
        assert langues_value(1e10) < 1e-9

    def test_positivity_weight_bounded(self):
        """P(e) must stay in (1-gamma, 1+gamma)."""
        gamma = 0.5
        for e in [-1000, -10, -1, 0, 1, 10, 1000]:
            p = positivity_weight(e, gamma)
            assert 0.5 <= p <= 1.5, f"P({e}) = {p} out of bounds"


class TestExponentialClamp:
    """Verify the exponential clamp prevents overflow."""

    def test_extreme_negative_clamped(self):
        result = discouragement_function(-1000.0)
        assert math.isfinite(result), f"Overflow at e=-1000: {result}"
        # Should be clamped at exp(50) ~ 5e21
        assert result < 1e22, f"Clamp failed: {result}"

    def test_extreme_negative_derivative_clamped(self):
        result = discouragement_derivative(-1000.0)
        assert math.isfinite(result), f"Overflow at e=-1000: {result}"


class TestLayerIndependence:
    """TFDD and other layers must not override each other incorrectly."""

    def test_high_tfdd_does_not_override_bad_geometry(self):
        """Positive emotion should NOT make a geometrically bad state ALLOW."""
        wt = WorldTreeMetric()
        # Good emotion but bad position (far from ideal)
        bad_position = HyperspacePoint(time=0, intent=2.0, policy=0.0, trust=0.1, risk=1.0, entropy=0.9)
        result = wt.compute_total(bad_position)
        # L_total should still be high even if emotional layer is favorable
        assert result["L_total"] > 10, f"Bad geometry not penalized: L_total={result['L_total']}"

    def test_lyapunov_always_reports(self):
        """Lyapunov monitor should always return a valid result."""
        wt = WorldTreeMetric()
        safe = HyperspacePoint(time=0, intent=0, policy=0.5, trust=0.9, risk=0.1, entropy=0.2)
        result = wt.compute_total(safe)
        assert "lyapunov" in result
        assert "is_stable" in result["lyapunov"]
        assert isinstance(result["lyapunov"]["is_stable"], bool)


class TestNuclearInput:
    """The ultimate test: every input is broken simultaneously."""

    def test_all_nan_inf_input_produces_finite_output(self):
        """No combination of bad inputs can break the system globally."""
        wt = WorldTreeMetric()
        nightmare = HyperspacePoint(
            time=float("nan"),
            intent=float("inf"),
            policy=float("-inf"),
            trust=float("nan"),
            risk=float("inf"),
            entropy=float("nan"),
        )
        r = wt.compute_total(nightmare)

        for k, v in r.items():
            if isinstance(v, (int, float)):
                assert math.isfinite(v), f"{k} is not finite: {v}"

    def test_zero_vector_produces_finite_output(self):
        wt = WorldTreeMetric()
        zero = HyperspacePoint(time=0, intent=0, policy=0, trust=0, risk=0, entropy=0)
        r = wt.compute_total(zero)
        assert math.isfinite(r["L_total"])
        assert math.isfinite(r["value"])

    def test_extreme_values_produce_finite_output(self):
        wt = WorldTreeMetric()
        extreme = HyperspacePoint(time=1e10, intent=1e10, policy=1e10, trust=1e10, risk=1e10, entropy=1e10)
        r = wt.compute_total(extreme)
        for k, v in r.items():
            if isinstance(v, (int, float)):
                assert math.isfinite(v), f"{k} overflowed at extreme input: {v}"


class TestWorldTreeCompleteness:
    """Verify the unified metric returns all expected fields."""

    def test_all_7_components_present(self):
        wt = WorldTreeMetric()
        safe = HyperspacePoint()
        r = wt.compute_total(safe)
        required = ["L_f", "L_gate", "L_fractal", "L_emotional", "L_eggs", "L_rh",
                     "L_total", "value", "D_f", "emotional_valence", "nearest_geodesic",
                     "emotional_state", "egg_profile", "lyapunov"]
        for key in required:
            assert key in r, f"Missing field: {key}"

    def test_all_outputs_finite(self):
        wt = WorldTreeMetric()
        for state in [
            HyperspacePoint(),
            HyperspacePoint(time=0, intent=0, policy=0.5, trust=0.9, risk=0.1, entropy=0.2),
            HyperspacePoint(time=0, intent=1.5, policy=0.1, trust=0.2, risk=0.9, entropy=0.8),
        ]:
            r = wt.compute_total(state)
            for key in ["L_f", "L_gate", "L_fractal", "L_emotional", "L_eggs", "L_rh", "L_total", "value"]:
                assert math.isfinite(r[key]), f"{key} is not finite: {r[key]} for state {state}"
