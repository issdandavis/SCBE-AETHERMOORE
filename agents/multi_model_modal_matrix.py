"""
Multi-Model Modal Matrix reducer.

Implements the N-model x K-modality object described in
docs/research/MULTI_MODEL_MODAL_MATRIX.md with deterministic signals and a
reliability-weighted decision reducer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal
import math


Decision = Literal["ALLOW", "QUARANTINE", "DENY"]


def _clamp01(x: float) -> float:
    if not math.isfinite(x):
        return 0.0
    return min(1.0, max(0.0, x))


@dataclass(frozen=True)
class MatrixCell:
    model_id: str
    modality_id: str
    prediction: Decision
    confidence: float
    latency_ms: float
    drift: float
    risk: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MatrixDecision:
    decision: Decision
    confidence: float
    support: dict[str, float]
    signals: dict[str, Any]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MultiModelModalMatrix:
    """
    Reducer for multi-model modal decisions.

    Cell:
      (prediction, confidence, latency_ms, drift, risk)
    """

    def __init__(self) -> None:
        self._cells: list[MatrixCell] = []
        self._prev_confidence: dict[tuple[str, str], float] = {}

    def clear(self) -> None:
        self._cells.clear()

    @property
    def cells(self) -> tuple[MatrixCell, ...]:
        return tuple(self._cells)

    def ingest(
        self,
        *,
        model_id: str,
        modality_id: str,
        prediction: Decision,
        confidence: float,
        latency_ms: float,
        risk: float,
    ) -> MatrixCell:
        if prediction not in {"ALLOW", "QUARANTINE", "DENY"}:
            raise ValueError(f"invalid prediction: {prediction}")
        key = (str(model_id), str(modality_id))
        prev = self._prev_confidence.get(key, _clamp01(confidence))
        conf = _clamp01(confidence)
        drift = _clamp01(abs(conf - prev))
        cell = MatrixCell(
            model_id=str(model_id),
            modality_id=str(modality_id),
            prediction=prediction,
            confidence=conf,
            latency_ms=max(0.0, float(latency_ms)),
            drift=drift,
            risk=_clamp01(risk),
        )
        self._cells.append(cell)
        self._prev_confidence[key] = conf
        return cell

    def derive_signals(self) -> dict[str, Any]:
        if not self._cells:
            return {
                "agreement_by_modality": {},
                "overall_agreement": 0.0,
                "reliability_by_model": {},
                "cross_model_drift": 0.0,
                "conflict_mass": 1.0,
            }

        by_modality: dict[str, list[MatrixCell]] = {}
        by_model: dict[str, list[MatrixCell]] = {}
        for c in self._cells:
            by_modality.setdefault(c.modality_id, []).append(c)
            by_model.setdefault(c.model_id, []).append(c)

        agreement_by_modality: dict[str, float] = {}
        for modality, cells in by_modality.items():
            counts = {"ALLOW": 0, "QUARANTINE": 0, "DENY": 0}
            for c in cells:
                counts[c.prediction] += 1
            best = max(counts.values())
            agreement_by_modality[modality] = round(best / max(1, len(cells)), 6)

        overall_agreement = sum(agreement_by_modality.values()) / max(1, len(agreement_by_modality))

        reliability_by_model: dict[str, float] = {}
        for model_id, cells in by_model.items():
            mean_conf = sum(c.confidence for c in cells) / len(cells)
            mean_risk = sum(c.risk for c in cells) / len(cells)
            mean_latency = sum(c.latency_ms for c in cells) / len(cells)
            latency_factor = 1.0 / (1.0 + (mean_latency / 4000.0))
            reliability = _clamp01(mean_conf * (1.0 - mean_risk) * latency_factor)
            reliability_by_model[model_id] = round(reliability, 6)

        cross_model_drift = sum(c.drift for c in self._cells) / len(self._cells)
        conflict_mass = 1.0 - _clamp01(overall_agreement)

        return {
            "agreement_by_modality": agreement_by_modality,
            "overall_agreement": round(overall_agreement, 6),
            "reliability_by_model": reliability_by_model,
            "cross_model_drift": round(cross_model_drift, 6),
            "conflict_mass": round(conflict_mass, 6),
        }

    def reduce(self) -> MatrixDecision:
        if not self._cells:
            raise ValueError("cannot reduce empty matrix")

        signals = self.derive_signals()
        reliability = signals["reliability_by_model"]
        support_raw = {"ALLOW": 0.0, "QUARANTINE": 0.0, "DENY": 0.0}

        for c in self._cells:
            rel = float(reliability.get(c.model_id, 0.5))
            weight = rel * c.confidence * (1.0 - c.risk)
            support_raw[c.prediction] += weight

        total = sum(support_raw.values())
        if total <= 1e-12:
            support = {"ALLOW": 0.0, "QUARANTINE": 0.0, "DENY": 1.0}
            decision: Decision = "DENY"
            confidence = 0.0
            rationale = "no reliable support; fail closed"
            return MatrixDecision(
                decision=decision,
                confidence=confidence,
                support=support,
                signals=signals,
                rationale=rationale,
            )

        support = {k: round(v / total, 6) for k, v in support_raw.items()}
        best = max(support.items(), key=lambda kv: kv[1])
        best_decision = best[0]
        base_conf = float(best[1])

        conflict_mass = float(signals["conflict_mass"])
        drift = float(signals["cross_model_drift"])
        penalty = _clamp01(0.65 * conflict_mass + 0.35 * drift)
        confidence = round(_clamp01(base_conf * (1.0 - penalty)), 6)

        if best_decision == "DENY" or penalty >= 0.75:
            decision = "DENY"
            rationale = f"deny due to best={best_decision}, penalty={penalty:.3f}"
        elif best_decision == "QUARANTINE" or confidence < 0.55:
            decision = "QUARANTINE"
            rationale = f"quarantine due to best={best_decision}, confidence={confidence:.3f}"
        else:
            decision = "ALLOW"
            rationale = f"allow with confidence={confidence:.3f}"

        return MatrixDecision(
            decision=decision,
            confidence=confidence,
            support=support,
            signals=signals,
            rationale=rationale,
        )

