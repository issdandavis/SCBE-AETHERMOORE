"""Golden vector tests for 14-layer pipeline cross-language parity.

These tests load golden vectors from pipeline14_golden.json and verify
that the Python implementations produce identical results. The same
JSON file should be consumed by the TypeScript test suite so both
languages are tested against the same ground-truth values.

All expected values in the JSON are derived from closed-form math,
NOT copied from implementation output.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List

import pytest

# ---------------------------------------------------------------------------
# Load golden vectors
# ---------------------------------------------------------------------------
_VECTOR_FILE = Path(__file__).resolve().parent / "pipeline14_golden.json"


def _load_vectors() -> Dict[str, Any]:
    return json.loads(_VECTOR_FILE.read_text(encoding="utf-8"))


GOLDEN = _load_vectors()
ALL_VECTORS: List[Dict[str, Any]] = GOLDEN["vectors"]

# ---------------------------------------------------------------------------
# Import the Python implementations under test
# ---------------------------------------------------------------------------
from src.primitives.phi_poincare import (  # noqa: E402
    PHI,
    phi_shell_radius,
    harmonic_cost_at_shell,
    fibonacci_ternary_consensus,
)


# ---------------------------------------------------------------------------
# Pure-math reference implementations (no dependency on src/)
# These mirror the formulas so we can cross-check both the implementation
# AND the golden vector values.
# ---------------------------------------------------------------------------
def _ref_hyperbolic_distance(u: List[float], v: List[float]) -> float:
    """dH(u,v) = acosh(1 + 2*||u-v||^2 / ((1-||u||^2)(1-||v||^2)))"""
    assert len(u) == len(v), "dimension mismatch"
    norm_u_sq = sum(x * x for x in u)
    norm_v_sq = sum(x * x for x in v)
    assert norm_u_sq < 1.0 and norm_v_sq < 1.0, "points must be inside unit ball"
    diff_sq = sum((a - b) ** 2 for a, b in zip(u, v))
    denom = (1.0 - norm_u_sq) * (1.0 - norm_v_sq)
    arg = 1.0 + 2.0 * diff_sq / denom
    return math.acosh(arg)


def _ref_harmonic_wall(d: float, R: float) -> float:
    """H(d, R) = R^(d^2)"""
    return R ** (d**2)


def _ref_phi_shell_radius(k: int) -> float:
    """r(k) = phi^k / (1 + phi^k)"""
    phi_k = PHI**k
    return phi_k / (1.0 + phi_k)


def _ref_harmonic_cost_at_shell(k: int, R: float) -> float:
    """Compose shell radius with harmonic wall."""
    r = _ref_phi_shell_radius(k)
    return R ** (r**2)


# ---------------------------------------------------------------------------
# Helpers to select vectors by function name
# ---------------------------------------------------------------------------
def _vectors_for(func_name: str) -> List[Dict[str, Any]]:
    return [v for v in ALL_VECTORS if v["function"] == func_name]


# ---------------------------------------------------------------------------
# Test: metadata
# ---------------------------------------------------------------------------
class TestGoldenVectorMetadata:
    def test_version(self) -> None:
        assert GOLDEN["version"] == "1.0.0"

    def test_has_vectors(self) -> None:
        assert len(ALL_VECTORS) >= 10, "Need at least 10 golden vectors"

    def test_all_vectors_have_required_keys(self) -> None:
        required = {"id", "layer", "function", "inputs", "expected", "tolerance"}
        for v in ALL_VECTORS:
            missing = required - set(v.keys())
            assert not missing, f"Vector {v.get('id', '?')} missing keys: {missing}"


# ---------------------------------------------------------------------------
# Test: L5 hyperbolic distance
# ---------------------------------------------------------------------------
class TestL5HyperbolicDistance:
    """Verify hyperbolic distance against golden vectors using the reference formula."""

    @pytest.mark.parametrize(
        "vec",
        _vectors_for("hyperbolic_distance_poincare"),
        ids=lambda v: v["id"],
    )
    def test_reference_matches_golden(self, vec: Dict[str, Any]) -> None:
        u = vec["inputs"]["u"]
        v = vec["inputs"]["v"]
        actual = _ref_hyperbolic_distance(u, v)
        assert actual == pytest.approx(
            vec["expected"], abs=vec["tolerance"]
        ), f"[{vec['id']}] ref={actual}, expected={vec['expected']}"


# ---------------------------------------------------------------------------
# Test: L12 harmonic wall  H(d, R) = R^(d^2)
# ---------------------------------------------------------------------------
class TestL12HarmonicWall:
    @pytest.mark.parametrize(
        "vec",
        _vectors_for("harmonic_wall"),
        ids=lambda v: v["id"],
    )
    def test_reference_matches_golden(self, vec: Dict[str, Any]) -> None:
        d = vec["inputs"]["d"]
        R = vec["inputs"]["R"]
        actual = _ref_harmonic_wall(d, R)
        assert actual == pytest.approx(
            vec["expected"], abs=vec["tolerance"]
        ), f"[{vec['id']}] ref={actual}, expected={vec['expected']}"


# ---------------------------------------------------------------------------
# Test: Sacred Tongue weights  PHI^k
# ---------------------------------------------------------------------------
class TestTongueWeights:
    def test_phi_constant(self) -> None:
        """PHI must equal (1+sqrt(5))/2 to full float64 precision."""
        expected_phi = (1.0 + math.sqrt(5.0)) / 2.0
        assert PHI == pytest.approx(expected_phi, abs=1e-15)

    def test_tongue_weights_match_golden(self) -> None:
        vec = next(v for v in ALL_VECTORS if v["function"] == "tongue_weights")
        for k, exp in zip(vec["inputs"]["k_values"], vec["expected"]):
            actual = PHI**k
            assert actual == pytest.approx(
                exp, abs=vec["tolerance"]
            ), f"Tongue weight k={k}: actual={actual}, expected={exp}"


# ---------------------------------------------------------------------------
# Test: phi shell radius  r(k) = phi^k / (1 + phi^k)
# ---------------------------------------------------------------------------
class TestPhiShellRadius:
    @pytest.mark.parametrize(
        "vec",
        _vectors_for("phi_shell_radius"),
        ids=lambda v: v["id"],
    )
    def test_impl_matches_golden(self, vec: Dict[str, Any]) -> None:
        """Verify the src.primitives.phi_poincare implementation."""
        k = vec["inputs"]["k"]
        actual = phi_shell_radius(k)
        assert actual == pytest.approx(
            vec["expected"], abs=vec["tolerance"]
        ), f"[{vec['id']}] phi_shell_radius({k})={actual}, expected={vec['expected']}"

    @pytest.mark.parametrize(
        "vec",
        _vectors_for("phi_shell_radius"),
        ids=lambda v: v["id"],
    )
    def test_reference_matches_golden(self, vec: Dict[str, Any]) -> None:
        """Cross-check: pure-math reference agrees with golden value."""
        k = vec["inputs"]["k"]
        actual = _ref_phi_shell_radius(k)
        assert actual == pytest.approx(
            vec["expected"], abs=vec["tolerance"]
        ), f"[{vec['id']}] ref phi_shell_radius({k})={actual}, expected={vec['expected']}"

    def test_monotonically_increasing(self) -> None:
        """Shell radii must increase with k (approaching boundary)."""
        radii = [phi_shell_radius(k) for k in range(6)]
        for i in range(1, len(radii)):
            assert radii[i] > radii[i - 1], f"r({i})={radii[i]} <= r({i-1})={radii[i-1]}"

    def test_bounded_in_unit_ball(self) -> None:
        """All shell radii must be in (0, 1)."""
        for k in range(20):
            r = phi_shell_radius(k)
            assert 0.0 < r < 1.0, f"phi_shell_radius({k})={r} out of (0,1)"


# ---------------------------------------------------------------------------
# Test: harmonic cost at shell
# ---------------------------------------------------------------------------
class TestHarmonicCostAtShell:
    @pytest.mark.parametrize(
        "vec",
        _vectors_for("harmonic_cost_at_shell"),
        ids=lambda v: v["id"],
    )
    def test_impl_matches_golden(self, vec: Dict[str, Any]) -> None:
        k = vec["inputs"]["k"]
        R = vec["inputs"]["R"]
        actual = harmonic_cost_at_shell(k, R)
        assert actual == pytest.approx(
            vec["expected"], abs=vec["tolerance"]
        ), f"[{vec['id']}] harmonic_cost_at_shell({k}, {R})={actual}, expected={vec['expected']}"

    @pytest.mark.parametrize(
        "vec",
        _vectors_for("harmonic_cost_at_shell"),
        ids=lambda v: v["id"],
    )
    def test_reference_matches_golden(self, vec: Dict[str, Any]) -> None:
        k = vec["inputs"]["k"]
        R = vec["inputs"]["R"]
        actual = _ref_harmonic_cost_at_shell(k, R)
        assert actual == pytest.approx(
            vec["expected"], abs=vec["tolerance"]
        ), f"[{vec['id']}] ref cost({k}, {R})={actual}, expected={vec['expected']}"

    def test_cost_increases_with_k(self) -> None:
        """Higher shells must be more expensive."""
        costs = [harmonic_cost_at_shell(k, 4.0) for k in range(6)]
        for i in range(1, len(costs)):
            assert costs[i] > costs[i - 1], f"cost(k={i}) not > cost(k={i-1})"


# ---------------------------------------------------------------------------
# Test: Fibonacci ternary consensus
# ---------------------------------------------------------------------------
class TestFibonacciTernaryConsensus:
    @pytest.mark.parametrize(
        "vec",
        _vectors_for("fibonacci_ternary_consensus"),
        ids=lambda v: v["id"],
    )
    def test_impl_matches_golden(self, vec: Dict[str, Any]) -> None:
        history = vec["inputs"]["history"]
        actual = fibonacci_ternary_consensus(history)
        assert actual == vec["expected"], f"[{vec['id']}] consensus({history})={actual}, expected={vec['expected']}"

    def test_neutral_holds_position(self) -> None:
        """All zeros should leave index at 0 -> FIB[0]=1."""
        assert fibonacci_ternary_consensus([0, 0, 0, 0, 0]) == 1

    def test_single_inhibit_from_zero_clamps(self) -> None:
        """Inhibit at bottom clamps to index 0."""
        assert fibonacci_ternary_consensus([-1]) == 1

    def test_activate_sequence_is_fibonacci(self) -> None:
        """consensus([1]*N) for N=0..10 should trace the Fibonacci ladder."""
        fib = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
        for n, expected in enumerate(fib):
            actual = fibonacci_ternary_consensus([1] * n)
            assert actual == expected, f"N={n}: got {actual}, expected {expected}"
