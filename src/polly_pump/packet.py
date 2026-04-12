from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


TONGUE_ORDER = ("KO", "AV", "RU", "CA", "UM", "DR")


def _coerce_six(values: Mapping[str, float] | Sequence[float]) -> tuple[float, ...]:
    if isinstance(values, Mapping):
        raw = [float(values.get(tongue, 0.0)) for tongue in TONGUE_ORDER]
    else:
        raw = [float(value) for value in values]
    if len(raw) != 6:
        raise ValueError(f"Expected 6 tongue values, got {len(raw)}")
    if any(value < 0.0 for value in raw):
        raise ValueError("Tongue values must be non-negative")
    total = sum(raw)
    if total <= 0.0:
        raise ValueError("Tongue values must sum to a positive number")
    return tuple(value / total for value in raw)


@dataclass(frozen=True)
class ModalityProfile:
    visual: float = 0.0
    audio: float = 0.0
    empirical: float = 0.0

    def normalized(self) -> "ModalityProfile":
        values = [max(0.0, float(self.visual)), max(0.0, float(self.audio)), max(0.0, float(self.empirical))]
        total = sum(values)
        if total <= 0.0:
            return ModalityProfile(0.0, 0.0, 0.0)
        return ModalityProfile(*(value / total for value in values))

    def coverage(self) -> float:
        normalized = self.normalized()
        return max(normalized.visual, normalized.audio, normalized.empirical)


@dataclass(frozen=True)
class PumpPacket:
    tongue_profile: tuple[float, ...]
    null_pattern: tuple[int, ...]
    governance_posture: str
    routing_hint: str
    modality: ModalityProfile
    retrieval_density: float = 0.0
    null_pressure: float = 0.0
    state21_projection: tuple[float, ...] | None = None

    @classmethod
    def from_inputs(
        cls,
        tongue_profile: Mapping[str, float] | Sequence[float],
        null_pattern: Sequence[int],
        governance_posture: str,
        routing_hint: str,
        modality: ModalityProfile,
        retrieval_density: float = 0.0,
        null_pressure: float = 0.0,
        state21_projection: Sequence[float] | None = None,
    ) -> "PumpPacket":
        profile = _coerce_six(tongue_profile)
        pattern = tuple(int(bool(value)) for value in null_pattern)
        if len(pattern) != 6:
            raise ValueError(f"Expected 6 null-pattern values, got {len(pattern)}")
        if state21_projection is not None:
            projection = tuple(float(value) for value in state21_projection)
        else:
            projection = None
        return cls(
            tongue_profile=profile,
            null_pattern=pattern,
            governance_posture=governance_posture.strip(),
            routing_hint=routing_hint.strip(),
            modality=modality.normalized(),
            retrieval_density=max(0.0, min(1.0, float(retrieval_density))),
            null_pressure=max(0.0, min(1.0, float(null_pressure))),
            state21_projection=projection,
        )

    def active_tongues(self, threshold: float = 0.12) -> int:
        return sum(1 for value in self.tongue_profile if value >= threshold)

