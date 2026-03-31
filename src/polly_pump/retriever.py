"""Bundle retrieval for the Polly pump.

Ranks candidate memory bundles against a sensed ``PumpPacket`` using a small,
deterministic score composed from tongue-profile proximity plus canon/null-state
compatibility. This is the first runtime bridge between packet sensing and
response composition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence

import numpy as np

from .packet import PumpPacket


def _normalize_profile(values: Sequence[float]) -> np.ndarray:
    arr = np.asarray(list(values), dtype=np.float64)
    if arr.shape != (6,):
        raise ValueError(f"Expected 6 tongue dimensions, got shape {arr.shape}")
    return arr


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _null_similarity(packet_pattern: str, bundle_pattern: str) -> float:
    if not packet_pattern or not bundle_pattern:
        return 0.0
    if len(packet_pattern) != len(bundle_pattern):
        return 0.0
    matches = sum(1 for left, right in zip(packet_pattern, bundle_pattern) if left == right)
    return matches / len(packet_pattern)


@dataclass
class RetrievedBundle:
    """A memory/aquifer bundle ranked against a ``PumpPacket``."""

    bundle_id: str
    text: str
    tongue_profile: List[float]
    canon: str = "general"
    emotion: str = "neutral"
    governance: str = "ALLOW"
    null_pattern: str = "######"
    source_root: str = ""
    tags: List[str] = field(default_factory=list)
    score: float = 0.0

    def scored(self, score: float) -> "RetrievedBundle":
        clone = RetrievedBundle(
            bundle_id=self.bundle_id,
            text=self.text,
            tongue_profile=list(self.tongue_profile),
            canon=self.canon,
            emotion=self.emotion,
            governance=self.governance,
            null_pattern=self.null_pattern,
            source_root=self.source_root,
            tags=list(self.tags),
            score=score,
        )
        return clone


class BundleRetriever:
    """Rank bundles in the aquifer against an incoming ``PumpPacket``."""

    def __init__(self, aquifer: Iterable[RetrievedBundle]):
        self._aquifer = list(aquifer)

    @property
    def aquifer(self) -> List[RetrievedBundle]:
        return list(self._aquifer)

    def score_bundle(self, packet: PumpPacket, bundle: RetrievedBundle) -> float:
        packet_profile = _normalize_profile(packet.tongue_profile)
        bundle_profile = _normalize_profile(bundle.tongue_profile)

        similarity = _cosine_similarity(packet_profile, bundle_profile)
        null_match = _null_similarity(packet.null_pattern, bundle.null_pattern)
        canon_match = 1.0 if packet.canon == bundle.canon else 0.0
        emotion_match = 1.0 if packet.emotion == bundle.emotion else 0.0
        governance_match = 1.0 if packet.governance == bundle.governance else 0.0

        # Keep the score deterministic and interpretable.
        score = (
            0.55 * similarity
            + 0.20 * null_match
            + 0.15 * canon_match
            + 0.05 * emotion_match
            + 0.05 * governance_match
        )
        return round(score, 6)

    def retrieve(self, packet: PumpPacket, top_k: int = 5) -> List[RetrievedBundle]:
        ranked = [bundle.scored(self.score_bundle(packet, bundle)) for bundle in self._aquifer]
        ranked.sort(key=lambda bundle: bundle.score, reverse=True)
        return ranked[: max(top_k, 0)]
