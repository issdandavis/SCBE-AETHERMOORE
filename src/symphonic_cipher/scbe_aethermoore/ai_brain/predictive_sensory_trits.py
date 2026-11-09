"""Predictive dual-trit sidecar for the canonical Layer-14A observation lane.

This module does not replace any fourteen-layer runtime.  It enriches a typed
``SpectralObservation`` with prediction error, adaptation, omission, and
precision state before an explicit adapter chooses whether to consume it.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from ..layer_contracts import ObservationStatus, SpectralObservation
from .dual_ternary import DualTernaryState


def _trit(value: float, threshold: float) -> int:
    if value > threshold:
        return 1
    if value < -threshold:
        return -1
    return 0


@dataclass(frozen=True)
class PredictiveTritFrame:
    """One typed Layer-14A predictive observation.

    ``primary`` is signed prediction error. ``mirror`` is observation context:
    +1 for present evidence, 0 for measured silence, and -1 for an expected
    omission. Missing and too-short inputs remain distinct in ``status`` and
    are never encoded as ordinary trit zero.
    """

    status: ObservationStatus
    state: DualTernaryState
    observed: float | None
    predicted: float | None
    residual: float | None
    adaptation: float
    precision: float
    omission: bool
    route_score: float

    @property
    def trit_pair(self) -> tuple[int, int]:
        return self.state.primary, self.state.mirror


class PredictiveSensoryTritRouter:
    """Small state machine over an existing bounded Layer-14A scalar lane."""

    def __init__(
        self,
        *,
        prediction_alpha: float = 0.2,
        adaptation_alpha: float = 0.2,
        residual_threshold: float = 0.05,
        omission_threshold: float = 0.1,
        similarity_scale: float = 0.1,
        adaptation_weight: float = 0.25,
        omission_weight: float = 0.5,
    ) -> None:
        for name, value in (
            ("prediction_alpha", prediction_alpha),
            ("adaptation_alpha", adaptation_alpha),
        ):
            if not math.isfinite(value) or not 0 < value <= 1:
                raise ValueError(f"{name} must be in (0, 1]")
        for name, value in (
            ("residual_threshold", residual_threshold),
            ("omission_threshold", omission_threshold),
            ("similarity_scale", similarity_scale),
            ("adaptation_weight", adaptation_weight),
            ("omission_weight", omission_weight),
        ):
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if similarity_scale == 0:
            raise ValueError("similarity_scale must be positive")
        self.prediction_alpha = prediction_alpha
        self.adaptation_alpha = adaptation_alpha
        self.residual_threshold = residual_threshold
        self.omission_threshold = omission_threshold
        self.similarity_scale = similarity_scale
        self.adaptation_weight = adaptation_weight
        self.omission_weight = omission_weight
        self.prediction = 0.0
        self.adaptation = 0.0
        self.has_prediction = False

    def process(self, observation: SpectralObservation, *, precision: float = 1.0) -> PredictiveTritFrame:
        """Advance one typed observation and return its dual-trit route state."""

        if not math.isfinite(precision) or not 0 <= precision <= 1:
            raise ValueError("precision must be in [0, 1]")
        if observation.status in (ObservationStatus.MISSING, ObservationStatus.TOO_SHORT):
            return PredictiveTritFrame(
                status=observation.status,
                state=DualTernaryState(0, 0),
                observed=None,
                predicted=self.prediction if self.has_prediction else None,
                residual=None,
                adaptation=self.adaptation,
                precision=precision,
                omission=False,
                route_score=0.0,
            )

        observed = float(observation.score)
        predicted = self.prediction if self.has_prediction else observed
        residual = observed - predicted
        omission = (
            observation.status is ObservationStatus.SILENT
            and self.has_prediction
            and abs(predicted) > self.omission_threshold
        )
        if self.has_prediction:
            similarity = math.exp(-abs(residual) / self.similarity_scale)
            self.adaptation = (1 - self.adaptation_alpha) * self.adaptation + self.adaptation_alpha * similarity
        primary = _trit(residual, self.residual_threshold)
        mirror = -1 if omission else (1 if observation.status is ObservationStatus.OBSERVED else 0)
        route_score = (
            precision * abs(residual)
            - self.adaptation_weight * self.adaptation
            + self.omission_weight * float(omission)
        )
        self.prediction = (
            observed
            if not self.has_prediction
            else (1 - self.prediction_alpha) * self.prediction + self.prediction_alpha * observed
        )
        self.has_prediction = True
        return PredictiveTritFrame(
            status=observation.status,
            state=DualTernaryState(primary, mirror),
            observed=observed,
            predicted=predicted,
            residual=residual,
            adaptation=self.adaptation,
            precision=precision,
            omission=omission,
            route_score=route_score,
        )


__all__ = ["PredictiveSensoryTritRouter", "PredictiveTritFrame"]
