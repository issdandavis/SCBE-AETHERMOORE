"""Minimal FFT probe for the "mirror problem" attention hypothesis.

This module does not claim to explain model internals. It provides a small,
repeatable experiment surface:

- turn an attention-like matrix into a 1D signal
- compute FFT-derived structure metrics
- compare the result against simple control patterns

The goal is to distinguish obvious structure from obvious noise before moving
to real model attention tensors.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

EPS = 1e-10


@dataclass(frozen=True)
class SpectralProbe:
    s_spec: float
    peak_ratio: float
    spectral_entropy: float
    dominant_bin: int
    energy_total: float


@dataclass(frozen=True)
class ProbeComparison:
    candidate: SpectralProbe
    uniform_control: SpectralProbe
    banded_control: SpectralProbe
    random_control: SpectralProbe


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    raw = np.asarray(matrix)
    dtype = np.complex128 if np.iscomplexobj(raw) else np.float64
    matrix = np.asarray(raw, dtype=dtype)
    if matrix.ndim != 2:
        raise ValueError("attention matrix must be 2D")
    row_sums = matrix.sum(axis=1, keepdims=True)
    identity = np.ones_like(row_sums, dtype=dtype)
    safe = np.where(np.abs(row_sums) < EPS, identity, row_sums)
    return matrix / safe


def attention_signal(matrix: np.ndarray, *, mode: str = "row_mean") -> np.ndarray:
    """Project an attention-like matrix to a 1D signal for spectral analysis."""
    normalized = _normalize_rows(matrix)
    if mode == "row_mean":
        return normalized.mean(axis=0)
    if mode == "column_mean":
        return normalized.mean(axis=1)
    if mode == "diagonal":
        return np.diag(normalized)
    if mode == "flatten":
        return normalized.reshape(-1)
    raise ValueError(f"unsupported attention projection mode: {mode}")


def whole_mirror(matrix: np.ndarray) -> np.ndarray:
    """Whole-mirror transform: negate the full matrix."""
    raw = np.asarray(matrix)
    dtype = np.complex128 if np.iscomplexobj(raw) else np.float64
    array = np.asarray(raw, dtype=dtype)
    if array.ndim != 2:
        raise ValueError("matrix must be 2D")
    return -array


def edge_mirror(matrix: np.ndarray) -> np.ndarray:
    """Edge mirror: swap input/output axes."""
    raw = np.asarray(matrix)
    dtype = np.complex128 if np.iscomplexobj(raw) else np.float64
    array = np.asarray(raw, dtype=dtype)
    if array.ndim != 2:
        raise ValueError("matrix must be 2D")
    return array.T.copy()


def signal_mirror(matrix: np.ndarray) -> np.ndarray:
    """Signal-order mirror: reverse row order while preserving columns."""
    raw = np.asarray(matrix)
    dtype = np.complex128 if np.iscomplexobj(raw) else np.float64
    array = np.asarray(raw, dtype=dtype)
    if array.ndim != 2:
        raise ValueError("matrix must be 2D")
    return np.flip(array, axis=0).copy()


def _normalize_profile(values: np.ndarray) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float64).reshape(-1)
    if vector.size == 0:
        raise ValueError("profile vector must not be empty")
    finite = np.nan_to_num(vector, nan=0.0, posinf=0.0, neginf=0.0)
    shifted = finite - float(np.min(finite))
    spread = float(np.max(shifted))
    if spread < EPS:
        return np.zeros_like(finite)
    return shifted / (spread + EPS)


def derive_thermal_profiles(matrix: np.ndarray, *, source: str = "l2_norm") -> tuple[np.ndarray, np.ndarray]:
    """Derive normalized row/column heat profiles from a matrix."""
    array = np.asarray(matrix, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError("matrix must be 2D")

    if source == "l2_norm":
        row_raw = np.linalg.norm(array, axis=1)
        col_raw = np.linalg.norm(array, axis=0)
    elif source == "abs_mean":
        row_raw = np.mean(np.abs(array), axis=1)
        col_raw = np.mean(np.abs(array), axis=0)
    else:
        raise ValueError(f"unsupported thermal profile source: {source}")

    return _normalize_profile(row_raw), _normalize_profile(col_raw)


def apply_thermal_mirror(
    matrix: np.ndarray,
    *,
    alpha: float = 1.0,
    source: str = "l2_norm",
    min_scale: float = 0.05,
) -> tuple[np.ndarray, dict[str, np.ndarray | float | str]]:
    """Apply a bounded thermal deformation using row/column heat profiles."""
    if alpha < 0:
        raise ValueError("alpha must be non-negative")
    if min_scale <= 0 or min_scale > 1:
        raise ValueError("min_scale must be in (0, 1]")

    array = np.asarray(matrix, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError("matrix must be 2D")

    row_heat, col_heat = derive_thermal_profiles(array, source=source)
    row_scale = np.clip(np.exp(-0.5 * alpha * row_heat), min_scale, 1.0)
    col_scale = np.clip(np.exp(-0.5 * alpha * col_heat), min_scale, 1.0)
    transformed = row_scale[:, None] * array * col_scale[None, :]
    profile = {
        "source": source,
        "variant": "attenuation",
        "alpha": float(alpha),
        "min_scale": float(min_scale),
        "row_heat": row_heat,
        "col_heat": col_heat,
        "row_scale": row_scale,
        "col_scale": col_scale,
    }
    return transformed, profile


def _gaussian_kernel1d(sigma: float) -> np.ndarray:
    if sigma <= 0:
        return np.array([1.0], dtype=np.float64)
    radius = max(1, int(np.ceil(3.0 * sigma)))
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    kernel = np.exp(-(x**2) / (2.0 * sigma**2))
    total = float(np.sum(kernel))
    return kernel / (total + EPS)


def _convolve1d_same(vector: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    radius = len(kernel) // 2
    padded = np.pad(vector, (radius, radius), mode="edge")
    return np.array(
        [float(np.dot(padded[i : i + len(kernel)], kernel)) for i in range(vector.size)],
        dtype=np.float64,
    )


def _gaussian_blur2d(matrix: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return np.asarray(matrix, dtype=np.float64).copy()
    kernel = _gaussian_kernel1d(sigma)
    blurred = np.apply_along_axis(lambda row: _convolve1d_same(row, kernel), 1, matrix)
    return np.apply_along_axis(lambda col: _convolve1d_same(col, kernel), 0, blurred)


def apply_thermal_mirage(
    matrix: np.ndarray,
    *,
    alpha: float = 1.0,
    sigma: float = 3.0,
) -> tuple[np.ndarray, dict[str, np.ndarray | float | str]]:
    """Apply a complex phase-warped mirage field derived from diffused weight magnitude."""
    if alpha < 0:
        raise ValueError("alpha must be non-negative")
    if sigma < 0:
        raise ValueError("sigma must be non-negative")

    raw = np.asarray(matrix)
    dtype = np.complex128 if np.iscomplexobj(raw) else np.float64
    array = np.asarray(raw, dtype=dtype)
    if array.ndim != 2:
        raise ValueError("matrix must be 2D")

    heat_field = _gaussian_blur2d(np.abs(array), sigma)
    max_heat = float(np.max(heat_field))
    if max_heat < EPS:
        phase_field = np.zeros_like(heat_field)
    else:
        phase_field = (heat_field / (max_heat + EPS)) * (np.pi * alpha)
    transformed = array.astype(np.complex128) * np.exp(1j * phase_field)
    profile = {
        "variant": "phase_mirage",
        "alpha": float(alpha),
        "sigma": float(sigma),
        "heat_field": heat_field,
        "phase_field": phase_field,
    }
    return transformed, profile


def compute_spectral_probe(signal: np.ndarray, *, cutoff_ratio: float = 0.25) -> SpectralProbe:
    """Compute simple FFT-based structure metrics for a 1D signal."""
    raw = np.asarray(signal)
    dtype = np.complex128 if np.iscomplexobj(raw) else np.float64
    vector = np.asarray(raw, dtype=dtype).reshape(-1)
    if vector.size < 4:
        raise ValueError("signal must contain at least 4 values")

    centered = vector - np.mean(vector)
    spectrum = np.fft.fft(centered) if np.iscomplexobj(centered) else np.fft.rfft(centered)
    power = np.abs(spectrum) ** 2
    total = float(np.sum(power))
    if total < EPS:
        return SpectralProbe(
            s_spec=1.0,
            peak_ratio=0.0,
            spectral_entropy=0.0,
            dominant_bin=0,
            energy_total=0.0,
        )

    cutoff_index = max(1, int(len(power) * cutoff_ratio))
    low = float(np.sum(power[:cutoff_index]))
    s_spec = low / (total + EPS)

    probs = power / (total + EPS)
    spectral_entropy = float(-np.sum(probs * np.log2(probs + EPS)))
    dominant_bin = int(np.argmax(power))
    peak_ratio = float(np.max(power) / (total + EPS))

    return SpectralProbe(
        s_spec=float(s_spec),
        peak_ratio=peak_ratio,
        spectral_entropy=spectral_entropy,
        dominant_bin=dominant_bin,
        energy_total=total,
    )


def probe_attention_matrix(matrix: np.ndarray, *, mode: str = "row_mean") -> SpectralProbe:
    return compute_spectral_probe(attention_signal(matrix, mode=mode))


def _resolve_shape(rows: int, cols: int | None = None) -> tuple[int, int]:
    row_count = int(rows)
    col_count = int(cols if cols is not None else rows)
    if row_count <= 0 or col_count <= 0:
        raise ValueError("control matrix dimensions must be positive")
    return row_count, col_count


def make_uniform_control(rows: int, cols: int | None = None) -> np.ndarray:
    row_count, col_count = _resolve_shape(rows, cols)
    return np.full((row_count, col_count), 1.0 / col_count, dtype=np.float64)


def make_banded_control(rows: int, cols: int | None = None, *, sigma: float = 1.5) -> np.ndarray:
    row_count, col_count = _resolve_shape(rows, cols)
    rows = []
    for i in range(row_count):
        j = np.arange(col_count, dtype=np.float64)
        if row_count == 1:
            center = (col_count - 1) / 2.0
        else:
            center = i * (col_count - 1) / (row_count - 1)
        row = np.exp(-((j - center) ** 2) / (2.0 * sigma**2))
        rows.append(row)
    return _normalize_rows(np.vstack(rows))


def make_random_control(rows: int, cols: int | None = None, *, seed: int = 7) -> np.ndarray:
    row_count, col_count = _resolve_shape(rows, cols)
    rng = np.random.default_rng(seed)
    return _normalize_rows(rng.random((row_count, col_count)))


def compare_attention_to_controls(matrix: np.ndarray, *, mode: str = "row_mean") -> ProbeComparison:
    shape = np.asarray(matrix).shape
    if len(shape) != 2:
        raise ValueError("attention matrix must be 2D")
    rows, cols = shape
    candidate = probe_attention_matrix(matrix, mode=mode)
    uniform_control = probe_attention_matrix(make_uniform_control(rows, cols), mode=mode)
    banded_control = probe_attention_matrix(make_banded_control(rows, cols), mode=mode)
    random_control = probe_attention_matrix(make_random_control(rows, cols), mode=mode)
    return ProbeComparison(
        candidate=candidate,
        uniform_control=uniform_control,
        banded_control=banded_control,
        random_control=random_control,
    )
