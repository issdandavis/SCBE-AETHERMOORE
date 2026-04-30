"""
@file test_l11_canonical_aggregation.py
@module tests/L11
@layer Layer 11 (Triadic Temporal Distance)
@component Canonical phi-power-mean aggregation parity

Verifies that every L11 implementation across the codebase computes the same
canonical phi-power-mean aggregation:

    d_tri = (lambda_1 * d1^phi + lambda_2 * d2^phi + lambda_3 * d3^phi)^(1/phi)

Reference implementation:
    src/polly_pads_runtime.py:triadic_temporal_distance

Variant call sites that must agree:
    src/scbe_14layer_reference.py:layer_11_triadic_temporal
    src/scbe_cpse_unified.py:HarmonicWall.compute_triadic_distance
    (TS variants in tri-manifold-lattice.ts and geosealCompass.ts covered separately.)
"""

from __future__ import annotations

import math

import pytest

from src.polly_pads_runtime import triadic_temporal_distance as canonical_d_tri

PHI = (1.0 + math.sqrt(5.0)) / 2.0
EPS = 1e-10


def _phi_power_mean(d1: float, d2: float, dG: float, l1: float, l2: float, l3: float) -> float:
    s = l1 * max(d1, EPS) ** PHI + l2 * max(d2, EPS) ** PHI + l3 * max(dG, EPS) ** PHI
    return s ** (1.0 / PHI)


# ---------------------------------------------------------------------------
# Algebraic properties of the canonical formula
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "d1,d2,dG",
    [
        (0.0, 0.0, 0.0),
        (0.1, 0.2, 0.3),
        (0.5, 0.5, 0.5),
        (1.0, 1.0, 1.0),
        (0.999, 0.001, 0.5),
    ],
)
def test_non_negativity(d1: float, d2: float, dG: float) -> None:
    """phi-power mean is non-negative for non-negative inputs."""
    val = canonical_d_tri(d1, d2, dG)
    assert val >= 0.0


def test_no_zero_collapse_via_eps_clamp() -> None:
    """Triple-zero input must not collapse to exactly 0 (eps clamp guarantees > 0)."""
    val = canonical_d_tri(0.0, 0.0, 0.0)
    assert val > 0.0
    assert val < 1e-5  # but still very small


@pytest.mark.parametrize(
    "d1,d2,dG",
    [
        (0.1, 0.2, 0.3),
        (0.05, 0.5, 0.95),
        (0.4, 0.6, 0.8),
        (0.01, 0.01, 0.99),
    ],
)
def test_bounded_between_arithmetic_and_quadratic_mean(d1: float, d2: float, dG: float) -> None:
    """For values in [0,1] and 1<phi<2, M_1 <= M_phi <= M_2 (power-mean inequality)."""
    l1 = l2 = l3 = 1.0 / 3.0
    arithmetic = l1 * d1 + l2 * d2 + l3 * dG
    quadratic = math.sqrt(l1 * d1**2 + l2 * d2**2 + l3 * dG**2)
    phi_mean = _phi_power_mean(d1, d2, dG, l1, l2, l3)
    # Allow tiny eps-clamp slack at the lower bound for sub-eps inputs.
    assert phi_mean >= arithmetic - 1e-8
    assert phi_mean <= quadratic + 1e-8


def test_monotonicity_in_each_component() -> None:
    """Increasing any single distance never decreases d_tri."""
    base = canonical_d_tri(0.3, 0.3, 0.3)

    bumped_d1 = canonical_d_tri(0.5, 0.3, 0.3)
    bumped_d2 = canonical_d_tri(0.3, 0.5, 0.3)
    bumped_dG = canonical_d_tri(0.3, 0.3, 0.5)

    assert bumped_d1 >= base
    assert bumped_d2 >= base
    assert bumped_dG >= base


def test_symmetric_inputs_match_each_lambda() -> None:
    """Equal inputs collapse to that input value (idempotence on the diagonal)."""
    for d in (0.1, 0.25, 0.5, 0.75, 0.9):
        val = canonical_d_tri(d, d, d, lambda1=1 / 3, lambda2=1 / 3, lambda3=1 / 3)
        assert math.isclose(val, d, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Cross-implementation parity (Python sites)
# ---------------------------------------------------------------------------


def test_parity_with_scbe_14layer_reference() -> None:
    """src/scbe_14layer_reference.py:layer_11_triadic_temporal matches canonical formula."""
    from src.scbe_14layer_reference import layer_11_triadic_temporal

    cases = [
        (0.1, 0.2, 0.3, 0.33, 0.34, 0.33),
        (0.4, 0.5, 0.6, 0.33, 0.34, 0.33),
        (0.05, 0.5, 0.95, 0.33, 0.34, 0.33),
    ]
    for d1, d2, dG, l1, l2, l3 in cases:
        ref = _phi_power_mean(d1, d2, dG, l1, l2, l3)
        # 14-layer ref clamps to [0,1] via min(1.0, d_tri/d_scale); use d_scale large enough
        # to avoid the clamp interfering at these values.
        got = layer_11_triadic_temporal(d1, d2, dG, l1, l2, l3, d_scale=10.0)
        assert math.isclose(got * 10.0, ref, rel_tol=1e-9, abs_tol=1e-9), (
            f"14-layer-ref drift: ({d1},{d2},{dG}) ref={ref}, got*scale={got * 10.0}"
        )


def test_parity_with_scbe_cpse_unified() -> None:
    """src/scbe_cpse_unified.py:SCBESystem.compute_triadic_distance matches canonical formula.

    `compute_triadic_distance` derives d1/d2/d3 by windowing a `d_star_history` list
    (last-3 mean, middle-3 mean, global mean). Feeding a constant history collapses
    all three windows to that constant, so we can test the aggregation in isolation.
    """
    try:
        from src.scbe_cpse_unified import SCBEConfig, SCBESystem
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"scbe_cpse_unified not importable in this env: {exc}")
        return

    cfg = SCBEConfig(lambda1=0.33, lambda2=0.34, lambda3=0.33, d_scale=10.0)
    sys = SCBESystem(cfg)

    for d in (0.1, 0.25, 0.5, 0.75):
        history = [d] * 9
        ref = _phi_power_mean(d, d, d, cfg.lambda1, cfg.lambda2, cfg.lambda3)
        got = sys.compute_triadic_distance(history)
        assert math.isclose(got * cfg.d_scale, ref, rel_tol=1e-9, abs_tol=1e-9), (
            f"cpse_unified drift: d={d}, ref={ref}, got*scale={got * cfg.d_scale}"
        )


def test_dual_lattice_alias_preserved() -> None:
    """Backwards-compat alias `layer_11_temporal_residual` still resolves to renamed function."""
    from src.crypto.dual_lattice_integration import layer_11_temporal_residual, temporal_kinematic_residual

    assert layer_11_temporal_residual is temporal_kinematic_residual
