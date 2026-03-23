"""Test boundary exploitation attacks against the Poincare ball model.

Boundary attacks push representations toward the edge of the Poincare disk
where:
  1. Distances become exponentially large (cost explosion)
  2. The harmonic wall H(d,R) = R^(d^2) provides exponential resistance
  3. Numerical precision issues can create edge-case behavior

These tests verify that the boundary detection signal catches
attempts to push state toward the disk edge.
"""
import math

import pytest
from tests.adversarial.attack_corpus import BASELINE_CLEAN, BOUNDARY_EXPLOIT
from tests.adversarial.scbe_harness import (
    SCBEDetectionGate,
    run_benchmark,
    text_to_tongue_coords,
    TONGUE_WEIGHTS,
)


@pytest.fixture()
def gate():
    g = SCBEDetectionGate()
    g.calibrate([p["prompt"] for p in BASELINE_CLEAN])
    return g


class TestBoundaryExploits:
    def test_high_detection_rate(self, gate):
        result = run_benchmark(gate, BOUNDARY_EXPLOIT)
        assert result.detection_rate >= 0.60

    def test_boundary_norm_elevated(self, gate):
        """Boundary attacks should produce coords with high L2 norm."""
        for attack in BOUNDARY_EXPLOIT:
            coords = text_to_tongue_coords(attack["prompt"])
            norm = math.sqrt(sum(c * c for c in coords))
            print(f"\n  {attack['id']}: norm={norm:.3f}")
            # At least some boundary attacks should have elevated norms
        max_norm = max(
            math.sqrt(sum(c * c for c in text_to_tongue_coords(a["prompt"])))
            for a in BOUNDARY_EXPLOIT
        )
        assert max_norm > 1.0

    def test_harmonic_cost_extreme(self, gate):
        """Boundary attacks should produce extreme harmonic costs."""
        costs = [gate.process(a["prompt"]).harmonic_cost for a in BOUNDARY_EXPLOIT]
        max_cost = max(costs)
        avg_cost = sum(costs) / len(costs)
        print(f"\n  Boundary: max_cost={max_cost:.2f}, avg_cost={avg_cost:.2f}")
        assert max_cost > 50.0  # Should be well above clean text

    def test_clean_text_not_at_boundary(self, gate):
        """Clean text should have coords well within the ball."""
        for p in BASELINE_CLEAN:
            coords = text_to_tongue_coords(p["prompt"])
            norm = math.sqrt(sum(c * c for c in coords))
            assert norm < 1.5, f"Clean text {p['id']} at boundary: norm={norm:.3f}"
