"""
Layer ratio diagnostics for SCBE 14-layer traces.

This module treats phi as a verification target for an observed layer ladder.
It does not modify the live harmonic wall. Instead, it measures whether an
existing 14-layer trace shows adjacent-layer ratios that drift toward phi.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable, Mapping, Sequence

PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_LAYER_COUNT = 14
DEFAULT_TRACE_KEY = "layer_energy"


@dataclass(frozen=True)
class PhiLayerDiagnostic:
    """Summary of phi alignment across a scalar layer ladder."""

    layer_count: int
    value_key: str
    layer_values: list[float]
    adjacent_ratios: list[float]
    target_ratio: float
    tail_start_layer: int
    tolerance: float
    mean_ratio: float
    tail_mean_ratio: float
    ratio_rmse: float
    tail_ratio_rmse: float
    max_abs_error: float
    aligned_ratio_count: int
    tail_aligned_ratio_count: int
    converges_to_phi: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require_positive_finite(values: Iterable[float]) -> list[float]:
    checked: list[float] = []
    for idx, value in enumerate(values, start=1):
        scalar = float(value)
        if not math.isfinite(scalar):
            raise ValueError(f"layer value at position {idx} is not finite")
        if scalar <= 0.0:
            raise ValueError(f"layer value at position {idx} must be > 0")
        checked.append(scalar)
    return checked


def _rmse(values: Sequence[float], target: float) -> float:
    if not values:
        return 0.0
    return math.sqrt(sum((value - target) ** 2 for value in values) / len(values))


def extract_layer_scalar_sequence(
    layer_trace: Sequence[Mapping[str, Any]],
    *,
    key: str = DEFAULT_TRACE_KEY,
    expected_layers: int = DEFAULT_LAYER_COUNT,
) -> list[float]:
    """
    Extract a scalar ladder from a 14-layer trace.

    The trace is expected to contain monotonically ordered layers starting at 1.
    """

    if len(layer_trace) != expected_layers:
        raise ValueError(f"expected {expected_layers} layers, got {len(layer_trace)}")

    values: list[float] = []
    for expected_layer, layer in enumerate(layer_trace, start=1):
        actual_layer = int(layer.get("layer", -1))
        if actual_layer != expected_layer:
            raise ValueError(f"expected layer {expected_layer}, got {actual_layer}")
        if key not in layer:
            raise ValueError(f"missing '{key}' in layer {expected_layer}")
        values.append(float(layer[key]))

    return _require_positive_finite(values)


def compute_phi_layer_diagnostic(
    layer_values: Sequence[float],
    *,
    value_key: str = DEFAULT_TRACE_KEY,
    target_ratio: float = PHI,
    tail_start_layer: int = 8,
    tolerance: float = 0.20,
) -> PhiLayerDiagnostic:
    """
    Compute adjacent-layer ratio diagnostics against phi.

    `tail_start_layer` marks where the "convergence window" begins. With 14
    layers, the default uses the late middle and tail of the ladder.
    """

    if len(layer_values) < 2:
        raise ValueError("need at least two layer values")
    if tail_start_layer < 2 or tail_start_layer > len(layer_values):
        raise ValueError("tail_start_layer must fall within the layer ladder")
    if tolerance <= 0.0:
        raise ValueError("tolerance must be > 0")

    checked = _require_positive_finite(layer_values)
    ratios = [checked[index + 1] / checked[index] for index in range(len(checked) - 1)]
    tail_ratio_index = tail_start_layer - 1
    tail_ratios = ratios[tail_ratio_index:]

    mean_ratio = sum(ratios) / len(ratios)
    tail_mean_ratio = sum(tail_ratios) / len(tail_ratios)
    ratio_rmse = _rmse(ratios, target_ratio)
    tail_ratio_rmse = _rmse(tail_ratios, target_ratio)
    abs_errors = [abs(ratio - target_ratio) for ratio in ratios]
    aligned_ratio_count = sum(1 for error in abs_errors if error <= tolerance)
    tail_aligned_ratio_count = sum(1 for error in abs_errors[tail_ratio_index:] if error <= tolerance)
    converges_to_phi = tail_ratio_rmse <= tolerance and tail_aligned_ratio_count == len(tail_ratios)

    return PhiLayerDiagnostic(
        layer_count=len(checked),
        value_key=value_key,
        layer_values=[round(value, 6) for value in checked],
        adjacent_ratios=[round(value, 6) for value in ratios],
        target_ratio=round(float(target_ratio), 6),
        tail_start_layer=tail_start_layer,
        tolerance=round(float(tolerance), 6),
        mean_ratio=round(mean_ratio, 6),
        tail_mean_ratio=round(tail_mean_ratio, 6),
        ratio_rmse=round(ratio_rmse, 6),
        tail_ratio_rmse=round(tail_ratio_rmse, 6),
        max_abs_error=round(max(abs_errors), 6),
        aligned_ratio_count=aligned_ratio_count,
        tail_aligned_ratio_count=tail_aligned_ratio_count,
        converges_to_phi=converges_to_phi,
    )


def compute_phi_trace_diagnostic(
    layer_trace: Sequence[Mapping[str, Any]],
    *,
    key: str = DEFAULT_TRACE_KEY,
    target_ratio: float = PHI,
    tail_start_layer: int = 8,
    tolerance: float = 0.20,
) -> PhiLayerDiagnostic:
    """Run the phi diagnostic directly on a 14-layer trace structure."""

    values = extract_layer_scalar_sequence(layer_trace, key=key)
    return compute_phi_layer_diagnostic(
        values,
        value_key=key,
        target_ratio=target_ratio,
        tail_start_layer=tail_start_layer,
        tolerance=tolerance,
    )


def compute_phi_scan_diagnostic(
    scan: Any,
    *,
    key: str = DEFAULT_TRACE_KEY,
    target_ratio: float = PHI,
    tail_start_layer: int = 8,
    tolerance: float = 0.20,
) -> PhiLayerDiagnostic:
    """Run the phi diagnostic on a DyeScan object or dict-like scan payload."""

    if isinstance(scan, Mapping):
        layer_trace = scan.get("layer_trace")
    else:
        layer_trace = getattr(scan, "layer_trace", None)
    if not isinstance(layer_trace, Sequence):
        raise ValueError("scan does not expose a layer_trace sequence")
    return compute_phi_trace_diagnostic(
        layer_trace,
        key=key,
        target_ratio=target_ratio,
        tail_start_layer=tail_start_layer,
        tolerance=tolerance,
    )
