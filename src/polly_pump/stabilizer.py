from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from src.polly_pump.packet import ModalityProfile, PumpPacket, TONGUE_ORDER


@dataclass
class PumpStabilizer:
    active_threshold: float = 0.12
    retrieval_gain: float = 0.35
    null_gain: float = 0.55

    def normalize_tongues(self, profile: Mapping[str, float] | Sequence[float]) -> tuple[float, ...]:
        packet = PumpPacket.from_inputs(
            tongue_profile=profile,
            null_pattern=(0, 0, 0, 0, 0, 0),
            governance_posture="bootstrap",
            routing_hint="bootstrap",
            modality=ModalityProfile(),
        )
        return packet.tongue_profile

    def infer_null_pattern(self, profile: Mapping[str, float] | Sequence[float]) -> tuple[int, ...]:
        normalized = self.normalize_tongues(profile)
        return tuple(1 if value < self.active_threshold else 0 for value in normalized)

    def compute_null_pressure(self, profile: Mapping[str, float] | Sequence[float]) -> float:
        normalized = self.normalize_tongues(profile)
        deficiency = [max(0.0, self.active_threshold - value) / self.active_threshold for value in normalized]
        return sum(deficiency) / len(deficiency)

    def compute_harmony(
        self,
        profile: Mapping[str, float] | Sequence[float],
        modality: ModalityProfile,
        retrieval_density: float,
    ) -> float:
        normalized = self.normalize_tongues(profile)
        active_ratio = sum(1 for value in normalized if value >= self.active_threshold) / len(TONGUE_ORDER)
        modality_score = modality.coverage()
        null_pressure = self.compute_null_pressure(normalized)
        harmony = (
            0.45 * active_ratio
            + 0.25 * modality_score
            + self.retrieval_gain * max(0.0, min(1.0, retrieval_density))
            - self.null_gain * null_pressure
        )
        return max(0.0, min(1.0, harmony))

    def build_packet(
        self,
        profile: Mapping[str, float] | Sequence[float],
        governance_posture: str,
        routing_hint: str,
        modality: ModalityProfile,
        retrieval_density: float = 0.0,
        state21_projection: Sequence[float] | None = None,
    ) -> PumpPacket:
        null_pattern = self.infer_null_pattern(profile)
        null_pressure = self.compute_null_pressure(profile)
        return PumpPacket.from_inputs(
            tongue_profile=profile,
            null_pattern=null_pattern,
            governance_posture=governance_posture,
            routing_hint=routing_hint,
            modality=modality,
            retrieval_density=retrieval_density,
            null_pressure=null_pressure,
            state21_projection=state21_projection,
        )
