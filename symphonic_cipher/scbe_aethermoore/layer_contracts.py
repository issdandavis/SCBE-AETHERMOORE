"""Typed cross-profile contracts for the canonical SCBE layer stack.

The TypeScript/reference and full Python profiles sometimes implement the same
role with a different coordinate order, composition order, or output shape.
These adapters keep those differences explicit.  They never infer a profile
from vector contents and they fail closed when a required tag is absent.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Optional, Sequence

import numpy as np


class RealificationOrder(str, Enum):
    BLOCK = "BLOCK_REAL_THEN_IMAG"
    INTERLEAVED = "INTERLEAVED_REAL_IMAG"


L02_CANONICAL_ORDER = RealificationOrder.BLOCK


def convert_realification(
    values: Sequence[float],
    *,
    source: RealificationOrder,
    target: RealificationOrder,
) -> np.ndarray:
    """Convert one tagged L02 vector without changing its complex values."""
    try:
        source = RealificationOrder(source)
        target = RealificationOrder(target)
    except ValueError as exc:
        raise ValueError("L02 coordinate order must be declared") from exc
    vector = np.asarray(values, dtype=np.float64)
    if vector.ndim != 1 or vector.size == 0 or vector.size % 2 or not np.all(np.isfinite(vector)):
        raise ValueError("L02 vector must be finite, non-empty, one-dimensional, and even-length")
    if source is target:
        return vector.copy()
    width = vector.size // 2
    if source is RealificationOrder.BLOCK:
        return np.column_stack((vector[:width], vector[width:])).reshape(-1)
    return np.concatenate((vector[0::2], vector[1::2]))


class PhaseCompositionOrder(str, Enum):
    ROTATE_THEN_TRANSLATE = "ROTATE_THEN_TRANSLATE"
    TRANSLATE_THEN_ROTATE = "TRANSLATE_THEN_ROTATE"


L07_CANONICAL_ORDER = PhaseCompositionOrder.ROTATE_THEN_TRANSLATE
L07_FULL_NATIVE_ORDER = PhaseCompositionOrder.TRANSLATE_THEN_ROTATE


def first_plane_rotation(dimension: int, phase: float) -> np.ndarray:
    """Return the exact rotation used by PY_FULL14's first coordinate plane."""
    if not isinstance(dimension, int) or dimension < 1 or not math.isfinite(float(phase)):
        raise ValueError("rotation dimension and phase must be valid")
    rotation = np.eye(dimension, dtype=np.float64)
    if dimension >= 2:
        c, s = math.cos(float(phase)), math.sin(float(phase))
        rotation[0, 0], rotation[0, 1] = c, -s
        rotation[1, 0], rotation[1, 1] = s, c
    return rotation


def adapt_mobius_shift(
    shift: Sequence[float],
    rotation: Sequence[Sequence[float]],
    *,
    source: PhaseCompositionOrder,
    target: PhaseCompositionOrder,
) -> np.ndarray:
    """Conjugate a shift so differently ordered L07 profiles map identically.

    Orthogonal rotations distribute over Mobius addition.  Therefore
    ``a (+) Qx == Q((Q.T a) (+) x)``.
    """
    try:
        source = PhaseCompositionOrder(source)
        target = PhaseCompositionOrder(target)
    except ValueError as exc:
        raise ValueError("L07 composition order must be declared") from exc
    offset = np.asarray(shift, dtype=np.float64)
    matrix = np.asarray(rotation, dtype=np.float64)
    if offset.ndim != 1 or matrix.shape != (offset.size, offset.size):
        raise ValueError("L07 shift and rotation dimensions differ")
    if not np.all(np.isfinite(offset)) or not np.all(np.isfinite(matrix)):
        raise ValueError("L07 shift and rotation must be finite")
    if not np.allclose(matrix.T @ matrix, np.eye(offset.size), atol=1e-9, rtol=0.0):
        raise ValueError("L07 rotation must be orthogonal")
    if source is target:
        return offset.copy()
    if source is PhaseCompositionOrder.ROTATE_THEN_TRANSLATE:
        return matrix.T @ offset
    return matrix @ offset


class ObservationStatus(str, Enum):
    OBSERVED = "OBSERVED"
    MISSING = "MISSING"
    SILENT = "SILENT"
    TOO_SHORT = "TOO_SHORT"


@dataclass(frozen=True)
class SpectralObservation:
    status: ObservationStatus
    score: Optional[float]
    sample_rate_hz: float
    cutoff_hz: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.sample_rate_hz) or self.sample_rate_hz <= 0:
            raise ValueError("L09 sample rate must be positive and finite")
        if not math.isfinite(self.cutoff_hz) or not 0 < self.cutoff_hz < self.sample_rate_hz / 2:
            raise ValueError("L09 cutoff must be positive and below Nyquist")
        if self.status in (ObservationStatus.OBSERVED, ObservationStatus.SILENT):
            if self.score is None or not math.isfinite(self.score) or not 0 <= self.score <= 1:
                raise ValueError("measured L09 observations require a bounded score")
            if self.status is ObservationStatus.SILENT and self.score != 0.0:
                raise ValueError("canonical L09 silence has score 0 and an explicit SILENT mask")
        elif self.score is not None:
            raise ValueError("missing or too-short L09 input cannot masquerade as a score")

    def decision_value(self, *, neutral: float = 0.5) -> float:
        if not math.isfinite(neutral) or not 0 <= neutral <= 1:
            raise ValueError("L09 neutral fallback must be in [0,1]")
        return float(self.score if self.score is not None else neutral)


def spectral_observation(
    signal: Optional[Sequence[float]],
    *,
    measured_score: Optional[float],
    sample_rate_hz: float,
    cutoff_hz: float,
    minimum_samples: int = 4,
) -> SpectralObservation:
    """Attach observation semantics to a profile's bounded spectral score."""
    if signal is None:
        return SpectralObservation(ObservationStatus.MISSING, None, sample_rate_hz, cutoff_hz)
    values = np.asarray(signal)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ValueError("L09 signal must be a finite one-dimensional array")
    if values.size == 0:
        return SpectralObservation(ObservationStatus.MISSING, None, sample_rate_hz, cutoff_hz)
    if float(np.max(np.abs(values))) == 0.0:
        return SpectralObservation(ObservationStatus.SILENT, 0.0, sample_rate_hz, cutoff_hz)
    if values.size < minimum_samples:
        return SpectralObservation(ObservationStatus.TOO_SHORT, None, sample_rate_hz, cutoff_hz)
    return SpectralObservation(ObservationStatus.OBSERVED, measured_score, sample_rate_hz, cutoff_hz)


class TelemetryKind(str, Enum):
    AUDIO_COHERENCE_INPUT = "L14A_AUDIO_COHERENCE_INPUT"
    VERDICT_SONIFICATION_OUTPUT = "L14B_VERDICT_SONIFICATION_OUTPUT"


@dataclass(frozen=True)
class TelemetryEnvelope:
    kind: TelemetryKind
    scalar: Optional[float] = None
    samples: Optional[tuple[float, ...]] = None

    def __post_init__(self) -> None:
        if self.kind is TelemetryKind.AUDIO_COHERENCE_INPUT:
            if self.scalar is None or not math.isfinite(self.scalar) or not 0 <= self.scalar <= 1:
                raise ValueError("L14A requires one bounded scalar")
            if self.samples is not None:
                raise ValueError("L14A cannot carry waveform samples")
            return
        if self.scalar is not None:
            raise ValueError("L14B cannot substitute a scalar for a waveform")
        if not self.samples or not all(math.isfinite(value) and abs(value) <= 1.0 + 1e-12 for value in self.samples):
            raise ValueError("L14B requires a finite, non-empty, unit-amplitude waveform")

    @classmethod
    def coherence(cls, score: float) -> "TelemetryEnvelope":
        return cls(TelemetryKind.AUDIO_COHERENCE_INPUT, scalar=float(score))

    @classmethod
    def sonification(cls, samples: Sequence[float]) -> "TelemetryEnvelope":
        return cls(TelemetryKind.VERDICT_SONIFICATION_OUTPUT, samples=tuple(float(x) for x in samples))


def validate_l14_dependency_order(l14a_step: int, decision_step: int, l14b_step: int) -> bool:
    """Require input evidence before L13 and sonification after L13."""
    if not all(isinstance(value, int) for value in (l14a_step, decision_step, l14b_step)):
        raise TypeError("L14 dependency steps must be integers")
    if not l14a_step < decision_step < l14b_step:
        raise ValueError("canonical telemetry order is L14A -> L13 -> L14B")
    return True


ALIGNMENT_IDS = (
    "SCBE.L02.COORDINATE_PERMUTATION",
    "SCBE.L07.COMPOSITION_ORDER_ADAPTER",
    "SCBE.L09.OBSERVATION_MASK_AND_UNITS",
    "SCBE.L14.TYPED_TELEMETRY_SPLIT",
)
