import math

import pytest

from src.video.layer_phi_verifier import (
    PHI,
    compute_phi_layer_diagnostic,
    compute_phi_scan_diagnostic,
    compute_phi_trace_diagnostic,
    extract_layer_scalar_sequence,
)


def _make_trace(values: list[float], key: str = "layer_energy") -> list[dict[str, float | int | str]]:
    return [
        {
            "layer": index + 1,
            "name": f"L{index + 1}",
            key: value,
            "cumulative_energy": sum(values[: index + 1]),
        }
        for index, value in enumerate(values)
    ]


def test_phi_ladder_converges_cleanly() -> None:
    values = [PHI**index for index in range(14)]
    diagnostic = compute_phi_layer_diagnostic(values, tail_start_layer=8, tolerance=0.001)

    assert diagnostic.converges_to_phi is True
    assert diagnostic.tail_mean_ratio == pytest.approx(PHI, abs=1e-6)
    assert diagnostic.tail_ratio_rmse == pytest.approx(0.0, abs=1e-6)
    assert diagnostic.aligned_ratio_count == 13


def test_non_phi_ladder_reports_large_drift() -> None:
    values = [2.0**index for index in range(14)]
    diagnostic = compute_phi_layer_diagnostic(values, tail_start_layer=8, tolerance=0.05)

    assert diagnostic.converges_to_phi is False
    assert diagnostic.tail_mean_ratio == pytest.approx(2.0, abs=1e-6)
    assert diagnostic.tail_ratio_rmse > 0.35
    assert diagnostic.max_abs_error > 0.35


def test_trace_extraction_requires_monotone_14_layer_shape() -> None:
    trace = _make_trace([1.0 + 0.1 * index for index in range(14)])
    values = extract_layer_scalar_sequence(trace)

    assert len(values) == 14
    assert values[0] == pytest.approx(1.0)
    assert values[-1] == pytest.approx(2.3)


def test_trace_diagnostic_uses_existing_layer_energy_key() -> None:
    trace = _make_trace([1.0 + 0.05 * index for index in range(14)])
    diagnostic = compute_phi_trace_diagnostic(trace)

    assert diagnostic.layer_count == 14
    assert len(diagnostic.adjacent_ratios) == 13
    assert all(math.isfinite(ratio) for ratio in diagnostic.adjacent_ratios)


def test_real_dye_scan_returns_finite_phi_metrics_when_available() -> None:
    try:
        from src.video.dye_injection import DyeInjector
    except ImportError:
        pytest.skip("dye injection dependencies not available")

    injector = DyeInjector()
    scan = injector.inject("Route a standard governance packet through the active relay.")
    diagnostic = compute_phi_scan_diagnostic(scan)

    assert diagnostic.layer_count == 14
    assert len(diagnostic.adjacent_ratios) == 13
    assert all(math.isfinite(ratio) for ratio in diagnostic.adjacent_ratios)
    assert diagnostic.value_key == "layer_energy"
